"""AI-powered transaction explanation service.

Extracts structured information from raw bank transaction descriptions using
pattern matching to identify payment methods, recipients/senders, reference
numbers, and generates human-readable explanations.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from app.services.classification.rules.merchant_patterns import (
    MERCHANT_PATTERNS,
    extract_merchant_name,
)
from app.services.classification.rules.transaction_codes import (
    BANK_IFSC_PREFIXES,
    parse_transaction_code,
)
from app.services.currency_helper import get_currency_symbol


@dataclass
class TransactionExplanation:
    """Structured explanation of a bank transaction."""

    explanation: str
    recipient_or_sender: Optional[str] = None
    payment_method: Optional[str] = None
    reference: Optional[str] = None
    category_suggestion: Optional[str] = None
    confidence: float = 0.5
    direction: Optional[str] = None
    card_reference: Optional[str] = None
    service: Optional[str] = None


# Direction indicators in Indian bank descriptions
_DIRECTION_PATTERNS = {
    "incoming": re.compile(
        r"\b(BY\s+TRANSFER|CR|CREDIT|RECEIVED|INWARD|SALARY|SAL\s*CR)\b",
        re.IGNORECASE,
    ),
    "outgoing": re.compile(
        r"\b(TO\s+TRANSFER|DR|DEBIT|PAID|OUTWARD|PAYMENT)\b",
        re.IGNORECASE,
    ),
}

# Payment method extraction
_PAYMENT_METHOD_PATTERN = re.compile(
    r"\b(UPI|NEFT|RTGS|IMPS|POS|ECS|NACH|ATM|VISA|MASTERCARD|RUPAY)\b",
    re.IGNORECASE,
)

# Reference number: 10-18 digit sequences
_REFERENCE_PATTERN = re.compile(r"\b(\d{10,18})\b")

# Masked card reference: XX followed by 3-4 digits
_CARD_REF_PATTERN = re.compile(r"\b(XX\d{3,4}|X{4}\d{4}|\*{4}\d{4})\b", re.IGNORECASE)

# UPI VPA pattern
_UPI_VPA_PATTERN = re.compile(r"([a-zA-Z0-9._-]+@[a-zA-Z]+)")

# Service provider from descriptions (e.g., "VISA PAY", "Google Pay")
_SERVICE_PATTERN = re.compile(
    r"\b(VISA\s*PAY|GOOGLE\s*PAY|GPAY|PHONEPE|PAYTM|BHIM|CRED|WHATSAPP\s*PAY|SAMSUNG\s*PAY)\b",
    re.IGNORECASE,
)

# IFSC code pattern
_IFSC_PATTERN = re.compile(r"\b([A-Z]{4}0[A-Z0-9]{6})\b")


def _extract_direction(description: str, transaction_type: Optional[str]) -> str:
    """Determine if money is incoming or outgoing."""
    if transaction_type == "credit":
        return "incoming"
    if transaction_type == "debit":
        return "outgoing"

    for direction, pattern in _DIRECTION_PATTERNS.items():
        if pattern.search(description):
            return direction

    return "unknown"


def _extract_payment_method(description: str) -> Optional[str]:
    """Extract the payment method from the description."""
    match = _PAYMENT_METHOD_PATTERN.search(description)
    if match:
        method = match.group(1).upper()
        if method in ("VISA", "MASTERCARD", "RUPAY"):
            return f"Card ({method})"
        return method
    return None


def _extract_reference(description: str) -> Optional[str]:
    """Extract reference/transaction number."""
    match = _REFERENCE_PATTERN.search(description)
    return match.group(1) if match else None


def _extract_card_reference(description: str) -> Optional[str]:
    """Extract masked card number reference."""
    match = _CARD_REF_PATTERN.search(description)
    return match.group(1) if match else None


def _extract_service(description: str) -> Optional[str]:
    """Extract payment service provider."""
    match = _SERVICE_PATTERN.search(description)
    if match:
        raw = match.group(1).strip()
        service_map = {
            "VISA PAY": "Visa Direct",
            "GOOGLE PAY": "Google Pay",
            "GPAY": "Google Pay",
            "PHONEPE": "PhonePe",
            "PAYTM": "Paytm",
            "BHIM": "BHIM UPI",
            "CRED": "CRED",
            "WHATSAPP PAY": "WhatsApp Pay",
            "SAMSUNG PAY": "Samsung Pay",
        }
        return service_map.get(raw.upper(), raw.title())
    return None


def _extract_recipient_from_segments(description: str) -> Optional[str]:
    """Extract recipient/sender by analyzing slash-separated segments."""
    parts = re.split(r"[/]", description)
    if len(parts) < 2:
        return None

    # The last meaningful segment is often the counterparty
    candidates = []
    for part in reversed(parts):
        cleaned = part.strip()
        if not cleaned:
            continue
        # Skip pure numbers (references)
        if re.match(r"^\d+$", cleaned):
            continue
        # Skip payment method keywords
        if re.match(
            r"^(UPI|NEFT|RTGS|IMPS|POS|DR|CR|DEBIT|CREDIT|BY\s*TRANSFER|TO\s*TRANSFER)$",
            cleaned,
            re.IGNORECASE,
        ):
            continue
        # Skip IFSC-like codes
        if re.match(r"^[A-Z]{4}0[A-Z0-9]{6}$", cleaned):
            continue
        # Skip card/ref patterns
        if re.match(r"^(RE\d|XX\d|X{4})", cleaned, re.IGNORECASE):
            continue
        candidates.append(cleaned)

    if candidates:
        # Prefer shorter, name-like candidates; the last segment is usually the name
        best = candidates[0]
        # If it looks like a service+name combo, try to split
        if len(best) > 3 and not re.match(r"^\d", best):
            return best.strip()

    return None


def _extract_bank_name(description: str) -> Optional[str]:
    """Extract bank name from IFSC prefix in description."""
    ifsc_match = _IFSC_PATTERN.search(description)
    if ifsc_match:
        prefix = ifsc_match.group(1)[:4]
        if prefix in BANK_IFSC_PREFIXES:
            return BANK_IFSC_PREFIXES[prefix]

    # Also check for 4-char IFSC prefixes embedded in segments
    for prefix, bank_name in BANK_IFSC_PREFIXES.items():
        if f"/{prefix}" in description.upper() or f"-{prefix}" in description.upper():
            return bank_name

    return None


def _get_category_from_patterns(description: str) -> Optional[str]:
    """Use merchant patterns to suggest a category."""
    cleaned = description.upper().strip()
    for pattern, category, _subcategory in MERCHANT_PATTERNS:
        if pattern.search(cleaned):
            return category
    return None


def _generate_explanation(
    description: str,
    amount: Optional[float],
    transaction_type: Optional[str],
    date: Optional[str],
    direction: str,
    payment_method: Optional[str],
    recipient: Optional[str],
    reference: Optional[str],
    service: Optional[str],
    bank_name: Optional[str],
    currency_symbol: str = "₹",
) -> str:
    """Generate a human-readable explanation of the transaction."""
    parts = []

    # Direction phrase
    if direction == "incoming":
        if amount:
            parts.append(f"This was a money transfer of {currency_symbol}{amount:,.0f} received")
        else:
            parts.append("This was a money transfer received")
    elif direction == "outgoing":
        if amount:
            parts.append(f"This was a payment of {currency_symbol}{amount:,.0f} sent")
        else:
            parts.append("This was a payment sent")
    else:
        if amount:
            parts.append(f"This was a transaction of {currency_symbol}{amount:,.0f}")
        else:
            parts.append("This was a transaction")

    # Payment method
    if payment_method:
        parts.append(f"via {payment_method}")

    # Recipient/sender
    if recipient:
        word = "from" if direction == "incoming" else "to"
        parts.append(f"{word} {recipient}")

    # Date
    if date:
        parts.append(f"on {date}")

    explanation = " ".join(parts) + "."

    # Additional context
    extras = []
    if service:
        extras.append(f"Payment processed through {service}.")
    if bank_name:
        if direction == "incoming":
            extras.append(f"Sender's bank: {bank_name}.")
        else:
            extras.append(f"Beneficiary bank: {bank_name}.")
    if reference:
        extras.append(f"Reference: {reference}.")

    if extras:
        explanation += " " + " ".join(extras)

    return explanation


def explain_transaction(
    description: str,
    amount: Optional[float] = None,
    transaction_type: Optional[str] = None,
    date: Optional[str] = None,
    category: Optional[str] = None,
    currency: str = "INR",
) -> TransactionExplanation:
    """Analyze a transaction description and return a structured explanation.

    Args:
        description: Raw bank transaction description.
        amount: Transaction amount (positive value).
        transaction_type: 'debit' or 'credit'.
        date: Transaction date as string.
        category: Current category assigned to the transaction.

    Returns:
        TransactionExplanation with all extracted fields.
    """
    if not description:
        return TransactionExplanation(
            explanation="No description available for this transaction.",
            confidence=0.0,
        )

    direction = _extract_direction(description, transaction_type)
    payment_method = _extract_payment_method(description)
    reference = _extract_reference(description)
    card_ref = _extract_card_reference(description)
    service = _extract_service(description)
    bank_name = _extract_bank_name(description)

    # Try to find recipient using merchant patterns first
    recipient = None
    cleaned_upper = description.upper().strip()
    for pattern, _cat, _sub in MERCHANT_PATTERNS:
        match = pattern.search(cleaned_upper)
        if match:
            recipient = extract_merchant_name(description, match)
            break

    # Fall back to segment-based extraction
    if not recipient:
        recipient = _extract_recipient_from_segments(description)

    # Check UPI VPA
    vpa_match = _UPI_VPA_PATTERN.search(description)
    vpa = vpa_match.group(1) if vpa_match else None
    if not recipient and vpa:
        recipient = vpa

    # Get category suggestion from patterns
    category_suggestion = _get_category_from_patterns(description)
    if not category_suggestion and direction == "incoming":
        category_suggestion = "Income"
    if not category_suggestion and payment_method == "ATM":
        category_suggestion = "Cash"

    # Compute confidence based on how much info we extracted
    confidence = 0.3
    if payment_method:
        confidence += 0.15
    if recipient:
        confidence += 0.25
    if reference:
        confidence += 0.1
    if direction != "unknown":
        confidence += 0.1
    if category_suggestion:
        confidence += 0.1
    confidence = min(confidence, 0.95)

    explanation_text = _generate_explanation(
        description=description,
        amount=amount,
        transaction_type=transaction_type,
        date=date,
        direction=direction,
        payment_method=payment_method,
        recipient=recipient,
        reference=reference,
        service=service,
        bank_name=bank_name,
        currency_symbol=get_currency_symbol(currency),
    )

    return TransactionExplanation(
        explanation=explanation_text,
        recipient_or_sender=recipient,
        payment_method=payment_method,
        reference=reference,
        category_suggestion=category_suggestion,
        confidence=confidence,
        direction=direction,
        card_reference=card_ref,
        service=service,
    )
