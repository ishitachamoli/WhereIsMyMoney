"""AI-powered transaction classification pipeline.

Three-tier architecture:
  Tier 1: Rule-based regex matching (fast, high confidence)
  Tier 2: Zero-shot ML classification (HuggingFace BART)
  Tier 3: LLM classification via Ollama (complex/ambiguous cases)
"""

from app.services.classification.pipeline import ClassificationPipeline
from app.services.classification.categories import CategoryTaxonomy

__all__ = ["ClassificationPipeline", "CategoryTaxonomy"]
