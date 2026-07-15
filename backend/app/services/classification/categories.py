"""Hierarchical category taxonomy for transaction classification.

Structure: Top-level Category > Subcategory > Specific type
Each category has an associated emoji, color, and list of subcategories.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class TopCategory(str, Enum):
    FOOD_DINING = "Food & Dining"
    TRANSPORTATION = "Transportation"
    SHOPPING = "Shopping"
    ENTERTAINMENT = "Entertainment"
    HEALTHCARE = "Healthcare"
    UTILITIES = "Utilities"
    BILLS_FEES = "Bills & Fees"
    EDUCATION = "Education"
    PERSONAL_CARE = "Personal Care"
    HOME = "Home"
    INCOME = "Income"
    TRANSFERS = "Transfers"
    INVESTMENTS = "Investments"
    CASH = "Cash"
    OTHER = "Other"


@dataclass(frozen=True)
class Subcategory:
    name: str
    keywords: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Category:
    name: TopCategory
    emoji: str
    color: str
    subcategories: tuple[Subcategory, ...] = field(default_factory=tuple)


TAXONOMY: dict[TopCategory, Category] = {
    TopCategory.FOOD_DINING: Category(
        name=TopCategory.FOOD_DINING,
        emoji="🍽️",
        color="#FF6B6B",
        subcategories=(
            Subcategory("Restaurants", ("restaurant", "dining", "food court")),
            Subcategory("Fast Food", ("mcdonald", "kfc", "burger king", "dominos", "pizza hut", "subway")),
            Subcategory("Food Delivery", ("swiggy", "zomato", "dunzo")),
            Subcategory("Cafes & Coffee", ("starbucks", "cafe coffee day", "ccd", "barista", "blue tokai", "third wave")),
            Subcategory("Groceries", ("bigbasket", "dmart", "reliance fresh", "more supermarket", "grocery", "blinkit", "zepto", "instamart")),
            Subcategory("Alcohol & Bars", ("bar", "pub", "brewery", "wine", "liquor")),
            Subcategory("Street Food & Snacks", ("snack", "chaat", "bakery", "sweet shop")),
        ),
    ),
    TopCategory.TRANSPORTATION: Category(
        name=TopCategory.TRANSPORTATION,
        emoji="🚗",
        color="#4ECDC4",
        subcategories=(
            Subcategory("Ride Sharing", ("uber", "ola", "rapido")),
            Subcategory("Fuel", ("petrol", "diesel", "fuel", "bharat petroleum", "hp petrol", "iocl", "indian oil")),
            Subcategory("Parking", ("parking", "park fee")),
            Subcategory("Public Transit", ("metro", "bus pass", "local train", "irctc", "railway")),
            Subcategory("Flights", ("flight", "airline", "indigo", "air india", "spicejet", "vistara", "makemytrip")),
            Subcategory("Auto & Maintenance", ("service center", "car wash", "tyre", "mechanic")),
            Subcategory("Tolls", ("fastag", "toll", "nhai")),
        ),
    ),
    TopCategory.SHOPPING: Category(
        name=TopCategory.SHOPPING,
        emoji="🛍️",
        color="#A78BFA",
        subcategories=(
            Subcategory("E-commerce", ("amazon", "flipkart", "meesho", "snapdeal")),
            Subcategory("Fashion & Clothing", ("myntra", "ajio", "zara", "h&m", "lifestyle", "westside", "pantaloons")),
            Subcategory("Electronics", ("croma", "reliance digital", "vijay sales", "apple store")),
            Subcategory("Home & Furniture", ("ikea", "pepperfry", "urban ladder", "hometown")),
            Subcategory("Beauty & Cosmetics", ("nykaa", "purplle", "sephora", "mac")),
            Subcategory("Books & Stationery", ("book", "stationery", "crossword", "kindle")),
            Subcategory("Gifts & Flowers", ("ferns n petals", "gift", "flower", "igp")),
        ),
    ),
    TopCategory.ENTERTAINMENT: Category(
        name=TopCategory.ENTERTAINMENT,
        emoji="🎬",
        color="#F59E0B",
        subcategories=(
            Subcategory("Streaming", ("netflix", "prime video", "hotstar", "disney", "spotify", "youtube premium", "apple music", "jio cinema")),
            Subcategory("Movies & Events", ("pvr", "inox", "cinepolis", "bookmyshow")),
            Subcategory("Gaming", ("steam", "playstation", "xbox", "game", "epic games")),
            Subcategory("Sports & Fitness", ("gym", "cult fit", "fitness", "sports")),
            Subcategory("Travel & Vacation", ("hotel", "oyo", "airbnb", "goibibo", "trivago", "yatra", "booking.com")),
            Subcategory("Hobbies", ("hobby", "music class", "dance class", "art")),
        ),
    ),
    TopCategory.HEALTHCARE: Category(
        name=TopCategory.HEALTHCARE,
        emoji="🏥",
        color="#10B981",
        subcategories=(
            Subcategory("Pharmacy", ("apollo pharmacy", "medplus", "1mg", "netmeds", "pharmeasy")),
            Subcategory("Hospital & Clinic", ("hospital", "clinic", "diagnostic", "lab test", "pathology")),
            Subcategory("Doctor Consultation", ("doctor", "consultation", "practo", "teleconsult")),
            Subcategory("Dental", ("dental", "dentist")),
            Subcategory("Optical", ("optical", "lens", "eye")),
            Subcategory("Mental Health", ("therapy", "therapist", "counseling")),
        ),
    ),
    TopCategory.UTILITIES: Category(
        name=TopCategory.UTILITIES,
        emoji="💡",
        color="#06B6D4",
        subcategories=(
            Subcategory("Electricity", ("electricity", "power", "bescom", "tata power", "adani electricity")),
            Subcategory("Water", ("water supply", "municipal", "corporation water")),
            Subcategory("Internet & Broadband", ("airtel fiber", "jio fiber", "act fiber", "bsnl broadband", "hathway")),
            Subcategory("Mobile Recharge", ("mobile recharge", "prepaid", "postpaid", "airtel", "jio", "vi", "bsnl")),
            Subcategory("Gas", ("gas cylinder", "lpg", "piped gas", "indane", "bharat gas", "hp gas")),
            Subcategory("DTH & Cable", ("tata play", "dish tv", "airtel dth", "sun direct", "d2h")),
        ),
    ),
    TopCategory.BILLS_FEES: Category(
        name=TopCategory.BILLS_FEES,
        emoji="📄",
        color="#8B5CF6",
        subcategories=(
            Subcategory("Credit Card Bill", ("credit card bill", "cc payment", "card payment")),
            Subcategory("Insurance", ("insurance", "policy premium", "lic", "health insurance", "term plan")),
            Subcategory("EMI & Loans", ("emi", "loan", "personal loan", "home loan")),
            Subcategory("Subscriptions", ("subscription", "membership", "annual fee")),
            Subcategory("Government & Tax", ("income tax", "gst", "property tax", "municipal tax", "stamp duty")),
            Subcategory("Bank Charges", ("bank charge", "maintenance charge", "sms charge", "atm charge")),
        ),
    ),
    TopCategory.EDUCATION: Category(
        name=TopCategory.EDUCATION,
        emoji="📚",
        color="#3B82F6",
        subcategories=(
            Subcategory("Courses & Training", ("udemy", "coursera", "unacademy", "byju", "upgrad")),
            Subcategory("School & College Fees", ("tuition", "school fee", "college fee", "university")),
            Subcategory("Books & Materials", ("textbook", "study material", "notebook")),
            Subcategory("Coaching", ("coaching", "tutorial", "class", "institute")),
        ),
    ),
    TopCategory.PERSONAL_CARE: Category(
        name=TopCategory.PERSONAL_CARE,
        emoji="💇",
        color="#EC4899",
        subcategories=(
            Subcategory("Salon & Spa", ("salon", "spa", "haircut", "parlour", "urban company")),
            Subcategory("Skincare & Grooming", ("skincare", "grooming", "dermatologist")),
            Subcategory("Laundry", ("laundry", "dry clean")),
        ),
    ),
    TopCategory.HOME: Category(
        name=TopCategory.HOME,
        emoji="🏠",
        color="#F97316",
        subcategories=(
            Subcategory("Rent", ("rent", "house rent", "landlord")),
            Subcategory("Maintenance", ("maintenance", "society", "apartment")),
            Subcategory("Repairs", ("plumber", "electrician", "repair", "carpenter")),
            Subcategory("Household Supplies", ("household", "cleaning", "detergent")),
            Subcategory("Domestic Help", ("maid", "cook", "domestic", "helper")),
        ),
    ),
    TopCategory.INCOME: Category(
        name=TopCategory.INCOME,
        emoji="💰",
        color="#22C55E",
        subcategories=(
            Subcategory("Salary", ("salary", "sal credit", "payroll")),
            Subcategory("Freelance", ("freelance", "consulting", "contract")),
            Subcategory("Refund", ("refund", "reversal", "cashback")),
            Subcategory("Interest", ("interest", "fd interest", "savings interest")),
            Subcategory("Dividend", ("dividend",)),
            Subcategory("Rental Income", ("rental income", "rent received")),
        ),
    ),
    TopCategory.TRANSFERS: Category(
        name=TopCategory.TRANSFERS,
        emoji="🔄",
        color="#6B7280",
        subcategories=(
            Subcategory("UPI Transfer", ("upi", "phonepe", "gpay", "google pay", "paytm")),
            Subcategory("Bank Transfer", ("neft", "rtgs", "imps")),
            Subcategory("Self Transfer", ("self transfer", "own account")),
            Subcategory("Family & Friends", ("family", "friend")),
        ),
    ),
    TopCategory.INVESTMENTS: Category(
        name=TopCategory.INVESTMENTS,
        emoji="📈",
        color="#14B8A6",
        subcategories=(
            Subcategory("Mutual Funds", ("mutual fund", "sip", "mf", "groww", "zerodha coin")),
            Subcategory("Stocks", ("stock", "share", "equity", "zerodha", "upstox", "angel")),
            Subcategory("Fixed Deposits", ("fixed deposit", "fd", "recurring deposit", "rd")),
            Subcategory("Crypto", ("crypto", "bitcoin", "wazirx", "coinswitch")),
            Subcategory("Gold", ("gold", "sovereign gold", "digital gold")),
            Subcategory("PPF & NPS", ("ppf", "nps", "provident fund", "epf")),
        ),
    ),
    TopCategory.CASH: Category(
        name=TopCategory.CASH,
        emoji="💵",
        color="#78716C",
        subcategories=(
            Subcategory("ATM Withdrawal", ("atm", "cash withdrawal", "atm wdl")),
            Subcategory("Cash Deposit", ("cash deposit", "cdr")),
        ),
    ),
    TopCategory.OTHER: Category(
        name=TopCategory.OTHER,
        emoji="❓",
        color="#9CA3AF",
        subcategories=(
            Subcategory("Uncategorized", ()),
            Subcategory("Charity & Donations", ("donation", "charity", "ngo")),
            Subcategory("Pets", ("pet", "vet", "veterinary")),
        ),
    ),
}


class CategoryTaxonomy:
    """Provides lookup and validation for the category taxonomy."""

    def __init__(self) -> None:
        self._taxonomy = TAXONOMY
        self._label_lookup: dict[str, TopCategory] = {}
        self._subcategory_lookup: dict[str, tuple[TopCategory, str]] = {}
        self._build_lookups()

    def _build_lookups(self) -> None:
        for top_cat, cat_data in self._taxonomy.items():
            self._label_lookup[top_cat.value.lower()] = top_cat
            for sub in cat_data.subcategories:
                key = f"{top_cat.value.lower()}|{sub.name.lower()}"
                self._subcategory_lookup[key] = (top_cat, sub.name)

    @property
    def top_categories(self) -> list[TopCategory]:
        return list(self._taxonomy.keys())

    @property
    def category_labels(self) -> list[str]:
        return [c.value for c in self._taxonomy.keys()]

    def get_category(self, name: str) -> Optional[Category]:
        """Look up a category by name (case-insensitive)."""
        for top_cat, cat_data in self._taxonomy.items():
            if top_cat.value.lower() == name.lower():
                return cat_data
        return None

    def get_subcategories(self, category: TopCategory) -> list[str]:
        """Get all subcategory names for a given top-level category."""
        cat_data = self._taxonomy.get(category)
        if not cat_data:
            return []
        return [sub.name for sub in cat_data.subcategories]

    def resolve_category(self, label: str) -> Optional[TopCategory]:
        """Resolve a free-text label to a TopCategory enum value."""
        label_lower = label.lower().strip()
        if label_lower in self._label_lookup:
            return self._label_lookup[label_lower]
        for top_cat in TopCategory:
            if label_lower in top_cat.value.lower() or top_cat.value.lower() in label_lower:
                return top_cat
        return None

    def get_emoji(self, category: TopCategory) -> str:
        cat_data = self._taxonomy.get(category)
        return cat_data.emoji if cat_data else "❓"

    def get_color(self, category: TopCategory) -> str:
        cat_data = self._taxonomy.get(category)
        return cat_data.color if cat_data else "#9CA3AF"
