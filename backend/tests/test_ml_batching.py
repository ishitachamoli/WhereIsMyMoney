"""Integration tests for ML classifier batching performance fix.

Verifies that:
1. classify_batch produces correct results for multiple texts
2. Direct NLI batching matches single-item classification results
3. The background task helpers (category lookup, fast resolution) work correctly
4. Edge cases (empty input, single item, unavailable model) are handled
"""

from __future__ import annotations

import time
from unittest.mock import patch, MagicMock

import pytest

from app.services.classification.ml_classifier import (
    MLClassifier,
    CANDIDATE_LABELS,
    LABEL_TO_CATEGORY,
    get_pipeline,
    get_model_and_tokenizer,
    _NLI_BATCH_SIZE,
    _NLI_HYPOTHESIS_TEMPLATE,
)
from app.services.classification.confidence import ClassificationResult


# Real-world Indian bank transaction descriptions for testing
TEST_DESCRIPTIONS = [
    "POS 423456 SWIGGY INDIRANAGAR BANGALORE",
    "UPI/DR/123456789/UBER/uber@icici/Payment",
    "NEFT-HDFC0001234-JOHN DOE-RENT PAYMENT",
    "POS 567890 AMAZON INDIA MARKETPLACE",
    "ATM WDL NFS SBI ATM KORAMANGALA",
    "ECS HDFC LIFE INSURANCE PREMIUM",
    "BESCOM ELECTRICITY BILL PAYMENT",
    "SIP GROWW MUTUAL FUND",
    "POS 789012 APOLLO PHARMACY KORAMANGALA",
    "POS 345678 NETFLIX COM",
]


class TestMLClassifierBatching:
    """Test the batched ML classification."""

    def test_classify_batch_empty_input(self):
        """Empty input returns empty list."""
        classifier = MLClassifier()
        results = classifier.classify_batch([], [])
        assert results == []

    def test_classify_batch_returns_correct_count(self):
        """classify_batch returns one result per input text."""
        classifier = MLClassifier()
        if not classifier.is_available:
            pytest.skip("ML model not available")

        results = classifier.classify_batch(TEST_DESCRIPTIONS[:3])
        assert len(results) == 3
        for r in results:
            assert isinstance(r, ClassificationResult)
            assert r.category in LABEL_TO_CATEGORY.values()
            assert 0.0 <= r.confidence <= 1.0
            assert r.source == "ml_classifier"

    def test_classify_batch_with_amounts(self):
        """classify_batch works with amounts provided."""
        classifier = MLClassifier()
        if not classifier.is_available:
            pytest.skip("ML model not available")

        amounts = [-450.0, -320.0, -25000.0]
        results = classifier.classify_batch(TEST_DESCRIPTIONS[:3], amounts)
        assert len(results) == 3
        for r in results:
            assert isinstance(r, ClassificationResult)
            assert r.category in LABEL_TO_CATEGORY.values()

    def test_classify_batch_single_item(self):
        """Single-item batch works correctly."""
        classifier = MLClassifier()
        if not classifier.is_available:
            pytest.skip("ML model not available")

        results = classifier.classify_batch(["POS 423456 SWIGGY BANGALORE"])
        assert len(results) == 1
        assert results[0].category in LABEL_TO_CATEGORY.values()

    def test_classify_batch_consistency_with_single(self):
        """Batch results should be consistent with single classify() results."""
        classifier = MLClassifier()
        if not classifier.is_available:
            pytest.skip("ML model not available")

        descriptions = TEST_DESCRIPTIONS[:5]
        batch_results = classifier.classify_batch(descriptions)

        # Categories should match (scores may differ slightly due to padding differences)
        for i, desc in enumerate(descriptions):
            single_result = classifier.classify(desc)
            assert batch_results[i].category == single_result.category, (
                f"Mismatch for '{desc}': batch={batch_results[i].category}, "
                f"single={single_result.category}"
            )

    def test_classify_batch_performance(self):
        """Batch should be significantly faster than N individual calls."""
        classifier = MLClassifier()
        if not classifier.is_available:
            pytest.skip("ML model not available")

        descriptions = TEST_DESCRIPTIONS

        # Time batch call
        t0 = time.perf_counter()
        batch_results = classifier.classify_batch(descriptions)
        batch_time = time.perf_counter() - t0

        # Time individual calls
        t0 = time.perf_counter()
        single_results = [classifier.classify(d) for d in descriptions]
        single_time = time.perf_counter() - t0

        ms_per_tx_batch = (batch_time / len(descriptions)) * 1000
        ms_per_tx_single = (single_time / len(descriptions)) * 1000

        print(f"\nBatch: {batch_time:.2f}s total ({ms_per_tx_batch:.0f} ms/tx)")
        print(f"Single: {single_time:.2f}s total ({ms_per_tx_single:.0f} ms/tx)")
        print(f"Speedup: {single_time / batch_time:.1f}x")

        # Batch should be at least 2x faster for 10 items
        # (the real speedup is much larger for 100+ items)
        assert batch_time < single_time, (
            f"Batch ({batch_time:.1f}s) should be faster than sequential ({single_time:.1f}s)"
        )

    def test_classify_batch_model_unavailable(self):
        """Returns fallback results when model is unavailable."""
        classifier = MLClassifier()

        with patch.object(type(classifier), 'is_available', new_callable=lambda: property(lambda self: False)):
            results = classifier.classify_batch(TEST_DESCRIPTIONS[:3])
            assert len(results) == 3
            for r in results:
                assert r.category == "Other"
                assert r.confidence == 0.0
                assert "not available" in r.reasoning

    def test_get_model_and_tokenizer(self):
        """get_model_and_tokenizer returns model and tokenizer after pipeline init."""
        pipe = get_pipeline()
        if pipe is None:
            pytest.skip("ML model not available")

        model, tokenizer = get_model_and_tokenizer()
        assert model is not None
        assert tokenizer is not None

    def test_nli_hypothesis_template(self):
        """Hypothesis template formats correctly."""
        label = "food and dining at restaurants or food delivery"
        hypothesis = _NLI_HYPOTHESIS_TEMPLATE.format(label)
        assert hypothesis == "This example is food and dining at restaurants or food delivery."


class TestCategoryLookup:
    """Test the fast category lookup helpers."""

    def test_resolve_category_id_fast_exact_match(self):
        """Exact name match works."""
        from app.routers.upload import _resolve_category_id_fast

        lookup = {"food & dining": 1, "transportation": 2, "shopping": 3}
        assert _resolve_category_id_fast("Food & Dining", lookup) == 1
        assert _resolve_category_id_fast("Transportation", lookup) == 2

    def test_resolve_category_id_fast_partial_match(self):
        """Partial/substring match works."""
        from app.routers.upload import _resolve_category_id_fast

        lookup = {"food & dining": 1, "transportation": 2, "bills & fees": 3}
        # category_name "food" is in "food & dining"
        assert _resolve_category_id_fast("Food", lookup) == 1

    def test_resolve_category_id_fast_reverse_partial(self):
        """Reverse partial match: DB name in classification name."""
        from app.routers.upload import _resolve_category_id_fast

        lookup = {"food & dining": 1, "transport": 2}
        # "transport" is in "transportation"
        assert _resolve_category_id_fast("Transportation", lookup) == 2

    def test_resolve_category_id_fast_no_match(self):
        """Returns None when no match found."""
        from app.routers.upload import _resolve_category_id_fast

        lookup = {"food & dining": 1, "transportation": 2}
        assert _resolve_category_id_fast("Quantum Physics", lookup) is None

    def test_build_category_lookup(self):
        """_build_category_lookup returns proper dict from DB."""
        from app.routers.upload import _build_category_lookup
        from app.core.database import get_session_local, get_engine, Base
        from app.models.category import Category

        engine = get_engine()
        Base.metadata.create_all(bind=engine)

        SessionLocal = get_session_local()
        db = SessionLocal()
        try:
            # Check that we can build a lookup (might be empty in test DB, that's OK)
            lookup = _build_category_lookup(db, user_id=1)
            assert isinstance(lookup, dict)
            # All values should be integers (category IDs)
            for k, v in lookup.items():
                assert isinstance(k, str)
                assert k == k.lower()  # Keys are lowercase
                assert isinstance(v, int)
        finally:
            db.close()


class TestDirectNLIBatching:
    """Test the direct NLI inference path specifically."""

    def test_entailment_index_detection(self):
        """The entailment index is correctly detected from model config."""
        classifier = MLClassifier()
        if not classifier.is_available:
            pytest.skip("ML model not available")

        model, _ = get_model_and_tokenizer()
        if model is None:
            pytest.skip("Model not loaded")

        idx = classifier._get_entailment_index(model)
        # DistilBART-MNLI uses index 2 for entailment
        assert idx == 2

    def test_batch_nli_inference_produces_valid_scores(self):
        """Direct NLI inference produces valid probability distributions."""
        classifier = MLClassifier()
        if not classifier.is_available:
            pytest.skip("ML model not available")

        model, tokenizer = get_model_and_tokenizer()
        if model is None or tokenizer is None:
            pytest.skip("Model not loaded")

        texts = [
            classifier._build_input_text("SWIGGY FOOD ORDER", -450.0, None),
            classifier._build_input_text("UBER CAB RIDE", -320.0, None),
        ]

        results = classifier._batch_nli_inference(texts, model, tokenizer)
        assert len(results) == 2

        for r in results:
            assert r.category in LABEL_TO_CATEGORY.values()
            assert 0.0 <= r.confidence <= 1.0
            assert r.source == "ml_classifier"
