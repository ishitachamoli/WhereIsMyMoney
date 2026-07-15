"""User feedback collection for continuous model improvement.

Stores user corrections when they override a classification, enabling:
1. Accuracy tracking over time
2. Retraining signals for ML models
3. Pattern discovery for new rule additions
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_FEEDBACK_DIR = Path("data/feedback")


@dataclass
class FeedbackEntry:
    """A single user correction record."""

    transaction_description: str
    original_category: str
    corrected_category: str
    original_subcategory: Optional[str] = None
    corrected_subcategory: Optional[str] = None
    original_confidence: float = 0.0
    original_source: str = "unknown"
    amount: Optional[float] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    user_note: Optional[str] = None

    @property
    def was_correct(self) -> bool:
        return self.original_category == self.corrected_category

    def to_dict(self) -> dict:
        return asdict(self)


class FeedbackStore:
    """Persists user feedback to disk as JSONL (one entry per line).

    Data is stored in a configurable directory with one file per day
    for easy management and rotation.
    """

    def __init__(self, feedback_dir: Optional[Path] = None):
        self._dir = feedback_dir or DEFAULT_FEEDBACK_DIR
        self._dir.mkdir(parents=True, exist_ok=True)
        self._entries_cache: list[FeedbackEntry] = []
        self._loaded = False

    def _current_file(self) -> Path:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self._dir / f"feedback_{date_str}.jsonl"

    def add_feedback(self, entry: FeedbackEntry) -> None:
        """Record a user correction.

        Args:
            entry: The feedback entry with original vs corrected categories.
        """
        filepath = self._current_file()
        try:
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict()) + "\n")
            self._entries_cache.append(entry)
            logger.info(
                "Feedback recorded: '%s' → %s (was: %s)",
                entry.transaction_description[:40],
                entry.corrected_category,
                entry.original_category,
            )
        except OSError as e:
            logger.error("Failed to write feedback: %s", e)

    def get_all_feedback(self) -> list[FeedbackEntry]:
        """Load all feedback entries from disk."""
        if self._loaded:
            return self._entries_cache

        entries: list[FeedbackEntry] = []
        if not self._dir.exists():
            return entries

        for filepath in sorted(self._dir.glob("feedback_*.jsonl")):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            data = json.loads(line)
                            entries.append(FeedbackEntry(**data))
            except (OSError, json.JSONDecodeError) as e:
                logger.warning("Error reading feedback file %s: %s", filepath, e)

        self._entries_cache = entries
        self._loaded = True
        return entries

    def get_accuracy_stats(self) -> dict:
        """Compute accuracy statistics from feedback data.

        Returns:
            Dict with overall accuracy, per-category accuracy, and
            common corrections.
        """
        entries = self.get_all_feedback()
        if not entries:
            return {
                "total_feedback": 0,
                "corrections": 0,
                "correct": 0,
                "accuracy_rate": None,
                "common_misclassifications": [],
            }

        corrections = [e for e in entries if not e.was_correct]
        correct = [e for e in entries if e.was_correct]

        # Count common misclassification patterns
        misclass_counts: dict[str, int] = {}
        for entry in corrections:
            key = f"{entry.original_category} → {entry.corrected_category}"
            misclass_counts[key] = misclass_counts.get(key, 0) + 1

        common_misclass = sorted(
            misclass_counts.items(), key=lambda x: x[1], reverse=True
        )[:10]

        # Per-category accuracy
        category_stats: dict[str, dict] = {}
        for entry in entries:
            cat = entry.corrected_category
            if cat not in category_stats:
                category_stats[cat] = {"total": 0, "correct": 0}
            category_stats[cat]["total"] += 1
            if entry.was_correct:
                category_stats[cat]["correct"] += 1

        per_category = {
            cat: {
                "total": stats["total"],
                "accuracy": round(stats["correct"] / stats["total"], 4) if stats["total"] > 0 else 0.0,
            }
            for cat, stats in category_stats.items()
        }

        return {
            "total_feedback": len(entries),
            "corrections": len(corrections),
            "correct": len(correct),
            "accuracy_rate": round(len(correct) / len(entries), 4) if entries else None,
            "common_misclassifications": [
                {"pattern": pattern, "count": count}
                for pattern, count in common_misclass
            ],
            "per_category": per_category,
        }

    def get_training_data(self) -> list[dict]:
        """Export feedback as training data for model fine-tuning.

        Returns pairs of (description, correct_category) suitable for
        training a text classifier.
        """
        entries = self.get_all_feedback()
        training_data = []
        for entry in entries:
            training_data.append({
                "text": entry.transaction_description,
                "label": entry.corrected_category,
                "sublabel": entry.corrected_subcategory,
                "amount": entry.amount,
            })
        return training_data

    def clear(self) -> None:
        """Remove all feedback data (destructive)."""
        if self._dir.exists():
            for filepath in self._dir.glob("feedback_*.jsonl"):
                filepath.unlink()
        self._entries_cache = []
        self._loaded = False
        logger.info("All feedback data cleared")
