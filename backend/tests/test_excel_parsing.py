"""Unit tests for Excel file format detection and parsing in bank_parser."""
import os
import pytest
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.bank_parser import (
    _detect_excel_file_format,
    _read_excel_with_engine,
    _find_excel_header_row,
    _find_header_row_in_df,
    parse_excel_statement,
    ParsingError,
    BankDetectionError,
)


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


class TestDetectExcelFileFormat:
    """Tests for _detect_excel_file_format."""

    def test_detects_ole_xls(self):
        """Real .xls files start with OLE2 magic bytes."""
        ole_header = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1' + b'\x00' * 100
        assert _detect_excel_file_format(ole_header) == "xls"

    def test_detects_xlsx_zip(self):
        """Real .xlsx files start with ZIP magic bytes."""
        zip_header = b'PK\x03\x04' + b'\x00' * 100
        assert _detect_excel_file_format(zip_header) == "xlsx"

    def test_detects_html(self):
        """HTML tables disguised as .xls."""
        html_content = b'<html><body><table><tr><td>data</td></tr></table></body></html>'
        assert _detect_excel_file_format(html_content) == "html"

    def test_detects_html_with_doctype(self):
        """HTML with DOCTYPE disguised as .xls."""
        html_content = b'<!DOCTYPE html><html><body><table></table></body></html>'
        assert _detect_excel_file_format(html_content) == "html"

    def test_detects_text_tsv(self):
        """Tab-separated text disguised as .xls (common Indian bank export)."""
        text_content = b'Account Name\t:\tTest User\r\nBalance\t:\t1000\r\n'
        assert _detect_excel_file_format(text_content) == "text"

    def test_detects_text_csv(self):
        """CSV text disguised as .xls."""
        text_content = b'Date,Description,Amount\r\n01/01/2025,Payment,500\r\n'
        assert _detect_excel_file_format(text_content) == "text"


class TestParseExcelStatementTextFormat:
    """Test parsing of text-based .xls files (SBI format)."""

    def test_parse_sbi_text_xls_fixture(self):
        """Parse the SBI text-format .xls fixture file."""
        filepath = os.path.join(FIXTURES_DIR, "sbi_statement.xls")
        with open(filepath, "rb") as f:
            file_bytes = f.read()

        bank, transactions = parse_excel_statement(file_bytes, "sbi_statement.xls")

        assert bank == "SBI"
        assert len(transactions) == 5

        # Verify first transaction (credit)
        assert transactions[0].transaction_type == "credit"
        assert transactions[0].amount == 2600.0
        assert transactions[0].date.day == 1
        assert transactions[0].date.month == 1

        # Verify second transaction (debit)
        assert transactions[1].transaction_type == "debit"
        assert transactions[1].amount == 3375.0

        # Verify last transaction (debit)
        assert transactions[4].transaction_type == "debit"
        assert transactions[4].amount == 1200.0

    def test_parse_sbi_text_xls_detects_bank_from_content(self):
        """Bank is detected from column headers even without 'sbi' in filename."""
        filepath = os.path.join(FIXTURES_DIR, "sbi_statement.xls")
        with open(filepath, "rb") as f:
            file_bytes = f.read()

        # Use a generic filename without 'sbi'
        bank, transactions = parse_excel_statement(file_bytes, "Jan-Dec-2025.xls")
        assert bank == "SBI"
        assert len(transactions) == 5

    def test_find_header_row_in_text_xls(self):
        """Header row is correctly detected past metadata rows."""
        filepath = os.path.join(FIXTURES_DIR, "sbi_statement.xls")
        with open(filepath, "rb") as f:
            file_bytes = f.read()

        file_format = _detect_excel_file_format(file_bytes)
        assert file_format == "text"

        header_row = _find_excel_header_row(file_bytes, file_format)
        assert header_row == 20  # 0-indexed, after 20 metadata rows
