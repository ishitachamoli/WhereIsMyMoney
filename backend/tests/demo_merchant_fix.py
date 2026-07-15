"""Demo of the simplified merchant extractor fix."""
from app.services.merchant_extractor import extract_merchant

# Real examples from the problem statement
examples = [
    ("BY TRANSFER-IMPS/534205572617/RE1-XX389-VISA PAY/RDA Vostr", 
     "BY TRANSFER-IMPS/534205572617/RE1-XX389-VISA PAY/RDA Vostr"),
    
    ("TO TRANSFER-UPI/DR/533849077740/Google I/UTIB/gpay-utili/UPI",
     "TO TRANSFER-UPI/DR/533849077740/Google I/UTIB/gpay-utili/UPI"),
    
    ("TO TRANSFER-UPI/DR/533512157582/KAILASH /HDFC/chamolikc@/UPI",
     "TO TRANSFER-UPI/DR/533512157582/KAILASH /HDFC/chamolikc@/UPI"),
    
    # With encoding artifacts
    ("ÊBY TRANSFER-IMPS/534205572617/RE1-XX389-VISA PAY/RDA VostrÊ",
     "BY TRANSFER-IMPS/534205572617/RE1-XX389-VISA PAY/RDA Vostr"),
]

print("🔍 Merchant Extractor - Full Description Display")
print("=" * 70)

all_passed = True
for i, (input_desc, expected) in enumerate(examples, 1):
    result = extract_merchant(input_desc)
    passed = result == expected
    all_passed = all_passed and passed
    
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"\nTest {i}: {status}")
    print(f"  Input:    {input_desc[:60]}{'...' if len(input_desc) > 60 else ''}")
    print(f"  Expected: {expected[:60]}{'...' if len(expected) > 60 else ''}")
    print(f"  Got:      {result[:60]}{'...' if len(result) > 60 else ''}")
    
    if not passed:
        print(f"  ❌ Mismatch!")
        print(f"     Expected length: {len(expected)}")
        print(f"     Got length:      {len(result)}")

print("\n" + "=" * 70)
if all_passed:
    print("✅ All tests passed! Merchant extractor is working correctly.")
    print("\n✨ Summary of fixes:")
    print("  • Full transaction descriptions are now displayed (no truncation)")
    print("  • Encoding artifacts (Ê, É, È) are cleaned")
    print("  • Leading/trailing dashes and whitespace are removed")
    print("  • Complex regex extraction has been removed")
else:
    print("❌ Some tests failed!")
