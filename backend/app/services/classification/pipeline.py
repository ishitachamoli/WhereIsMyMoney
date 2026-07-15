"""Classification pipeline orchestrator.

Implements the four-tier architecture:
  Tier 0: User Learned Rules (from corrections, highest priority)
  Tier 1: Rule Engine (fast regex, <1ms)
  Tier 2: ML Zero-shot (HuggingFace, 50-200ms)
  Tier 3: LLM via Ollama (100-300ms, optional)

Escalates to the next tier only when confidence is below threshold.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from app.services.classification.confidence import (
    ClassificationResult,
    RULE_ACCEPT_THRESHOLD,
    ML_ACCEPT_THRESHOLD,
    needs_manual_review,
    should_escalate_to_llm,
    should_escalate_to_ml,
)
from app.services.classification.llm_classifier import LLMClassifier
from app.services.classification.ml_classifier import MLClassifier
from app.services.classification.rule_engine import RuleEngine

logger = logging.getLogger(__name__)


@dataclass
class PipelineStats:
    """Tracks classification pipeline performance metrics."""

    total_classified: int = 0
    rule_hits: int = 0
    ml_hits: int = 0
    llm_hits: int = 0
    unclassified: int = 0
    total_latency_ms: float = 0.0
    feedback_corrections: int = 0

    @property
    def rule_hit_rate(self) -> float:
        if self.total_classified == 0:
            return 0.0
        return self.rule_hits / self.total_classified

    @property
    def ml_hit_rate(self) -> float:
        if self.total_classified == 0:
            return 0.0
        return self.ml_hits / self.total_classified

    @property
    def llm_hit_rate(self) -> float:
        if self.total_classified == 0:
            return 0.0
        return self.llm_hits / self.total_classified

    @property
    def avg_latency_ms(self) -> float:
        if self.total_classified == 0:
            return 0.0
        return self.total_latency_ms / self.total_classified

    @property
    def accuracy_estimate(self) -> float:
        """Estimated accuracy based on tier distribution and corrections."""
        if self.total_classified == 0:
            return 0.0
        correct = self.total_classified - self.feedback_corrections
        return correct / self.total_classified

    def to_dict(self) -> dict:
        return {
            "total_classified": self.total_classified,
            "rule_hits": self.rule_hits,
            "ml_hits": self.ml_hits,
            "llm_hits": self.llm_hits,
            "unclassified": self.unclassified,
            "rule_hit_rate": round(self.rule_hit_rate, 4),
            "ml_hit_rate": round(self.ml_hit_rate, 4),
            "llm_hit_rate": round(self.llm_hit_rate, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "accuracy_estimate": round(self.accuracy_estimate, 4),
            "feedback_corrections": self.feedback_corrections,
        }


@dataclass
class PipelineConfig:
    """Configuration for the classification pipeline."""

    enable_ml: bool = True
    enable_llm: bool = False
    rule_threshold: float = RULE_ACCEPT_THRESHOLD
    ml_threshold: float = ML_ACCEPT_THRESHOLD
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_timeout: float = 30.0
    ml_model_name: str = "valhalla/distilbart-mnli-12-3"
    ml_device: int = -1


class ClassificationPipeline:
    """Orchestrates multi-tier transaction classification.

    Usage:
        pipeline = ClassificationPipeline()
        result = pipeline.classify("POS 423456 SWIGGY BANGALORE", amount=-450.0)
        print(result.category, result.confidence)
    """

    def __init__(self, config: Optional[PipelineConfig] = None):
        self._config = config or PipelineConfig()
        self._rule_engine = RuleEngine()
        self._ml_classifier: Optional[MLClassifier] = None
        self._llm_classifier: Optional[LLMClassifier] = None
        self._stats = PipelineStats()

        if self._config.enable_ml:
            self._ml_classifier = MLClassifier(
                model_name=self._config.ml_model_name,
                device=self._config.ml_device,
            )
        if self._config.enable_llm:
            self._llm_classifier = LLMClassifier(
                base_url=self._config.ollama_base_url,
                model=self._config.ollama_model,
                timeout=self._config.ollama_timeout,
            )

    @property
    def stats(self) -> PipelineStats:
        return self._stats

    def classify(
        self,
        description: str,
        amount: Optional[float] = None,
        transaction_type: Optional[str] = None,
        db=None,
        user_id: Optional[int] = None,
    ) -> ClassificationResult:
        """Classify a single transaction through the tiered pipeline.

        Args:
            description: Raw transaction description from bank statement.
            amount: Transaction amount. Positive=credit, negative=debit.
            transaction_type: Optional explicit 'debit'/'credit' hint.
            db: Optional SQLAlchemy session for learned rules lookup.
            user_id: Optional user ID for learned rules lookup.

        Returns:
            ClassificationResult with category, confidence, source, and metadata.
        """
        start = time.perf_counter()

        # TIER 0: User Learned Rules (highest priority)
        if db is not None and user_id is not None:
            from app.services.classification.learned_rules import match_learned_rules
            match = match_learned_rules(db, user_id, description)
            if match:
                category_name, confidence = match
                self._record_hit("rule", start)
                return ClassificationResult(
                    category=category_name,
                    subcategory=None,
                    merchant=None,
                    confidence=confidence,
                    source="learned_rule",
                    needs_review=False,
                    reasoning=f"Matched user learned rule",
                )

        # TIER 1: Rule Engine
        result = self._rule_engine.classify(description, amount, transaction_type)
        if result.confidence >= self._config.rule_threshold:
            self._record_hit("rule", start)
            return result

        # TIER 2: ML Zero-shot
        if self._ml_classifier and self._ml_classifier.is_available and should_escalate_to_ml(result):
            ml_result = self._ml_classifier.classify(description, amount, transaction_type)
            if ml_result.confidence >= self._config.ml_threshold:
                # Preserve merchant from rules if ML doesn't find one
                if result.merchant and not ml_result.merchant:
                    ml_result.merchant = result.merchant
                self._record_hit("ml", start)
                return ml_result

            # If ML result is better than rules but below threshold, keep it for LLM comparison
            if ml_result.confidence > result.confidence:
                result = ml_result

        # TIER 3: LLM (Ollama)
        if self._llm_classifier and self._llm_classifier.is_available and should_escalate_to_llm(result):
            llm_result = self._llm_classifier.classify(description, amount, transaction_type)
            if llm_result.confidence > result.confidence:
                # Preserve merchant if LLM doesn't extract one
                if result.merchant and not llm_result.merchant:
                    llm_result.merchant = result.merchant
                self._record_hit("llm", start)
                return llm_result

        # Nothing confident enough — return best we have
        result.needs_review = needs_manual_review(result)
        self._record_hit("unclassified" if result.confidence == 0.0 else "rule", start)
        return result

    def classify_batch(
        self,
        transactions: list[dict],
        db=None,
        user_id: Optional[int] = None,
    ) -> list[ClassificationResult]:
        """Classify multiple transactions.

        Each transaction dict should have at minimum:
          - description: str
        Optional:
          - amount: float
          - transaction_type: str

        Args:
            transactions: List of transaction dicts.
            db: Optional SQLAlchemy session for learned rules lookup.
            user_id: Optional user ID for learned rules lookup.

        Returns:
            List of ClassificationResults in same order.
        """
        results: list[ClassificationResult] = []
        needs_ml: list[tuple[int, dict]] = []

        # TIER 0: Check learned rules first
        learned_rule_matches: set[int] = set()
        if db is not None and user_id is not None:
            from app.services.classification.learned_rules import match_learned_rules
            for i, tx in enumerate(transactions):
                desc = tx.get("description", "")
                match = match_learned_rules(db, user_id, desc)
                if match:
                    category_name, confidence = match
                    results.append(ClassificationResult(
                        category=category_name,
                        subcategory=None,
                        merchant=None,
                        confidence=confidence,
                        source="learned_rule",
                        needs_review=False,
                        reasoning="Matched user learned rule",
                    ))
                    learned_rule_matches.add(i)
                    self._stats.rule_hits += 1
                else:
                    results.append(None)  # type: ignore
            # Fill in None entries with rule engine results
            for i, tx in enumerate(transactions):
                if i in learned_rule_matches:
                    continue
                desc = tx.get("description", "")
                amount = tx.get("amount")
                tx_type = tx.get("transaction_type")
                result = self._rule_engine.classify(desc, amount, tx_type)
                results[i] = result
                if result.confidence < self._config.rule_threshold:
                    needs_ml.append((i, tx))
                else:
                    self._stats.rule_hits += 1
        else:
            # No learned rules — original path
            for i, tx in enumerate(transactions):
                desc = tx.get("description", "")
                amount = tx.get("amount")
                tx_type = tx.get("transaction_type")
                result = self._rule_engine.classify(desc, amount, tx_type)
                results.append(result)
                if result.confidence < self._config.rule_threshold:
                    needs_ml.append((i, tx))
                else:
                    self._stats.rule_hits += 1

        # Second pass: batch ML for remaining
        if needs_ml and self._ml_classifier and self._ml_classifier.is_available:
            ml_descriptions = [tx["description"] for _, tx in needs_ml]
            ml_amounts = [tx.get("amount") for _, tx in needs_ml]
            ml_results = self._ml_classifier.classify_batch(ml_descriptions, ml_amounts)

            needs_llm: list[tuple[int, dict]] = []
            for (orig_idx, tx), ml_result in zip(needs_ml, ml_results):
                if ml_result.confidence >= self._config.ml_threshold:
                    if results[orig_idx].merchant and not ml_result.merchant:
                        ml_result.merchant = results[orig_idx].merchant
                    results[orig_idx] = ml_result
                    self._stats.ml_hits += 1
                else:
                    if ml_result.confidence > results[orig_idx].confidence:
                        results[orig_idx] = ml_result
                    needs_llm.append((orig_idx, tx))
        else:
            needs_llm = needs_ml

        # Third pass: LLM for remaining (one-by-one, LLM doesn't batch well)
        if needs_llm and self._llm_classifier and self._llm_classifier.is_available:
            for orig_idx, tx in needs_llm:
                llm_result = self._llm_classifier.classify(
                    tx["description"],
                    tx.get("amount"),
                    tx.get("transaction_type"),
                )
                if llm_result.confidence > results[orig_idx].confidence:
                    if results[orig_idx].merchant and not llm_result.merchant:
                        llm_result.merchant = results[orig_idx].merchant
                    results[orig_idx] = llm_result
                    self._stats.llm_hits += 1

        # Final pass: mark review needed
        for r in results:
            r.needs_review = needs_manual_review(r)

        self._stats.total_classified += len(transactions)
        return results

    def record_feedback_correction(self) -> None:
        """Record that a user corrected a classification."""
        self._stats.feedback_corrections += 1

    def _record_hit(self, tier: str, start_time: float) -> None:
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        self._stats.total_classified += 1
        self._stats.total_latency_ms += elapsed_ms

        if tier == "rule":
            self._stats.rule_hits += 1
        elif tier == "ml":
            self._stats.ml_hits += 1
        elif tier == "llm":
            self._stats.llm_hits += 1
        else:
            self._stats.unclassified += 1
