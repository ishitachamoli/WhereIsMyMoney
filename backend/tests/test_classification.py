"""Integration tests for the classification pipeline.

Tests the full pipeline from raw transaction descriptions through all
classification tiers, exercising real pattern matching, keyword logic,
confidence scoring, feedback storage, and API endpoints.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
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
from app.services.classification.rules.merchant_patterns import (
    MERCHANT_PATTERNS,
    extract_merchant_name,
)
from app.services.classification.rules.transaction_codes import (
    extract_counterparty_from_code,
    parse_transaction_code,
)


# ─── FIXTURES ────────────────────────────────────────────────────────────────

# Real-world Indian bank transaction descriptions
REAL_TRANSACTIONS = [
    # POS transactions
    {"description": "POS 423456 SWIGGY INDIRANAGAR BANGALORE", "amount": -450.0, "expected_category": "Food & Dining", "expected_merchant": "Swiggy"},
    {"description": "POS 892101 ZOMATO ONLINE ORDER", "amount": -680.0, "expected_category": "Food & Dining", "expected_merchant": "Zomato"},
    {"description": "POS 123789 UBER BV AMSTERDAM NL", "amount": -320.0, "expected_category": "Transportation", "expected_merchant": "Uber"},
    {"description": "POS 567890 AMAZON INDIA MARKETPLACE", "amount": -2499.0, "expected_category": "Shopping", "expected_merchant": "Amazon"},
    {"description": "POS 345678 NETFLIX COM", "amount": -649.0, "expected_category": "Entertainment", "expected_merchant": "Netflix"},
    {"description": "POS 789012 APOLLO PHARMACY KORAMANGALA", "amount": -380.0, "expected_category": "Healthcare", "expected_merchant": "Apollo Pharmacy"},
    # UPI transactions
    {"description": "UPI/DR/123456789/SWIGGY/swiggy@icici/Payment", "amount": -299.0, "expected_category": "Food & Dining", "expected_merchant": "Swiggy"},
    {"description": "UPI/CR/987654321/SALARY/employer@hdfc/", "amount": 85000.0, "expected_category": "Income", "expected_merchant": None},
    {"description": "UPI-PHONEPE-9876543210@ybl-PAYMENT", "amount": -1500.0, "expected_category": "Transfers", "expected_merchant": None},
    # NEFT transactions
    {"description": "NEFT-HDFC0001234-JOHN DOE-RENT PAYMENT", "amount": -25000.0, "expected_category": "Home", "expected_merchant": None},
    {"description": "NEFT CR SBIN0000123 EMPLOYER SAL CREDIT", "amount": 95000.0, "expected_category": "Income", "expected_merchant": None},
    # Card transactions
    {"description": "VISA 4567 FLIPKART INTERNET PVT LTD", "amount": -1899.0, "expected_category": "Shopping", "expected_merchant": "Flipkart"},
    {"description": "MASTERCARD 8901 STARBUCKS COFFEE INDIA", "amount": -450.0, "expected_category": "Food & Dining", "expected_merchant": "Starbucks"},
    # ATM
    {"description": "ATM WDL NFS SBI ATM KORAMANGALA", "amount": -10000.0, "expected_category": "Cash", "expected_merchant": None},
    # Direct Debit / ECS
    {"description": "ECS HDFC LIFE INSURANCE PREMIUM", "amount": -5000.0, "expected_category": "Bills & Fees", "expected_merchant": None},
    {"description": "NACH BAJAJ FINSERV EMI AUTO DEBIT", "amount": -8500.0, "expected_category": "Bills & Fees", "expected_merchant": None},
    # Others
    {"description": "IRCTC RAIL BOOKING PNR 1234567890", "amount": -2100.0, "expected_category": "Transportation", "expected_merchant": "IRCTC"},
    {"description": "POS 111222 CROMA ELECTRONICS WHITEFIELD", "amount": -15999.0, "expected_category": "Shopping", "expected_merchant": "Croma"},
    {"description": "BESCOM ELECTRICITY BILL PAYMENT", "amount": -2300.0, "expected_category": "Utilities", "expected_merchant": None},
    {"description": "SIP GROWW MUTUAL FUND", "amount": -5000.0, "expected_category": "Investments", "expected_merchant": "Groww"},
    {"description": "POS 333444 DECATHLON SPORTS INDIA", "amount": -3200.0, "expected_category": "Entertainment", "expected_merchant": "Decathlon"},
    {"description": "POS 555666 URBAN COMPANY SALON", "amount": -800.0, "expected_category": "Personal Care", "expected_merchant": "Urban Company"},
    {"description": "POS 777888 BOOKMYSHOW CINEMAS", "amount": -500.0, "expected_category": "Entertainment", "expected_merchant": "BookMyShow"},
]


# ─── CATEGORY TAXONOMY TESTS ────────────────────────────────────────────────


class TestCategoryTaxonomy:
    def setup_method(self):
        self.taxonomy = CategoryTaxonomy()

    def test_all_top_categories_present(self):
        cats = self.taxonomy.top_categories
        assert len(cats) == 15
        assert TopCategory.FOOD_DINING in cats
        assert TopCategory.OTHER in cats

    def test_category_labels_are_strings(self):
        labels = self.taxonomy.category_labels
        assert all(isinstance(l, str) for l in labels)
        assert "Food & Dining" in labels
        assert "Transportation" in labels

    def test_get_category_by_name(self):
        cat = self.taxonomy.get_category("Food & Dining")
        assert cat is not None
        assert cat.emoji == "🍽️"
        assert len(cat.subcategories) > 0

    def test_get_category_case_insensitive(self):
        cat = self.taxonomy.get_category("food & dining")
        assert cat is not None
        assert cat.name == TopCategory.FOOD_DINING

    def test_get_subcategories(self):
        subs = self.taxonomy.get_subcategories(TopCategory.FOOD_DINING)
        assert "Restaurants" in subs
        assert "Groceries" in subs
        assert "Food Delivery" in subs

    def test_resolve_category_exact(self):
        resolved = self.taxonomy.resolve_category("Food & Dining")
        assert resolved == TopCategory.FOOD_DINING

    def test_resolve_category_partial(self):
        resolved = self.taxonomy.resolve_category("food")
        assert resolved == TopCategory.FOOD_DINING

    def test_resolve_category_unknown(self):
        resolved = self.taxonomy.resolve_category("xyzzy")
        assert resolved is None

    def test_get_emoji(self):
        assert self.taxonomy.get_emoji(TopCategory.TRANSPORTATION) == "🚗"
        assert self.taxonomy.get_emoji(TopCategory.HEALTHCARE) == "🏥"


# ─── CONFIDENCE SCORING TESTS ───────────────────────────────────────────────


class TestConfidenceScoring:
    def test_rule_confidence_pattern_match(self):
        conf = compute_rule_confidence(pattern_matched=True, keyword_matched=False)
        assert conf >= 0.95

    def test_rule_confidence_keyword_match(self):
        conf = compute_rule_confidence(pattern_matched=False, keyword_matched=True)
        assert 0.75 <= conf <= 0.85

    def test_rule_confidence_no_match(self):
        conf = compute_rule_confidence(pattern_matched=False, keyword_matched=False)
        assert conf == 0.0

    def test_ml_confidence_high_gap(self):
        conf = compute_ml_confidence(top_score=0.9, second_score=0.05)
        assert conf >= 0.75

    def test_ml_confidence_low_gap(self):
        conf = compute_ml_confidence(top_score=0.3, second_score=0.25)
        assert conf < 0.5

    def test_needs_manual_review_low_confidence(self):
        result = ClassificationResult(category="Other", confidence=0.3, source="test")
        assert needs_manual_review(result) is True

    def test_needs_manual_review_high_confidence(self):
        result = ClassificationResult(category="Food & Dining", confidence=0.95, source="test")
        assert needs_manual_review(result) is False

    def test_confidence_level_enum(self):
        high = ClassificationResult(category="test", confidence=0.9, source="t")
        assert high.confidence_level == ConfidenceLevel.HIGH
        low = ClassificationResult(category="test", confidence=0.3, source="t")
        assert low.confidence_level == ConfidenceLevel.VERY_LOW


# ─── TRANSACTION CODE TESTS ──────────────────────────────────────────────────


class TestTransactionCodes:
    def test_parse_pos_transaction(self):
        info = parse_transaction_code("POS 423456 SWIGGY BANGALORE")
        assert info is not None
        assert info.transaction_type == "POS"
        assert info.is_debit is True

    def test_parse_upi_debit(self):
        info = parse_transaction_code("UPI/DR/123456/PayeeName/payee@vpa/")
        assert info is not None
        assert info.transaction_type == "UPI_DEBIT"
        assert info.is_debit is True

    def test_parse_upi_credit(self):
        info = parse_transaction_code("UPI/CR/123456/PayerName/payer@vpa/")
        assert info is not None
        assert info.transaction_type == "UPI_CREDIT"
        assert info.is_debit is False

    def test_parse_neft(self):
        info = parse_transaction_code("NEFT-HDFC0001234-JOHN DOE-RENT")
        assert info is not None
        assert "NEFT" in info.transaction_type

    def test_parse_atm(self):
        info = parse_transaction_code("ATM WDL NFS SBI ATM")
        assert info is not None
        assert info.transaction_type == "ATM"
        assert info.is_debit is True

    def test_parse_unknown_returns_none(self):
        info = parse_transaction_code("RANDOM TEXT HERE")
        assert info is None

    def test_extract_counterparty_pos(self):
        cp = extract_counterparty_from_code("POS 423456 SWIGGY BANGALORE")
        assert cp is not None
        assert "SWIGGY" in cp.upper()

    def test_extract_counterparty_upi(self):
        cp = extract_counterparty_from_code("UPI/DR/123456/JOHN DOE/john@upi/")
        assert cp is not None
        assert "JOHN" in cp.upper()

    def test_extract_counterparty_neft(self):
        cp = extract_counterparty_from_code("NEFT-HDFC0001234-JANE SMITH-RENT")
        assert cp is not None


# ─── KEYWORD MATCHING TESTS ──────────────────────────────────────────────────


class TestKeywordMatching:
    def test_find_grocery_keywords(self):
        matches = find_keyword_matches("bought vegetables at supermarket")
        assert len(matches) > 0
        assert matches[0].category == "Food & Dining"

    def test_find_fuel_keyword(self):
        matches = find_keyword_matches("PETROL PUMP PAYMENT")
        assert len(matches) > 0
        assert matches[0].category == "Transportation"

    def test_find_salary_keyword(self):
        matches = find_keyword_matches("MONTHLY SALARY CREDIT")
        assert len(matches) > 0
        assert matches[0].category == "Income"

    def test_best_keyword_match(self):
        best = get_best_keyword_match("ELECTRICITY BILL PAYMENT")
        assert best is not None
        assert best.category == "Utilities"
        assert best.subcategory == "Electricity"

    def test_no_match_returns_empty(self):
        matches = find_keyword_matches("XYZZYFLURBO")
        assert len(matches) == 0

    def test_multiple_keyword_hits_sorted_by_weight(self):
        matches = find_keyword_matches("RESTAURANT FOOD COURT DINING")
        assert len(matches) >= 2
        # Should be sorted by weight, highest first
        assert matches[0].weight >= matches[1].weight


# ─── RULE ENGINE TESTS ───────────────────────────────────────────────────────


class TestRuleEngine:
    def setup_method(self):
        self.engine = RuleEngine()

    def test_classify_swiggy(self):
        result = self.engine.classify("POS 423456 SWIGGY INDIRANAGAR BANGALORE", amount=-450.0)
        assert result.category == "Food & Dining"
        assert result.subcategory == "Food Delivery"
        assert result.confidence >= 0.90
        assert result.merchant is not None

    def test_classify_uber(self):
        result = self.engine.classify("POS 567 UBER BV TRIP BANGALORE", amount=-320.0)
        assert result.category == "Transportation"
        assert result.confidence >= 0.90

    def test_classify_netflix(self):
        result = self.engine.classify("POS 999 NETFLIX COM SUBSCRIPTION", amount=-649.0)
        assert result.category == "Entertainment"
        assert result.subcategory == "Streaming"
        assert result.confidence >= 0.90

    def test_classify_amazon(self):
        result = self.engine.classify("VISA 4567 AMAZON INDIA MARKETPLACE", amount=-2499.0)
        assert result.category == "Shopping"
        assert result.confidence >= 0.90

    def test_classify_atm_withdrawal(self):
        result = self.engine.classify("ATM WDL NFS SBI ATM KORAMANGALA", amount=-10000.0)
        assert result.category == "Cash"
        assert result.confidence >= 0.90

    def test_classify_salary(self):
        result = self.engine.classify("NEFT CR SBIN SAL CREDIT MAY 2026", amount=95000.0)
        assert result.category == "Income"
        assert result.confidence >= 0.75

    def test_classify_electricity(self):
        result = self.engine.classify("BESCOM ELECTRICITY BILL PAYMENT ONLINE", amount=-2300.0)
        assert result.category == "Utilities"
        assert result.subcategory == "Electricity"

    def test_classify_unknown_returns_other(self):
        result = self.engine.classify("XYZZY FLURBO 123 RANDOM", amount=-100.0)
        assert result.category == "Other"
        assert result.confidence < 0.5
        assert result.needs_review is True

    def test_classify_grocery_store(self):
        result = self.engine.classify("POS 111 BIGBASKET ONLINE DELIVERY", amount=-1200.0)
        assert result.category == "Food & Dining"
        assert result.subcategory == "Groceries"

    def test_classify_flight(self):
        result = self.engine.classify("POS 222 INDIGO 6E FLIGHT BOOKING", amount=-5600.0)
        assert result.category == "Transportation"
        assert result.subcategory == "Flights"

    def test_classify_insurance(self):
        result = self.engine.classify("ECS HDFC LIFE INSURANCE PREMIUM AUG", amount=-5000.0)
        assert result.category == "Bills & Fees"
        assert result.subcategory == "Insurance"

    def test_classify_mutual_fund(self):
        result = self.engine.classify("SIP GROWW MUTUAL FUND PURCHASE", amount=-5000.0)
        assert result.category == "Investments"
        assert result.subcategory == "Mutual Funds"

    def test_classify_salon(self):
        result = self.engine.classify("POS 333 URBAN COMPANY SALON SERVICE", amount=-800.0)
        assert result.category == "Personal Care"
        assert result.subcategory == "Salon & Spa"

    def test_classify_rent(self):
        result = self.engine.classify("NEFT-HDFC0001234-LANDLORD-RENT PAYMENT JUN 2026", amount=-25000.0)
        assert result.category == "Home"
        assert result.subcategory == "Rent"

    def test_classify_education(self):
        result = self.engine.classify("POS 444 UDEMY ONLINE COURSE PAYMENT", amount=-1299.0)
        assert result.category == "Education"
        assert result.subcategory == "Courses & Training"

    def test_case_insensitivity(self):
        result = self.engine.classify("pos 423 swiggy bangalore", amount=-450.0)
        assert result.category == "Food & Dining"

    def test_classify_credit_with_no_match(self):
        result = self.engine.classify("NEFT CR UNKNOWN SENDER PAYMENT", amount=5000.0)
        # Should be low confidence since no pattern matches well
        assert result.confidence < 0.9


# ─── PIPELINE TESTS ──────────────────────────────────────────────────────────


class TestPipeline:
    def setup_method(self):
        # Disable ML and LLM for fast unit testing (they need models)
        config = PipelineConfig(enable_ml=False, enable_llm=False)
        self.pipeline = ClassificationPipeline(config=config)

    def test_pipeline_classify_known_merchant(self):
        result = self.pipeline.classify("POS 423456 SWIGGY BANGALORE", amount=-450.0)
        assert result.category == "Food & Dining"
        assert result.confidence >= 0.90
        assert result.source == "rule_engine"

    def test_pipeline_classify_unknown_transaction(self):
        result = self.pipeline.classify("XYZZY MYSTERY PAYMENT", amount=-100.0)
        assert result.confidence < 0.9
        assert result.needs_review is True

    def test_pipeline_batch_classification(self):
        transactions = [
            {"description": "POS 111 SWIGGY ORDER", "amount": -450.0},
            {"description": "POS 222 UBER TRIP", "amount": -320.0},
            {"description": "ATM WDL CASH SBI", "amount": -5000.0},
            {"description": "POS 333 NETFLIX SUBSCRIPTION", "amount": -649.0},
        ]
        results = self.pipeline.classify_batch(transactions)
        assert len(results) == 4
        assert results[0].category == "Food & Dining"
        assert results[1].category == "Transportation"
        assert results[2].category == "Cash"
        assert results[3].category == "Entertainment"

    def test_pipeline_stats_tracking(self):
        self.pipeline.classify("POS 423456 SWIGGY BANGALORE", amount=-450.0)
        self.pipeline.classify("POS 567 UBER TRIP", amount=-320.0)
        stats = self.pipeline.stats
        assert stats.total_classified == 2
        assert stats.rule_hits >= 2

    def test_pipeline_stats_dict(self):
        self.pipeline.classify("POS 100 ZOMATO ORDER", amount=-500.0)
        stats_dict = self.pipeline.stats.to_dict()
        assert "total_classified" in stats_dict
        assert "rule_hit_rate" in stats_dict
        assert "avg_latency_ms" in stats_dict

    def test_real_transaction_fixtures(self):
        """Run all real transaction fixtures through the pipeline."""
        correct = 0
        total = len(REAL_TRANSACTIONS)

        for tx in REAL_TRANSACTIONS:
            result = self.pipeline.classify(
                tx["description"],
                amount=tx["amount"],
            )
            if result.category == tx["expected_category"]:
                correct += 1
            else:
                # Print misclassifications for debugging
                print(
                    f"  MISS: '{tx['description'][:50]}' → "
                    f"{result.category} (expected: {tx['expected_category']}, "
                    f"conf={result.confidence:.2f}, src={result.source})"
                )

        accuracy = correct / total
        print(f"\n  Rule-only accuracy: {correct}/{total} = {accuracy:.1%}")
        # We expect at least 70% accuracy with rules alone
        assert accuracy >= 0.70, f"Accuracy too low: {accuracy:.1%}"


# ─── FEEDBACK TESTS ──────────────────────────────────────────────────────────


class TestFeedback:
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.store = FeedbackStore(feedback_dir=Path(self.temp_dir))

    def test_add_and_retrieve_feedback(self):
        entry = FeedbackEntry(
            transaction_description="POS 123 MYSTERY STORE",
            original_category="Shopping",
            corrected_category="Food & Dining",
            original_confidence=0.75,
            original_source="rule_engine",
        )
        self.store.add_feedback(entry)

        # Force reload from disk
        self.store._loaded = False
        self.store._entries_cache = []
        entries = self.store.get_all_feedback()
        assert len(entries) == 1
        assert entries[0].corrected_category == "Food & Dining"
        assert entries[0].was_correct is False

    def test_feedback_accuracy_stats(self):
        # Add mix of correct and incorrect
        self.store.add_feedback(FeedbackEntry(
            transaction_description="SWIGGY ORDER",
            original_category="Food & Dining",
            corrected_category="Food & Dining",
            original_confidence=0.95,
        ))
        self.store.add_feedback(FeedbackEntry(
            transaction_description="MYSTERY TX",
            original_category="Shopping",
            corrected_category="Food & Dining",
            original_confidence=0.6,
        ))
        self.store.add_feedback(FeedbackEntry(
            transaction_description="UBER TRIP",
            original_category="Transportation",
            corrected_category="Transportation",
            original_confidence=0.92,
        ))

        self.store._loaded = False
        self.store._entries_cache = []
        stats = self.store.get_accuracy_stats()
        assert stats["total_feedback"] == 3
        assert stats["corrections"] == 1
        assert stats["correct"] == 2
        assert stats["accuracy_rate"] is not None
        assert 0.6 <= stats["accuracy_rate"] <= 0.7  # 2/3

    def test_feedback_training_data_export(self):
        self.store.add_feedback(FeedbackEntry(
            transaction_description="SWIGGY ORDER",
            original_category="Other",
            corrected_category="Food & Dining",
            amount=-450.0,
        ))
        training = self.store.get_training_data()
        assert len(training) == 1
        assert training[0]["text"] == "SWIGGY ORDER"
        assert training[0]["label"] == "Food & Dining"

    def test_clear_feedback(self):
        self.store.add_feedback(FeedbackEntry(
            transaction_description="test",
            original_category="A",
            corrected_category="B",
        ))
        self.store.clear()
        self.store._loaded = False
        entries = self.store.get_all_feedback()
        assert len(entries) == 0


# ─── API ENDPOINT TESTS ─────────────────────────────────────────────────────


class TestAPI:
    def setup_method(self):
        self.client = TestClient(app)

    def test_health_check(self):
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_classify_single_transaction(self):
        response = self.client.post(
            "/api/classify",
            json={
                "description": "POS 423456 SWIGGY INDIRANAGAR BANGALORE",
                "amount": -450.0,
                "transaction_type": "debit",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "Food & Dining"
        assert data["confidence"] >= 0.90
        assert data["source"] == "rule_engine"
        assert "confidence_level" in data

    def test_classify_batch(self):
        response = self.client.post(
            "/api/classify/batch",
            json={
                "transactions": [
                    {"description": "POS 111 SWIGGY ORDER", "amount": -450.0},
                    {"description": "POS 222 UBER TRIP", "amount": -320.0},
                    {"description": "ATM WDL CASH", "amount": -5000.0},
                ]
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert len(data["results"]) == 3
        assert data["results"][0]["category"] == "Food & Dining"
        assert data["results"][1]["category"] == "Transportation"
        assert data["results"][2]["category"] == "Cash"

    def test_classify_empty_description_fails(self):
        response = self.client.post(
            "/api/classify",
            json={"description": "", "amount": -100.0},
        )
        assert response.status_code == 422

    def test_classify_batch_too_many_fails(self):
        response = self.client.post(
            "/api/classify/batch",
            json={
                "transactions": [
                    {"description": f"TX {i}"} for i in range(101)
                ]
            },
        )
        assert response.status_code == 422

    def test_submit_feedback(self):
        response = self.client.post(
            "/api/classify/feedback",
            json={
                "transaction_description": "MYSTERY STORE PAYMENT",
                "original_category": "Shopping",
                "corrected_category": "Food & Dining",
                "original_confidence": 0.65,
                "original_source": "rule_engine",
                "amount": -500.0,
                "user_note": "This is actually a restaurant",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_get_stats(self):
        # Make a classification first to populate stats
        self.client.post(
            "/api/classify",
            json={"description": "POS 423 SWIGGY BANGALORE", "amount": -450.0},
        )
        response = self.client.get("/api/classify/stats")
        assert response.status_code == 200
        data = response.json()
        assert "pipeline_stats" in data
        assert "feedback_stats" in data
        assert data["pipeline_stats"]["total_classified"] >= 1

    def test_classify_upi_transaction(self):
        response = self.client.post(
            "/api/classify",
            json={
                "description": "UPI/DR/123456789/SWIGGY/swiggy@icici/Payment",
                "amount": -299.0,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "Food & Dining"

    def test_classify_with_only_description(self):
        response = self.client.post(
            "/api/classify",
            json={"description": "NETFLIX SUBSCRIPTION RENEWAL"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "Entertainment"


# ─── MERCHANT PATTERN COVERAGE TESTS ────────────────────────────────────────


class TestMerchantPatternCoverage:
    """Verify that our pattern registry covers the required 100+ merchants."""

    def test_minimum_pattern_count(self):
        # Count unique merchants covered across all patterns
        import re
        total_merchants = 0
        for pattern, _, _ in MERCHANT_PATTERNS:
            # Count alternatives in each pattern (split by |)
            alts = pattern.pattern.count("|") + 1
            total_merchants += alts
        # We should have 100+ merchant patterns across all categories
        assert total_merchants >= 100, f"Only {total_merchants} merchant patterns (need 100+)"

    def test_food_delivery_patterns(self):
        engine = RuleEngine()
        for merchant in ["SWIGGY", "ZOMATO", "DUNZO"]:
            result = engine.classify(f"POS 123 {merchant} BANGALORE")
            assert result.category == "Food & Dining", f"Failed for {merchant}"
            assert result.confidence >= 0.90

    def test_ecommerce_patterns(self):
        engine = RuleEngine()
        for merchant in ["AMAZON", "FLIPKART", "MYNTRA", "MEESHO"]:
            result = engine.classify(f"POS 123 {merchant} INDIA")
            assert result.category == "Shopping", f"Failed for {merchant}"

    def test_streaming_patterns(self):
        engine = RuleEngine()
        for merchant in ["NETFLIX", "SPOTIFY", "HOTSTAR", "YOUTUBE PREMIUM"]:
            result = engine.classify(f"POS 123 {merchant} SUBSCRIPTION")
            assert result.category == "Entertainment", f"Failed for {merchant}"

    def test_ride_sharing_patterns(self):
        engine = RuleEngine()
        for merchant in ["UBER", "OLA", "RAPIDO"]:
            result = engine.classify(f"POS 123 {merchant} TRIP FARE")
            assert result.category == "Transportation", f"Failed for {merchant}"

    def test_utility_patterns(self):
        engine = RuleEngine()
        for desc in ["BESCOM ELECTRICITY BILL", "AIRTEL FIBER BROADBAND", "LPG GAS CYLINDER"]:
            result = engine.classify(desc)
            assert result.category == "Utilities", f"Failed for '{desc}'"
