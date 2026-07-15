"""Tier 2: Zero-shot classification using HuggingFace transformers.

Uses valhalla/distilbart-mnli-12-3 for zero-shot classification when rule-based
matching fails or has low confidence. The model is loaded ONCE as a module-level
singleton and shared across all MLClassifier instances.

Performance note: The HuggingFace ZeroShotClassificationPipeline does NOT truly
batch across input texts — it iterates texts one at a time internally. For batch
classification, we bypass the pipeline and run NLI pairs directly through the
model in real batches, achieving 50-200x speedup on multi-text workloads.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import numpy as np

from app.services.classification.categories import CategoryTaxonomy
from app.services.classification.confidence import (
    ClassificationResult,
    compute_ml_confidence,
)

logger = logging.getLogger(__name__)


def _tune_torch_threads() -> None:
    """Tune CPU thread counts for inference once, at module import time.

    No-op on GPU. m6a.large has 2 vCPUs; default torch on CPU may not use all
    cores efficiently, so we set them explicitly. ``set_num_interop_threads``
    MUST be called before any other torch ops, so it is wrapped in try/except —
    if torch was already initialized elsewhere we log a warning rather than crash.
    ``set_num_threads`` always works and is applied regardless.
    """
    import os

    import torch

    cpu_count = os.cpu_count() or 2
    interop = min(cpu_count, 2)

    torch.set_num_threads(cpu_count)
    try:
        torch.set_num_interop_threads(interop)
    except Exception as e:  # torch already initialized — non-fatal
        logger.warning("Could not set torch interop threads (already initialized?): %s", e)

    logger.info(
        "PyTorch threads tuned: num_threads=%d, num_interop_threads=%d",
        cpu_count, interop,
    )


try:
    _tune_torch_threads()
except Exception as e:  # torch unavailable — model load will handle gracefully
    logger.warning("Skipped torch thread tuning (torch unavailable?): %s", e)

# ─── Module-level singletons for HuggingFace model ───────────────────────────
_pipeline_singleton = None
_model_singleton = None
_tokenizer_singleton = None
_pipeline_lock = threading.Lock()
_pipeline_load_failed = False


def get_pipeline(model_name: str = "valhalla/distilbart-mnli-12-3", device: int = -1):
    """Get or create the singleton ML pipeline.

    Thread-safe double-checked locking ensures the model loads exactly once,
    regardless of how many MLClassifier instances or threads call this.

    Args:
        model_name: HuggingFace model identifier.
        device: -1 for CPU, >= 0 for GPU index.

    Returns:
        The HuggingFace zero-shot-classification pipeline, or None if loading failed.
    """
    global _pipeline_singleton, _pipeline_load_failed, _model_singleton, _tokenizer_singleton

    if _pipeline_singleton is not None:
        return _pipeline_singleton

    if _pipeline_load_failed:
        return None

    with _pipeline_lock:
        if _pipeline_singleton is not None:
            return _pipeline_singleton
        if _pipeline_load_failed:
            return None

        try:
            from transformers import pipeline as hf_pipeline

            kwargs: dict = {
                "model": model_name,
                "device": device,
            }

            if device >= 0:
                try:
                    import torch
                    kwargs["torch_dtype"] = torch.float16
                except ImportError:
                    pass

            logger.info("Loading zero-shot classification model (one-time): %s", model_name)
            start = time.time()
            _pipeline_singleton = hf_pipeline("zero-shot-classification", **kwargs)
            _model_singleton = _pipeline_singleton.model
            _tokenizer_singleton = _pipeline_singleton.tokenizer
            logger.info("ML model loaded in %.1fs", time.time() - start)
        except Exception as e:
            logger.warning("ML model failed to load (will use rules only): %s", e)
            _pipeline_load_failed = True
            return None

    return _pipeline_singleton


def get_model_and_tokenizer(model_name: str = "valhalla/distilbart-mnli-12-3", device: int = -1):
    """Get the underlying model and tokenizer for direct inference.

    Returns:
        Tuple of (model, tokenizer), or (None, None) if loading failed.
    """
    get_pipeline(model_name, device)
    return _model_singleton, _tokenizer_singleton

# Candidate labels for zero-shot classification (must be natural language)
CANDIDATE_LABELS = [
    "food and dining at restaurants or food delivery",
    "transportation including fuel, cabs, and flights",
    "online or offline shopping and retail purchases",
    "entertainment including movies, streaming, and gaming",
    "healthcare including pharmacy, hospital, and doctor",
    "utility bills like electricity, water, internet, and mobile",
    "bills, fees, insurance, EMI, and loan payments",
    "education including courses, school, and coaching fees",
    "personal care including salon, spa, and grooming",
    "home expenses like rent, maintenance, and repairs",
    "income including salary, refund, and interest",
    "money transfers via UPI, NEFT, RTGS, or IMPS",
    "investments in mutual funds, stocks, or fixed deposits",
    "cash withdrawal from ATM",
    "other miscellaneous expenses",
]

# Map from zero-shot label index to category name
LABEL_TO_CATEGORY: dict[int, str] = {
    0: "Food & Dining",
    1: "Transportation",
    2: "Shopping",
    3: "Entertainment",
    4: "Healthcare",
    5: "Utilities",
    6: "Bills & Fees",
    7: "Education",
    8: "Personal Care",
    9: "Home",
    10: "Income",
    11: "Transfers",
    12: "Investments",
    13: "Cash",
    14: "Other",
}

CATEGORY_TO_LABEL_IDX: dict[str, int] = {v: k for k, v in LABEL_TO_CATEGORY.items()}

# Internal batching: how many (text, label) NLI pairs to process per forward pass.
# For direct model inference, this controls the actual batch of tokenized pairs.
# On CPU with 8GB RAM (shared by postgres/frontend/nginx/backend/torch),
# 16 keeps peak activation memory low to avoid swap; CPU batches don't scale
# linearly anyway, so the throughput hit from 32→16 is modest.
_NLI_BATCH_SIZE = 16

# External chunk size: how many texts to send per pipeline call (for single-item fallback).
_CHUNK_SIZE = 128

# NLI hypothesis template for zero-shot classification
_NLI_HYPOTHESIS_TEMPLATE = "This example is {}."


class MLClassifier:
    """Zero-shot classifier using DistilBART (or BART-large) for NLI.

    Uses the module-level singleton pipeline (via get_pipeline()) so the model
    loads exactly ONCE regardless of how many MLClassifier instances exist.

    For batch inference, bypasses the HuggingFace ZeroShotClassificationPipeline
    (which iterates texts one-at-a-time internally) and directly tokenizes all
    (premise, hypothesis) NLI pairs, running them through the model in real batches.
    This provides 50-200x speedup for multi-text workloads.
    """

    def __init__(self, model_name: str = "valhalla/distilbart-mnli-12-3", device: int = -1):
        self._model_name = model_name
        self._device = device
        self._taxonomy = CategoryTaxonomy()

    @property
    def pipeline(self):
        """Access the singleton pipeline, triggering lazy-load if needed."""
        return get_pipeline(model_name=self._model_name, device=self._device)

    @property
    def is_loaded(self) -> bool:
        return _pipeline_singleton is not None

    @property
    def is_available(self) -> bool:
        if _pipeline_load_failed:
            return False
        return True

    def classify(
        self,
        description: str,
        amount: Optional[float] = None,
        transaction_type: Optional[str] = None,
    ) -> ClassificationResult:
        """Classify a transaction using zero-shot inference.

        Args:
            description: Transaction description text.
            amount: Transaction amount (used as context hint).
            transaction_type: 'debit' or 'credit' hint.

        Returns:
            ClassificationResult with category and confidence.
        """
        if not self.is_available:
            return ClassificationResult(
                category="Other",
                subcategory="Uncategorized",
                confidence=0.0,
                source="ml_classifier",
                needs_review=True,
                reasoning="ML model not available",
            )

        pipe = self.pipeline
        if pipe is None:
            return ClassificationResult(
                category="Other",
                subcategory="Uncategorized",
                confidence=0.0,
                source="ml_classifier",
                needs_review=True,
                reasoning="ML model failed to load",
            )

        input_text = self._build_input_text(description, amount, transaction_type)

        try:
            result = pipe(
                input_text,
                CANDIDATE_LABELS,
                multi_label=False,
                batch_size=_NLI_BATCH_SIZE,
                truncation=True,
            )
        except Exception as e:
            logger.error("ML inference error: %s", e)
            return ClassificationResult(
                category="Other",
                subcategory="Uncategorized",
                confidence=0.0,
                source="ml_classifier",
                needs_review=True,
                reasoning=f"Inference error: {str(e)[:100]}",
            )

        top_label_idx = CANDIDATE_LABELS.index(result["labels"][0])
        top_score = result["scores"][0]
        second_score = result["scores"][1] if len(result["scores"]) > 1 else 0.0

        category = LABEL_TO_CATEGORY.get(top_label_idx, "Other")
        confidence = compute_ml_confidence(top_score, second_score, len(CANDIDATE_LABELS))

        return ClassificationResult(
            category=category,
            subcategory=None,
            merchant=None,
            confidence=confidence,
            source="ml_classifier",
            needs_review=confidence < 0.70,
            reasoning=f"Zero-shot: '{result['labels'][0][:40]}' (raw={top_score:.3f})",
        )

    def classify_batch(
        self,
        descriptions: list[str],
        amounts: Optional[list[Optional[float]]] = None,
    ) -> list[ClassificationResult]:
        """Classify multiple transactions with TRUE cross-text batching.

        Bypasses the HuggingFace ZeroShotClassificationPipeline (which processes
        texts one-at-a-time internally despite accepting a list) and instead:
        1. Tokenizes ALL (premise, hypothesis) NLI pairs across all texts at once
        2. Runs them through the model in real batches of _NLI_BATCH_SIZE pairs
        3. Reshapes logits to (num_texts, num_labels) and applies softmax

        This achieves 50-200x speedup vs the HF pipeline for multi-text workloads.

        Args:
            descriptions: List of transaction descriptions.
            amounts: Optional list of amounts corresponding to descriptions.

        Returns:
            List of ClassificationResults in the same order.
        """
        if not descriptions:
            return []

        fallback = ClassificationResult(
            category="Other",
            subcategory="Uncategorized",
            confidence=0.0,
            source="ml_classifier",
            needs_review=True,
            reasoning="ML model not available",
        )

        if not self.is_available:
            return [fallback for _ in descriptions]

        model, tokenizer = get_model_and_tokenizer(self._model_name, self._device)
        if model is None or tokenizer is None:
            return [fallback for _ in descriptions]

        input_texts = []
        for i, desc in enumerate(descriptions):
            amt = amounts[i] if amounts and i < len(amounts) else None
            input_texts.append(self._build_input_text(desc, amt, None))

        try:
            t0 = time.perf_counter()
            results = self._batch_nli_inference(input_texts, model, tokenizer)
            elapsed = time.perf_counter() - t0

            logger.info(
                "ML batch classification: %d transactions in %.1fs (%.0f ms/tx)",
                len(input_texts), elapsed, (elapsed / max(len(input_texts), 1)) * 1000,
            )
            return results

        except Exception as e:
            logger.error("Batch ML inference error (falling back to sequential): %s", e)
            return self._classify_batch_sequential_fallback(input_texts)

    def _batch_nli_inference(
        self,
        input_texts: list[str],
        model,
        tokenizer,
    ) -> list[ClassificationResult]:
        """Run true batched NLI inference across all texts × all labels.

        Constructs all (premise, hypothesis) pairs, tokenizes them together,
        runs the model in real batches, and extracts entailment scores.
        """
        import torch

        num_texts = len(input_texts)
        num_labels = len(CANDIDATE_LABELS)
        total_pairs = num_texts * num_labels

        hypotheses = [_NLI_HYPOTHESIS_TEMPLATE.format(label) for label in CANDIDATE_LABELS]

        # Build all (premise, hypothesis) pairs: text_0×label_0, text_0×label_1, ..., text_N×label_M
        premises = []
        hyps = []
        for text in input_texts:
            for h in hypotheses:
                premises.append(text)
                hyps.append(h)

        logger.info(
            "Direct NLI batching: %d texts × %d labels = %d pairs (batch_size=%d)",
            num_texts, num_labels, total_pairs, _NLI_BATCH_SIZE,
        )

        # Process NLI pairs in real batches through the model
        all_entailment_scores = np.zeros(total_pairs, dtype=np.float32)
        model.eval()

        # Determine the entailment index from the model config
        entail_idx = self._get_entailment_index(model)

        with torch.no_grad():
            for batch_start in range(0, total_pairs, _NLI_BATCH_SIZE):
                batch_end = min(batch_start + _NLI_BATCH_SIZE, total_pairs)
                batch_premises = premises[batch_start:batch_end]
                batch_hyps = hyps[batch_start:batch_end]

                encodings = tokenizer(
                    batch_premises,
                    batch_hyps,
                    return_tensors="pt",
                    padding=True,
                    truncation=True,
                    # Bank transaction descriptions are short (~10-20 tokens). 64
                    # covers ~99% of cases (incl. longer transfer/invoice memos)
                    # while avoiding the wasted padding/compute of max_length=256.
                    max_length=64,
                )

                device = next(model.parameters()).device
                encodings = {k: v.to(device) for k, v in encodings.items()}

                outputs = model(**encodings)
                logits = outputs.logits.cpu().numpy()

                # Extract entailment scores (softmax over [contradiction, neutral, entailment])
                # For each pair, the entailment logit is our "match score"
                exp_logits = np.exp(logits - logits.max(axis=1, keepdims=True))
                probs = exp_logits / exp_logits.sum(axis=1, keepdims=True)
                all_entailment_scores[batch_start:batch_end] = probs[:, entail_idx]

        # Reshape to (num_texts, num_labels) and extract top results
        scores_matrix = all_entailment_scores.reshape(num_texts, num_labels)

        results: list[ClassificationResult] = []
        for i in range(num_texts):
            text_scores = scores_matrix[i]
            # Normalize scores to sum to 1 (like the HF pipeline does)
            text_scores_normalized = text_scores / text_scores.sum()
            sorted_indices = np.argsort(text_scores_normalized)[::-1]

            top_idx = sorted_indices[0]
            top_score = float(text_scores_normalized[top_idx])
            second_score = float(text_scores_normalized[sorted_indices[1]]) if num_labels > 1 else 0.0

            category = LABEL_TO_CATEGORY.get(top_idx, "Other")
            confidence = compute_ml_confidence(top_score, second_score, num_labels)

            results.append(ClassificationResult(
                category=category,
                subcategory=None,
                merchant=None,
                confidence=confidence,
                source="ml_classifier",
                needs_review=confidence < 0.70,
                reasoning=f"Zero-shot: '{CANDIDATE_LABELS[top_idx][:40]}' (raw={top_score:.3f})",
            ))

        return results

    def _get_entailment_index(self, model) -> int:
        """Determine which output index corresponds to 'entailment' in the NLI model."""
        if hasattr(model, "config") and hasattr(model.config, "label2id"):
            label2id = model.config.label2id
            # Common label names for entailment
            for key in ("entailment", "ENTAILMENT", "Entailment"):
                if key in label2id:
                    return label2id[key]
        # Default: DistilBART-MNLI uses index 2 for entailment
        return 2

    def _classify_batch_sequential_fallback(
        self,
        input_texts: list[str],
    ) -> list[ClassificationResult]:
        """Fallback: use HF pipeline one text at a time if direct inference fails."""
        pipe = self.pipeline
        if pipe is None:
            return [
                ClassificationResult(
                    category="Other", subcategory="Uncategorized", confidence=0.0,
                    source="ml_classifier", needs_review=True, reasoning="ML model failed to load",
                )
                for _ in input_texts
            ]

        results: list[ClassificationResult] = []
        t0 = time.perf_counter()

        for text in input_texts:
            try:
                result = pipe(text, CANDIDATE_LABELS, multi_label=False, truncation=True)
                top_label_idx = CANDIDATE_LABELS.index(result["labels"][0])
                top_score = result["scores"][0]
                second_score = result["scores"][1] if len(result["scores"]) > 1 else 0.0
                category = LABEL_TO_CATEGORY.get(top_label_idx, "Other")
                confidence = compute_ml_confidence(top_score, second_score, len(CANDIDATE_LABELS))
                results.append(ClassificationResult(
                    category=category, subcategory=None, merchant=None,
                    confidence=confidence, source="ml_classifier",
                    needs_review=confidence < 0.70,
                    reasoning=f"Zero-shot: '{result['labels'][0][:40]}' (raw={top_score:.3f})",
                ))
            except Exception as e:
                logger.error("Sequential fallback inference error: %s", e)
                results.append(ClassificationResult(
                    category="Other", subcategory="Uncategorized", confidence=0.0,
                    source="ml_classifier", needs_review=True,
                    reasoning=f"Inference error: {str(e)[:50]}",
                ))

        elapsed = time.perf_counter() - t0
        logger.warning(
            "ML batch classification (SEQUENTIAL FALLBACK): %d transactions in %.1fs (%.0f ms/tx)",
            len(input_texts), elapsed, (elapsed / max(len(input_texts), 1)) * 1000,
        )
        return results

    def _build_input_text(
        self,
        description: str,
        amount: Optional[float],
        transaction_type: Optional[str],
    ) -> str:
        """Build enriched input text for the model."""
        parts = [description]
        if amount is not None:
            direction = "received" if amount > 0 else "paid"
            parts.append(f"Amount: {abs(amount):.2f} INR ({direction})")
        if transaction_type:
            parts.append(f"Type: {transaction_type}")
        return " | ".join(parts)
