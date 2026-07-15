#!/usr/bin/env python3
"""Test runner that exercises the classification pipeline end-to-end.

Runs all tests without requiring pytest (which needs unittest module).
"""

import sys
import json
import tempfile
import traceback
from pathlib import Path

sys.path.insert(0, "/local/home/tchamoli/roko-projects/personal/whereIsMyMoneyGoing/backend")

# Import all modules
from app.services.classification.categories import CategoryTaxonomy, TopCategory
from app.services.classification.confidence import (
    ClassificationResult,
    ConfidenceLevel,
    compute_ml_confidence,
    compute_rule_confidence,
    needs_manual_review,
)
from app.services.classification.feedback import FeedbackEntry, FeedbackStore
from app.services.classification.pipeline import ClassificationPipeline, PipelineConfig
from app.services.classification.rule_engine import RuleEngine
from app.services.classification.rules.keywords import find_keyword_matches, get_best_keyword_match
from app.services.classification.rules.merchant_patterns import MERCHANT_PATTERNS
from app.services.classification.rules.transaction_codes import (
    extract_counterparty_from_code,
    parse_transaction_code,
)


passed = 0
failed = 0
errors = []


def test(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✓ {name}")
    else:
        failed += 1
        msg = f"  ✗ {name}"
        if detail:
            msg += f" — {detail}"
        print(msg)
        errors.append(msg)


# ═══════════════════════════════════════════════════════════════════════════════
# CATEGORY TAXONOMY TESTS
# ═══════════════════════════════════════════════════════════════════════════════

print("\n═══ Category Taxonomy Tests ═══")
taxonomy = CategoryTaxonomy()

test("All 15 top categories present", len(taxonomy.top_categories) == 15, f"got {len(taxonomy.top_categories)}")
test("Food & Dining in labels", "Food & Dining" in taxonomy.category_labels)
test("Get category by name", taxonomy.get_category("Food & Dining") is not None)
test("Get category case-insensitive", taxonomy.get_category("food & dining") is not None)
test("Get subcategories", "Restaurants" in taxonomy.get_subcategories(TopCategory.FOOD_DINING))
test("Resolve exact category", taxonomy.resolve_category("Food & Dining") == TopCategory.FOOD_DINING)
test("Resolve partial category", taxonomy.resolve_category("food") == TopCategory.FOOD_DINING)
test("Resolve unknown returns None", taxonomy.resolve_category("xyzzy") is None)
test("Get emoji", taxonomy.get_emoji(TopCategory.TRANSPORTATION) == "🚗")
test("Get color", taxonomy.get_color(TopCategory.HEALTHCARE) == "#10B981")


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIDENCE SCORING TESTS
# ═══════════════════════════════════════════════════════════════════════════════

print("\n═══ Confidence Scoring Tests ═══")

conf = compute_rule_confidence(pattern_matched=True, keyword_matched=False)
test("Rule confidence: pattern match >= 0.95", conf >= 0.95, f"got {conf}")

conf = compute_rule_confidence(pattern_matched=False, keyword_matched=True)
test("Rule confidence: keyword match 0.75-0.85", 0.75 <= conf <= 0.85, f"got {conf}")

conf = compute_rule_confidence(pattern_matched=False, keyword_matched=False)
test("Rule confidence: no match = 0", conf == 0.0)

conf = compute_ml_confidence(top_score=0.9, second_score=0.05)
test("ML confidence: high gap >= 0.75", conf >= 0.75, f"got {conf}")

conf = compute_ml_confidence(top_score=0.3, second_score=0.25)
test("ML confidence: low gap < 0.5", conf < 0.5, f"got {conf}")

result = ClassificationResult(category="Other", confidence=0.3, source="test")
test("Needs review: low confidence", needs_manual_review(result) is True)

result = ClassificationResult(category="Food", confidence=0.95, source="test")
test("No review needed: high confidence", needs_manual_review(result) is False)

result = ClassificationResult(category="test", confidence=0.9, source="t")
test("Confidence level HIGH for 0.9", result.confidence_level == ConfidenceLevel.HIGH)

result = ClassificationResult(category="test", confidence=0.3, source="t")
test("Confidence level VERY_LOW for 0.3", result.confidence_level == ConfidenceLevel.VERY_LOW)


# ═══════════════════════════════════════════════════════════════════════════════
# TRANSACTION CODE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

print("\n═══ Transaction Code Tests ═══")

info = parse_transaction_code("POS 423456 SWIGGY BANGALORE")
test("Parse POS code", info is not None and info.transaction_type == "POS" and info.is_debit)

info = parse_transaction_code("UPI/DR/123456/PayeeName/payee@vpa/")
test("Parse UPI debit", info is not None and info.transaction_type == "UPI_DEBIT")

info = parse_transaction_code("UPI/CR/123456/PayerName/payer@vpa/")
test("Parse UPI credit", info is not None and info.transaction_type == "UPI_CREDIT" and not info.is_debit)

info = parse_transaction_code("ATM WDL NFS SBI ATM")
test("Parse ATM withdrawal", info is not None and info.transaction_type == "ATM")

info = parse_transaction_code("RANDOM TEXT HERE")
test("Unknown code returns None", info is None)

cp = extract_counterparty_from_code("POS 423456 SWIGGY BANGALORE")
test("Extract counterparty from POS", cp is not None and "SWIGGY" in cp.upper())

cp = extract_counterparty_from_code("UPI/DR/123456/JOHN DOE/john@upi/")
test("Extract counterparty from UPI", cp is not None and "JOHN" in cp.upper())


# ═══════════════════════════════════════════════════════════════════════════════
# KEYWORD MATCHING TESTS
# ═══════════════════════════════════════════════════════════════════════════════

print("\n═══ Keyword Matching Tests ═══")

matches = find_keyword_matches("bought vegetables at supermarket")
test("Keyword: grocery/supermarket found", len(matches) > 0 and matches[0].category == "Food & Dining")

matches = find_keyword_matches("PETROL PUMP PAYMENT")
test("Keyword: petrol = Transportation", len(matches) > 0 and matches[0].category == "Transportation")

matches = find_keyword_matches("MONTHLY SALARY CREDIT")
test("Keyword: salary = Income", len(matches) > 0 and matches[0].category == "Income")

best = get_best_keyword_match("ELECTRICITY BILL PAYMENT")
test("Best keyword: electricity = Utilities", best is not None and best.category == "Utilities")

matches = find_keyword_matches("XYZZYFLURBO")
test("No keywords matched for gibberish", len(matches) == 0)

matches = find_keyword_matches("RESTAURANT FOOD DINING")
test("Multiple keywords sorted by weight", len(matches) >= 2 and matches[0].weight >= matches[1].weight)


# ═══════════════════════════════════════════════════════════════════════════════
# RULE ENGINE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

print("\n═══ Rule Engine Tests ═══")
engine = RuleEngine()

result = engine.classify("POS 423456 SWIGGY INDIRANAGAR BANGALORE", amount=-450.0)
test("Swiggy → Food & Dining", result.category == "Food & Dining" and result.confidence >= 0.90,
     f"got {result.category} conf={result.confidence:.2f}")

result = engine.classify("POS 567 UBER BV TRIP BANGALORE", amount=-320.0)
test("Uber → Transportation", result.category == "Transportation" and result.confidence >= 0.90)

result = engine.classify("POS 999 NETFLIX COM SUBSCRIPTION", amount=-649.0)
test("Netflix → Entertainment/Streaming", result.category == "Entertainment" and result.subcategory == "Streaming")

result = engine.classify("VISA 4567 AMAZON INDIA MARKETPLACE", amount=-2499.0)
test("Amazon → Shopping", result.category == "Shopping" and result.confidence >= 0.90)

result = engine.classify("ATM WDL NFS SBI ATM KORAMANGALA", amount=-10000.0)
test("ATM → Cash", result.category == "Cash" and result.confidence >= 0.90)

result = engine.classify("NEFT CR SBIN SAL CREDIT MAY 2026", amount=95000.0)
test("Salary → Income", result.category == "Income" and result.confidence >= 0.75,
     f"got {result.category} conf={result.confidence:.2f}")

result = engine.classify("BESCOM ELECTRICITY BILL PAYMENT ONLINE", amount=-2300.0)
test("BESCOM → Utilities/Electricity", result.category == "Utilities" and result.subcategory == "Electricity")

result = engine.classify("XYZZY FLURBO 123 RANDOM", amount=-100.0)
test("Unknown → Other + low confidence", result.category == "Other" and result.confidence < 0.5)

result = engine.classify("POS 111 BIGBASKET ONLINE DELIVERY", amount=-1200.0)
test("BigBasket → Food & Dining/Groceries", result.category == "Food & Dining" and result.subcategory == "Groceries")

result = engine.classify("POS 222 INDIGO 6E FLIGHT BOOKING", amount=-5600.0)
test("IndiGo → Transportation/Flights", result.category == "Transportation" and result.subcategory == "Flights")

result = engine.classify("ECS HDFC LIFE INSURANCE PREMIUM", amount=-5000.0)
test("HDFC Life → Bills & Fees/Insurance", result.category == "Bills & Fees" and result.subcategory == "Insurance")

result = engine.classify("SIP GROWW MUTUAL FUND PURCHASE", amount=-5000.0)
test("Groww SIP → Investments/Mutual Funds", result.category == "Investments")

result = engine.classify("POS 333 URBAN COMPANY SALON SERVICE", amount=-800.0)
test("Urban Company → Personal Care", result.category == "Personal Care")

result = engine.classify("POS 444 UDEMY ONLINE COURSE PAYMENT", amount=-1299.0)
test("Udemy → Education", result.category == "Education")

# Case insensitivity
result = engine.classify("pos 423 swiggy bangalore", amount=-450.0)
test("Case insensitive matching", result.category == "Food & Dining")


# ═══════════════════════════════════════════════════════════════════════════════
# PIPELINE TESTS (Rules-only mode)
# ═══════════════════════════════════════════════════════════════════════════════

print("\n═══ Pipeline Tests (Rules-only) ═══")
config = PipelineConfig(enable_ml=False, enable_llm=False)
pipeline = ClassificationPipeline(config=config)

result = pipeline.classify("POS 423456 SWIGGY BANGALORE", amount=-450.0)
test("Pipeline: Swiggy classified", result.category == "Food & Dining" and result.source == "rule_engine")

result = pipeline.classify("XYZZY MYSTERY PAYMENT", amount=-100.0)
test("Pipeline: Unknown → needs review", result.needs_review is True)

# Batch
transactions = [
    {"description": "POS 111 SWIGGY ORDER", "amount": -450.0},
    {"description": "POS 222 UBER TRIP", "amount": -320.0},
    {"description": "ATM WDL CASH SBI", "amount": -5000.0},
    {"description": "POS 333 NETFLIX SUBSCRIPTION", "amount": -649.0},
]
results = pipeline.classify_batch(transactions)
test("Batch: correct count", len(results) == 4)
test("Batch: Swiggy → Food", results[0].category == "Food & Dining")
test("Batch: Uber → Transport", results[1].category == "Transportation")
test("Batch: ATM → Cash", results[2].category == "Cash")
test("Batch: Netflix → Entertainment", results[3].category == "Entertainment")

# Stats
stats = pipeline.stats.to_dict()
test("Stats tracked", stats["total_classified"] >= 5)
test("Stats has avg_latency", "avg_latency_ms" in stats)


# ═══════════════════════════════════════════════════════════════════════════════
# REAL TRANSACTION FIXTURES
# ═══════════════════════════════════════════════════════════════════════════════

print("\n═══ Real Transaction Fixtures ═══")

REAL_TRANSACTIONS = [
    {"description": "POS 423456 SWIGGY INDIRANAGAR BANGALORE", "amount": -450.0, "expected": "Food & Dining"},
    {"description": "POS 892101 ZOMATO ONLINE ORDER", "amount": -680.0, "expected": "Food & Dining"},
    {"description": "POS 123789 UBER BV AMSTERDAM NL", "amount": -320.0, "expected": "Transportation"},
    {"description": "POS 567890 AMAZON INDIA MARKETPLACE", "amount": -2499.0, "expected": "Shopping"},
    {"description": "POS 345678 NETFLIX COM", "amount": -649.0, "expected": "Entertainment"},
    {"description": "POS 789012 APOLLO PHARMACY KORAMANGALA", "amount": -380.0, "expected": "Healthcare"},
    {"description": "UPI/DR/123456789/SWIGGY/swiggy@icici/Payment", "amount": -299.0, "expected": "Food & Dining"},
    {"description": "UPI-PHONEPE-9876543210@ybl-PAYMENT", "amount": -1500.0, "expected": "Transfers"},
    {"description": "NEFT-HDFC0001234-JOHN DOE-RENT PAYMENT", "amount": -25000.0, "expected": "Home"},
    {"description": "VISA 4567 FLIPKART INTERNET PVT LTD", "amount": -1899.0, "expected": "Shopping"},
    {"description": "MASTERCARD 8901 STARBUCKS COFFEE INDIA", "amount": -450.0, "expected": "Food & Dining"},
    {"description": "ATM WDL NFS SBI ATM KORAMANGALA", "amount": -10000.0, "expected": "Cash"},
    {"description": "ECS HDFC LIFE INSURANCE PREMIUM", "amount": -5000.0, "expected": "Bills & Fees"},
    {"description": "IRCTC RAIL BOOKING PNR 1234567890", "amount": -2100.0, "expected": "Transportation"},
    {"description": "POS 111222 CROMA ELECTRONICS WHITEFIELD", "amount": -15999.0, "expected": "Shopping"},
    {"description": "BESCOM ELECTRICITY BILL PAYMENT", "amount": -2300.0, "expected": "Utilities"},
    {"description": "SIP GROWW MUTUAL FUND", "amount": -5000.0, "expected": "Investments"},
    {"description": "POS 333444 DECATHLON SPORTS INDIA", "amount": -3200.0, "expected": "Entertainment"},
    {"description": "POS 555666 URBAN COMPANY SALON", "amount": -800.0, "expected": "Personal Care"},
    {"description": "POS 777888 BOOKMYSHOW CINEMAS", "amount": -500.0, "expected": "Entertainment"},
]

correct = 0
for tx in REAL_TRANSACTIONS:
    result = pipeline.classify(tx["description"], amount=tx["amount"])
    if result.category == tx["expected"]:
        correct += 1
    else:
        print(f"    MISS: '{tx['description'][:45]}' → {result.category} (expected: {tx['expected']}, conf={result.confidence:.2f})")

accuracy = correct / len(REAL_TRANSACTIONS)
test(f"Real transactions accuracy >= 70% ({correct}/{len(REAL_TRANSACTIONS)} = {accuracy:.0%})", accuracy >= 0.70)


# ═══════════════════════════════════════════════════════════════════════════════
# FEEDBACK STORE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

print("\n═══ Feedback Store Tests ═══")

temp_dir = tempfile.mkdtemp()
store = FeedbackStore(feedback_dir=Path(temp_dir))

entry = FeedbackEntry(
    transaction_description="POS 123 MYSTERY STORE",
    original_category="Shopping",
    corrected_category="Food & Dining",
    original_confidence=0.75,
    original_source="rule_engine",
)
store.add_feedback(entry)

store._loaded = False
store._entries_cache = []
entries = store.get_all_feedback()
test("Feedback persisted and retrieved", len(entries) == 1 and entries[0].corrected_category == "Food & Dining")
test("Feedback was_correct = False", entries[0].was_correct is False)

# Add more for stats
store.add_feedback(FeedbackEntry(
    transaction_description="SWIGGY ORDER",
    original_category="Food & Dining",
    corrected_category="Food & Dining",
    original_confidence=0.95,
))
store.add_feedback(FeedbackEntry(
    transaction_description="UBER TRIP",
    original_category="Transportation",
    corrected_category="Transportation",
    original_confidence=0.92,
))

store._loaded = False
store._entries_cache = []
stats = store.get_accuracy_stats()
test("Feedback stats: total = 3", stats["total_feedback"] == 3)
test("Feedback stats: corrections = 1", stats["corrections"] == 1)
test("Feedback stats: accuracy ~0.67", stats["accuracy_rate"] is not None and 0.6 <= stats["accuracy_rate"] <= 0.7,
     f"got {stats['accuracy_rate']}")

training = store.get_training_data()
test("Training data export", len(training) == 3 and training[0]["label"] == "Food & Dining")

store.clear()
store._loaded = False
test("Feedback cleared", len(store.get_all_feedback()) == 0)


# ═══════════════════════════════════════════════════════════════════════════════
# API ENDPOINT TESTS (using TestClient)
# ═══════════════════════════════════════════════════════════════════════════════

print("\n═══ API Endpoint Tests ═══")

try:
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    resp = client.get("/health")
    test("GET /health → 200", resp.status_code == 200 and resp.json()["status"] == "healthy")

    resp = client.post("/api/classify", json={
        "description": "POS 423456 SWIGGY INDIRANAGAR BANGALORE",
        "amount": -450.0,
        "transaction_type": "debit",
    })
    data = resp.json()
    test("POST /api/classify → Food & Dining", resp.status_code == 200 and data["category"] == "Food & Dining")
    test("Response has confidence_level", "confidence_level" in data)
    test("Response has source", data["source"] == "rule_engine")

    resp = client.post("/api/classify/batch", json={
        "transactions": [
            {"description": "POS 111 SWIGGY ORDER", "amount": -450.0},
            {"description": "POS 222 UBER TRIP", "amount": -320.0},
            {"description": "ATM WDL CASH", "amount": -5000.0},
        ]
    })
    data = resp.json()
    test("POST /api/classify/batch → 3 results", resp.status_code == 200 and data["total"] == 3)
    test("Batch results correct", data["results"][0]["category"] == "Food & Dining"
         and data["results"][1]["category"] == "Transportation"
         and data["results"][2]["category"] == "Cash")

    resp = client.post("/api/classify", json={"description": "", "amount": -100.0})
    test("Empty description → 422", resp.status_code == 422)

    resp = client.post("/api/classify/feedback", json={
        "transaction_description": "MYSTERY STORE PAYMENT",
        "original_category": "Shopping",
        "corrected_category": "Food & Dining",
        "original_confidence": 0.65,
        "original_source": "rule_engine",
        "amount": -500.0,
        "user_note": "This is actually a restaurant",
    })
    test("POST /api/classify/feedback → success", resp.status_code == 200 and resp.json()["status"] == "success")

    resp = client.get("/api/classify/stats")
    data = resp.json()
    test("GET /api/classify/stats → has pipeline_stats", resp.status_code == 200 and "pipeline_stats" in data)

    resp = client.post("/api/classify", json={"description": "NETFLIX SUBSCRIPTION RENEWAL"})
    test("Classify with only description", resp.status_code == 200 and resp.json()["category"] == "Entertainment")

except Exception as e:
    print(f"  ✗ API tests failed with error: {e}")
    traceback.print_exc()
    failed += 1


# ═══════════════════════════════════════════════════════════════════════════════
# MERCHANT PATTERN COVERAGE CHECK
# ═══════════════════════════════════════════════════════════════════════════════

print("\n═══ Merchant Pattern Coverage ═══")

total_merchants = 0
for pattern, _, _ in MERCHANT_PATTERNS:
    alts = pattern.pattern.count("|") + 1
    total_merchants += alts

test(f"100+ merchant patterns ({total_merchants} found)", total_merchants >= 100)

# Test key merchants
for merchant in ["SWIGGY", "ZOMATO", "DUNZO", "UBER", "OLA", "AMAZON", "FLIPKART",
                 "NETFLIX", "SPOTIFY", "CROMA", "BIGBASKET", "MYNTRA"]:
    result = engine.classify(f"POS 123 {merchant} INDIA")
    test(f"Pattern: {merchant} classified", result.confidence >= 0.90, f"conf={result.confidence:.2f}")


# ═══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════

print(f"\n{'═' * 60}")
print(f"  RESULTS: {passed} passed, {failed} failed, {passed + failed} total")
print(f"{'═' * 60}")

if failed > 0:
    print("\nFailed tests:")
    for e in errors:
        print(f"  {e}")
    sys.exit(1)
else:
    print("\n  ✅ ALL TESTS PASSED!")
    sys.exit(0)
