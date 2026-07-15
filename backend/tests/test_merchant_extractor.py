"""Tests for the simplified merchant extractor."""
import pytest
from app.services.merchant_extractor import extract_merchant


class TestMerchantExtractor:
    """Test the extract_merchant function."""

    def test_extract_full_imps_description(self):
        """IMPS transactions should return full description."""
        desc = "BY TRANSFER-IMPS/534205572617/RE1-XX389-VISA PAY/RDA Vostr"
        result = extract_merchant(desc)
        assert result == desc
        # Should NOT be truncated to "Imps/"
        assert "IMPS" in result
        assert "RDA Vostr" in result

    def test_extract_full_upi_description(self):
        """UPI transactions should return full description."""
        desc = "TO TRANSFER-UPI/DR/533849077740/Google I/UTIB/gpay-utili/UPI"
        result = extract_merchant(desc)
        assert result == desc
        # Should NOT be truncated to "Upi/"
        assert "TRANSFER-UPI" in result
        assert "gpay-utili" in result

    def test_extract_full_upi_description_variant(self):
        """Another UPI variant should also return full description."""
        desc = "TO TRANSFER-UPI/DR/533512157582/KAILASH /HDFC/chamolikc@/UPI"
        result = extract_merchant(desc)
        assert result == desc
        # Should NOT be truncated to "Upi/"
        assert "KAILASH" in result
        assert "chamolikc" in result

    def test_strip_encoding_artifacts(self):
        """Encoding artifacts (Ê, É, È) should be removed."""
        desc = "ÊTO TRANSFER-IMPS/534205572617/RDA VostrÊ"
        result = extract_merchant(desc)
        assert result == "TO TRANSFER-IMPS/534205572617/RDA Vostr"
        assert "Ê" not in result

    def test_strip_leading_trailing_dashes(self):
        """Leading and trailing dashes should be removed."""
        desc = "---BY TRANSFER-IMPS/534205572617/RDA Vostr---"
        result = extract_merchant(desc)
        assert result == "BY TRANSFER-IMPS/534205572617/RDA Vostr"
        assert not result.startswith("-")
        assert not result.endswith("-")

    def test_strip_whitespace(self):
        """Leading and trailing whitespace should be removed."""
        desc = "   BY TRANSFER-IMPS/534205572617/RDA Vostr   "
        result = extract_merchant(desc)
        assert result == "BY TRANSFER-IMPS/534205572617/RDA Vostr"

    def test_combined_cleaning(self):
        """Combination of artifacts, dashes, and whitespace."""
        desc = "  Ê---TO TRANSFER-UPI/DR/533849077740/Google I/UTIB/gpay-utili/UPI---Ê  "
        result = extract_merchant(desc)
        assert result == "TO TRANSFER-UPI/DR/533849077740/Google I/UTIB/gpay-utili/UPI"
        assert not result.startswith("-")
        assert not result.startswith(" ")
        assert not result.endswith("-")
        assert not result.endswith(" ")
        assert "Ê" not in result

    def test_empty_description(self):
        """Empty description should return 'Unknown'."""
        assert extract_merchant("") == "Unknown"
        assert extract_merchant(None) == "Unknown"

    def test_whitespace_only_description(self):
        """Whitespace-only description should return 'Unknown'."""
        assert extract_merchant("   ") == "Unknown"
        assert extract_merchant("\t\n") == "Unknown"

    def test_dashes_only_description(self):
        """Dashes-only description should return 'Unknown'."""
        assert extract_merchant("---") == "Unknown"
        assert extract_merchant("---   ---") == "Unknown"

    def test_preserve_internal_structure(self):
        """Internal slashes, dashes, and spaces should be preserved."""
        desc = "BY TRANSFER-IMPS/534205572617/RE1-XX389-VISA PAY/RDA Vostr"
        result = extract_merchant(desc)
        # All the slashes and dashes inside the description should be preserved
        assert result.count("/") == 3
        assert "RE1-XX389" in result
        assert "VISA PAY" in result

    def test_returns_string(self):
        """extract_merchant should always return a string, never None."""
        result = extract_merchant("Some description")
        assert isinstance(result, str)
        
        result = extract_merchant("")
        assert isinstance(result, str)
        
        result = extract_merchant(None)
        assert isinstance(result, str)
