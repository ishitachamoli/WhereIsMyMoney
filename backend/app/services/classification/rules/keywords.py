"""Keyword-to-category mapping for fallback rule matching.

When merchant pattern matching fails, keyword matching provides a secondary
signal. Keywords are ranked by specificity — more specific keywords have
higher weight.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KeywordEntry:
    keyword: str
    category: str
    subcategory: str
    weight: float = 1.0


# Higher weight = more specific/reliable keyword
KEYWORD_MAPPINGS: list[KeywordEntry] = [
    # ─── Food & Dining (weight: 0.7–1.0) ───
    KeywordEntry("restaurant", "Food & Dining", "Restaurants", 0.9),
    KeywordEntry("food", "Food & Dining", "Restaurants", 0.7),
    KeywordEntry("dining", "Food & Dining", "Restaurants", 0.9),
    KeywordEntry("cafe", "Food & Dining", "Cafes & Coffee", 0.85),
    KeywordEntry("coffee", "Food & Dining", "Cafes & Coffee", 0.8),
    KeywordEntry("tea", "Food & Dining", "Cafes & Coffee", 0.6),
    KeywordEntry("bakery", "Food & Dining", "Street Food & Snacks", 0.85),
    KeywordEntry("sweet", "Food & Dining", "Street Food & Snacks", 0.6),
    KeywordEntry("grocery", "Food & Dining", "Groceries", 0.9),
    KeywordEntry("supermarket", "Food & Dining", "Groceries", 0.95),
    KeywordEntry("vegetable", "Food & Dining", "Groceries", 0.85),
    KeywordEntry("fruit", "Food & Dining", "Groceries", 0.75),
    KeywordEntry("meat", "Food & Dining", "Groceries", 0.75),
    KeywordEntry("dairy", "Food & Dining", "Groceries", 0.8),
    KeywordEntry("liquor", "Food & Dining", "Alcohol & Bars", 0.95),
    KeywordEntry("wine", "Food & Dining", "Alcohol & Bars", 0.8),
    KeywordEntry("beer", "Food & Dining", "Alcohol & Bars", 0.85),
    KeywordEntry("bar", "Food & Dining", "Alcohol & Bars", 0.6),

    # ─── Transportation ───
    KeywordEntry("petrol", "Transportation", "Fuel", 0.95),
    KeywordEntry("diesel", "Transportation", "Fuel", 0.95),
    KeywordEntry("fuel", "Transportation", "Fuel", 0.9),
    KeywordEntry("parking", "Transportation", "Parking", 0.95),
    KeywordEntry("toll", "Transportation", "Tolls", 0.9),
    KeywordEntry("fastag", "Transportation", "Tolls", 0.98),
    KeywordEntry("cab", "Transportation", "Ride Sharing", 0.8),
    KeywordEntry("ride", "Transportation", "Ride Sharing", 0.7),
    KeywordEntry("taxi", "Transportation", "Ride Sharing", 0.85),
    KeywordEntry("auto", "Transportation", "Ride Sharing", 0.5),
    KeywordEntry("metro", "Transportation", "Public Transit", 0.85),
    KeywordEntry("railway", "Transportation", "Public Transit", 0.9),
    KeywordEntry("train", "Transportation", "Public Transit", 0.75),
    KeywordEntry("flight", "Transportation", "Flights", 0.9),
    KeywordEntry("airline", "Transportation", "Flights", 0.95),
    KeywordEntry("airport", "Transportation", "Flights", 0.8),

    # ─── Shopping ───
    KeywordEntry("shopping", "Shopping", "E-commerce", 0.7),
    KeywordEntry("online", "Shopping", "E-commerce", 0.5),
    KeywordEntry("fashion", "Shopping", "Fashion & Clothing", 0.85),
    KeywordEntry("clothing", "Shopping", "Fashion & Clothing", 0.9),
    KeywordEntry("garment", "Shopping", "Fashion & Clothing", 0.85),
    KeywordEntry("shoes", "Shopping", "Fashion & Clothing", 0.8),
    KeywordEntry("electronics", "Shopping", "Electronics", 0.9),
    KeywordEntry("mobile", "Shopping", "Electronics", 0.5),
    KeywordEntry("laptop", "Shopping", "Electronics", 0.9),
    KeywordEntry("furniture", "Shopping", "Home & Furniture", 0.9),
    KeywordEntry("decor", "Shopping", "Home & Furniture", 0.8),

    # ─── Entertainment ───
    KeywordEntry("movie", "Entertainment", "Movies & Events", 0.9),
    KeywordEntry("cinema", "Entertainment", "Movies & Events", 0.95),
    KeywordEntry("theatre", "Entertainment", "Movies & Events", 0.8),
    KeywordEntry("concert", "Entertainment", "Movies & Events", 0.9),
    KeywordEntry("game", "Entertainment", "Gaming", 0.6),
    KeywordEntry("gaming", "Entertainment", "Gaming", 0.9),
    KeywordEntry("stream", "Entertainment", "Streaming", 0.6),
    KeywordEntry("subscription", "Entertainment", "Streaming", 0.5),
    KeywordEntry("gym", "Entertainment", "Sports & Fitness", 0.9),
    KeywordEntry("fitness", "Entertainment", "Sports & Fitness", 0.85),
    KeywordEntry("sport", "Entertainment", "Sports & Fitness", 0.7),
    KeywordEntry("hotel", "Entertainment", "Travel & Vacation", 0.85),
    KeywordEntry("travel", "Entertainment", "Travel & Vacation", 0.8),
    KeywordEntry("resort", "Entertainment", "Travel & Vacation", 0.9),
    KeywordEntry("vacation", "Entertainment", "Travel & Vacation", 0.95),

    # ─── Healthcare ───
    KeywordEntry("hospital", "Healthcare", "Hospital & Clinic", 0.95),
    KeywordEntry("clinic", "Healthcare", "Hospital & Clinic", 0.9),
    KeywordEntry("doctor", "Healthcare", "Doctor Consultation", 0.9),
    KeywordEntry("medical", "Healthcare", "Hospital & Clinic", 0.85),
    KeywordEntry("pharmacy", "Healthcare", "Pharmacy", 0.95),
    KeywordEntry("medicine", "Healthcare", "Pharmacy", 0.85),
    KeywordEntry("diagnostic", "Healthcare", "Hospital & Clinic", 0.9),
    KeywordEntry("pathology", "Healthcare", "Hospital & Clinic", 0.9),
    KeywordEntry("dental", "Healthcare", "Dental", 0.95),
    KeywordEntry("eye", "Healthcare", "Optical", 0.6),
    KeywordEntry("optical", "Healthcare", "Optical", 0.9),

    # ─── Utilities ───
    KeywordEntry("electricity", "Utilities", "Electricity", 0.95),
    KeywordEntry("power", "Utilities", "Electricity", 0.7),
    KeywordEntry("water", "Utilities", "Water", 0.7),
    KeywordEntry("internet", "Utilities", "Internet & Broadband", 0.85),
    KeywordEntry("broadband", "Utilities", "Internet & Broadband", 0.95),
    KeywordEntry("wifi", "Utilities", "Internet & Broadband", 0.9),
    KeywordEntry("recharge", "Utilities", "Mobile Recharge", 0.8),
    KeywordEntry("gas", "Utilities", "Gas", 0.7),
    KeywordEntry("cylinder", "Utilities", "Gas", 0.9),
    KeywordEntry("lpg", "Utilities", "Gas", 0.95),

    # ─── Bills & Fees ───
    KeywordEntry("insurance", "Bills & Fees", "Insurance", 0.95),
    KeywordEntry("premium", "Bills & Fees", "Insurance", 0.7),
    KeywordEntry("policy", "Bills & Fees", "Insurance", 0.75),
    KeywordEntry("emi", "Bills & Fees", "EMI & Loans", 0.95),
    KeywordEntry("loan", "Bills & Fees", "EMI & Loans", 0.85),
    KeywordEntry("credit card", "Bills & Fees", "Credit Card Bill", 0.9),
    KeywordEntry("annual fee", "Bills & Fees", "Subscriptions", 0.85),
    KeywordEntry("membership", "Bills & Fees", "Subscriptions", 0.8),
    KeywordEntry("tax", "Bills & Fees", "Government & Tax", 0.7),
    KeywordEntry("income tax", "Bills & Fees", "Government & Tax", 0.95),
    KeywordEntry("gst", "Bills & Fees", "Government & Tax", 0.9),

    # ─── Education ───
    KeywordEntry("tuition", "Education", "School & College Fees", 0.95),
    KeywordEntry("school", "Education", "School & College Fees", 0.8),
    KeywordEntry("college", "Education", "School & College Fees", 0.85),
    KeywordEntry("university", "Education", "School & College Fees", 0.9),
    KeywordEntry("course", "Education", "Courses & Training", 0.75),
    KeywordEntry("training", "Education", "Courses & Training", 0.7),
    KeywordEntry("coaching", "Education", "Coaching", 0.9),

    # ─── Personal Care ───
    KeywordEntry("salon", "Personal Care", "Salon & Spa", 0.95),
    KeywordEntry("spa", "Personal Care", "Salon & Spa", 0.9),
    KeywordEntry("haircut", "Personal Care", "Salon & Spa", 0.95),
    KeywordEntry("parlour", "Personal Care", "Salon & Spa", 0.9),
    KeywordEntry("laundry", "Personal Care", "Laundry", 0.95),
    KeywordEntry("dry clean", "Personal Care", "Laundry", 0.95),

    # ─── Home ───
    KeywordEntry("rent", "Home", "Rent", 0.8),
    KeywordEntry("maintenance", "Home", "Maintenance", 0.7),
    KeywordEntry("society", "Home", "Maintenance", 0.75),
    KeywordEntry("plumber", "Home", "Repairs", 0.9),
    KeywordEntry("electrician", "Home", "Repairs", 0.9),
    KeywordEntry("carpenter", "Home", "Repairs", 0.9),
    KeywordEntry("maid", "Home", "Domestic Help", 0.9),

    # ─── Income ───
    KeywordEntry("salary", "Income", "Salary", 0.98),
    KeywordEntry("payroll", "Income", "Salary", 0.95),
    KeywordEntry("refund", "Income", "Refund", 0.9),
    KeywordEntry("cashback", "Income", "Refund", 0.85),
    KeywordEntry("reversal", "Income", "Refund", 0.85),
    KeywordEntry("interest", "Income", "Interest", 0.75),
    KeywordEntry("dividend", "Income", "Dividend", 0.9),

    # ─── Investments ───
    KeywordEntry("mutual fund", "Investments", "Mutual Funds", 0.95),
    KeywordEntry("sip", "Investments", "Mutual Funds", 0.9),
    KeywordEntry("stock", "Investments", "Stocks", 0.7),
    KeywordEntry("share", "Investments", "Stocks", 0.5),
    KeywordEntry("equity", "Investments", "Stocks", 0.85),
    KeywordEntry("fixed deposit", "Investments", "Fixed Deposits", 0.95),
    KeywordEntry("fd", "Investments", "Fixed Deposits", 0.6),
    KeywordEntry("ppf", "Investments", "PPF & NPS", 0.95),
    KeywordEntry("nps", "Investments", "PPF & NPS", 0.9),
    KeywordEntry("gold", "Investments", "Gold", 0.6),

    # ─── Cash ───
    KeywordEntry("atm", "Cash", "ATM Withdrawal", 0.9),
    KeywordEntry("withdrawal", "Cash", "ATM Withdrawal", 0.7),
    KeywordEntry("cash", "Cash", "ATM Withdrawal", 0.5),

    # ─── Transfers ───
    KeywordEntry("transfer", "Transfers", "Bank Transfer", 0.6),
    KeywordEntry("neft", "Transfers", "Bank Transfer", 0.85),
    KeywordEntry("rtgs", "Transfers", "Bank Transfer", 0.85),
    KeywordEntry("imps", "Transfers", "Bank Transfer", 0.85),
    KeywordEntry("upi", "Transfers", "UPI Transfer", 0.7),

    # ─── Other ───
    KeywordEntry("donation", "Other", "Charity & Donations", 0.9),
    KeywordEntry("charity", "Other", "Charity & Donations", 0.95),
    KeywordEntry("temple", "Other", "Charity & Donations", 0.7),
    KeywordEntry("church", "Other", "Charity & Donations", 0.7),
    KeywordEntry("pet", "Other", "Pets", 0.6),
    KeywordEntry("veterinary", "Other", "Pets", 0.95),
]


def find_keyword_matches(description: str) -> list[KeywordEntry]:
    """Find all matching keywords in a transaction description.

    Returns matches sorted by weight (highest first).
    """
    desc_lower = description.lower()
    matches = []
    for entry in KEYWORD_MAPPINGS:
        if entry.keyword in desc_lower:
            matches.append(entry)
    return sorted(matches, key=lambda e: e.weight, reverse=True)


def get_best_keyword_match(description: str) -> KeywordEntry | None:
    """Return the single best keyword match for a description."""
    matches = find_keyword_matches(description)
    return matches[0] if matches else None
