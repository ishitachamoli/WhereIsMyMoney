#!/usr/bin/env python3
"""Standalone CSV parser test - no app initialization."""
import sys
import csv

# Test 1: Basic CSV reading
print("Test 1: Reading CSV file directly...")
try:
    with open('TanishqChamoli-2026.csv', 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    print(f"✓ Successfully read {len(rows)} transactions")
    print(f"✓ Columns: {list(rows[0].keys()) if rows else 'N/A'}")
    print(f"\nFirst transaction:")
    if rows:
        for k, v in list(rows[0].items())[:5]:
            print(f"  {k}: {v}")
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)

# Test 2: Pandas reading
print("\nTest 2: Reading with pandas...")
try:
    import pandas as pd
    df = pd.read_csv('TanishqChamoli-2026.csv')
    print(f"✓ Pandas parsed {len(df)} rows, {len(df.columns)} columns")
    print(f"✓ Column dtypes:")
    for col in df.columns:
        print(f"    {col}: {df[col].dtype}")
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)

print("\n✓ All tests passed!")
