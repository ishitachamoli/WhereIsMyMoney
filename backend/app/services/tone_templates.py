"""Tone-specific phrase banks and phrasing helpers for AI summaries.

The monthly AI summary computes the same underlying statistics regardless of
the requested tone. This module turns those raw numbers into differently-voiced
prose so the same data can be rendered as a roast, praise, an executive report,
or a fun recap.

Each tone exposes a small set of pure helper functions that take pre-computed
stats and return display strings. No database access happens here.
"""

from __future__ import annotations

import hashlib
from typing import Optional

# Valid tone identifiers accepted by the monthly summary endpoint.
VALID_TONES = ("roast", "praise", "executive", "fun")

# Human-friendly metadata for each tone (used by the frontend tab bar / headers).
TONE_META: dict[str, dict[str, str]] = {
    "roast": {
        "emoji": "🔥",
        "label": "Roast",
        "tagline": "Brutally honest. You asked for this.",
    },
    "praise": {
        "emoji": "🌟",
        "label": "Praise",
        "tagline": "Celebrating your wins, big and small.",
    },
    "executive": {
        "emoji": "💼",
        "label": "Executive Summary",
        "tagline": "The formal, data-driven quarterly-report voice.",
    },
    "fun": {
        "emoji": "🎉",
        "label": "Fun Summary",
        "tagline": "Playful stats and questionable life choices.",
    },
}


def _pick(options: list[str], seed: str) -> str:
    """Deterministically choose one option from a list based on a seed string.

    Using a hash of the seed keeps output stable for the same (month, category)
    combination across regenerations while still varying between categories.
    """
    if not options:
        return ""
    digest = hashlib.md5(seed.encode("utf-8")).hexdigest()
    idx = int(digest, 16) % len(options)
    return options[idx]


# ─── Roast phrase bank ──────────────────────────────────────────────────────

_ROAST_CATEGORY_PUNCHLINES = [
    "Your kitchen is officially decorative.",
    "That's a small loan in liquid form.",
    "Your barista has equity in you now.",
    "At this point it's not a habit, it's a subscription to regret.",
    "Marie Kondo is filing a restraining order.",
    "Your wallet filed for emotional damages.",
    "That's enough to make an accountant weep.",
    "Bold strategy. Let's see if it pays off. (It won't.)",
    "Future-you is writing a strongly worded letter.",
    "Somewhere, a financial advisor felt a disturbance.",
    "You didn't budget — you freestyled.",
    "Impressive commitment to financial chaos.",
    "That money had dreams. You crushed them.",
    "Your savings account left on read.",
]

_ROAST_OPENERS = [
    "Let's talk about {month}. Brace yourself.",
    "{month} called. It wants its money back.",
    "Reviewing {month} so you don't have to. You're welcome.",
    "Buckle up — {month} was a financial rollercoaster.",
]

_ROAST_SAVINGS_NEGATIVE = [
    "You spent more than you earned. Bold. Reckless. On brand.",
    "Negative savings rate? That's not a budget, that's a cry for help.",
    "You out-spent your income. The math is not mathing.",
]

_ROAST_SAVINGS_LOW = [
    "You saved a whopping {rate}%. Don't spend it all in one place. Oh wait.",
    "A {rate}% savings rate. Truly, the bare minimum has a face.",
]

_ROAST_SAVINGS_OK = [
    "Fine, you saved {rate}%. I'll allow it. Barely.",
    "{rate}% saved. Look at you, pretending to be responsible.",
]


def roast_category_line(category: str, amount: str, month: str) -> str:
    punchline = _pick(_ROAST_CATEGORY_PUNCHLINES, seed=category + month)
    return f"You spent {amount} on {category}. {punchline}"


def roast_opener(month: str) -> str:
    return _pick(_ROAST_OPENERS, seed=month).format(month=month)


def roast_savings_line(rate: float) -> str:
    if rate < 0:
        return _pick(_ROAST_SAVINGS_NEGATIVE, seed=f"neg{rate}")
    if rate < 15:
        return _pick(_ROAST_SAVINGS_LOW, seed=f"low{rate}").format(rate=f"{rate:.0f}")
    return _pick(_ROAST_SAVINGS_OK, seed=f"ok{rate}").format(rate=f"{rate:.0f}")


def roast_merchant_line(merchant: str, count: int) -> str:
    options = [
        f"{count} transactions at {merchant}. They should name a chair after you.",
        f"You visited {merchant} {count} times. That's not loyalty, that's dependency.",
        f"{merchant}: {count} visits. Consider asking for a staff discount.",
    ]
    return _pick(options, seed=merchant + str(count))


# ─── Praise phrase bank ─────────────────────────────────────────────────────

_PRAISE_OPENERS = [
    "Let's celebrate {month} — you did some great things! 🌟",
    "{month} is looking good on you. Here's why. ✨",
    "Time for some well-deserved credit for {month}. 🎉",
    "You showed up for your finances in {month}. Respect. 💪",
]

_PRAISE_SAVINGS_GREAT = [
    "You saved {rate}% of your income — that's elite-tier discipline! 🏆",
    "A {rate}% savings rate? You're a budgeting machine. Keep going! 🚀",
]

_PRAISE_SAVINGS_OK = [
    "You kept your savings rate positive at {rate}%. Every bit counts! 🌱",
    "A {rate}% savings rate means more in your pocket than out. Nice work! 👏",
]

_PRAISE_SAVINGS_NEGATIVE = [
    "Spending edged out income this month, but awareness is step one — you've got this. 💛",
    "It was a heavier month, but tracking it is already a win. Next month is yours. 🌅",
]

_PRAISE_CATEGORY_LOW = [
    "You kept {category} spending in check this month — that restraint pays off! 🌟",
    "Nicely done keeping {category} modest at {amount}. Future-you says thanks! 🙌",
    "{category} stayed lean at {amount}. That's how habits are built! 💚",
]


def praise_opener(month: str) -> str:
    return _pick(_PRAISE_OPENERS, seed=month).format(month=month)


def praise_savings_line(rate: float) -> str:
    if rate >= 20:
        return _pick(_PRAISE_SAVINGS_GREAT, seed=f"great{rate}").format(rate=f"{rate:.0f}")
    if rate >= 0:
        return _pick(_PRAISE_SAVINGS_OK, seed=f"ok{rate}").format(rate=f"{rate:.0f}")
    return _pick(_PRAISE_SAVINGS_NEGATIVE, seed=f"neg{rate}")


def praise_category_line(category: str, amount: str, month: str) -> str:
    return _pick(_PRAISE_CATEGORY_LOW, seed=category + month).format(
        category=category, amount=amount
    )


def praise_consistency_line(no_spend_days: int) -> str:
    options = [
        f"You had {no_spend_days} no-spend days this month — pure self-control! 🧘",
        f"{no_spend_days} days without spending a thing. That discipline adds up! 💪",
    ]
    return _pick(options, seed=f"nospend{no_spend_days}")


# ─── Executive phrase bank ──────────────────────────────────────────────────


def exec_overview_line(currency: str, total_out: float, txn_count: int, month: str) -> str:
    return (
        f"Total outflow for {month}: {currency}{total_out:,.0f} across "
        f"{txn_count} transactions."
    )


def exec_category_line(category: str, currency: str, amount: float, pct: float) -> str:
    return (
        f"{category} expenditure totaled {currency}{amount:,.0f}, representing "
        f"{pct:.1f}% of monthly outflow."
    )


def exec_savings_line(rate: float, benchmark: float = 15.0) -> str:
    if rate >= benchmark:
        return (
            f"Net savings rate: {rate:.1f}%, exceeding the {benchmark:.0f}% benchmark."
        )
    if rate >= 0:
        return (
            f"Net savings rate: {rate:.1f}%, below the {benchmark:.0f}% benchmark. "
            f"Corrective action recommended."
        )
    return (
        f"Net savings rate: {rate:.1f}% (deficit). Outflow exceeded inflow for the period."
    )


def exec_mom_line(currency: str, change_pct: Optional[float], prev_month: str) -> Optional[str]:
    if change_pct is None:
        return None
    direction = "increase" if change_pct >= 0 else "decrease"
    return (
        f"Month-over-month outflow reflects a {abs(change_pct):.1f}% {direction} "
        f"relative to {prev_month}."
    )


# ─── Fun phrase bank ────────────────────────────────────────────────────────

_FUN_OPENERS = [
    "🎉 Welcome to your {month} money montage!",
    "🎢 {month}, by the numbers (and the vibes):",
    "✨ Your {month} financial highlight reel is ready!",
    "🍿 Grab a snack — here's how {month} went down:",
]

_FUN_CATEGORY_COMMENTS = [
    "treat yourself energy, certified.",
    "the people's champion of your budget.",
    "no notes, only vibes.",
    "main character spending.",
    "an iconic line item, honestly.",
    "your wallet's favorite cardio.",
    "a bold and beautiful choice.",
]


def fun_opener(month: str) -> str:
    return _pick(_FUN_OPENERS, seed=month).format(month=month)


def fun_category_line(category: str, amount: str, month: str) -> str:
    comment = _pick(_FUN_CATEGORY_COMMENTS, seed=category + month)
    return f"💸 Splash of the month: {amount} on {category} — {comment}"


def fun_count_line(label: str, count: int, emoji: str = "🎯") -> str:
    options = [
        f"{emoji} {label} count: {count}. That's a whole personality.",
        f"{emoji} You racked up {count} {label.lower()}. Iconic behavior.",
        f"{emoji} {count} {label.lower()} this month. Respectfully, wow.",
    ]
    return _pick(options, seed=label + str(count))


def fun_savings_line(rate: float) -> str:
    if rate >= 20:
        return f"🏦 You stashed away {rate:.0f}% of your income. Sigma saver behavior. 💪"
    if rate >= 0:
        return f"🪙 Savings rate: {rate:.0f}%. Small wins are still wins, bestie. ✨"
    return "🙃 Savings rate went negative this month. We move. We recover. We thrive."


# ─── Year recap personality titles ──────────────────────────────────────────

# Maps a dominant-spend signal to a Spotify-Wrapped-style personality title.
YEAR_PERSONALITY_TITLES: dict[str, dict[str, str]] = {
    "food": {"title": "The Foodie Royalty", "emoji": "🍽️"},
    "coffee": {"title": "The Coffee Connoisseur", "emoji": "☕"},
    "shopping": {"title": "The Retail Therapist", "emoji": "🛍️"},
    "travel": {"title": "The Jetsetter", "emoji": "✈️"},
    "entertainment": {"title": "The Good-Time Guru", "emoji": "🎬"},
    "housing": {"title": "The Homebody", "emoji": "🏠"},
    "transport": {"title": "The Road Warrior", "emoji": "🚗"},
    "investment": {"title": "The Wealth Builder", "emoji": "📈"},
    "saver": {"title": "The Vault Keeper", "emoji": "💎"},
    "balanced": {"title": "The Balanced Tactician", "emoji": "⚖️"},
}


def year_narrative(year: int, personality_title: str, top_category: Optional[str]) -> str:
    """Compose the closing narrative paragraph for the year recap."""
    if top_category:
        return (
            f"{year} was the year of {top_category}. You earned the title of "
            f"\"{personality_title}\" — a story told in transactions, one swipe at a time. "
            f"Here's to an even smarter year ahead. 🥂"
        )
    return (
        f"{year} was a year of building habits. You earned the title of "
        f"\"{personality_title}\". Onward to the next chapter! 🥂"
    )
