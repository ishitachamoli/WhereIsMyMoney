"""Tests for the generic bank statement parser with 41-bank format support."""
import os
import sys

# Ensure app imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.bank_parser import (
    parse_generic_csv,
    parse_generic_amount,
    parse_generic_date,
    parse_csv_statement,
    parse_date_smart,
    detect_delimiter,
    detect_bank_from_headers,
    _get_region_hint,
    _detect_date_region_from_data,
    _match_column,
    _match_column_with_currency,
)


class TestParseGenericAmount:
    """Test amount parsing for various international formats."""

    def test_us_format(self):
        assert parse_generic_amount("1,234.56") == 1234.56

    def test_european_format(self):
        assert parse_generic_amount("1.234,56") == 1234.56

    def test_simple_decimal(self):
        assert parse_generic_amount("123.45") == 123.45

    def test_european_decimal_only(self):
        assert parse_generic_amount("123,45") == 123.45

    def test_negative_with_minus(self):
        assert parse_generic_amount("-500.00") == -500.00

    def test_negative_with_parentheses(self):
        assert parse_generic_amount("(500.00)") == -500.00

    def test_negative_trailing_minus(self):
        assert parse_generic_amount("500.00-") == -500.00

    def test_currency_euro(self):
        assert parse_generic_amount("€1.234,56") == 1234.56

    def test_currency_dollar(self):
        assert parse_generic_amount("$1,234.56") == 1234.56

    def test_currency_pound(self):
        assert parse_generic_amount("£500.00") == 500.00

    def test_currency_rupee(self):
        assert parse_generic_amount("₹10,000.50") == 10000.50

    def test_none_input(self):
        assert parse_generic_amount(None) is None

    def test_empty_string(self):
        assert parse_generic_amount("") is None

    def test_dash(self):
        assert parse_generic_amount("-") is None

    def test_float_input(self):
        assert parse_generic_amount(42.5) == 42.5

    def test_int_input(self):
        assert parse_generic_amount(100) == 100.0


class TestParseDateSmart:
    """Test smart date parsing with disambiguation."""

    def test_iso_format(self):
        d = parse_date_smart("2024-01-15")
        assert d is not None
        assert d.year == 2024 and d.month == 1 and d.day == 15

    def test_iso_with_time(self):
        d = parse_date_smart("2024-01-15 14:23:45")
        assert d is not None
        assert d.year == 2024 and d.month == 1 and d.day == 15

    def test_yyyymmdd_no_separators(self):
        """ING Netherlands format."""
        d = parse_date_smart("20240115")
        assert d is not None
        assert d.year == 2024 and d.month == 1 and d.day == 15

    def test_german_dot_format(self):
        d = parse_date_smart("15.01.2024")
        assert d is not None
        assert d.year == 2024 and d.month == 1 and d.day == 15

    def test_dd_mm_yyyy_unambiguous(self):
        """Day > 12 makes it unambiguous DD/MM/YYYY."""
        d = parse_date_smart("25/01/2024")
        assert d is not None
        assert d.year == 2024 and d.month == 1 and d.day == 25

    def test_mm_dd_yyyy_unambiguous(self):
        """Second part > 12 makes it unambiguous MM/DD/YYYY."""
        d = parse_date_smart("01/25/2024")
        assert d is not None
        assert d.year == 2024 and d.month == 1 and d.day == 25

    def test_ambiguous_us_hint(self):
        """Ambiguous date (both <= 12) with US region hint = MM/DD."""
        d = parse_date_smart("01/05/2024", region_hint="US")
        assert d is not None
        assert d.year == 2024 and d.month == 1 and d.day == 5

    def test_ambiguous_eu_hint(self):
        """Ambiguous date (both <= 12) with EU region hint = DD/MM."""
        d = parse_date_smart("01/05/2024", region_hint="EU")
        assert d is not None
        assert d.year == 2024 and d.month == 5 and d.day == 1

    def test_ambiguous_india_hint(self):
        """India uses DD/MM like Europe."""
        d = parse_date_smart("01/05/2024", region_hint="India")
        assert d is not None
        assert d.year == 2024 and d.month == 5 and d.day == 1

    def test_ambiguous_no_hint_defaults_dd_mm(self):
        """Without hint, defaults to DD/MM (majority of world)."""
        d = parse_date_smart("05/06/2024")
        assert d is not None
        assert d.year == 2024 and d.month == 6 and d.day == 5

    def test_month_name_dd_mmm_yyyy(self):
        d = parse_date_smart("15 Jan 2024")
        assert d is not None
        assert d.year == 2024 and d.month == 1 and d.day == 15

    def test_month_name_dd_dash_mmm_dash_yyyy(self):
        d = parse_date_smart("15-Jan-2024")
        assert d is not None
        assert d.year == 2024 and d.month == 1 and d.day == 15

    def test_short_year(self):
        d = parse_date_smart("15/01/24")
        assert d is not None
        assert d.year == 2024 and d.month == 1 and d.day == 15

    def test_none_input(self):
        assert parse_date_smart(None) is None

    def test_nan(self):
        assert parse_date_smart("nan") is None

    def test_empty(self):
        assert parse_date_smart("") is None


class TestDetectDelimiter:
    """Test delimiter detection."""

    def test_comma_delimiter(self):
        content = "Date,Description,Amount\n01/01/2024,Test,100.00\n"
        assert detect_delimiter(content) == ','

    def test_semicolon_delimiter(self):
        content = "Datum;Beschreibung;Betrag\n15.01.2024;Test;100,00\n"
        assert detect_delimiter(content) == ';'

    def test_tab_delimiter(self):
        content = "Date\tDescription\tAmount\n01/01/2024\tTest\t100.00\n"
        assert detect_delimiter(content) == '\t'

    def test_pipe_delimiter(self):
        content = "Date|Description|Amount\n01/01/2024|Test|100.00\n"
        assert detect_delimiter(content) == '|'


class TestDetectBankFromHeaders:
    """Test bank signature detection."""

    def test_chase(self):
        headers = ["Transaction Date", "Post Date", "Description", "Amount", "Type", "Balance"]
        assert detect_bank_from_headers(headers) == "Chase"

    def test_paypal(self):
        headers = ["Date", "Time", "TimeZone", "Name", "Type", "Status", "Currency", "Gross", "Fee", "Net"]
        assert detect_bank_from_headers(headers) == "PayPal"

    def test_revolut(self):
        headers = ["Type", "Product", "Started Date", "Completed Date", "Description", "Amount", "Fee", "Currency"]
        assert detect_bank_from_headers(headers) == "Revolut"

    def test_n26(self):
        headers = ["Date", "Payee", "Account number", "Transaction type", "Payment reference", "Amount (EUR)"]
        assert detect_bank_from_headers(headers) == "N26"

    def test_capital_one(self):
        headers = ["Transaction Date", "Posted Date", "Card No.", "Description", "Category", "Debit", "Credit"]
        assert detect_bank_from_headers(headers) == "Capital One"

    def test_santander(self):
        headers = ["Date", "Description", "Money In", "Money Out", "Balance"]
        assert detect_bank_from_headers(headers) == "Santander UK"

    def test_unknown_bank(self):
        headers = ["Column1", "Column2", "Column3"]
        assert detect_bank_from_headers(headers) is None


class TestMatchColumnWithCurrency:
    """Test column matching with currency in parentheses."""

    def test_amount_eur(self):
        cols = ["Date", "Description", "Amount (EUR)", "Balance"]
        result = _match_column_with_currency(cols, ["amount"])
        assert result == "Amount (EUR)"

    def test_betrag_eur(self):
        cols = ["Datum", "Beschreibung", "Betrag (EUR)", "Saldo"]
        result = _match_column_with_currency(cols, ["betrag"])
        assert result == "Betrag (EUR)"

    def test_direct_match_preferred(self):
        cols = ["Date", "Amount", "Amount (EUR)"]
        result = _match_column_with_currency(cols, ["amount"])
        assert result == "Amount"


class TestGenericCSVParser:
    """Test the full generic CSV parser with various bank formats."""

    def test_european_single_amount_column(self):
        """European bank with single amount column (positive=credit, negative=debit)."""
        csv_content = """Datum,Beschreibung,Betrag,Saldo
15.01.2024,Gehalt Firma GmbH,2500.00,5000.00
16.01.2024,Miete Januar,-800.00,4200.00
17.01.2024,Supermarkt Einkauf,-45.50,4154.50
"""
        transactions = parse_generic_csv(csv_content, "deutsche_bank.csv")
        assert len(transactions) == 3

        # First transaction: credit (positive amount)
        assert transactions[0].transaction_type == "credit"
        assert transactions[0].amount == 2500.00
        assert "Gehalt" in transactions[0].description

        # Second transaction: debit (negative amount)
        assert transactions[1].transaction_type == "debit"
        assert transactions[1].amount == 800.00

        # Third transaction: debit (negative amount)
        assert transactions[2].transaction_type == "debit"
        assert transactions[2].amount == 45.50

    def test_separate_debit_credit_columns(self):
        """Bank with separate Debit and Credit columns."""
        csv_content = """Date,Description,Debit,Credit,Balance
2024-01-15,Salary,,5000.00,10000.00
2024-01-16,Rent Payment,1200.00,,8800.00
2024-01-17,Grocery Store,85.50,,8714.50
"""
        transactions = parse_generic_csv(csv_content, "any_bank.csv")
        assert len(transactions) == 3

        assert transactions[0].transaction_type == "credit"
        assert transactions[0].amount == 5000.00

        assert transactions[1].transaction_type == "debit"
        assert transactions[1].amount == 1200.00

        assert transactions[2].transaction_type == "debit"
        assert transactions[2].amount == 85.50

    def test_amount_with_type_indicator(self):
        """Bank with single Amount column and D/C type indicator."""
        csv_content = """Transaction Date,Details,Amount,Dr/Cr,Balance
15/01/2024,Monthly Salary,5000.00,CR,10000.00
16/01/2024,Electricity Bill,150.00,DR,9850.00
17/01/2024,Online Shopping,200.00,DR,9650.00
"""
        transactions = parse_generic_csv(csv_content, "statement.csv")
        assert len(transactions) == 3

        assert transactions[0].transaction_type == "credit"
        assert transactions[0].amount == 5000.00

        assert transactions[1].transaction_type == "debit"
        assert transactions[1].amount == 150.00

    def test_semicolon_separated(self):
        """European CSV with semicolons as separator."""
        csv_content = """Datum;Beschreibung;Betrag;Saldo
15.01.2024;Gehalt;2500,00;5000,00
16.01.2024;Miete;-800,00;4200,00
"""
        transactions = parse_generic_csv(csv_content, "european_bank.csv")
        assert len(transactions) == 2

        assert transactions[0].transaction_type == "credit"
        assert transactions[0].amount == 2500.00

        assert transactions[1].transaction_type == "debit"
        assert transactions[1].amount == 800.00

    def test_dutch_bank_format(self):
        """Dutch bank with 'af' (debit) and 'bij' (credit) columns."""
        csv_content = """Datum,Omschrijving,Af,Bij,Saldo
15-01-2024,Salaris,,3000.00,5000.00
16-01-2024,Huur,1000.00,,4000.00
17-01-2024,Albert Heijn,52.30,,3947.70
"""
        transactions = parse_generic_csv(csv_content, "nl_bank.csv")
        assert len(transactions) == 3

        assert transactions[0].transaction_type == "credit"
        assert transactions[0].amount == 3000.00

        assert transactions[1].transaction_type == "debit"
        assert transactions[1].amount == 1000.00

    def test_fallback_from_bank_detection(self):
        """parse_csv_statement should fall back to generic when bank not detected."""
        csv_content = """Booking Date,Memo,Amount,Running Balance
2024-01-15,Wire Transfer: Monthly Salary,3500.00,8500.00
2024-01-16,Direct Debit: Insurance,-120.00,8380.00
2024-01-17,Card Payment: Restaurant,-45.00,8335.00
"""
        bank_name, transactions = parse_csv_statement(csv_content, "my_statement.csv")
        assert bank_name == "Generic"
        assert len(transactions) == 3

        assert transactions[0].transaction_type == "credit"
        assert transactions[0].amount == 3500.00

        assert transactions[1].transaction_type == "debit"
        assert transactions[1].amount == 120.00

    # ===================================================================
    # NEW: Tests for 41-bank format support
    # ===================================================================

    def test_chase_format(self):
        """Chase US bank: MM/DD/YYYY dates, single signed amount."""
        csv_content = """Transaction Date,Post Date,Description,Category,Type,Amount,Memo
01/15/2024,01/16/2024,AMAZON.COM,Shopping,Sale,-47.99,
01/17/2024,01/18/2024,PAYROLL DIRECT DEP,Income,Payment,3500.00,
"""
        transactions = parse_generic_csv(csv_content, "chase_statement.csv")
        assert len(transactions) == 2

        assert transactions[0].transaction_type == "debit"
        assert transactions[0].amount == 47.99
        assert "AMAZON" in transactions[0].description
        # Chase detected, US date format: month=1, day=15
        assert transactions[0].date.month == 1
        assert transactions[0].date.day == 15

        assert transactions[1].transaction_type == "credit"
        assert transactions[1].amount == 3500.00

    def test_bank_of_america_format(self):
        """Bank of America: MM/DD, single amount, running balance."""
        csv_content = """Date,Description,Amount,Running Bal.
01/15/2024,PAYROLL DIRECT DEP,3500.00,8500.00
01/16/2024,ELECTRIC BILL AUTO PAY,-120.00,8380.00
"""
        transactions = parse_generic_csv(csv_content, "bofa_statement.csv")
        assert len(transactions) == 2

        assert transactions[0].transaction_type == "credit"
        assert transactions[0].amount == 3500.00

        assert transactions[1].transaction_type == "debit"
        assert transactions[1].amount == 120.00

    def test_capital_one_format(self):
        """Capital One: ISO dates, separate debit/credit."""
        csv_content = """Transaction Date,Posted Date,Card No.,Description,Category,Debit,Credit
2024-01-15,2024-01-16,1234,AMAZON.COM,Merchandise,47.99,
2024-01-20,2024-01-20,1234,PAYMENT - THANK YOU,Payment,,500.00
"""
        transactions = parse_generic_csv(csv_content, "capital_one.csv")
        assert len(transactions) == 2

        assert transactions[0].transaction_type == "debit"
        assert transactions[0].amount == 47.99
        assert transactions[0].date.year == 2024
        assert transactions[0].date.month == 1
        assert transactions[0].date.day == 15

        assert transactions[1].transaction_type == "credit"
        assert transactions[1].amount == 500.00

    def test_citi_format(self):
        """Citibank: Status column, separate debit/credit."""
        csv_content = """Status,Date,Description,Debit,Credit,Member Name
Cleared,01/15/2024,GROCERY STORE,85.50,,John Doe
Cleared,01/20/2024,PAYROLL,,3000.00,John Doe
"""
        transactions = parse_generic_csv(csv_content, "citi_statement.csv")
        assert len(transactions) == 2

        assert transactions[0].transaction_type == "debit"
        assert transactions[0].amount == 85.50

        assert transactions[1].transaction_type == "credit"
        assert transactions[1].amount == 3000.00

    def test_barclays_format(self):
        """Barclays UK: Single signed amount, DD/MM/YYYY."""
        csv_content = """Number,Date,Account,Amount,Subcategory,Memo
123456789,15/01/2024,Barclays Account,-45.99,Shopping,AMAZON.CO.UK
987654321,20/01/2024,Barclays Account,2500.00,Income,SALARY
"""
        transactions = parse_generic_csv(csv_content, "barclays.csv")
        assert len(transactions) == 2

        assert transactions[0].transaction_type == "debit"
        assert transactions[0].amount == 45.99
        assert transactions[0].date.day == 15
        assert transactions[0].date.month == 1

        assert transactions[1].transaction_type == "credit"
        assert transactions[1].amount == 2500.00

    def test_monzo_format(self):
        """Monzo UK: Very detailed format with Money Out/Money In."""
        csv_content = """Date,Time,Type,Name,Emoji,Category,Amount,Currency,Local amount,Local currency,Notes and #tags,Address,Receipt,Description,Category split,Money Out,Money In
15/01/2024,14:23:00,Card payment,Tesco,🛒,Groceries,-25.50,GBP,-25.50,GBP,Weekly shop,,,,,-25.50,
20/01/2024,09:00:00,Bank transfer,Salary,💰,Income,2500.00,GBP,2500.00,GBP,Salary,,,,,,2500.00
"""
        transactions = parse_generic_csv(csv_content, "monzo.csv")
        assert len(transactions) == 2

        assert transactions[0].transaction_type == "debit"
        assert transactions[0].amount == 25.50

        assert transactions[1].transaction_type == "credit"
        assert transactions[1].amount == 2500.00

    def test_n26_format(self):
        """N26 Germany: ISO dates, amount with currency in header."""
        csv_content = """Date,Payee,Account number,Transaction type,Payment reference,Amount (EUR)
2024-01-15,REWE Supermarket,DE89370400440532013000,MasterCard Payment,Card Payment,-45.67
2024-01-20,Salary,DE89370400440532013000,Income,Monthly Salary,2500.00
"""
        transactions = parse_generic_csv(csv_content, "n26.csv")
        assert len(transactions) == 2

        assert transactions[0].transaction_type == "debit"
        assert transactions[0].amount == 45.67
        assert "REWE" in transactions[0].description

        assert transactions[1].transaction_type == "credit"
        assert transactions[1].amount == 2500.00

    def test_revolut_generic(self):
        """Revolut format through generic parser."""
        csv_content = """Type,Product,Started Date,Completed Date,Description,Amount,Fee,Currency,State,Balance
CARD_PAYMENT,Current,2024-01-15 14:23:45,2024-01-15 14:23:45,Tesco,-25.50,0,GBP,COMPLETED,1524.50
TRANSFER,Current,2024-01-16 09:00:00,2024-01-16 09:00:00,From John,100.00,0,GBP,COMPLETED,1624.50
"""
        transactions = parse_generic_csv(csv_content, "revolut.csv")
        assert len(transactions) == 2

        assert transactions[0].transaction_type == "debit"
        assert transactions[0].amount == 25.50

        assert transactions[1].transaction_type == "credit"
        assert transactions[1].amount == 100.00

    def test_santander_uk_format(self):
        """Santander UK: Money In / Money Out columns."""
        csv_content = """Date,Description,Money In,Money Out,Balance
15/01/2024,SALARY,,, 
15/01/2024,DIRECT DEBIT GAS,,45.00,4955.00
15/01/2024,SALARY CREDIT,3000.00,,7955.00
"""
        transactions = parse_generic_csv(csv_content, "santander.csv")
        assert len(transactions) >= 2

        # Find the debit and credit transactions
        debits = [t for t in transactions if t.transaction_type == "debit"]
        credits = [t for t in transactions if t.transaction_type == "credit"]
        assert len(debits) >= 1
        assert debits[0].amount == 45.00
        assert len(credits) >= 1
        assert credits[0].amount == 3000.00

    def test_paypal_gross_fee_net(self):
        """PayPal: Gross/Fee/Net pattern."""
        csv_content = """Date,Time,TimeZone,Name,Type,Status,Currency,Gross,Fee,Net,From Email,To Email,Transaction ID
01/15/2024,10:00:00,UTC,eBay Sale,Express Checkout,Completed,USD,47.99,-1.69,46.30,buyer@email.com,seller@email.com,TXN123
01/16/2024,11:00:00,UTC,Monthly Sub,Subscription,Completed,USD,-9.99,0.00,-9.99,seller@email.com,service@email.com,TXN456
"""
        transactions = parse_generic_csv(csv_content, "paypal.csv")
        assert len(transactions) == 2

        # First: net is positive (credit)
        assert transactions[0].transaction_type == "credit"
        assert transactions[0].amount == 46.30

        # Second: net is negative (debit)
        assert transactions[1].transaction_type == "debit"
        assert transactions[1].amount == 9.99

    def test_lloyds_format(self):
        """Lloyds UK: Separate Debit Amount / Credit Amount."""
        csv_content = """Transaction Date,Transaction Type,Sort Code,Account Number,Transaction Description,Debit Amount,Credit Amount,Balance
15/01/2024,DD,12-34-56,12345678,GAS COMPANY,45.00,,4955.00
20/01/2024,TFR,12-34-56,12345678,SALARY,,3000.00,7955.00
"""
        transactions = parse_generic_csv(csv_content, "lloyds.csv")
        assert len(transactions) == 2

        assert transactions[0].transaction_type == "debit"
        assert transactions[0].amount == 45.00
        assert transactions[0].date.day == 15

        assert transactions[1].transaction_type == "credit"
        assert transactions[1].amount == 3000.00

    def test_wise_format(self):
        """Wise (TransferWise): DD-MM-YYYY, signed amount."""
        csv_content = """TransferWise ID,Date,Amount,Currency,Description,Payment Reference,Running Balance
TXN001,15-01-2024,-250.00,GBP,Transfer to EUR,,1750.00
TXN002,20-01-2024,3000.00,GBP,Salary from Company,,4750.00
"""
        transactions = parse_generic_csv(csv_content, "wise.csv")
        assert len(transactions) == 2

        assert transactions[0].transaction_type == "debit"
        assert transactions[0].amount == 250.00
        assert transactions[0].date.day == 15
        assert transactions[0].date.month == 1

        assert transactions[1].transaction_type == "credit"
        assert transactions[1].amount == 3000.00

    def test_deutsche_bank_semicolon(self):
        """Deutsche Bank Germany: Semicolons, German headers, DD.MM.YYYY."""
        csv_content = """Buchungstag;Wertstellung;Buchungstext;Verwendungszweck;Betrag;Währung;Saldo
15.01.2024;15.01.2024;Lastschrift;Miete Januar;-800,00;EUR;4200,00
20.01.2024;20.01.2024;Gehalt;Firma GmbH;2500,00;EUR;6700,00
"""
        transactions = parse_generic_csv(csv_content, "deutsche_bank.csv")
        assert len(transactions) == 2

        assert transactions[0].transaction_type == "debit"
        assert transactions[0].amount == 800.00
        assert transactions[0].date.day == 15
        assert transactions[0].date.month == 1

        assert transactions[1].transaction_type == "credit"
        assert transactions[1].amount == 2500.00

    def test_discover_format(self):
        """Discover US: Abbreviated header, MM/DD, signed amount."""
        csv_content = """Trans. Date,Post Date,Description,Amount,Category
01/15/2024,01/16/2024,AMAZON.COM,-47.99,Merchandise
01/20/2024,01/20/2024,AUTOPAY PAYMENT,500.00,Payments
"""
        transactions = parse_generic_csv(csv_content, "discover.csv")
        assert len(transactions) == 2

        assert transactions[0].transaction_type == "debit"
        assert transactions[0].amount == 47.99

        assert transactions[1].transaction_type == "credit"
        assert transactions[1].amount == 500.00

    def test_hdfc_generic_fallback(self):
        """HDFC India format through generic parser (if specific parser fails)."""
        csv_content = """Date,Narration,Debit Amount,Credit Amount,Closing Balance
15/01/2024,UPI-MERCHANT PAYMENT,250.00,,15750.00
20/01/2024,SALARY CREDIT,,45000.00,60750.00
"""
        transactions = parse_generic_csv(csv_content, "statement.csv")
        assert len(transactions) == 2

        assert transactions[0].transaction_type == "debit"
        assert transactions[0].amount == 250.00

        assert transactions[1].transaction_type == "credit"
        assert transactions[1].amount == 45000.00

    def test_sbi_date_format(self):
        """SBI India: DD MMM YYYY date format."""
        csv_content = """Txn Date,Value Date,Description,Ref No.,Debit,Credit,Balance
15 Jan 2024,15 Jan 2024,UPI/123456789/Payment,UPI123456789,500.00,,48500.00
20 Jan 2024,20 Jan 2024,SALARY CREDIT BY TRANSFER,NEFT456789,,50000.00,98500.00
"""
        transactions = parse_generic_csv(csv_content, "statement.csv")
        assert len(transactions) == 2

        assert transactions[0].transaction_type == "debit"
        assert transactions[0].amount == 500.00
        assert transactions[0].date.day == 15
        assert transactions[0].date.month == 1

        assert transactions[1].transaction_type == "credit"
        assert transactions[1].amount == 50000.00

    def test_metadata_rows_skipped(self):
        """File with metadata rows before header should still be parsed."""
        csv_content = """Account Number: 1234567890
Export Date: 2024-01-31

Transaction Date,Post Date,Description,Amount,Type
01/15/2024,01/16/2024,GROCERY STORE,-45.99,Sale
01/20/2024,01/20/2024,DIRECT DEPOSIT,3500.00,Payment
"""
        transactions = parse_generic_csv(csv_content, "chase.csv")
        assert len(transactions) == 2

        assert transactions[0].transaction_type == "debit"
        assert transactions[0].amount == 45.99

        assert transactions[1].transaction_type == "credit"
        assert transactions[1].amount == 3500.00

    def test_summary_rows_skipped(self):
        """Summary/footer rows containing 'total' should be skipped."""
        csv_content = """Date,Description,Amount,Balance
2024-01-15,Salary,3000.00,5000.00
2024-01-16,Groceries,-50.00,4950.00
2024-01-31,Total Debit: 50.00,,
2024-01-31,Total Credit: 3000.00,,
"""
        transactions = parse_generic_csv(csv_content, "statement.csv")
        # Only 2 real transactions, summary rows skipped
        assert len(transactions) == 2

    def test_consecutive_invalid_rows_stop(self):
        """Parser should stop after 5 consecutive invalid date rows."""
        csv_content = """Date,Description,Amount
2024-01-15,Valid Transaction,100.00
invalid,Bad Row 1,0
invalid,Bad Row 2,0
invalid,Bad Row 3,0
invalid,Bad Row 4,0
invalid,Bad Row 5,0
2024-01-20,This should not be reached,200.00
"""
        transactions = parse_generic_csv(csv_content, "statement.csv")
        assert len(transactions) == 1
        assert transactions[0].amount == 100.00

    def test_starling_format(self):
        """Starling Bank UK: Currency in header, spending category."""
        csv_content = """Date,Counter Party,Reference,Type,Amount (GBP),Balance (GBP),Spending Category,Notes
15/01/2024,Tesco,Card Payment,CARD,-25.50,1524.50,GROCERIES,
20/01/2024,Employer Ltd,Salary,FASTER_PAYMENT,3000.00,4524.50,INCOME,
"""
        transactions = parse_generic_csv(csv_content, "starling.csv")
        assert len(transactions) == 2

        assert transactions[0].transaction_type == "debit"
        assert transactions[0].amount == 25.50

        assert transactions[1].transaction_type == "credit"
        assert transactions[1].amount == 3000.00

    def test_natwest_format(self):
        """NatWest UK: 'Value' column as amount."""
        csv_content = """Date,Type,Description,Value,Balance,Account Name,Account Number
15/01/2024,DEB,DIRECT DEBIT - GAS CO,-45.00,4955.00,Current Account,12345678
20/01/2024,TFR,SALARY,3000.00,7955.00,Current Account,12345678
"""
        transactions = parse_generic_csv(csv_content, "natwest.csv")
        assert len(transactions) == 2

        assert transactions[0].transaction_type == "debit"
        assert transactions[0].amount == 45.00

        assert transactions[1].transaction_type == "credit"
        assert transactions[1].amount == 3000.00

    def test_indian_bank_withdrawal_deposit(self):
        """Indian bank using Withdrawal/Deposit column names."""
        csv_content = """Transaction Date,Value Date,Description,Cheque Number,Withdrawal,Deposit,Balance
01/01/2024,01/01/2024,ATM WITHDRAWAL 123456,,500.00,,45500.00
05/01/2024,05/01/2024,NEFT CREDIT FROM ABC,,,25000.00,70500.00
"""
        transactions = parse_generic_csv(csv_content, "icici_statement.csv")
        assert len(transactions) == 2

        assert transactions[0].transaction_type == "debit"
        assert transactions[0].amount == 500.00

        assert transactions[1].transaction_type == "credit"
        assert transactions[1].amount == 25000.00


class TestGetRegionHint:
    """Test region hint detection."""

    def test_us_bank(self):
        assert _get_region_hint("Chase") == "US"
        assert _get_region_hint("Bank of America") == "US"
        assert _get_region_hint("Wells Fargo") == "US"

    def test_eu_bank(self):
        assert _get_region_hint("Barclays") == "EU"
        assert _get_region_hint("N26") == "EU"
        assert _get_region_hint("Deutsche Bank") == "EU"

    def test_india_bank(self):
        assert _get_region_hint("HDFC") == "India"
        assert _get_region_hint("SBI") == "India"

    def test_filename_hint(self):
        assert _get_region_hint(None, "chase_statement.csv") == "US"
        assert _get_region_hint(None, "bofa_export.csv") == "US"

    def test_no_hint(self):
        assert _get_region_hint(None, "my_bank.csv") is None


class TestParseGenericDate:
    """Test the older generic date parser still works (backwards compatibility)."""

    def test_iso_format(self):
        d = parse_generic_date("2024-01-15")
        assert d is not None
        assert d.year == 2024 and d.month == 1 and d.day == 15

    def test_eu_slash(self):
        d = parse_generic_date("15/01/2024")
        assert d is not None
        assert d.year == 2024 and d.month == 1 and d.day == 15

    def test_eu_dot(self):
        d = parse_generic_date("15.01.2024")
        assert d is not None
        assert d.year == 2024 and d.month == 1 and d.day == 15

    def test_eu_dash(self):
        d = parse_generic_date("15-01-2024")
        assert d is not None
        assert d.year == 2024 and d.month == 1 and d.day == 15

    def test_month_name(self):
        d = parse_generic_date("15 Jan 2024")
        assert d is not None
        assert d.year == 2024 and d.month == 1 and d.day == 15

    def test_month_name_dash(self):
        d = parse_generic_date("15-Jan-2024")
        assert d is not None
        assert d.year == 2024 and d.month == 1 and d.day == 15

    def test_none_input(self):
        assert parse_generic_date(None) is None

    def test_nan(self):
        assert parse_generic_date("nan") is None

    def test_empty(self):
        assert parse_generic_date("") is None


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
