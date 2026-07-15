"""Test Revolut CSV parser with actual sample data."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.bank_parser import parse_csv_statement


def test_revolut_csv_parser():
    """Test that the Revolut CSV parser correctly parses the sample file."""
    # Path to test file
    test_file_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "TanishqChamoli-2026.csv"
    )
    
    if not os.path.exists(test_file_path):
        pytest.skip(f"Test file not found: {test_file_path}")
    
    # Read the CSV file
    with open(test_file_path, 'r', encoding='utf-8') as f:
        csv_content = f.read()
    
    # Parse using the parser
    bank_name, transactions = parse_csv_statement(csv_content, 'TanishqChamoli-2026.csv')
    
    # Assertions
    assert bank_name == "Revolut", f"Expected bank 'Revolut', got '{bank_name}'"
    assert len(transactions) == 862, f"Expected 862 transactions, got {len(transactions)}"
    
    # Verify first transaction
    first_txn = transactions[0]
    assert first_txn.description == "Uber Eats"
    assert first_txn.amount == 18.7
    assert first_txn.transaction_type == "debit"
    assert first_txn.balance == 700.78
    assert first_txn.bank_name == "Revolut"
    
    # Verify currency is detected from the CSV
    assert first_txn.currency == "EUR", f"Expected currency 'EUR', got '{first_txn.currency}'"
    
    # Verify transaction type distribution
    debits = sum(1 for t in transactions if t.transaction_type == "debit")
    credits = sum(1 for t in transactions if t.transaction_type == "credit")
    assert debits == 793, f"Expected 793 debits, got {debits}"
    assert credits == 69, f"Expected 69 credits, got {credits}"
    
    # Verify all have required fields
    for txn in transactions:
        assert txn.date is not None, "Transaction missing date"
        assert txn.description, "Transaction missing description"
        assert txn.amount > 0, f"Transaction amount not positive: {txn.amount}"
        assert txn.transaction_type in ("debit", "credit"), f"Invalid transaction type: {txn.transaction_type}"
    
    # Verify totals
    total_debits = sum(t.amount for t in transactions if t.transaction_type == "debit")
    total_credits = sum(t.amount for t in transactions if t.transaction_type == "credit")
    assert abs(total_debits - 68230.35) < 0.01, f"Debit total mismatch: {total_debits}"
    assert abs(total_credits - 68591.02) < 0.01, f"Credit total mismatch: {total_credits}"
    
    print("✅ All Revolut CSV parser tests passed!")


if __name__ == "__main__":
    test_revolut_csv_parser()
