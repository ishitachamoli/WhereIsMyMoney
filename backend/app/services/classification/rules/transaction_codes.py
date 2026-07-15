"""Bank-specific transaction code patterns and prefixes.

Indian banks use specific prefixes and codes in transaction descriptions:
- POS: Point of Sale (card swipe)
- UPI: Unified Payments Interface
- NEFT: National Electronic Funds Transfer
- RTGS: Real Time Gross Settlement
- IMPS: Immediate Payment Service
- ECS: Electronic Clearing Service
- NACH: National Automated Clearing House
- ATM: Automated Teller Machine
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TransactionCodeInfo:
    transaction_type: str
    is_debit: bool
    description_hint: str


# Common transaction code prefixes across Indian banks
TRANSACTION_CODE_PATTERNS: dict[str, re.Pattern] = {
    "pos": re.compile(
        r"^POS\s+(\d{4,6})\s+(.+?)(?:\s+\d{2}/\d{2})?$",
        re.IGNORECASE,
    ),
    "upi_credit": re.compile(
        r"^UPI[-/]CR[-/](\d+)[-/]([^/]+?)[-/]([^/]+?)[-/]",
        re.IGNORECASE,
    ),
    "upi_debit": re.compile(
        r"^UPI[-/]DR[-/](\d+)[-/]([^/]+?)[-/]([^/]+?)[-/]",
        re.IGNORECASE,
    ),
    "upi_generic": re.compile(
        r"^UPI[-/]([^/]+?)[-/]([^/]+?)(?:[-/]|$)",
        re.IGNORECASE,
    ),
    "neft_credit": re.compile(
        r"^NEFT[-/\s]*CR[-/\s]*([A-Z0-9]+)[-/\s]*([^/]+?)(?:[-/]|$)",
        re.IGNORECASE,
    ),
    "neft_debit": re.compile(
        r"^NEFT[-/\s]*DR[-/\s]*([A-Z0-9]+)[-/\s]*([^/]+?)(?:[-/]|$)",
        re.IGNORECASE,
    ),
    "neft_generic": re.compile(
        r"^NEFT[-/\s]+([A-Z0-9]+)[-/\s]+(.+?)(?:\s+\d|$)",
        re.IGNORECASE,
    ),
    "rtgs": re.compile(
        r"^RTGS[-/\s]*([A-Z0-9]+)[-/\s]*(.+?)(?:\s+\d|$)",
        re.IGNORECASE,
    ),
    "imps": re.compile(
        r"^IMPS[-/\s]*([A-Z0-9]+)[-/\s]*(.+?)(?:\s+\d|$)",
        re.IGNORECASE,
    ),
    "ecs": re.compile(
        r"^(?:ECS|NACH)[-/\s]*(.+?)(?:\s+\d|$)",
        re.IGNORECASE,
    ),
    "atm_withdrawal": re.compile(
        r"^(?:ATM[-/\s]*(?:WDL|WITHDRAWAL|CASH)|NFS[-/\s]*ATM|CASH\s*WDL)",
        re.IGNORECASE,
    ),
    "card_payment": re.compile(
        r"^(?:VISA|MASTERCARD|RUPAY|MC)\s*\d{4,6}\s+(.+)",
        re.IGNORECASE,
    ),
    "international": re.compile(
        r"^(?:INTL|INTERNATIONAL|FOREIGN)\s+(.+)",
        re.IGNORECASE,
    ),
    "standing_instruction": re.compile(
        r"^(?:SI|STANDING\s*INSTRUCTION|AUTO\s*DEBIT)[-/\s]*(.+)",
        re.IGNORECASE,
    ),
}

# Bank-specific IFSC code patterns for identifying source/destination banks
BANK_IFSC_PREFIXES: dict[str, str] = {
    "HDFC": "HDFC Bank",
    "ICIC": "ICICI Bank",
    "SBIN": "State Bank of India",
    "UTIB": "Axis Bank",
    "KKBK": "Kotak Mahindra Bank",
    "PUNB": "Punjab National Bank",
    "BARB": "Bank of Baroda",
    "CNRB": "Canara Bank",
    "UBIN": "Union Bank",
    "IDFB": "IDFC First Bank",
    "YESB": "Yes Bank",
    "INDB": "IndusInd Bank",
    "FDRL": "Federal Bank",
    "ALLA": "Allahabad Bank",
    "BKID": "Bank of India",
    "CORP": "Union Bank (erstwhile Corp Bank)",
    "RATN": "RBL Bank",
    "MAHB": "Bank of Maharashtra",
}


def parse_transaction_code(description: str) -> Optional[TransactionCodeInfo]:
    """Parse a transaction description to extract the code type and details.

    Returns None if no known transaction code pattern is found.
    """
    description = description.strip()

    if TRANSACTION_CODE_PATTERNS["pos"].match(description):
        return TransactionCodeInfo("POS", is_debit=True, description_hint="Card payment at merchant")

    if TRANSACTION_CODE_PATTERNS["upi_credit"].match(description):
        return TransactionCodeInfo("UPI_CREDIT", is_debit=False, description_hint="UPI money received")

    if TRANSACTION_CODE_PATTERNS["upi_debit"].match(description):
        return TransactionCodeInfo("UPI_DEBIT", is_debit=True, description_hint="UPI payment sent")

    if TRANSACTION_CODE_PATTERNS["upi_generic"].match(description):
        return TransactionCodeInfo("UPI", is_debit=True, description_hint="UPI transaction")

    if TRANSACTION_CODE_PATTERNS["neft_credit"].match(description):
        return TransactionCodeInfo("NEFT_CREDIT", is_debit=False, description_hint="NEFT received")

    if TRANSACTION_CODE_PATTERNS["neft_debit"].match(description):
        return TransactionCodeInfo("NEFT_DEBIT", is_debit=True, description_hint="NEFT sent")

    if TRANSACTION_CODE_PATTERNS["neft_generic"].match(description):
        return TransactionCodeInfo("NEFT", is_debit=True, description_hint="NEFT transfer")

    if TRANSACTION_CODE_PATTERNS["rtgs"].match(description):
        return TransactionCodeInfo("RTGS", is_debit=True, description_hint="RTGS transfer")

    if TRANSACTION_CODE_PATTERNS["imps"].match(description):
        return TransactionCodeInfo("IMPS", is_debit=True, description_hint="IMPS transfer")

    if TRANSACTION_CODE_PATTERNS["ecs"].match(description):
        return TransactionCodeInfo("ECS", is_debit=True, description_hint="Auto-debit/mandate")

    if TRANSACTION_CODE_PATTERNS["atm_withdrawal"].match(description):
        return TransactionCodeInfo("ATM", is_debit=True, description_hint="ATM cash withdrawal")

    if TRANSACTION_CODE_PATTERNS["card_payment"].match(description):
        return TransactionCodeInfo("CARD", is_debit=True, description_hint="Card payment")

    if TRANSACTION_CODE_PATTERNS["standing_instruction"].match(description):
        return TransactionCodeInfo("SI", is_debit=True, description_hint="Standing instruction/auto-pay")

    return None


def extract_counterparty_from_code(description: str) -> Optional[str]:
    """Extract the counterparty (merchant/person) from transaction code patterns.

    For UPI transactions: extracts the VPA or name
    For NEFT/RTGS/IMPS: extracts the beneficiary name
    For POS: extracts the merchant name after the terminal ID
    """
    description = description.strip()

    # POS: "POS 423456 SWIGGY BANGALORE"
    m = TRANSACTION_CODE_PATTERNS["pos"].match(description)
    if m:
        return m.group(2).strip()

    # UPI debit: "UPI/DR/123456/PayeeName/PayeeVPA/..."
    m = TRANSACTION_CODE_PATTERNS["upi_debit"].match(description)
    if m:
        return m.group(2).strip()

    # UPI credit: "UPI/CR/123456/PayerName/PayerVPA/..."
    m = TRANSACTION_CODE_PATTERNS["upi_credit"].match(description)
    if m:
        return m.group(2).strip()

    # UPI generic: "UPI-PayeeName-PayeeVPA"
    m = TRANSACTION_CODE_PATTERNS["upi_generic"].match(description)
    if m:
        return m.group(1).strip()

    # NEFT: "NEFT-HDFC0001234-JOHN DOE"
    for key in ("neft_credit", "neft_debit", "neft_generic"):
        m = TRANSACTION_CODE_PATTERNS[key].match(description)
        if m:
            return m.group(2).strip()

    # RTGS / IMPS
    for key in ("rtgs", "imps"):
        m = TRANSACTION_CODE_PATTERNS[key].match(description)
        if m:
            return m.group(2).strip()

    # Card payment: "VISA 4567 AMAZON INDIA"
    m = TRANSACTION_CODE_PATTERNS["card_payment"].match(description)
    if m:
        return m.group(1).strip()

    return None


def identify_bank_from_ifsc(ifsc_or_description: str) -> Optional[str]:
    """Identify the bank name from IFSC code prefix in descriptions."""
    text = ifsc_or_description.upper()
    for prefix, bank_name in BANK_IFSC_PREFIXES.items():
        if prefix in text:
            return bank_name
    return None
