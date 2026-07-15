"""
Multi-bank statement parser supporting HDFC, ICICI, SBI, Axis, Kotak, and IDFC formats.
Handles both CSV and PDF file formats, auto-detects bank from file content,
and normalizes all formats to a common transaction schema.
"""
from __future__ import annotations

import pandas as pd
import pdfplumber
import io
import re
import logging
from datetime import datetime
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


def _decode_bytes_with_fallback(data: bytes) -> str:
    """Decode bytes trying UTF-8 first, then cp1252, then latin-1 as final fallback."""
    try:
        return data.decode("utf-8")
    except (UnicodeDecodeError, ValueError):
        pass
    try:
        return data.decode("utf-8-sig")
    except (UnicodeDecodeError, ValueError):
        pass
    try:
        return data.decode("cp1252")
    except (UnicodeDecodeError, ValueError):
        pass
    return data.decode("latin-1")


@dataclass
class ParsedTransaction:
    """Normalized transaction from any bank format."""
    date: datetime
    description: str
    amount: float
    transaction_type: str  # "debit" or "credit"
    balance: Optional[float] = None
    reference_number: Optional[str] = None
    bank_name: Optional[str] = None
    currency: str = "INR"


class BankDetectionError(Exception):
    pass


class ParsingError(Exception):
    pass


def detect_bank_from_csv(content: str, filename: str = "") -> str:
    """Detect bank from CSV content headers or filename patterns."""
    content_lower = content.lower()
    filename_lower = filename.lower()

    # Filename-based detection
    if "revolut" in filename_lower or "tanishq" in filename_lower:
        return "Revolut"
    if "hdfc" in filename_lower:
        return "HDFC"
    if "icici" in filename_lower:
        return "ICICI"
    if "sbi" in filename_lower:
        return "SBI"
    if "axis" in filename_lower:
        return "Axis"
    if "kotak" in filename_lower:
        return "Kotak"
    if "idfc" in filename_lower:
        return "IDFC"

    # Content-based detection via header patterns
    first_lines = content_lower[:2000]

    if "narration" in first_lines and "chq./ref.no." in first_lines:
        return "HDFC"
    if "transaction id" in first_lines and "value dat" in first_lines and "cr/dr" in first_lines:
        return "ICICI"
    if "txn date" in first_lines and "value date" in first_lines and "debit" in first_lines and "credit" in first_lines:
        # Could be SBI or generic
        if "sbi" in first_lines or "state bank" in first_lines:
            return "SBI"
        return "SBI"  # Default pattern match
    if "tran date" in first_lines and "particulars" in first_lines and "chq no" in first_lines:
        return "Axis"
    if "sl. no" in first_lines and "instrument" in first_lines and "dr / cr" in first_lines:
        return "Kotak"
    if "transaction date" in first_lines and "transaction remarks" in first_lines:
        if "idfc" in first_lines:
            return "IDFC"
        return "IDFC"  # IDFC pattern
    # Revolut pattern: Type, Product, Started Date, Completed Date, Description, Amount
    if "type" in first_lines and "product" in first_lines and "started date" in first_lines and "completed date" in first_lines:
        if "description" in first_lines and "amount" in first_lines and "currency" in first_lines:
            return "Revolut"

    raise BankDetectionError(
        f"Could not detect bank from file content. "
        f"Please rename the file with the bank name (e.g., hdfc_statement.csv)"
    )


def detect_bank_from_pdf(text: str, filename: str = "") -> str:
    """Detect bank from PDF text content or filename."""
    filename_lower = filename.lower()
    text_lower = text.lower()

    if "hdfc" in filename_lower or "hdfc bank" in text_lower:
        return "HDFC"
    if "icici" in filename_lower or "icici bank" in text_lower:
        return "ICICI"
    if "sbi" in filename_lower or "state bank of india" in text_lower:
        return "SBI"
    if "axis" in filename_lower or "axis bank" in text_lower:
        return "Axis"
    if "kotak" in filename_lower or "kotak mahindra" in text_lower:
        return "Kotak"
    if "idfc" in filename_lower or "idfc first" in text_lower:
        return "IDFC"

    raise BankDetectionError("Could not detect bank from PDF content or filename.")


def detect_bank_from_excel(df: pd.DataFrame, filename: str = "") -> str:
    """Detect bank from Excel column headers or filename patterns."""
    filename_lower = filename.lower()
    cols_lower = [str(col).lower() for col in df.columns]
    cols_str = " ".join(cols_lower)

    # Filename-based detection
    if "hdfc" in filename_lower:
        return "HDFC"
    if "icici" in filename_lower:
        return "ICICI"
    if "sbi" in filename_lower:
        return "SBI"
    if "axis" in filename_lower:
        return "Axis"
    if "kotak" in filename_lower:
        return "Kotak"
    if "idfc" in filename_lower:
        return "IDFC"

    # Column-based detection
    if "narration" in cols_str and "chq./ref.no." in cols_str:
        return "HDFC"
    if "transaction id" in cols_str and "cr/dr" in cols_str:
        return "ICICI"
    if "txn date" in cols_str and "debit" in cols_str and "credit" in cols_str:
        return "SBI"
    if "tran date" in cols_str and "particulars" in cols_str and "chq no" in cols_str:
        return "Axis"
    if "sl. no" in cols_str and "instrument" in cols_str and "dr / cr" in cols_str:
        return "Kotak"
    if "transaction date" in cols_str and "transaction remarks" in cols_str:
        return "IDFC"

    raise BankDetectionError(
        f"Could not detect bank from Excel file. "
        f"Please rename the file with the bank name (e.g., hdfc_statement.xlsx)"
    )


def parse_indian_date(date_str: str) -> Optional[datetime]:
    """Parse various Indian date formats."""
    date_str = date_str.strip()
    formats = [
        "%d/%m/%Y", "%d/%m/%y",
        "%d-%m-%Y", "%d-%m-%y",
        "%d %b %Y", "%d %b %y",
        "%d-%b-%Y", "%d-%b-%y",
        "%d/%b/%Y", "%d/%b/%y",
        "%Y-%m-%d", "%Y/%m/%d",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def parse_generic_date(date_str: str) -> Optional[datetime]:
    """Parse dates in many international formats (European, US, ISO, Indian)."""
    if pd.isna(date_str) or date_str is None:
        return None
    date_str = str(date_str).strip()
    if not date_str or date_str.lower() == "nan":
        return None

    formats = [
        "%Y-%m-%d",          # ISO: 2024-01-15
        "%Y/%m/%d",          # ISO variant: 2024/01/15
        "%d/%m/%Y",          # EU/India: 15/01/2024
        "%d/%m/%y",          # EU/India short: 15/01/24
        "%m/%d/%Y",          # US: 01/15/2024
        "%m/%d/%y",          # US short: 01/15/24
        "%d-%m-%Y",          # EU dash: 15-01-2024
        "%d-%m-%y",          # EU dash short: 15-01-24
        "%d.%m.%Y",          # EU dot: 15.01.2024
        "%d.%m.%y",          # EU dot short: 15.01.24
        "%d %b %Y",          # 15 Jan 2024
        "%d %b %y",          # 15 Jan 24
        "%d-%b-%Y",          # 15-Jan-2024
        "%d-%b-%y",          # 15-Jan-24
        "%d/%b/%Y",          # 15/Jan/2024
        "%b %d, %Y",         # Jan 15, 2024
        "%B %d, %Y",         # January 15, 2024
        "%Y-%m-%dT%H:%M:%S", # ISO with time
        "%d %B %Y",          # 15 January 2024
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    # Try pandas as last resort
    try:
        result = pd.to_datetime(date_str, dayfirst=True)
        if pd.notna(result):
            return result.to_pydatetime()
    except (ValueError, TypeError):
        pass
    return None


def parse_generic_amount(amount_str) -> Optional[float]:
    """
    Parse amount string handling both European (1.234,56) and US/Indian (1,234.56) formats.
    Also handles currency symbols from many countries.
    """
    if pd.isna(amount_str) or amount_str is None:
        return None
    if isinstance(amount_str, (int, float)):
        return float(amount_str)
    amount_str = str(amount_str).strip()
    if not amount_str or amount_str == "-" or amount_str == "":
        return None

    # Remove common currency symbols and codes
    currency_symbols = [
        "€", "$", "£", "¥", "₹", "CHF", "SEK", "NOK", "DKK", "PLN", "CZK",
        "HUF", "RON", "BGN", "HRK", "RSD", "TRY", "BRL", "AUD", "CAD", "NZD",
        "INR", "USD", "EUR", "GBP", "JPY", "KR", "ZŁ", "KČ", "FT", "LEI",
    ]
    for sym in currency_symbols:
        amount_str = amount_str.replace(sym, "")
    amount_str = amount_str.strip()

    if not amount_str or amount_str == "-":
        return None

    # Determine sign
    negative = False
    if amount_str.startswith("(") and amount_str.endswith(")"):
        negative = True
        amount_str = amount_str[1:-1].strip()
    elif amount_str.startswith("-"):
        negative = True
        amount_str = amount_str[1:].strip()
    elif amount_str.endswith("-"):
        negative = True
        amount_str = amount_str[:-1].strip()

    # Detect European vs US/Indian number format
    # European: 1.234,56 (dot as thousands sep, comma as decimal)
    # US/Indian: 1,234.56 (comma as thousands sep, period as decimal)
    has_comma = "," in amount_str
    has_dot = "." in amount_str

    if has_comma and has_dot:
        # Both present - determine which is decimal separator
        last_comma = amount_str.rfind(",")
        last_dot = amount_str.rfind(".")
        if last_comma > last_dot:
            # European format: 1.234,56
            amount_str = amount_str.replace(".", "").replace(",", ".")
        else:
            # US/Indian format: 1,234.56
            amount_str = amount_str.replace(",", "")
    elif has_comma and not has_dot:
        # Could be European decimal (3,50) or thousands separator (1,234)
        parts = amount_str.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2:
            # Likely European decimal: 3,50 or 1234,56
            amount_str = amount_str.replace(",", ".")
        else:
            # Likely thousands separator: 1,234 or 1,234,567
            amount_str = amount_str.replace(",", "")
    elif has_dot and not has_comma:
        # Could be decimal point or thousands separator
        parts = amount_str.split(".")
        if len(parts) == 2 and len(parts[1]) <= 2:
            # Likely decimal: 3.50 or 1234.56 - keep as-is
            pass
        elif len(parts) == 2 and len(parts[1]) == 3:
            # Ambiguous: could be 1.234 (EU thousands) or 1.234 (decimal with 3 places)
            # Default: treat as decimal point (more common in CSV exports)
            pass
        elif len(parts) > 2:
            # Multiple dots = thousands separator (European): 1.234.567
            amount_str = amount_str.replace(".", "")

    # Remove any remaining whitespace or non-numeric chars except dot and minus
    amount_str = re.sub(r"[^\d.\-]", "", amount_str)

    try:
        value = float(amount_str)
        return -value if negative else value
    except ValueError:
        return None


def parse_amount(amount_str) -> Optional[float]:
    """Parse amount string handling Indian number formats with commas."""
    if pd.isna(amount_str) or amount_str is None:
        return None
    if isinstance(amount_str, (int, float)):
        return float(amount_str)
    amount_str = str(amount_str).strip()
    if not amount_str or amount_str == "-" or amount_str == "":
        return None
    # Remove commas and currency symbols
    amount_str = amount_str.replace(",", "").replace("₹", "").replace("INR", "").strip()
    # Handle parentheses for negative
    if amount_str.startswith("(") and amount_str.endswith(")"):
        amount_str = "-" + amount_str[1:-1]
    try:
        return float(amount_str)
    except ValueError:
        return None


def parse_hdfc_csv(content: str) -> list[ParsedTransaction]:
    """
    Parse HDFC Bank CSV format.
    Columns: Date, Narration, Chq./Ref.No., Value Dt, Withdrawal Amt., Deposit Amt., Closing Balance
    """
    df = pd.read_csv(io.StringIO(content), skipinitialspace=True)
    df.columns = [col.strip() for col in df.columns]

    transactions = []
    for _, row in df.iterrows():
        date = parse_indian_date(str(row.get("Date", "")))
        if date is None:
            continue

        description = str(row.get("Narration", "")).strip()
        withdrawal = parse_amount(row.get("Withdrawal Amt.", row.get("Withdrawal Amt", None)))
        deposit = parse_amount(row.get("Deposit Amt.", row.get("Deposit Amt", None)))
        balance = parse_amount(row.get("Closing Balance", None))
        ref = str(row.get("Chq./Ref.No.", row.get("Chq./Ref.No", ""))).strip()

        if withdrawal and withdrawal > 0:
            transactions.append(ParsedTransaction(
                date=date, description=description, amount=withdrawal,
                transaction_type="debit", balance=balance,
                reference_number=ref if ref and ref != "nan" else None,
                bank_name="HDFC"
            ))
        elif deposit and deposit > 0:
            transactions.append(ParsedTransaction(
                date=date, description=description, amount=deposit,
                transaction_type="credit", balance=balance,
                reference_number=ref if ref and ref != "nan" else None,
                bank_name="HDFC"
            ))

    return transactions


def parse_icici_csv(content: str) -> list[ParsedTransaction]:
    """
    Parse ICICI Bank CSV format.
    Columns: S No., Value Date, Transaction Date, Cheque Number, Transaction Remarks, 
             Withdrawal Amount (INR), Deposit Amount (INR), Balance (INR)
    OR: Transaction ID, Value Dat, Txn Posted Date, ChequeNo, Description, Cr/Dr, Transaction Amount, Available Balance
    """
    df = pd.read_csv(io.StringIO(content), skipinitialspace=True)
    df.columns = [col.strip() for col in df.columns]

    transactions = []

    # Detect ICICI format variant
    cols_lower = [c.lower() for c in df.columns]

    if any("cr/dr" in c for c in cols_lower):
        # Format with Cr/Dr column
        for _, row in df.iterrows():
            date_col = next((c for c in df.columns if "transaction date" in c.lower() or "txn posted" in c.lower()), None)
            if date_col is None:
                date_col = next((c for c in df.columns if "value dat" in c.lower()), None)
            if date_col is None:
                continue

            date = parse_indian_date(str(row.get(date_col, "")))
            if date is None:
                continue

            desc_col = next((c for c in df.columns if "description" in c.lower() or "remark" in c.lower()), "")
            description = str(row.get(desc_col, "")).strip()

            amt_col = next((c for c in df.columns if "transaction amount" in c.lower() or "amount" in c.lower()), None)
            amount = parse_amount(row.get(amt_col)) if amt_col else None
            if not amount:
                continue

            cr_dr_col = next((c for c in df.columns if "cr/dr" in c.lower()), "")
            cr_dr = str(row.get(cr_dr_col, "")).strip().upper()
            txn_type = "credit" if cr_dr == "CR" else "debit"

            balance_col = next((c for c in df.columns if "balance" in c.lower()), None)
            balance = parse_amount(row.get(balance_col)) if balance_col else None

            transactions.append(ParsedTransaction(
                date=date, description=description, amount=abs(amount),
                transaction_type=txn_type, balance=balance, bank_name="ICICI"
            ))
    else:
        # Format with separate withdrawal/deposit columns
        for _, row in df.iterrows():
            date_col = next((c for c in df.columns if "transaction date" in c.lower()), None)
            if date_col is None:
                date_col = next((c for c in df.columns if "value date" in c.lower()), None)
            if date_col is None:
                continue

            date = parse_indian_date(str(row.get(date_col, "")))
            if date is None:
                continue

            desc_col = next((c for c in df.columns if "remark" in c.lower() or "description" in c.lower()), "")
            description = str(row.get(desc_col, "")).strip()

            withdrawal_col = next((c for c in df.columns if "withdrawal" in c.lower()), None)
            deposit_col = next((c for c in df.columns if "deposit" in c.lower()), None)
            balance_col = next((c for c in df.columns if "balance" in c.lower()), None)

            withdrawal = parse_amount(row.get(withdrawal_col)) if withdrawal_col else None
            deposit = parse_amount(row.get(deposit_col)) if deposit_col else None
            balance = parse_amount(row.get(balance_col)) if balance_col else None

            if withdrawal and withdrawal > 0:
                transactions.append(ParsedTransaction(
                    date=date, description=description, amount=withdrawal,
                    transaction_type="debit", balance=balance, bank_name="ICICI"
                ))
            elif deposit and deposit > 0:
                transactions.append(ParsedTransaction(
                    date=date, description=description, amount=deposit,
                    transaction_type="credit", balance=balance, bank_name="ICICI"
                ))

    return transactions


def parse_sbi_csv(content: str) -> list[ParsedTransaction]:
    """
    Parse SBI CSV format.
    Columns: Txn Date, Value Date, Description, Ref No./Cheque No., Debit, Credit, Balance
    """
    df = pd.read_csv(io.StringIO(content), skipinitialspace=True)
    df.columns = [col.strip() for col in df.columns]

    transactions = []
    for _, row in df.iterrows():
        date_col = next((c for c in df.columns if "txn date" in c.lower() or "transaction date" in c.lower()), None)
        if date_col is None:
            continue

        date = parse_indian_date(str(row.get(date_col, "")))
        if date is None:
            continue

        desc_col = next((c for c in df.columns if "description" in c.lower() or "narration" in c.lower()), "")
        description = str(row.get(desc_col, "")).strip()
        # Strip SBI padding characters (0xCA=Ê, 0xC9=É in cp1252) and trailing dashes
        description = re.sub(r'^[\xca\xc9\xc8\s]+', '', description).strip()
        description = description.rstrip('-').strip()

        ref_col = next((c for c in df.columns if "ref" in c.lower() or "cheque" in c.lower()), None)
        ref = str(row.get(ref_col, "")).strip() if ref_col else None

        debit_col = next((c for c in df.columns if "debit" in c.lower()), None)
        credit_col = next((c for c in df.columns if "credit" in c.lower()), None)
        balance_col = next((c for c in df.columns if "balance" in c.lower()), None)

        debit = parse_amount(row.get(debit_col)) if debit_col else None
        credit = parse_amount(row.get(credit_col)) if credit_col else None
        balance = parse_amount(row.get(balance_col)) if balance_col else None

        if debit and debit > 0:
            transactions.append(ParsedTransaction(
                date=date, description=description, amount=debit,
                transaction_type="debit", balance=balance,
                reference_number=ref if ref and ref != "nan" else None,
                bank_name="SBI"
            ))
        elif credit and credit > 0:
            transactions.append(ParsedTransaction(
                date=date, description=description, amount=credit,
                transaction_type="credit", balance=balance,
                reference_number=ref if ref and ref != "nan" else None,
                bank_name="SBI"
            ))

    return transactions


def parse_axis_csv(content: str) -> list[ParsedTransaction]:
    """
    Parse Axis Bank CSV format.
    Columns: Tran Date, Chq No, Particulars, Debit, Credit, Balance, Init. Br
    """
    df = pd.read_csv(io.StringIO(content), skipinitialspace=True)
    df.columns = [col.strip() for col in df.columns]

    transactions = []
    for _, row in df.iterrows():
        date_col = next((c for c in df.columns if "tran date" in c.lower() or "transaction date" in c.lower()), None)
        if date_col is None:
            continue

        date = parse_indian_date(str(row.get(date_col, "")))
        if date is None:
            continue

        desc_col = next((c for c in df.columns if "particular" in c.lower() or "description" in c.lower()), "")
        description = str(row.get(desc_col, "")).strip()

        chq_col = next((c for c in df.columns if "chq" in c.lower()), None)
        ref = str(row.get(chq_col, "")).strip() if chq_col else None

        debit_col = next((c for c in df.columns if "debit" in c.lower()), None)
        credit_col = next((c for c in df.columns if "credit" in c.lower()), None)
        balance_col = next((c for c in df.columns if "balance" in c.lower()), None)

        debit = parse_amount(row.get(debit_col)) if debit_col else None
        credit = parse_amount(row.get(credit_col)) if credit_col else None
        balance = parse_amount(row.get(balance_col)) if balance_col else None

        if debit and debit > 0:
            transactions.append(ParsedTransaction(
                date=date, description=description, amount=debit,
                transaction_type="debit", balance=balance,
                reference_number=ref if ref and ref != "nan" else None,
                bank_name="Axis"
            ))
        elif credit and credit > 0:
            transactions.append(ParsedTransaction(
                date=date, description=description, amount=credit,
                transaction_type="credit", balance=balance,
                reference_number=ref if ref and ref != "nan" else None,
                bank_name="Axis"
            ))

    return transactions


def parse_kotak_csv(content: str) -> list[ParsedTransaction]:
    """
    Parse Kotak Mahindra Bank CSV format.
    Columns: Sl. No., Transaction Date, Value Date, Description, Chq / Ref No., Amount, Dr / Cr, Balance
    """
    df = pd.read_csv(io.StringIO(content), skipinitialspace=True)
    df.columns = [col.strip() for col in df.columns]

    transactions = []
    for _, row in df.iterrows():
        date_col = next((c for c in df.columns if "transaction date" in c.lower()), None)
        if date_col is None:
            continue

        date = parse_indian_date(str(row.get(date_col, "")))
        if date is None:
            continue

        desc_col = next((c for c in df.columns if "description" in c.lower()), "")
        description = str(row.get(desc_col, "")).strip()

        ref_col = next((c for c in df.columns if "ref" in c.lower() or "chq" in c.lower()), None)
        ref = str(row.get(ref_col, "")).strip() if ref_col else None

        amount_col = next((c for c in df.columns if "amount" in c.lower()), None)
        balance_col = next((c for c in df.columns if "balance" in c.lower()), None)
        dr_cr_col = next((c for c in df.columns if "dr" in c.lower() and "cr" in c.lower()), None)

        amount = parse_amount(row.get(amount_col)) if amount_col else None
        balance = parse_amount(row.get(balance_col)) if balance_col else None

        if not amount or amount <= 0:
            continue

        if dr_cr_col:
            dr_cr = str(row.get(dr_cr_col, "")).strip().upper()
            txn_type = "credit" if "CR" in dr_cr else "debit"
        else:
            txn_type = "debit"

        transactions.append(ParsedTransaction(
            date=date, description=description, amount=abs(amount),
            transaction_type=txn_type, balance=balance,
            reference_number=ref if ref and ref != "nan" else None,
            bank_name="Kotak"
        ))

    return transactions


def parse_idfc_csv(content: str) -> list[ParsedTransaction]:
    """
    Parse IDFC First Bank CSV format.
    Columns: Transaction Date, Value Date, Transaction Remarks, Withdrawal Amount, Deposit Amount, Balance
    """
    df = pd.read_csv(io.StringIO(content), skipinitialspace=True)
    df.columns = [col.strip() for col in df.columns]

    transactions = []
    for _, row in df.iterrows():
        date_col = next((c for c in df.columns if "transaction date" in c.lower()), None)
        if date_col is None:
            continue

        date = parse_indian_date(str(row.get(date_col, "")))
        if date is None:
            continue

        desc_col = next((c for c in df.columns if "remark" in c.lower() or "description" in c.lower()), "")
        description = str(row.get(desc_col, "")).strip()

        withdrawal_col = next((c for c in df.columns if "withdrawal" in c.lower()), None)
        deposit_col = next((c for c in df.columns if "deposit" in c.lower()), None)
        balance_col = next((c for c in df.columns if "balance" in c.lower()), None)

        withdrawal = parse_amount(row.get(withdrawal_col)) if withdrawal_col else None
        deposit = parse_amount(row.get(deposit_col)) if deposit_col else None
        balance = parse_amount(row.get(balance_col)) if balance_col else None

        if withdrawal and withdrawal > 0:
            transactions.append(ParsedTransaction(
                date=date, description=description, amount=withdrawal,
                transaction_type="debit", balance=balance, bank_name="IDFC"
            ))
        elif deposit and deposit > 0:
            transactions.append(ParsedTransaction(
                date=date, description=description, amount=deposit,
                transaction_type="credit", balance=balance, bank_name="IDFC"
            ))

    return transactions


def parse_revolut_csv(content: str) -> list[ParsedTransaction]:
    """
    Parse Revolut Bank CSV format (fintech multi-currency).
    Columns: Type, Product, Started Date, Completed Date, Description, Amount, Fee, Currency, State, Balance
    
    Revolut uses signed amounts: negative = debit/expense, positive = credit/income
    """
    df = pd.read_csv(io.StringIO(content), skipinitialspace=True)
    df.columns = [col.strip() for col in df.columns]

    transactions = []
    for _, row in df.iterrows():
        # Parse date - prefer Started Date if available, else Completed Date
        date = None
        for date_col in ["Started Date", "Completed Date", "started date", "completed date"]:
            if date_col in df.columns:
                date_str = str(row.get(date_col, "")).strip()
                if date_str and date_str != "nan":
                    date = parse_generic_date(date_str)
                    if date:
                        break
        
        if date is None:
            continue

        description = str(row.get("Description", "")).strip() if "Description" in df.columns else ""
        if not description:
            continue

        amount = parse_generic_amount(row.get("Amount")) if "Amount" in df.columns else None
        if not amount:
            continue

        balance = parse_generic_amount(row.get("Balance")) if "Balance" in df.columns else None

        # Detect currency from the Currency column
        currency = "EUR"
        for cur_col in ["Currency", "currency"]:
            if cur_col in df.columns:
                cur_val = str(row.get(cur_col, "")).strip().upper()
                if cur_val and cur_val != "NAN":
                    currency = cur_val
                    break
        
        # Revolut uses signed amounts: negative = debit, positive = credit
        if amount < 0:
            transactions.append(ParsedTransaction(
                date=date,
                description=description,
                amount=abs(amount),
                transaction_type="debit",
                balance=balance,
                bank_name="Revolut",
                currency=currency,
            ))
        elif amount > 0:
            transactions.append(ParsedTransaction(
                date=date,
                description=description,
                amount=amount,
                transaction_type="credit",
                balance=balance,
                bank_name="Revolut",
                currency=currency,
            ))

    return transactions


def parse_hdfc_excel(df: pd.DataFrame) -> list[ParsedTransaction]:
    """
    Parse HDFC Bank Excel format.
    Columns: Date, Narration, Chq./Ref.No., Value Dt, Withdrawal Amt., Deposit Amt., Closing Balance
    """
    df.columns = [col.strip() for col in df.columns]
    transactions = []
    for _, row in df.iterrows():
        date = parse_indian_date(str(row.get("Date", "")))
        if date is None:
            continue

        description = str(row.get("Narration", "")).strip()
        withdrawal = parse_amount(row.get("Withdrawal Amt.", row.get("Withdrawal Amt", None)))
        deposit = parse_amount(row.get("Deposit Amt.", row.get("Deposit Amt", None)))
        balance = parse_amount(row.get("Closing Balance", None))
        ref = str(row.get("Chq./Ref.No.", row.get("Chq./Ref.No", ""))).strip()

        if withdrawal and withdrawal > 0:
            transactions.append(ParsedTransaction(
                date=date, description=description, amount=withdrawal,
                transaction_type="debit", balance=balance,
                reference_number=ref if ref and ref != "nan" else None,
                bank_name="HDFC"
            ))
        elif deposit and deposit > 0:
            transactions.append(ParsedTransaction(
                date=date, description=description, amount=deposit,
                transaction_type="credit", balance=balance,
                reference_number=ref if ref and ref != "nan" else None,
                bank_name="HDFC"
            ))

    return transactions


def parse_icici_excel(df: pd.DataFrame) -> list[ParsedTransaction]:
    """
    Parse ICICI Bank Excel format.
    Columns: S No., Value Date, Transaction Date, Cheque Number, Transaction Remarks, 
             Withdrawal Amount (INR), Deposit Amount (INR), Balance (INR)
    OR: Transaction ID, Value Dat, Txn Posted Date, ChequeNo, Description, Cr/Dr, Transaction Amount, Available Balance
    """
    df.columns = [col.strip() for col in df.columns]
    transactions = []
    cols_lower = [c.lower() for c in df.columns]

    if any("cr/dr" in c for c in cols_lower):
        # Format with Cr/Dr column
        for _, row in df.iterrows():
            date_col = next((c for c in df.columns if "transaction date" in c.lower() or "txn posted" in c.lower()), None)
            if date_col is None:
                date_col = next((c for c in df.columns if "value dat" in c.lower()), None)
            if date_col is None:
                continue

            date = parse_indian_date(str(row.get(date_col, "")))
            if date is None:
                continue

            desc_col = next((c for c in df.columns if "description" in c.lower() or "remark" in c.lower()), "")
            description = str(row.get(desc_col, "")).strip()

            amt_col = next((c for c in df.columns if "transaction amount" in c.lower() or "amount" in c.lower()), None)
            amount = parse_amount(row.get(amt_col)) if amt_col else None
            if not amount:
                continue

            cr_dr_col = next((c for c in df.columns if "cr/dr" in c.lower()), "")
            cr_dr = str(row.get(cr_dr_col, "")).strip().upper()
            txn_type = "credit" if cr_dr == "CR" else "debit"

            balance_col = next((c for c in df.columns if "balance" in c.lower()), None)
            balance = parse_amount(row.get(balance_col)) if balance_col else None

            transactions.append(ParsedTransaction(
                date=date, description=description, amount=abs(amount),
                transaction_type=txn_type, balance=balance, bank_name="ICICI"
            ))
    else:
        # Format with separate withdrawal/deposit columns
        for _, row in df.iterrows():
            date_col = next((c for c in df.columns if "transaction date" in c.lower()), None)
            if date_col is None:
                date_col = next((c for c in df.columns if "value date" in c.lower()), None)
            if date_col is None:
                continue

            date = parse_indian_date(str(row.get(date_col, "")))
            if date is None:
                continue

            desc_col = next((c for c in df.columns if "remark" in c.lower() or "description" in c.lower()), "")
            description = str(row.get(desc_col, "")).strip()

            withdrawal_col = next((c for c in df.columns if "withdrawal" in c.lower()), None)
            deposit_col = next((c for c in df.columns if "deposit" in c.lower()), None)
            balance_col = next((c for c in df.columns if "balance" in c.lower()), None)

            withdrawal = parse_amount(row.get(withdrawal_col)) if withdrawal_col else None
            deposit = parse_amount(row.get(deposit_col)) if deposit_col else None
            balance = parse_amount(row.get(balance_col)) if balance_col else None

            if withdrawal and withdrawal > 0:
                transactions.append(ParsedTransaction(
                    date=date, description=description, amount=withdrawal,
                    transaction_type="debit", balance=balance, bank_name="ICICI"
                ))
            elif deposit and deposit > 0:
                transactions.append(ParsedTransaction(
                    date=date, description=description, amount=deposit,
                    transaction_type="credit", balance=balance, bank_name="ICICI"
                ))

    return transactions


def parse_sbi_excel(df: pd.DataFrame) -> list[ParsedTransaction]:
    """
    Parse SBI Bank Excel format.
    Columns: Txn Date, Value Date, Debit, Credit, Particulars, Balance
    """
    df.columns = [col.strip() for col in df.columns]
    transactions = []
    for _, row in df.iterrows():
        date_col = next((c for c in df.columns if "txn date" in c.lower()), None)
        if date_col is None:
            continue

        date = parse_indian_date(str(row.get(date_col, "")))
        if date is None:
            continue

        desc_col = next(
            (c for c in df.columns if "description" in c.lower() or "particulars" in c.lower() or "narration" in c.lower()),
            ""
        )
        description = str(row.get(desc_col, "")).strip()
        # Strip SBI padding characters (0xCA=Ê in cp1252) and trailing dashes
        description = re.sub(r'^[\xca\xc9\xc8\s]+', '', description).strip()
        description = description.rstrip('-').strip()

        ref_col = next((c for c in df.columns if "ref" in c.lower() or "cheque" in c.lower()), None)
        ref = str(row.get(ref_col, "")).strip() if ref_col else None

        debit_col = next((c for c in df.columns if "debit" in c.lower()), None)
        credit_col = next((c for c in df.columns if "credit" in c.lower()), None)
        balance_col = next((c for c in df.columns if "balance" in c.lower()), None)

        debit = parse_amount(row.get(debit_col)) if debit_col else None
        credit = parse_amount(row.get(credit_col)) if credit_col else None
        balance = parse_amount(row.get(balance_col)) if balance_col else None

        if debit and debit > 0:
            transactions.append(ParsedTransaction(
                date=date, description=description, amount=debit,
                transaction_type="debit", balance=balance,
                reference_number=ref if ref and ref != "nan" else None,
                bank_name="SBI"
            ))
        elif credit and credit > 0:
            transactions.append(ParsedTransaction(
                date=date, description=description, amount=credit,
                transaction_type="credit", balance=balance,
                reference_number=ref if ref and ref != "nan" else None,
                bank_name="SBI"
            ))

    return transactions


def parse_axis_excel(df: pd.DataFrame) -> list[ParsedTransaction]:
    """
    Parse Axis Bank Excel format.
    Columns: Tran Date, Chq No, Particulars, Debit, Credit, Balance, Init. Br
    """
    df.columns = [col.strip() for col in df.columns]
    transactions = []
    for _, row in df.iterrows():
        date_col = next((c for c in df.columns if "tran date" in c.lower() or "transaction date" in c.lower()), None)
        if date_col is None:
            continue

        date = parse_indian_date(str(row.get(date_col, "")))
        if date is None:
            continue

        desc_col = next((c for c in df.columns if "particular" in c.lower() or "description" in c.lower()), "")
        description = str(row.get(desc_col, "")).strip()

        chq_col = next((c for c in df.columns if "chq" in c.lower()), None)
        ref = str(row.get(chq_col, "")).strip() if chq_col else None

        debit_col = next((c for c in df.columns if "debit" in c.lower()), None)
        credit_col = next((c for c in df.columns if "credit" in c.lower()), None)
        balance_col = next((c for c in df.columns if "balance" in c.lower()), None)

        debit = parse_amount(row.get(debit_col)) if debit_col else None
        credit = parse_amount(row.get(credit_col)) if credit_col else None
        balance = parse_amount(row.get(balance_col)) if balance_col else None

        if debit and debit > 0:
            transactions.append(ParsedTransaction(
                date=date, description=description, amount=debit,
                transaction_type="debit", balance=balance,
                reference_number=ref if ref and ref != "nan" else None,
                bank_name="Axis"
            ))
        elif credit and credit > 0:
            transactions.append(ParsedTransaction(
                date=date, description=description, amount=credit,
                transaction_type="credit", balance=balance,
                reference_number=ref if ref and ref != "nan" else None,
                bank_name="Axis"
            ))

    return transactions


def parse_kotak_excel(df: pd.DataFrame) -> list[ParsedTransaction]:
    """
    Parse Kotak Bank Excel format.
    Columns: Sl. No, Transaction Date, Instrument, Particulars, Cheque No, Dr / Cr, Amount, Balance
    """
    df.columns = [col.strip() for col in df.columns]
    transactions = []
    for _, row in df.iterrows():
        date_col = next((c for c in df.columns if "transaction date" in c.lower()), None)
        if date_col is None:
            continue

        date = parse_indian_date(str(row.get(date_col, "")))
        if date is None:
            continue

        desc_col = next((c for c in df.columns if "particulars" in c.lower()), "")
        description = str(row.get(desc_col, "")).strip()

        amount_col = next((c for c in df.columns if "amount" in c.lower() and "balance" not in c.lower()), None)
        dr_cr_col = next((c for c in df.columns if "dr / cr" in c.lower() or "dr/cr" in c.lower()), None)
        balance_col = next((c for c in df.columns if "balance" in c.lower()), None)
        ref_col = next((c for c in df.columns if "cheque" in c.lower()), None)

        amount = parse_amount(row.get(amount_col)) if amount_col else None
        if not amount:
            continue

        dr_cr = str(row.get(dr_cr_col, "")).strip().upper() if dr_cr_col else ""
        txn_type = "credit" if dr_cr == "CR" else "debit"
        balance = parse_amount(row.get(balance_col)) if balance_col else None
        ref = str(row.get(ref_col, "")).strip() if ref_col else None

        transactions.append(ParsedTransaction(
            date=date, description=description, amount=amount,
            transaction_type=txn_type, balance=balance,
            reference_number=ref if ref and ref != "nan" else None,
            bank_name="Kotak"
        ))

    return transactions


def parse_idfc_excel(df: pd.DataFrame) -> list[ParsedTransaction]:
    """
    Parse IDFC First Bank Excel format.
    Columns: Transaction Date, Value Date, Transaction Remarks, Withdrawal Amount, Deposit Amount, Balance
    """
    df.columns = [col.strip() for col in df.columns]
    transactions = []
    for _, row in df.iterrows():
        date_col = next((c for c in df.columns if "transaction date" in c.lower()), None)
        if date_col is None:
            continue

        date = parse_indian_date(str(row.get(date_col, "")))
        if date is None:
            continue

        desc_col = next((c for c in df.columns if "remark" in c.lower() or "description" in c.lower()), "")
        description = str(row.get(desc_col, "")).strip()

        withdrawal_col = next((c for c in df.columns if "withdrawal" in c.lower()), None)
        deposit_col = next((c for c in df.columns if "deposit" in c.lower()), None)
        balance_col = next((c for c in df.columns if "balance" in c.lower()), None)

        withdrawal = parse_amount(row.get(withdrawal_col)) if withdrawal_col else None
        deposit = parse_amount(row.get(deposit_col)) if deposit_col else None
        balance = parse_amount(row.get(balance_col)) if balance_col else None

        if withdrawal and withdrawal > 0:
            transactions.append(ParsedTransaction(
                date=date, description=description, amount=withdrawal,
                transaction_type="debit", balance=balance, bank_name="IDFC"
            ))
        elif deposit and deposit > 0:
            transactions.append(ParsedTransaction(
                date=date, description=description, amount=deposit,
                transaction_type="credit", balance=balance, bank_name="IDFC"
            ))

    return transactions



# ---------------------------------------------------------------------------
# Generic / Universal Bank Statement Parser
# Supports 41+ banks worldwide (India, Europe, US, Global platforms)
# ---------------------------------------------------------------------------

# Encoding fallback chain ordered by prevalence
ENCODING_CHAIN = ['utf-8', 'utf-8-sig', 'cp1252', 'iso-8859-1', 'latin-1']

# Column name patterns for auto-detection (multilingual, covering 41+ banks)
_DATE_KEYWORDS = [
    # Exact matches (highest priority)
    "date", "transaction date", "txn date", "value date", "posting date",
    "completed date", "started date", "settled date", "post date",
    "posted date", "tran date", "booking date", "trans. date", "trans date",
    # Indian
    "transaction posted date", "txn posted date",
    # German
    "buchungstag", "wertstellung", "datum",
    # Dutch
    "boekingsdatum",
    # Spanish
    "fecha", "fecha valor",
    # French
    "date opération", "date valeur",
    # Italian
    "data", "data operazione", "data valuta",
]

_DESCRIPTION_KEYWORDS = [
    "description", "narration", "particulars", "details", "memo",
    "transaction details", "payment details", "reference",
    "transaction description", "transaction remarks", "remarks",
    "name", "payee", "merchant", "counter party",
    # German
    "verwendungszweck", "buchungstext", "beschreibung",
    # Dutch
    "omschrijving", "naam / omschrijving",
    # Spanish
    "concepto", "descripción",
    # French
    "libellé",
    # Italian
    "descrizione",
    # Generic
    "text",
]

_DEBIT_KEYWORDS = [
    "debit", "withdrawal", "debit amount", "money out", "paid out",
    "withdrawal amt", "withdrawal amt.", "withdrawals",
    "debit(inr)", "debit amount (inr)",
    "dr",
    # Dutch
    "af",
    # German
    "soll", "belastung",
    # Spanish
    "debe",
    # Italian
    "addebito",
    # Generic
    "expense", "ausgabe",
]

_CREDIT_KEYWORDS = [
    "credit", "deposit", "credit amount", "money in", "paid in",
    "deposit amt", "deposit amt.", "deposits",
    "credit(inr)", "credit amount (inr)",
    "cr",
    # Dutch
    "bij",
    # German
    "haben", "gutschrift",
    # Spanish
    "haber",
    # Italian
    "accredito",
    # Generic
    "income", "eingabe",
]

_AMOUNT_KEYWORDS = [
    "amount", "transaction amount", "value", "sum", "total", "net", "gross",
    # German
    "betrag", "umsatz",
    # Dutch
    "bedrag",
    # Spanish
    "importe", "monto",
    # Italian
    "importo",
    # Swedish
    "belopp",
    # Generic
    "valor",
]

_BALANCE_KEYWORDS = [
    "balance", "running balance", "closing balance", "available balance",
    "running bal.", "running bal",
    # German
    "saldo", "kontostand",
    # French
    "solde",
]

_TYPE_KEYWORDS = [
    "dr / cr", "dr/cr", "cr/dr", "type", "transaction type", "d/c",
]

_GROSS_KEYWORDS = ["gross", "gross amount"]
_FEE_KEYWORDS = ["fee", "fees", "charge", "charges"]
_NET_KEYWORDS = ["net", "net amount"]

# Bank header signatures for known banks (lowercase for matching)
BANK_SIGNATURES: dict[str, list[str]] = {
    "Chase": [
        "transaction date", "post date", "description", "amount", "type",
    ],
    "Bank of America": [
        "date", "description", "amount", "running bal.",
    ],
    "Wells Fargo": [
        "date", "amount", "description",
    ],
    "Citi": [
        "status", "date", "description", "debit", "credit",
    ],
    "Capital One": [
        "transaction date", "posted date", "card no.", "description", "category", "debit", "credit",
    ],
    "Barclays": [
        "number", "date", "account", "amount", "subcategory", "memo",
    ],
    "HSBC UK": [
        "date", "description", "amount",
    ],
    "Monzo": [
        "date", "time", "type", "name", "emoji", "category", "amount", "currency",
    ],
    "N26": [
        "date", "payee", "account number", "transaction type", "payment reference",
    ],
    "Wise": [
        "transferwise id", "date", "amount", "currency", "description",
    ],
    "PayPal": [
        "date", "time", "timezone", "name", "type", "status", "currency", "gross", "fee", "net",
    ],
    "Revolut": [
        "type", "product", "started date", "completed date", "description", "amount", "fee", "currency",
    ],
    "Starling": [
        "date", "counter party", "reference", "type", "amount", "balance", "spending category",
    ],
    "Lloyds": [
        "transaction date", "transaction type", "sort code", "account number",
        "transaction description", "debit amount", "credit amount", "balance",
    ],
    "NatWest": [
        "date", "type", "description", "value", "balance", "account name", "account number",
    ],
    "Santander UK": [
        "date", "description", "money in", "money out", "balance",
    ],
    "ING": [
        "datum", "naam / omschrijving", "rekening", "tegenrekening", "code", "af bij",
    ],
    "Deutsche Bank": [
        "buchungstag", "wertstellung", "buchungstext", "verwendungszweck", "betrag",
    ],
    "Discover": [
        "trans. date", "post date", "description", "amount", "category",
    ],
}

# Region hints for date format disambiguation
_US_BANKS = {"Chase", "Bank of America", "Wells Fargo", "Citi", "Capital One", "Discover", "USAA"}
_EU_BANKS = {"Barclays", "HSBC UK", "Monzo", "N26", "Starling", "Lloyds", "NatWest",
             "Santander UK", "ING", "Deutsche Bank", "Wise"}
_INDIA_BANKS = {"HDFC", "ICICI", "SBI", "Axis", "Kotak", "IDFC", "YES Bank", "PNB", "BOB", "IndusInd"}

# Summary/footer row keywords to skip
_SKIP_ROW_KEYWORDS = [
    "total", "subtotal", "summary", "balance:", "end of statement",
    "grand total", "total debit", "total credit", "opening balance",
]


def detect_bank_from_headers(headers: list[str]) -> Optional[str]:
    """Match header row against known bank signatures. Returns bank name or None."""
    header_set = set(h.strip().lower() for h in headers if h and str(h).strip())
    best_match = None
    best_score = 0.0
    best_overlap = 0

    for bank, signature in BANK_SIGNATURES.items():
        sig_set = set(s.lower() for s in signature)
        overlap = len(sig_set & header_set)
        score = overlap / len(sig_set) if sig_set else 0
        # Prefer higher score; on tie, prefer more specific (higher overlap count)
        if score >= 0.7 and (score > best_score or (score == best_score and overlap > best_overlap)):
            best_match = bank
            best_score = score
            best_overlap = overlap

    return best_match


def _get_region_hint(bank_name: Optional[str], filename: str = "") -> Optional[str]:
    """Determine region hint from bank name or filename for date disambiguation."""
    if bank_name:
        if bank_name in _US_BANKS:
            return "US"
        if bank_name in _EU_BANKS:
            return "EU"
        if bank_name in _INDIA_BANKS:
            return "India"
    fn_lower = filename.lower()
    us_indicators = ["chase", "bofa", "wells", "citi", "capital_one", "discover", "usaa"]
    if any(ind in fn_lower for ind in us_indicators):
        return "US"
    return None


def detect_delimiter(content: str) -> str:
    """Detect CSV delimiter from content by analyzing first few lines."""
    lines = [l for l in content.split('\n')[:5] if l.strip()]
    if not lines:
        return ','

    # Check semicolon first (European files where comma is decimal separator)
    for delim in [';', '\t', '|', ',']:
        counts = [line.count(delim) for line in lines]
        if all(c > 0 for c in counts) and max(counts) - min(counts) <= 1:
            return delim

    return ','


def parse_date_smart(date_str, region_hint: Optional[str] = None) -> Optional[datetime]:
    """
    Parse date with format disambiguation.
    Uses region hints and day>12 logic to resolve DD/MM vs MM/DD ambiguity.
    """
    if pd.isna(date_str) or date_str is None:
        return None
    date_str = str(date_str).strip()
    if not date_str or date_str.lower() == "nan":
        return None

    # ISO format (unambiguous): YYYY-MM-DD or YYYY-MM-DD HH:MM:SS
    if re.match(r'^\d{4}-\d{2}-\d{2}', date_str):
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

    # YYYYMMDD (no separators, ING Netherlands)
    if re.match(r'^\d{8}$', date_str):
        try:
            return datetime.strptime(date_str, "%Y%m%d")
        except ValueError:
            pass

    # German dot format: DD.MM.YYYY
    if re.match(r'^\d{1,2}\.\d{1,2}\.\d{4}$', date_str):
        try:
            return datetime.strptime(date_str, "%d.%m.%Y")
        except ValueError:
            pass
    if re.match(r'^\d{1,2}\.\d{1,2}\.\d{2}$', date_str):
        try:
            return datetime.strptime(date_str, "%d.%m.%y")
        except ValueError:
            pass

    # Month name formats (unambiguous): DD MMM YYYY, DD-MMM-YYYY, etc.
    month_patterns = [
        ("%d %b %Y", r'^\d{1,2}\s+[A-Za-z]{3}\s+\d{4}$'),
        ("%d %b %y", r'^\d{1,2}\s+[A-Za-z]{3}\s+\d{2}$'),
        ("%d-%b-%Y", r'^\d{1,2}-[A-Za-z]{3}-\d{4}$'),
        ("%d-%b-%y", r'^\d{1,2}-[A-Za-z]{3}-\d{2}$'),
        ("%d/%b/%Y", r'^\d{1,2}/[A-Za-z]{3}/\d{4}$'),
        ("%b %d, %Y", r'^[A-Za-z]{3}\s+\d{1,2},\s*\d{4}$'),
        ("%B %d, %Y", r'^[A-Za-z]+\s+\d{1,2},\s*\d{4}$'),
        ("%d %B %Y", r'^\d{1,2}\s+[A-Za-z]+\s+\d{4}$'),
    ]
    for fmt, pattern in month_patterns:
        if re.match(pattern, date_str):
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

    # Slash or dash separated: need disambiguation between DD/MM and MM/DD
    slash_match = re.match(r'^(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})$', date_str)
    if slash_match:
        part1 = int(slash_match.group(1))
        part2 = int(slash_match.group(2))
        year_str = slash_match.group(3)
        year = int(year_str) if len(year_str) == 4 else (2000 + int(year_str))

        # Unambiguous cases
        if part1 > 12 and part2 <= 12:
            # Must be DD/MM (day > 12)
            try:
                return datetime(year, part2, part1)
            except ValueError:
                pass
        elif part2 > 12 and part1 <= 12:
            # Must be MM/DD (day > 12 in second position)
            try:
                return datetime(year, part1, part2)
            except ValueError:
                pass
        else:
            # Ambiguous (both <= 12): use region hint
            if region_hint == "US":
                # MM/DD/YYYY
                try:
                    return datetime(year, part1, part2)
                except ValueError:
                    pass
            else:
                # DD/MM/YYYY (default for India, Europe, UK)
                try:
                    return datetime(year, part2, part1)
                except ValueError:
                    try:
                        return datetime(year, part1, part2)
                    except ValueError:
                        pass

    # Fall back to pandas as last resort
    try:
        dayfirst = region_hint != "US"
        result = pd.to_datetime(date_str, dayfirst=dayfirst)
        if pd.notna(result):
            return result.to_pydatetime()
    except (ValueError, TypeError):
        pass

    return None


def _detect_date_region_from_data(df: pd.DataFrame, date_col: str) -> Optional[str]:
    """
    Sample date values to determine if format is US (MM/DD) or EU/India (DD/MM).
    If any date has first number > 12, it's DD/MM. If second number > 12, it's MM/DD.
    """
    sample = df[date_col].dropna().head(20)
    for val in sample:
        val_str = str(val).strip()
        match = re.match(r'^(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})$', val_str)
        if match:
            part1, part2 = int(match.group(1)), int(match.group(2))
            if part1 > 12:
                return "EU"
            if part2 > 12:
                return "US"
    return None


def _is_summary_row(row_values: list) -> bool:
    """Check if a row is a summary/footer row that should be skipped."""
    combined = " ".join(str(v).lower() for v in row_values if pd.notna(v))
    return any(kw in combined for kw in _SKIP_ROW_KEYWORDS)


def _match_column(columns: list[str], keywords: list[str]) -> Optional[str]:
    """Find the first column name that matches any keyword (case-insensitive)."""
    cols_lower = {col: col.lower().strip() for col in columns}
    # Exact match first (highest priority)
    for keyword in keywords:
        for col, col_lower in cols_lower.items():
            if col_lower == keyword:
                return col
    # Partial/contains match as fallback (but short keywords need word boundaries)
    for keyword in keywords:
        for col, col_lower in cols_lower.items():
            if len(keyword) <= 3:
                # Short keywords (dr, cr, af, bij) must appear as whole words
                if re.search(r'\b' + re.escape(keyword) + r'\b', col_lower):
                    return col
            else:
                if keyword in col_lower:
                    return col
    return None


def _match_column_with_currency(columns: list[str], keywords: list[str]) -> Optional[str]:
    """
    Like _match_column but also handles columns with currency in parentheses.
    E.g., "Amount (EUR)" matches "amount".
    """
    result = _match_column(columns, keywords)
    if result:
        return result
    # Try stripping parenthetical currency: "Amount (EUR)" -> "amount"
    cols_stripped = {}
    for col in columns:
        stripped = re.sub(r'\s*\([^)]*\)\s*$', '', col).strip().lower()
        cols_stripped[col] = stripped
    for keyword in keywords:
        for col, stripped in cols_stripped.items():
            if stripped == keyword:
                return col
            if len(keyword) <= 3:
                if re.search(r'\b' + re.escape(keyword) + r'\b', stripped):
                    return col
            elif keyword in stripped:
                return col
    return None


def parse_generic_csv(content: str, filename: str = "") -> list[ParsedTransaction]:
    """
    Generic CSV parser that auto-detects columns by matching common header keywords.
    Works for any bank statement format from any country. Supports all 41+ banks
    from the research corpus including US, European, Indian, and global fintech formats.
    """
    # Detect delimiter from content
    delimiter = detect_delimiter(content)

    df = None
    # Try detected delimiter first, then fallbacks
    delimiters_to_try = [delimiter] + [d for d in [",", ";", "\t", "|"] if d != delimiter]
    for sep in delimiters_to_try:
        try:
            candidate = pd.read_csv(io.StringIO(content), sep=sep, skipinitialspace=True)
            if len(candidate.columns) >= 3:
                df = candidate
                break
        except Exception:
            continue

    if df is None:
        # Files with metadata rows before header cause parse errors.
        # Try skipping 1-10 rows to find the real header.
        for skip in range(1, 11):
            for sep in delimiters_to_try:
                try:
                    candidate = pd.read_csv(
                        io.StringIO(content), sep=sep, skipinitialspace=True, skiprows=skip
                    )
                    if len(candidate.columns) >= 3:
                        df = candidate
                        break
                except Exception:
                    continue
            if df is not None:
                break

    if df is None:
        # Last resort: let pandas sniff the separator
        try:
            df = pd.read_csv(io.StringIO(content), sep=None, engine="python", skipinitialspace=True)
        except Exception:
            return []

    if df is None or len(df.columns) < 2:
        return []

    df.columns = [str(col).strip() for col in df.columns]

    # If columns look like data (no header row), try re-reading with header detection
    cols_str = " ".join(str(c).lower() for c in df.columns)
    has_header_keywords = any(
        kw in cols_str
        for kw in (_DATE_KEYWORDS[:8] + _DESCRIPTION_KEYWORDS[:6] + _AMOUNT_KEYWORDS[:3])
    )
    if not has_header_keywords and len(df) > 1:
        # Try to find header row in first 20 rows
        for skip in range(1, min(20, len(df))):
            try:
                df_test = pd.read_csv(
                    io.StringIO(content), sep=delimiter, skipinitialspace=True, skiprows=skip
                )
                df_test.columns = [str(c).strip() for c in df_test.columns]
                test_cols = " ".join(str(c).lower() for c in df_test.columns)
                if any(kw in test_cols for kw in _DATE_KEYWORDS[:8]):
                    df = df_test
                    break
            except Exception:
                continue

    return _parse_generic_dataframe(df, filename)


def parse_generic_excel(df: pd.DataFrame, filename: str = "") -> list[ParsedTransaction]:
    """
    Generic Excel parser that auto-detects columns by matching common header keywords.
    Works for any bank statement format from any country.
    """
    df.columns = [str(col).strip() for col in df.columns]
    return _parse_generic_dataframe(df, filename)


def _parse_generic_dataframe(df: pd.DataFrame, filename: str = "") -> list[ParsedTransaction]:
    """Core generic parsing logic that works on any DataFrame with auto-detected columns."""
    columns = list(df.columns)

    # Try to detect known bank from headers
    detected_bank = detect_bank_from_headers(columns)
    if detected_bank:
        logger.info(f"Generic parser detected bank signature: {detected_bank}")

    # Auto-detect column mappings
    date_col = _match_column_with_currency(columns, _DATE_KEYWORDS)
    desc_col = _match_column_with_currency(columns, _DESCRIPTION_KEYWORDS)
    debit_col = _match_column_with_currency(columns, _DEBIT_KEYWORDS)
    credit_col = _match_column_with_currency(columns, _CREDIT_KEYWORDS)
    amount_col = _match_column_with_currency(columns, _AMOUNT_KEYWORDS)
    balance_col = _match_column_with_currency(columns, _BALANCE_KEYWORDS)
    type_col = _match_column(columns, _TYPE_KEYWORDS)
    gross_col = _match_column_with_currency(columns, _GROSS_KEYWORDS)
    fee_col = _match_column_with_currency(columns, _FEE_KEYWORDS)
    net_col = _match_column_with_currency(columns, _NET_KEYWORDS)

    if date_col is None:
        logger.warning(f"Generic parser: no date column found in {filename}. Columns: {columns}")
        return []

    if desc_col is None:
        # Use first non-date text column as description
        for col in columns:
            if col in (date_col, balance_col, amount_col, debit_col, credit_col):
                continue
            sample = df[col].dropna().head(5)
            if sample.dtype == object and len(sample) > 0:
                desc_col = col
                break

    # If debit/credit cols resolved to the same column as type_col, they're not actual
    # amount columns — they're type indicators (e.g., "Dr/Cr" matching both "dr" and "cr")
    if type_col and debit_col == type_col:
        debit_col = None
    if type_col and credit_col == type_col:
        credit_col = None
    # Also disqualify if debit and credit map to the same column
    if debit_col and credit_col and debit_col == credit_col:
        debit_col = None
        credit_col = None

    # Determine which amount pattern we have
    has_gross_fee_net = gross_col is not None and net_col is not None
    has_separate_debit_credit = debit_col is not None or credit_col is not None
    has_single_amount = amount_col is not None

    if not has_gross_fee_net and not has_separate_debit_credit and not has_single_amount:
        # Last resort: look for any numeric column that could be an amount
        for col in columns:
            if col in (date_col, desc_col, balance_col, type_col):
                continue
            sample = df[col].dropna().head(10)
            if len(sample) > 0:
                numeric_count = sum(1 for v in sample if parse_generic_amount(v) is not None)
                if numeric_count >= len(sample) * 0.5:
                    amount_col = col
                    has_single_amount = True
                    break

    if not has_gross_fee_net and not has_separate_debit_credit and not has_single_amount:
        logger.warning(f"Generic parser: no amount columns found in {filename}. Columns: {columns}")
        return []

    # Determine region hint for date disambiguation
    region_hint = _get_region_hint(detected_bank, filename)
    if not region_hint:
        region_hint = _detect_date_region_from_data(df, date_col)

    # Detect currency from column names or a dedicated Currency column
    detected_currency = "INR"
    currency_col = _match_column(columns, ["currency", "ccy", "curr"])
    if currency_col:
        # Will read per-row
        detected_currency = None
    else:
        # Try to detect from column names like "Amount (EUR)" or "Withdrawal (USD)"
        for col in columns:
            col_upper = col.upper()
            for code in ["EUR", "USD", "GBP", "CHF", "SEK", "NOK", "DKK", "PLN", "CZK", "CAD", "AUD", "NZD", "JPY"]:
                if code in col_upper:
                    detected_currency = code
                    break
            if detected_currency != "INR":
                break

    transactions = []
    consecutive_invalid = 0

    for _, row in df.iterrows():
        # Skip summary/footer rows
        row_values = [row.get(c) for c in columns]
        if _is_summary_row(row_values):
            continue

        # Parse date
        date = parse_date_smart(row.get(date_col), region_hint=region_hint)
        if date is None:
            consecutive_invalid += 1
            if consecutive_invalid >= 5:
                break
            continue
        consecutive_invalid = 0

        # Parse description
        description = str(row.get(desc_col, "")).strip() if desc_col else ""
        if not description or description.lower() == "nan":
            description = "Unknown transaction"

        # Parse balance
        balance = parse_generic_amount(row.get(balance_col)) if balance_col else None

        # Determine amount and transaction type using smart pattern detection
        txn_type = None
        amount = None

        if has_gross_fee_net:
            # Pattern 1: Gross/Fee/Net (PayPal, Stripe)
            net_val = parse_generic_amount(row.get(net_col))
            gross_val = parse_generic_amount(row.get(gross_col))
            # Prefer net (what actually hits the account), fall back to gross
            raw_amount = net_val if net_val is not None else gross_val
            if raw_amount is not None and raw_amount != 0:
                txn_type = "credit" if raw_amount > 0 else "debit"
                amount = abs(raw_amount)

        elif has_separate_debit_credit:
            # Pattern 2: Separate Debit/Credit columns
            debit_val = parse_generic_amount(row.get(debit_col)) if debit_col else None
            credit_val = parse_generic_amount(row.get(credit_col)) if credit_col else None

            if debit_val and abs(debit_val) > 0:
                amount = abs(debit_val)
                txn_type = "debit"
            elif credit_val and abs(credit_val) > 0:
                amount = abs(credit_val)
                txn_type = "credit"

        elif has_single_amount:
            # Pattern 3: Single amount column (may need sign from type column)
            raw_amount = parse_generic_amount(row.get(amount_col))
            if raw_amount is None or raw_amount == 0:
                continue

            # Determine type from type indicator column or sign
            if type_col:
                type_val = str(row.get(type_col, "")).strip().upper()
                if any(ind in type_val for ind in ["CR", "CREDIT", "HABEN", "BIJ",
                                                    "DEPOSIT", "INCOME"]):
                    txn_type = "credit"
                    amount = abs(raw_amount)
                elif any(ind in type_val for ind in ["DR", "DEBIT", "SOLL", "AF",
                                                      "WITHDRAWAL", "CARD PAYMENT",
                                                      "CARD_PAYMENT", "BUY"]):
                    txn_type = "debit"
                    amount = abs(raw_amount)
                else:
                    # Fall back to sign
                    txn_type = "credit" if raw_amount > 0 else "debit"
                    amount = abs(raw_amount)
            else:
                # Use sign: positive = credit, negative = debit
                txn_type = "credit" if raw_amount > 0 else "debit"
                amount = abs(raw_amount)

        if amount is None or amount == 0 or txn_type is None:
            continue

        # Resolve per-row currency if a currency column exists
        row_currency = detected_currency
        if currency_col:
            cur_val = str(row.get(currency_col, "")).strip().upper()
            row_currency = cur_val if cur_val and cur_val != "NAN" else "INR"

        transactions.append(ParsedTransaction(
            date=date,
            description=description,
            amount=amount,
            transaction_type=txn_type,
            balance=balance,
            bank_name=detected_bank or "Generic",
            currency=row_currency,
        ))

    return transactions


# Mapping of bank names to CSV parsers
CSV_PARSERS = {
    "HDFC": parse_hdfc_csv,
    "ICICI": parse_icici_csv,
    "SBI": parse_sbi_csv,
    "Axis": parse_axis_csv,
    "Kotak": parse_kotak_csv,
    "IDFC": parse_idfc_csv,
    "Revolut": parse_revolut_csv,
}


def parse_csv_statement(content: str, filename: str = "") -> tuple[str, list[ParsedTransaction]]:
    """
    Parse a CSV bank statement. Auto-detects the bank and returns parsed transactions.
    Falls back to the generic parser if no specific bank is detected.

    Returns:
        Tuple of (bank_name, list of ParsedTransaction)

    Raises:
        ParsingError: If file cannot be parsed by any method
    """
    # Try bank-specific parser first
    try:
        bank = detect_bank_from_csv(content, filename)
        parser = CSV_PARSERS.get(bank)
        if parser:
            try:
                transactions = parser(content)
                if transactions:
                    return bank, transactions
            except Exception as e:
                logger.warning(f"Bank-specific parser failed for {bank}: {e}, trying generic...")
    except BankDetectionError:
        logger.info(f"No specific bank detected for {filename}, using generic parser")

    # Fall back to generic parser
    try:
        transactions = parse_generic_csv(content, filename)
        if transactions:
            return "Generic", transactions
    except Exception as e:
        raise ParsingError(f"Generic CSV parser failed: {str(e)}")

    raise ParsingError(
        "Could not parse any transactions from the file. "
        "Please ensure the file contains a header row with recognizable column names "
        "(e.g., Date, Description, Amount/Debit/Credit)."
    )


# Mapping of bank names to Excel parsers
EXCEL_PARSERS = {
    "HDFC": parse_hdfc_excel,
    "ICICI": parse_icici_excel,
    "SBI": parse_sbi_excel,
    "Axis": parse_axis_excel,
    "Kotak": parse_kotak_excel,
    "IDFC": parse_idfc_excel,
}


_EXCEL_HEADER_KEYWORDS = {
    "date", "transaction date", "txn date", "tran date", "value date",
    "posting date", "posted date", "booking date", "completed date", "started date",
    "narration", "description", "particulars", "transaction remarks", "remarks",
    "transaction details", "payment details", "payee", "name", "merchant",
    "withdrawal", "deposit", "debit", "credit", "amount", "balance",
    "money in", "money out", "paid in", "paid out",
    "cheque", "chq", "ref", "s no", "sl. no",
    "gross", "fee", "net", "currency",
    # International / European keywords
    "datum", "fecha", "data", "buchungstag", "wertstellung",
    "beschreibung", "verwendungszweck", "concepto", "omschrijving",
    "betrag", "importe", "saldo", "solde", "kontostand",
    "booking date", "posted", "memo", "text",
    # Dutch
    "boekingsdatum", "bedrag", "af", "bij",
    # French
    "libellé", "date opération",
}

# OLE2 Compound Document magic bytes (real .xls)
_OLE_MAGIC = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'
# ZIP magic bytes (real .xlsx)
_ZIP_MAGIC = b'PK\x03\x04'


def _detect_excel_file_format(file_bytes: bytes) -> str:
    """
    Detect the actual format of a file with an Excel extension.

    Indian bank exports commonly save tab-separated text or HTML tables
    with a .xls extension. This function inspects the raw bytes to determine
    the true format.

    Returns:
        One of: "xls", "xlsx", "html", "text"
    """
    header = file_bytes[:32]

    if header[:8] == _OLE_MAGIC:
        return "xls"
    if header[:4] == _ZIP_MAGIC:
        return "xlsx"

    # Check for HTML (common with some bank exports)
    text_sample = file_bytes[:1000].lower()
    if b'<html' in text_sample or b'<table' in text_sample or b'<!doctype html' in text_sample:
        return "html"

    # If it's not binary, treat as text (TSV/CSV disguised as .xls)
    return "text"


def _read_excel_with_engine(file_bytes: bytes, file_format: str, **kwargs) -> pd.DataFrame:
    """
    Read an Excel-like file using the appropriate engine based on detected format.

    Args:
        file_bytes: Raw file content
        file_format: One of "xls", "xlsx", "html", "text" from _detect_excel_file_format
        **kwargs: Additional arguments passed to pd.read_excel or pd.read_csv

    Returns:
        DataFrame with the file data
    """
    if file_format == "xls":
        return pd.read_excel(io.BytesIO(file_bytes), engine='xlrd', **kwargs)
    elif file_format == "xlsx":
        return pd.read_excel(io.BytesIO(file_bytes), engine='openpyxl', **kwargs)
    elif file_format == "html":
        tables = pd.read_html(io.BytesIO(file_bytes))
        if not tables:
            raise ParsingError("HTML file contains no tables")
        # Return the largest table (most likely the transactions)
        return max(tables, key=lambda t: len(t))
    else:
        # Text file (TSV/CSV) disguised as .xls
        content = _decode_bytes_with_fallback(file_bytes)
        # Detect delimiter: tab is most common for Indian bank TSV exports
        if '\t' in content[:2000]:
            sep = '\t'
        elif ',' in content[:2000]:
            sep = ','
        else:
            sep = '\t'
        return pd.read_csv(io.StringIO(content), sep=sep, **kwargs)


def _find_header_row_in_df(df_raw: pd.DataFrame) -> Optional[int]:
    """
    Scan a raw DataFrame for the actual header row by looking for known column keywords.
    Returns the 0-based row index of the header, or None if not detected.
    """
    for idx in range(min(len(df_raw), 30)):
        row_values = [str(v).strip().lower() for v in df_raw.iloc[idx] if pd.notna(v) and str(v).strip()]
        if len(row_values) < 3:
            continue
        matches = sum(
            1 for val in row_values
            if any(kw in val for kw in _EXCEL_HEADER_KEYWORDS)
        )
        if matches >= 3:
            return idx
    return None


def _find_excel_header_row(file_bytes: bytes, file_format: str) -> Optional[int]:
    """
    Scan an Excel file for the actual header row by looking for known column keywords.
    Indian bank Excel exports often have metadata rows before the real data table.
    Returns the 0-based row index of the header, or None if not detected.
    """
    try:
        df_raw = _read_excel_with_engine(file_bytes, file_format, header=None, nrows=30)
    except Exception:
        return None

    return _find_header_row_in_df(df_raw)


def parse_excel_statement(file_bytes: bytes, filename: str = "") -> tuple[str, list[ParsedTransaction]]:
    """
    Parse an Excel bank statement. Auto-detects the bank and returns parsed transactions.
    Supports .xlsx (openpyxl), .xls (xlrd), HTML tables, and text (TSV/CSV) files
    that are commonly saved with .xls extension by Indian bank portals.
    Falls back to generic parser if no specific bank is detected.

    Returns:
        Tuple of (bank_name, list of ParsedTransaction)

    Raises:
        ParsingError: If file cannot be parsed by any method
    """
    file_format = _detect_excel_file_format(file_bytes)
    logger.info(f"Detected file format for '{filename}': {file_format}")

    # For text-format files, try the CSV parsing path first (more robust)
    if file_format == "text":
        try:
            content = _decode_bytes_with_fallback(file_bytes)
            bank_name, transactions = parse_csv_statement(content, filename)
            if transactions:
                return bank_name, transactions
        except (BankDetectionError, ParsingError):
            pass

    try:
        header_row = _find_excel_header_row(file_bytes, file_format)
        df = _read_excel_with_engine(
            file_bytes, file_format,
            header=header_row if header_row is not None else 0,
        )

        if df.empty:
            raise ParsingError("Excel file appears to be empty")

        # Drop fully-empty columns and unnamed/placeholder columns
        df = df.dropna(axis=1, how="all")
        df = df.loc[:, [
            c for c in df.columns
            if str(c).strip()
            and str(c).lower() != "nan"
            and not str(c).startswith("Unnamed")
        ]]

        # Try bank-specific parser first
        try:
            bank = detect_bank_from_excel(df, filename)
            parser = EXCEL_PARSERS.get(bank)
            if parser:
                transactions = parser(df)
                if transactions:
                    return bank, transactions
                logger.warning(f"Bank-specific parser for {bank} returned no transactions, trying generic...")
        except BankDetectionError:
            logger.info(f"No specific bank detected for Excel file {filename}, using generic parser")

        # Fall back to generic Excel parser
        transactions = parse_generic_excel(df, filename)
        if transactions:
            return "Generic", transactions

        raise ParsingError(
            "Could not parse any transactions from the Excel file. "
            "Please ensure the file contains a header row with recognizable column names "
            "(e.g., Date, Description, Amount/Debit/Credit)."
        )

    except ParsingError:
        raise
    except Exception as e:
        raise ParsingError(f"Error parsing Excel file: {str(e)}")


def parse_pdf_statement(file_bytes: bytes, filename: str = "") -> tuple[str, list[ParsedTransaction]]:
    """
    Parse a PDF bank statement. Extracts tables using pdfplumber and normalizes.
    Falls back to generic table parsing if no specific bank is detected.

    Returns:
        Tuple of (bank_name, list of ParsedTransaction)

    Raises:
        ParsingError: If file cannot be parsed by any method
    """
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            full_text = ""
            all_tables = []

            for page in pdf.pages:
                page_text = page.extract_text() or ""
                full_text += page_text + "\n"

                tables = page.extract_tables()
                if tables:
                    all_tables.extend(tables)

            if not full_text.strip():
                raise ParsingError("PDF appears to be empty or image-only (no extractable text)")

            # Try bank-specific detection first
            try:
                bank = detect_bank_from_pdf(full_text, filename)
                transactions = _parse_pdf_tables(all_tables, bank)
                if transactions:
                    return bank, transactions
            except BankDetectionError:
                logger.info(f"No specific bank detected in PDF {filename}, using generic parsing")

            # Fall back to generic PDF table parsing
            transactions = _parse_pdf_tables(all_tables, "Generic")
            if transactions:
                return "Generic", transactions

            raise ParsingError(
                "Could not parse any transactions from the PDF. "
                "The file may be image-only or in an unsupported layout."
            )

    except ParsingError:
        raise
    except Exception as e:
        raise ParsingError(f"Error reading PDF: {str(e)}")


def _parse_pdf_tables(tables: list, bank: str) -> list[ParsedTransaction]:
    """Convert PDF-extracted tables to transactions using bank-specific logic."""
    transactions = []

    for table in tables:
        if not table or len(table) < 2:
            continue

        # Use first row as headers
        headers = [str(h).strip().lower() if h else "" for h in table[0]]

        for row in table[1:]:
            if not row or all(cell is None or str(cell).strip() == "" for cell in row):
                continue

            row_dict = {}
            for i, header in enumerate(headers):
                if i < len(row):
                    row_dict[header] = row[i]

            txn = _extract_transaction_from_row(row_dict, bank)
            if txn:
                transactions.append(txn)

    return transactions


def _extract_transaction_from_row(row: dict, bank: str) -> Optional[ParsedTransaction]:
    """Extract a transaction from a PDF table row based on bank format."""
    # Find date field
    date = None
    for key in ["date", "transaction date", "txn date", "tran date", "value date"]:
        if key in row and row[key]:
            date = parse_indian_date(str(row[key]))
            if date:
                break

    if not date:
        return None

    # Find description
    description = ""
    for key in ["narration", "description", "particulars", "transaction remarks", "remarks", "details"]:
        if key in row and row[key]:
            description = str(row[key]).strip()
            break

    if not description:
        return None

    # Find amounts
    debit = None
    credit = None
    amount = None

    for key in ["withdrawal", "withdrawal amt.", "withdrawal amt", "debit", "dr"]:
        if key in row:
            debit = parse_amount(row[key])
            break

    for key in ["deposit", "deposit amt.", "deposit amt", "credit", "cr"]:
        if key in row:
            credit = parse_amount(row[key])
            break

    # Single amount column with dr/cr indicator
    for key in ["amount", "transaction amount"]:
        if key in row:
            amount = parse_amount(row[key])
            break

    # Find balance
    balance = None
    for key in ["balance", "closing balance", "available balance"]:
        if key in row:
            balance = parse_amount(row[key])
            break

    # Find reference
    ref = None
    for key in ["ref", "chq", "cheque", "reference", "chq./ref.no."]:
        if key in row and row[key]:
            ref_val = str(row[key]).strip()
            if ref_val and ref_val != "nan" and ref_val != "None":
                ref = ref_val
                break

    # Determine transaction type and amount
    if debit and debit > 0:
        return ParsedTransaction(
            date=date, description=description, amount=debit,
            transaction_type="debit", balance=balance,
            reference_number=ref, bank_name=bank
        )
    elif credit and credit > 0:
        return ParsedTransaction(
            date=date, description=description, amount=credit,
            transaction_type="credit", balance=balance,
            reference_number=ref, bank_name=bank
        )
    elif amount and amount > 0:
        # Check for dr/cr indicator
        dr_cr = None
        for key in ["dr / cr", "dr/cr", "cr/dr", "type"]:
            if key in row and row[key]:
                dr_cr = str(row[key]).strip().upper()
                break
        txn_type = "credit" if dr_cr and "CR" in dr_cr else "debit"
        return ParsedTransaction(
            date=date, description=description, amount=amount,
            transaction_type=txn_type, balance=balance,
            reference_number=ref, bank_name=bank
        )

    return None

