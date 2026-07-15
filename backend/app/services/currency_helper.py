"""Currency helper utilities for formatting amounts with appropriate symbols."""
from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.transaction import Transaction


CURRENCY_SYMBOLS = {
    "INR": "₹",
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "JPY": "¥",
    "AUD": "$",
    "CAD": "$",
    "CHF": "CHF",
    "SEK": "kr",
    "NOK": "kr",
    "DKK": "kr",
    "PLN": "zł",
    "CZK": "Kč",
    "HUF": "Ft",
    "RON": "lei",
    "BGN": "лв",
    "HRK": "kn",
    "RSD": "дин.",
    "TRY": "₺",
    "BRL": "R$",
    "NZD": "$",
    "ZAR": "R",
    "SGD": "$",
    "HKD": "HK$",
    "CNY": "¥",
}


def get_dominant_currency(db: Session, user_id: int) -> str:
    """Return the most common currency in user's transactions.
    
    Args:
        db: Database session
        user_id: The user ID
        
    Returns:
        Currency code (e.g., 'INR', 'EUR', 'USD') with INR as default fallback
    """
    result = (
        db.query(
            Transaction.currency,
            func.count(Transaction.id).label("count"),
        )
        .filter(Transaction.user_id == user_id)
        .group_by(Transaction.currency)
        .order_by(desc("count"))
        .first()
    )
    
    if result and result.currency:
        return result.currency
    return "INR"


def get_currency_symbol(currency: str) -> str:
    """Get the symbol for a given currency code.
    
    Args:
        currency: ISO 4217 currency code (e.g., 'INR', 'EUR')
        
    Returns:
        Currency symbol or code as fallback
    """
    return CURRENCY_SYMBOLS.get(currency, currency)
