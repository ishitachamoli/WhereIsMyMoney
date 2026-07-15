"""Service for managing user-learned classification rules.

When users reclassify transactions, the system extracts merchant/keyword patterns
and stores them as learned rules. These rules take highest priority in the
classification pipeline.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from sqlalchemy.orm import Session

from app.models.learned_rule import LearnedRule

logger = logging.getLogger(__name__)

# Common noise words to strip when extracting patterns
NOISE_WORDS = {
    "pos", "upi", "neft", "imps", "rtgs", "atm", "ach",
    "ref", "no", "txn", "transaction", "payment", "transfer",
    "debit", "credit", "card", "ending", "from", "to", "for",
    "the", "and", "via", "by", "on", "at", "in", "of",
}

# Regex to remove reference numbers, dates, amounts
NOISE_PATTERNS = [
    r"\b\d{6,}\b",         # long numbers (ref numbers, card numbers)
    r"\b\d{2}[/-]\d{2}[/-]\d{2,4}\b",  # dates
    r"\bINR\s*[\d,.]+\b",  # amounts
    r"\b₹\s*[\d,.]+\b",
    r"\bRS\.?\s*[\d,.]+\b",
    r"\b\d{4}\b",          # 4-digit numbers (card last 4, etc.)
]


def extract_merchant_pattern(description: str) -> Optional[str]:
    """Extract the meaningful merchant/keyword pattern from a transaction description.

    Args:
        description: Raw transaction description from bank statement.

    Returns:
        Cleaned pattern string, or None if no meaningful pattern can be extracted.
    """
    if not description:
        return None

    text = description.lower().strip()

    # Remove noise patterns (numbers, dates, amounts)
    for pattern in NOISE_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    # Split into words and filter noise
    words = [w.strip() for w in re.split(r"[\s/\-_@.]+", text) if w.strip()]
    meaningful = [w for w in words if w not in NOISE_WORDS and len(w) > 1]

    if not meaningful:
        return None

    # Take the first 3 meaningful words as the pattern
    pattern = " ".join(meaningful[:3]).strip()

    # Must be at least 3 chars to be useful
    if len(pattern) < 3:
        return None

    return pattern


def create_learned_rule(
    db: Session,
    user_id: int,
    description: str,
    category_name: str,
) -> Optional[LearnedRule]:
    """Create or update a learned rule from a user correction.

    If a rule with the same pattern already exists for the user, update it.
    Otherwise, create a new rule.

    Args:
        db: Database session.
        user_id: The user who made the correction.
        description: The transaction description to extract pattern from.
        category_name: The correct category assigned by the user.

    Returns:
        The created/updated LearnedRule, or None if no pattern could be extracted.
    """
    pattern = extract_merchant_pattern(description)
    if not pattern:
        return None

    # Check if rule already exists for this user + pattern
    existing = (
        db.query(LearnedRule)
        .filter(
            LearnedRule.user_id == user_id,
            LearnedRule.pattern == pattern,
        )
        .first()
    )

    if existing:
        existing.category_name = category_name
        existing.hit_count += 1
        existing.confidence = 1.0
        db.commit()
        db.refresh(existing)
        logger.info(
            "Updated learned rule: '%s' → %s (hits: %d)",
            pattern, category_name, existing.hit_count,
        )
        return existing

    rule = LearnedRule(
        user_id=user_id,
        pattern=pattern,
        category_name=category_name,
        confidence=1.0,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    logger.info("Created learned rule: '%s' → %s", pattern, category_name)
    return rule


def match_learned_rules(
    db: Session,
    user_id: int,
    description: str,
) -> Optional[tuple[str, float]]:
    """Check if a transaction description matches any learned rules for the user.

    Args:
        db: Database session.
        user_id: The user whose rules to check.
        description: The transaction description to match.

    Returns:
        Tuple of (category_name, confidence) if matched, None otherwise.
    """
    rules = (
        db.query(LearnedRule)
        .filter(LearnedRule.user_id == user_id)
        .order_by(LearnedRule.hit_count.desc())
        .all()
    )

    if not rules:
        return None

    desc_lower = description.lower()

    for rule in rules:
        if rule.pattern in desc_lower:
            return (rule.category_name, rule.confidence)

    return None


def get_user_rules(db: Session, user_id: int) -> list[LearnedRule]:
    """Get all learned rules for a user."""
    return (
        db.query(LearnedRule)
        .filter(LearnedRule.user_id == user_id)
        .order_by(LearnedRule.hit_count.desc())
        .all()
    )
