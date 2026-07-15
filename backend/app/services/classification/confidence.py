"""Confidence scoring logic for classification results.

Defines thresholds, combines multi-signal scores, and determines
whether manual review is needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ConfidenceLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"


# Thresholds for pipeline decision-making
RULE_ACCEPT_THRESHOLD = 0.90
ML_ACCEPT_THRESHOLD = 0.70
LLM_ACCEPT_THRESHOLD = 0.60
MANUAL_REVIEW_THRESHOLD = 0.50


@dataclass
class ClassificationResult:
    """Result of a classification attempt from any tier."""

    category: str
    subcategory: Optional[str] = None
    merchant: Optional[str] = None
    confidence: float = 0.0
    source: str = "unknown"
    needs_review: bool = False
    reasoning: Optional[str] = None

    @property
    def confidence_level(self) -> ConfidenceLevel:
        if self.confidence >= 0.85:
            return ConfidenceLevel.HIGH
        elif self.confidence >= 0.65:
            return ConfidenceLevel.MEDIUM
        elif self.confidence >= 0.45:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "subcategory": self.subcategory,
            "merchant": self.merchant,
            "confidence": round(self.confidence, 4),
            "confidence_level": self.confidence_level.value,
            "source": self.source,
            "needs_review": self.needs_review,
            "reasoning": self.reasoning,
        }


def compute_rule_confidence(
    pattern_matched: bool,
    keyword_matched: bool,
    amount_range_typical: bool = True,
) -> float:
    """Compute confidence for rule-based classification.

    A direct pattern match (merchant name regex) gives high confidence.
    Keyword-only matches are slightly lower. Amount typicality is a minor boost.
    """
    if pattern_matched:
        base = 0.95
    elif keyword_matched:
        base = 0.80
    else:
        return 0.0

    if amount_range_typical:
        base = min(base + 0.03, 1.0)

    return base


def compute_ml_confidence(
    top_score: float,
    second_score: float,
    num_labels: int = 15,
) -> float:
    """Compute adjusted confidence for ML zero-shot results.

    Uses the gap between top and second scores as a signal of certainty.
    A large gap means the model is decisive; a small gap means ambiguity.
    """
    gap = top_score - second_score
    random_baseline = 1.0 / num_labels

    if top_score < random_baseline * 1.5:
        return 0.3

    gap_bonus = min(gap * 0.5, 0.15)
    adjusted = top_score * 0.85 + gap_bonus

    return min(max(adjusted, 0.0), 1.0)


def compute_llm_confidence(
    llm_reported_confidence: float,
    response_valid_json: bool = True,
    category_in_taxonomy: bool = True,
) -> float:
    """Compute adjusted confidence for LLM results.

    Penalizes if the response wasn't valid JSON or category is unknown.
    LLM self-reported confidence is discounted slightly (models overconfident).
    """
    base = llm_reported_confidence * 0.85

    if not response_valid_json:
        base *= 0.6
    if not category_in_taxonomy:
        base *= 0.7

    return min(max(base, 0.0), 1.0)


def should_escalate_to_ml(result: ClassificationResult) -> bool:
    """Determine if the rule engine result warrants ML escalation."""
    return result.confidence < RULE_ACCEPT_THRESHOLD


def should_escalate_to_llm(result: ClassificationResult) -> bool:
    """Determine if the ML result warrants LLM escalation."""
    return result.confidence < ML_ACCEPT_THRESHOLD


def needs_manual_review(result: ClassificationResult) -> bool:
    """Flag results that should be presented to the user for confirmation."""
    return result.confidence < MANUAL_REVIEW_THRESHOLD
