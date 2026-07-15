"""Tier 1: Rule-based classifier using regex patterns and keyword matching.

Handles 70-80% of transactions with high confidence (<1ms per transaction).
Uses merchant pattern matching first, then falls back to keyword matching
and transaction code analysis.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from app.services.classification.confidence import (
    ClassificationResult,
    compute_rule_confidence,
)
from app.services.classification.rules.keywords import (
    find_keyword_matches,
)
from app.services.classification.rules.merchant_patterns import (
    MERCHANT_PATTERNS,
    extract_merchant_name,
)
from app.services.classification.rules.transaction_codes import (
    extract_counterparty_from_code,
    parse_transaction_code,
)

logger = logging.getLogger(__name__)


def _clean_description(description: str) -> str:
    """Normalize transaction description for matching."""
    cleaned = description.upper().strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    # Remove common noise: dates, trailing numbers, reference IDs
    cleaned = re.sub(r"\b\d{2}/\d{2}/\d{2,4}\b", "", cleaned)
    cleaned = re.sub(r"\b\d{12,}\b", "", cleaned)
    return cleaned.strip()


class RuleEngine:
    """Regex-based transaction classifier for known merchants and patterns.

    Processes a transaction description through three stages:
    1. Merchant pattern matching (highest confidence)
    2. Transaction code parsing + counterparty extraction
    3. Keyword-based fallback matching
    """

    def classify(
        self,
        description: str,
        amount: Optional[float] = None,
        transaction_type: Optional[str] = None,
    ) -> ClassificationResult:
        """Classify a transaction using rule-based patterns.

        Args:
            description: Raw transaction description from bank statement.
            amount: Transaction amount (positive=credit, negative=debit).
            transaction_type: Optional hint ('debit' or 'credit').

        Returns:
            ClassificationResult with category, confidence, and metadata.
        """
        cleaned = _clean_description(description)

        # Stage 1: Direct merchant pattern matching
        result = self._match_merchant_patterns(cleaned, description)
        if result and result.confidence >= 0.85:
            return result

        # Stage 2: Transaction code parsing + re-classify counterparty
        code_info = parse_transaction_code(description)
        counterparty = extract_counterparty_from_code(description)

        if counterparty:
            counterparty_result = self._match_merchant_patterns(
                _clean_description(counterparty), counterparty
            )
            if counterparty_result and counterparty_result.confidence >= 0.85:
                counterparty_result.merchant = counterparty_result.merchant or counterparty.title()
                return counterparty_result

        # Stage 3: Keyword-based matching
        keyword_result = self._match_keywords(cleaned, description)

        # If we have both a weak merchant match and keyword match, combine
        if result and keyword_result:
            if keyword_result.confidence > result.confidence:
                keyword_result.merchant = result.merchant
                return keyword_result
            return result

        if result:
            return result
        if keyword_result:
            return keyword_result

        # Special handling: credit transactions with no match → Income or Transfer
        if amount is not None and amount > 0:
            if code_info and "CREDIT" in code_info.transaction_type:
                return ClassificationResult(
                    category="Income",
                    subcategory="Other",
                    merchant=counterparty,
                    confidence=0.4,
                    source="rule_engine",
                    needs_review=True,
                    reasoning="Credit transaction with no pattern match",
                )

        # Nothing matched
        return ClassificationResult(
            category="Other",
            subcategory="Uncategorized",
            merchant=counterparty,
            confidence=0.0,
            source="rule_engine",
            needs_review=True,
            reasoning="No rule matched",
        )

    def _match_merchant_patterns(
        self, cleaned: str, original: str
    ) -> Optional[ClassificationResult]:
        """Try all merchant regex patterns against the description."""
        for pattern, category, subcategory in MERCHANT_PATTERNS:
            match = pattern.search(cleaned)
            if match:
                merchant = extract_merchant_name(original, match)
                confidence = compute_rule_confidence(
                    pattern_matched=True,
                    keyword_matched=False,
                    amount_range_typical=True,
                )
                return ClassificationResult(
                    category=category,
                    subcategory=subcategory,
                    merchant=merchant,
                    confidence=confidence,
                    source="rule_engine",
                    needs_review=False,
                    reasoning=f"Matched pattern: {pattern.pattern[:50]}",
                )
        return None

    def _match_keywords(
        self, cleaned: str, original: str
    ) -> Optional[ClassificationResult]:
        """Try keyword matching as a fallback."""
        matches = find_keyword_matches(cleaned)
        if not matches:
            matches = find_keyword_matches(original)

        if not matches:
            return None

        best = matches[0]
        confidence = compute_rule_confidence(
            pattern_matched=False,
            keyword_matched=True,
            amount_range_typical=True,
        )
        # Scale by keyword weight
        confidence *= best.weight

        return ClassificationResult(
            category=best.category,
            subcategory=best.subcategory,
            merchant=None,
            confidence=confidence,
            source="rule_engine",
            needs_review=confidence < 0.75,
            reasoning=f"Keyword match: '{best.keyword}' (weight={best.weight})",
        )
