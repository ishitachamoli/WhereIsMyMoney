"""Tier 3: LLM-based classification via Ollama (Llama 3.1 8B).

Used as a fallback for complex/ambiguous transactions that neither rules
nor zero-shot ML can classify confidently. Integrates with a local Ollama
instance and gracefully falls back if unavailable.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

import httpx

from app.services.classification.categories import CategoryTaxonomy, TopCategory
from app.services.classification.confidence import (
    ClassificationResult,
    compute_llm_confidence,
)
from app.services.currency_helper import get_currency_symbol

logger = logging.getLogger(__name__)

CLASSIFICATION_PROMPT = """You are a financial transaction classifier for Indian bank statements.
Classify the following bank transaction into exactly one category.

Transaction Details:
- Description: {description}
- Amount: {currency_symbol}{amount}
- Type: {tx_type}

Available Categories (pick exactly one):
- Food & Dining (restaurants, groceries, cafes, food delivery)
- Transportation (fuel, ride-sharing, parking, flights, public transit)
- Shopping (e-commerce, fashion, electronics, furniture)
- Entertainment (movies, streaming, gaming, sports, travel)
- Healthcare (pharmacy, hospital, doctor, dental)
- Utilities (electricity, water, internet, mobile, gas)
- Bills & Fees (credit card bills, insurance, EMI, bank charges)
- Education (courses, school/college fees, coaching)
- Personal Care (salon, spa, laundry)
- Home (rent, maintenance, repairs, household)
- Income (salary, refund, interest, dividend)
- Transfers (UPI, NEFT, RTGS, IMPS transfers)
- Investments (mutual funds, stocks, FD, crypto, gold)
- Cash (ATM withdrawal, cash deposit)
- Other (donations, miscellaneous)

Respond ONLY with valid JSON (no markdown, no explanation):
{{"category": "<category_name>", "subcategory": "<specific_type>", "merchant": "<extracted_merchant_name_or_null>", "confidence": <0.0_to_1.0>, "reasoning": "<brief_one_line_reason>"}}"""


class LLMClassifier:
    """Ollama-based LLM classifier for complex transactions.

    Connects to a local Ollama instance running Llama 3.1 8B.
    Gracefully handles unavailability — returns a low-confidence fallback
    result if Ollama is not running.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.1:8b",
        timeout: float = 30.0,
    ):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._taxonomy = CategoryTaxonomy()
        self._available: Optional[bool] = None

    @property
    def is_available(self) -> bool:
        """Check if Ollama is reachable (cached after first check)."""
        if self._available is None:
            self._available = self._check_availability()
        return self._available

    def reset_availability(self) -> None:
        """Force re-check of Ollama availability on next call."""
        self._available = None

    def _check_availability(self) -> bool:
        """Ping Ollama to verify it's running."""
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(f"{self._base_url}/api/tags")
                if resp.status_code == 200:
                    models = resp.json().get("models", [])
                    model_names = [m.get("name", "") for m in models]
                    if any(self._model in name for name in model_names):
                        logger.info("Ollama available with model: %s", self._model)
                        return True
                    logger.warning(
                        "Ollama running but model '%s' not found. Available: %s",
                        self._model,
                        model_names,
                    )
                    return False
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            logger.info("Ollama not available: %s", e)
        return False

    def classify(
        self,
        description: str,
        amount: Optional[float] = None,
        transaction_type: Optional[str] = None,
        currency: str = "INR",
    ) -> ClassificationResult:
        """Classify a transaction using the LLM.

        Args:
            description: Transaction description.
            amount: Transaction amount.
            transaction_type: 'debit' or 'credit'.
            currency: ISO 4217 currency code (default: INR).

        Returns:
            ClassificationResult. If Ollama is unavailable, returns a
            low-confidence "Other" result with needs_review=True.
        """
        if not self.is_available:
            return ClassificationResult(
                category="Other",
                subcategory="Uncategorized",
                confidence=0.0,
                source="llm_classifier",
                needs_review=True,
                reasoning="Ollama not available — skipping LLM classification",
            )

        amount_str = f"{abs(amount):.2f}" if amount is not None else "unknown"
        tx_type = transaction_type or ("credit" if amount and amount > 0 else "debit")

        prompt = CLASSIFICATION_PROMPT.format(
            description=description,
            amount=amount_str,
            tx_type=tx_type,
            currency_symbol=get_currency_symbol(currency),
        )

        try:
            response_text = self._call_ollama(prompt)
            return self._parse_response(response_text)
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            logger.warning("Ollama request failed: %s", e)
            self._available = False
            return ClassificationResult(
                category="Other",
                subcategory="Uncategorized",
                confidence=0.0,
                source="llm_classifier",
                needs_review=True,
                reasoning=f"Ollama connection error: {str(e)[:80]}",
            )
        except Exception as e:
            logger.error("LLM classification error: %s", e)
            return ClassificationResult(
                category="Other",
                subcategory="Uncategorized",
                confidence=0.0,
                source="llm_classifier",
                needs_review=True,
                reasoning=f"LLM error: {str(e)[:80]}",
            )

    def _call_ollama(self, prompt: str) -> str:
        """Make a synchronous request to Ollama's generate API."""
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(
                f"{self._base_url}/api/generate",
                json={
                    "model": self._model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 256,
                    },
                },
            )
            resp.raise_for_status()
            return resp.json().get("response", "")

    def _parse_response(self, response_text: str) -> ClassificationResult:
        """Parse LLM JSON response into a ClassificationResult."""
        response_text = response_text.strip()
        valid_json = True
        category_in_taxonomy = True

        try:
            data = json.loads(response_text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            import re

            json_match = re.search(r"\{[^}]+\}", response_text)
            if json_match:
                try:
                    data = json.loads(json_match.group())
                except json.JSONDecodeError:
                    valid_json = False
                    data = {}
            else:
                valid_json = False
                data = {}

        category = data.get("category", "Other")
        subcategory = data.get("subcategory")
        merchant = data.get("merchant")
        raw_confidence = float(data.get("confidence", 0.5))
        reasoning = data.get("reasoning", "LLM classification")

        # Validate category against taxonomy
        resolved = self._taxonomy.resolve_category(category)
        if resolved is None:
            category_in_taxonomy = False
            category = "Other"
        else:
            category = resolved.value

        # Null-out "null" string merchants
        if merchant and merchant.lower() in ("null", "none", "unknown", "n/a"):
            merchant = None

        confidence = compute_llm_confidence(
            llm_reported_confidence=raw_confidence,
            response_valid_json=valid_json,
            category_in_taxonomy=category_in_taxonomy,
        )

        return ClassificationResult(
            category=category,
            subcategory=subcategory,
            merchant=merchant,
            confidence=confidence,
            source="llm_classifier",
            needs_review=confidence < 0.60,
            reasoning=reasoning,
        )
