"""Tests for the transaction explainer service."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.transaction_explainer import explain_transaction


def test_imps_incoming():
    result = explain_transaction(
        description="BY TRANSFER-IMPS/534205572617/RE1-XX389-VISA PAY/RDA Vostr",
        amount=50000,
        transaction_type="credit",
        date="Dec 15, 2025",
    )
    assert result.payment_method == "IMPS"
    assert result.direction == "incoming"
    assert result.reference == "534205572617"
    assert result.card_reference == "XX389"
    assert "RDA Vostr" in (result.recipient_or_sender or "")
    assert result.confidence > 0.5
    assert "50,000" in result.explanation
    assert "received" in result.explanation.lower()
    print(f"✓ IMPS incoming: {result.explanation}")


def test_upi_outgoing():
    result = explain_transaction(
        description="TO TRANSFER-UPI/DR/533849077740/Google I/UTIB/gpay-utili/UPI",
        amount=500,
        transaction_type="debit",
        date="Jan 3, 2026",
    )
    assert result.payment_method == "UPI"
    assert result.direction == "outgoing"
    assert result.reference == "533849077740"
    assert result.confidence > 0.4
    assert "payment" in result.explanation.lower() or "sent" in result.explanation.lower()
    print(f"✓ UPI outgoing: {result.explanation}")


def test_neft_transfer():
    result = explain_transaction(
        description="NEFT/CR/HDFC0001234/JOHN DOE ENTERPRISES/SALARY",
        amount=85000,
        transaction_type="credit",
    )
    assert result.payment_method == "NEFT"
    assert result.direction == "incoming"
    assert result.confidence > 0.4
    print(f"✓ NEFT credit: {result.explanation}")


def test_pos_swiggy():
    result = explain_transaction(
        description="POS 423456 SWIGGY BANGALORE 15/01",
        amount=450,
        transaction_type="debit",
    )
    assert result.direction == "outgoing"
    assert result.recipient_or_sender is not None
    assert "swiggy" in result.recipient_or_sender.lower()
    assert result.category_suggestion == "Food & Dining"
    print(f"✓ POS Swiggy: {result.explanation}")


def test_atm_withdrawal():
    result = explain_transaction(
        description="ATM WDL/CASH/SBI ATM NEAR HOME",
        amount=10000,
        transaction_type="debit",
    )
    assert result.payment_method == "ATM"
    assert result.direction == "outgoing"
    assert result.category_suggestion == "Cash"
    print(f"✓ ATM withdrawal: {result.explanation}")


def test_empty_description():
    result = explain_transaction(description="", amount=100, transaction_type="debit")
    assert result.confidence == 0.0
    assert "No description" in result.explanation
    print(f"✓ Empty description: {result.explanation}")


def test_salary_credit():
    result = explain_transaction(
        description="SALARY/CR/AMAZON DEVELOPMENT CENTRE/SAL MAY 2025",
        amount=150000,
        transaction_type="credit",
    )
    assert result.direction == "incoming"
    assert result.category_suggestion in ("Income", "Transfers")
    assert result.confidence > 0.4
    print(f"✓ Salary credit: {result.explanation}")


def test_netflix_subscription():
    result = explain_transaction(
        description="VISA 4567 NETFLIX INDIA",
        amount=649,
        transaction_type="debit",
    )
    assert result.recipient_or_sender is not None
    assert "netflix" in result.recipient_or_sender.lower()
    assert result.category_suggestion == "Entertainment"
    print(f"✓ Netflix: {result.explanation}")


if __name__ == "__main__":
    test_imps_incoming()
    test_upi_outgoing()
    test_neft_transfer()
    test_pos_swiggy()
    test_atm_withdrawal()
    test_empty_description()
    test_salary_credit()
    test_netflix_subscription()
    print("\n✅ All transaction explainer tests passed!")
