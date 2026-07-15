"""Extract merchant/recipient information from raw bank transaction descriptions.

This module provides simple, straightforward extraction of merchant/recipient
information from bank transaction descriptions. Rather than attempting complex
regex parsing that tends to truncate or distort the original text, this module
returns the full cleaned description as-is.

The philosophy: The complete transaction description usually provides the most
useful information to the user. Attempting to extract a "short merchant name"
via regex patterns often loses important context and produces worse results
than showing the full text.
"""
from __future__ import annotations


def extract_merchant(description: str) -> str:
    """Extract and clean merchant/recipient information from transaction description.

    Performs minimal cleaning:
    - Removes encoding artifacts (Ê, É, È characters from cp1252)
    - Strips leading/trailing whitespace and dashes
    - Returns the full cleaned description

    Args:
        description: Raw transaction description from bank statement.

    Returns:
        Cleaned full description, or "Unknown" if empty/invalid.

    Example:
        >>> extract_merchant("BY TRANSFER-IMPS/534205572617/RE1-XX389-VISA PAY/RDA Vostr")
        'BY TRANSFER-IMPS/534205572617/RE1-XX389-VISA PAY/RDA Vostr'

        >>> extract_merchant("TO TRANSFER-UPI/DR/533849077740/Google I/UTIB/gpay-utili/UPI")
        'TO TRANSFER-UPI/DR/533849077740/Google I/UTIB/gpay-utili/UPI'

        >>> extract_merchant("")
        'Unknown'
    """
    if not description:
        return "Unknown"

    # Clean encoding artifacts (0xCA=Ê, 0xC9=É, 0xC8=È in cp1252)
    cleaned = description.replace("Ê", "").replace("É", "").replace("È", "")
    cleaned = cleaned.strip()

    # Remove leading/trailing dashes
    cleaned = cleaned.strip("-").strip()

    # Return cleaned description or "Unknown" if empty
    return cleaned if cleaned else "Unknown"
