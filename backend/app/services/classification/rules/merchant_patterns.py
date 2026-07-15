"""Regex patterns for 100+ Indian merchants organized by category.

Each pattern dict maps a category to subcategory dicts, each containing
a compiled regex that matches transaction descriptions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class MerchantMatch:
    merchant_name: str
    category: str
    subcategory: str
    pattern_source: str


# ─── FOOD & DINING ───────────────────────────────────────────────────────────

FOOD_DELIVERY_PATTERN = re.compile(
    r"(SWIGGY|ZOMATO|DUNZO\s*DAILY|DUNZO|EATSURE|BOX8|FAASOS|BEHROUZ)",
    re.IGNORECASE,
)
FAST_FOOD_PATTERN = re.compile(
    r"(DOMINOS|DOMINO'?S|PIZZA\s*HUT|KFC|MCDONALD|MCDONALDS|MC\s*DONALD|"
    r"BURGER\s*KING|SUBWAY|WENDY|TACO\s*BELL|HALDIRAM|BIKANERVALA)",
    re.IGNORECASE,
)
CAFES_PATTERN = re.compile(
    r"(STARBUCKS|CAFE\s*COFFEE\s*DAY|CCD|BARISTA|BLUE\s*TOKAI|"
    r"THIRD\s*WAVE|CHAAYOS|CHAI\s*POINT|TIM\s*HORTONS)",
    re.IGNORECASE,
)
GROCERIES_PATTERN = re.compile(
    r"(BIGBASKET|BIG\s*BASKET|BLINKIT|ZEPTO|INSTAMART|SWIGGY\s*INSTAMART|"
    r"DMART|D\s*MART|RELIANCE\s*FRESH|RELIANCE\s*SMART|MORE\s*SUPERMARKET|"
    r"MORE\s*MEGA|NATURE'?S\s*BASKET|STAR\s*BAZAAR|SPENCER|GROFERS|"
    r"JIOMART|JIO\s*MART|FRESH\s*TO\s*HOME|LICIOUS|COUNTRY\s*DELIGHT)",
    re.IGNORECASE,
)
RESTAURANTS_PATTERN = re.compile(
    r"(RESTAURANT|RESTRO|DINE|DINING|BIRYANI|TANDOOR|DHABA|KITCHEN|EATERY|FOOD\s*COURT)",
    re.IGNORECASE,
)
ALCOHOL_PATTERN = re.compile(
    r"(LIQUOR|WINE\s*SHOP|BAR\s+|BREWERY|PUB\s|DRINX|MADHULOKA|TONIQUE)",
    re.IGNORECASE,
)

# ─── TRANSPORTATION ──────────────────────────────────────────────────────────

RIDE_SHARING_PATTERN = re.compile(
    r"(UBER\s*INDIA|UBER\s*TRIP|UBER\s*BV|UBER|OLA\s*CABS|OLA\s*MONEY|OLA|"
    r"RAPIDO|NAMMA\s*YATRI|MERU\s*CABS|JUGNOO)",
    re.IGNORECASE,
)
FUEL_PATTERN = re.compile(
    r"(PETROL|DIESEL|FUEL\s*STATION|BHARAT\s*PETROLEUM|BPCL|"
    r"HP\s*PETROL|HPCL|INDIAN\s*OIL|IOCL|SHELL\s*FUEL|RELIANCE\s*PETRO)",
    re.IGNORECASE,
)
PARKING_PATTERN = re.compile(
    r"(PARKING|PARK\s*FEE|PARK\s*PLUS|GET\s*MY\s*PARKING)",
    re.IGNORECASE,
)
PUBLIC_TRANSIT_PATTERN = re.compile(
    r"(IRCTC|RAILWAY|METRO\s*CARD|METRO\s*RECHARGE|DMRC|BMRC|"
    r"NAMMA\s*METRO|REDBUS|RED\s*BUS|ABHIBUS|BUS\s*PASS)",
    re.IGNORECASE,
)
FLIGHTS_PATTERN = re.compile(
    r"(INDIGO|6E\s*|AIRINDIA|AIR\s*INDIA|SPICEJET|VISTARA|AKASA|"
    r"MAKEMYTRIP|MMT|CLEARTRIP|IXIGO|GOAIR|GO\s*FIRST|"
    r"EASE\s*MY\s*TRIP|YATRA)",
    re.IGNORECASE,
)
TOLLS_PATTERN = re.compile(
    r"(FASTAG|FAST\s*TAG|TOLL\s*PLAZA|NHAI|NATIONAL\s*HIGHWAY)",
    re.IGNORECASE,
)

# ─── SHOPPING ────────────────────────────────────────────────────────────────

ECOMMERCE_PATTERN = re.compile(
    r"(AMAZON|AMZN|FLIPKART|MEESHO|SNAPDEAL|SHOPCLUES|TATACLIQ|TATA\s*CLIQ|"
    r"FIRSTCRY|FIRST\s*CRY|NYKAA\s*FASHION)",
    re.IGNORECASE,
)
FASHION_PATTERN = re.compile(
    r"(MYNTRA|AJIO|ZARA|H&M|H\s*AND\s*M|LIFESTYLE|WESTSIDE|PANTALOONS|"
    r"ALLEN\s*SOLLY|VAN\s*HEUSEN|MAX\s*FASHION|FABINDIA|BIBA|W\s*STORE|"
    r"MANGO|UNIQLO|FOREVER\s*21|LEVI|PEPE\s*JEANS|TRENDS)",
    re.IGNORECASE,
)
ELECTRONICS_PATTERN = re.compile(
    r"(CROMA|RELIANCE\s*DIGITAL|VIJAY\s*SALES|APPLE\s*STORE|APPLE\s*IND|"
    r"SAMSUNG\s*STORE|MI\s*STORE|ONEPLUS\s*STORE|BOAT|NOISE)",
    re.IGNORECASE,
)
HOME_FURNITURE_PATTERN = re.compile(
    r"(IKEA|PEPPERFRY|URBAN\s*LADDER|HOMETOWN|NILKAMAL|GODREJ\s*INTER|"
    r"SLEEPWELL|WAKEFIT|HOME\s*CENTRE|@HOME)",
    re.IGNORECASE,
)
BEAUTY_PATTERN = re.compile(
    r"(NYKAA|PURPLLE|SEPHORA|MAC\s*COSMETIC|BATH\s*BODY|FOREST\s*ESSENT|"
    r"MAMAEARTH|WOW\s*SKIN|SUGAR\s*COSMETIC)",
    re.IGNORECASE,
)

# ─── ENTERTAINMENT ───────────────────────────────────────────────────────────

STREAMING_PATTERN = re.compile(
    r"(NETFLIX|PRIME\s*VIDEO|AMAZON\s*PRIME|HOTSTAR|DISNEY\s*PLUS|"
    r"SPOTIFY|YOUTUBE\s*PREMIUM|APPLE\s*MUSIC|JIO\s*CINEMA|SONYLIV|"
    r"ZEE5|VOOT|AUDIBLE|GAANA)",
    re.IGNORECASE,
)
MOVIES_EVENTS_PATTERN = re.compile(
    r"(PVR|INOX|CINEPOLIS|BOOKMYSHOW|BOOK\s*MY\s*SHOW|PAYTM\s*MOVIES|"
    r"CARNIVAL\s*CINEMA|MIRAJ\s*CINEMA)",
    re.IGNORECASE,
)
GAMING_PATTERN = re.compile(
    r"(STEAM|PLAYSTATION|PSN|XBOX|EPIC\s*GAMES|RIOT|SUPERCELL|"
    r"GOOGLE\s*PLAY|APP\s*STORE|BATTLEGROUNDS|CODM)",
    re.IGNORECASE,
)
SPORTS_FITNESS_PATTERN = re.compile(
    r"(GYM|CULT\s*FIT|CURE\s*FIT|FITNESS\s*FIRST|GOLD\s*GYM|"
    r"ANYTIME\s*FITNESS|CROSSFIT|YOGA|DECATHLON)",
    re.IGNORECASE,
)
TRAVEL_PATTERN = re.compile(
    r"(HOTEL|OYO|AIRBNB|GOIBIBO|TRIVAGO|BOOKING\.COM|"
    r"TAJ\s*HOTEL|ITC\s*HOTEL|MARRIOTT|HYATT|LEMON\s*TREE|TREEBO|FABHOTEL)",
    re.IGNORECASE,
)

# ─── HEALTHCARE ──────────────────────────────────────────────────────────────

PHARMACY_PATTERN = re.compile(
    r"(APOLLO\s*PHARMACY|MEDPLUS|MED\s*PLUS|1MG|NETMEDS|PHARMEASY|"
    r"TATA\s*1MG|WELLNESS\s*FOREVER|FRANK\s*ROSS|GUARDIAN\s*PHARMACY)",
    re.IGNORECASE,
)
HOSPITAL_PATTERN = re.compile(
    r"(HOSPITAL|CLINIC|DIAGNOSTIC|PATHOLOGY|LAB\s*TEST|FORTIS|MANIPAL|"
    r"MAX\s*HOSPITAL|MEDANTA|NARAYANA|COLUMBIA\s*ASIA|APOLLO\s*HOSP|"
    r"AIIMS|NIMHANS|SRL\s*DIAGNOSTIC|DR\s*LAL|THYROCARE)",
    re.IGNORECASE,
)
DOCTOR_PATTERN = re.compile(
    r"(PRACTO|TELECONSULT|CONSULTATION\s*FEE|DR\.\s*\w+|DOCTOR)",
    re.IGNORECASE,
)

# ─── UTILITIES ───────────────────────────────────────────────────────────────

ELECTRICITY_PATTERN = re.compile(
    r"(ELECTRICITY|POWER\s*BILL|BESCOM|TATA\s*POWER|ADANI\s*ELECT|"
    r"BSES|MSEDCL|TNEB|CESC|TORRENT\s*POWER|UHBVN|JVVNL)",
    re.IGNORECASE,
)
WATER_PATTERN = re.compile(
    r"(WATER\s*SUPPLY|WATER\s*BILL|MUNICIPAL|CORPORATION\s*WATER|"
    r"BWSSB|DELHI\s*JAL|MCGM\s*WATER)",
    re.IGNORECASE,
)
INTERNET_PATTERN = re.compile(
    r"(AIRTEL\s*FIBER|AIRTEL\s*XSTREAM|JIO\s*FIBER|ACT\s*FIBER|"
    r"BSNL\s*BROAD|HATHWAY|YOU\s*BROADBAND|TIKONA|EXCITEL|TATA\s*SKY\s*BROAD)",
    re.IGNORECASE,
)
MOBILE_RECHARGE_PATTERN = re.compile(
    r"(MOBILE\s*RECHARGE|PREPAID\s*RECHARGE|POSTPAID\s*BILL|"
    r"AIRTEL\s*MOBILE|JIO\s*RECHARGE|VI\s*RECHARGE|BSNL\s*RECHARGE)",
    re.IGNORECASE,
)
GAS_PATTERN = re.compile(
    r"(LPG|GAS\s*CYLINDER|INDANE\s*GAS|BHARAT\s*GAS|HP\s*GAS|"
    r"PIPED\s*GAS|IGL|MAHANAGAR\s*GAS|ADANI\s*GAS|GAIL)",
    re.IGNORECASE,
)

# ─── BILLS & FEES ────────────────────────────────────────────────────────────

CREDIT_CARD_BILL_PATTERN = re.compile(
    r"(CREDIT\s*CARD\s*BILL|CC\s*PAYMENT|CARD\s*BILL\s*PAYMENT|"
    r"CITI\s*CARD|HDFC\s*CARD\s*BILL|ICICI\s*CARD\s*BILL|SBI\s*CARD\s*BILL)",
    re.IGNORECASE,
)
INSURANCE_PATTERN = re.compile(
    r"(INSURANCE|POLICY\s*PREMIUM|LIC\s*|HDFC\s*LIFE|ICICI\s*PRUD|"
    r"SBI\s*LIFE|MAX\s*LIFE|BAJAJ\s*ALLIANZ|STAR\s*HEALTH|"
    r"DIGIT\s*INSUR|ACKO|POLICY\s*BAZAAR)",
    re.IGNORECASE,
)
EMI_PATTERN = re.compile(
    r"(EMI|LOAN\s*EMI|PERSONAL\s*LOAN|HOME\s*LOAN|CAR\s*LOAN|"
    r"EDUCATION\s*LOAN|BAJAJ\s*FINSERV|HDFC\s*LTD|ICICI\s*HFC)",
    re.IGNORECASE,
)
BANK_CHARGES_PATTERN = re.compile(
    r"(BANK\s*CHARGE|MAINTENANCE\s*CHARGE|SMS\s*CHARGE|ATM\s*CHARGE|"
    r"ANNUAL\s*FEE|SERVICE\s*CHARGE|DEBIT\s*CARD\s*FEE|LOCKER\s*CHARGE)",
    re.IGNORECASE,
)

# ─── EDUCATION ───────────────────────────────────────────────────────────────

EDUCATION_PATTERN = re.compile(
    r"(UDEMY|COURSERA|UNACADEMY|BYJU|UPGRAD|SIMPLILEARN|EDUREKA|"
    r"GREAT\s*LEARNING|SCALER|CODING\s*NINJA|WHITEHAT|VEDANTU|TOPPR|"
    r"LINKEDIN\s*LEARN|SKILLSHARE)",
    re.IGNORECASE,
)
SCHOOL_FEES_PATTERN = re.compile(
    r"(TUITION\s*FEE|SCHOOL\s*FEE|COLLEGE\s*FEE|UNIVERSITY|"
    r"EXAM\s*FEE|SEMESTER\s*FEE|ADMISSION\s*FEE)",
    re.IGNORECASE,
)

# ─── PERSONAL CARE ───────────────────────────────────────────────────────────

SALON_PATTERN = re.compile(
    r"(SALON|SPA|PARLOUR|PARLOR|HAIRCUT|URBAN\s*COMPANY|"
    r"URBAN\s*CLAP|NATURALS|JAWED\s*HABIB|LAKME\s*SALON|ENRICH)",
    re.IGNORECASE,
)

# ─── HOME ────────────────────────────────────────────────────────────────────

RENT_PATTERN = re.compile(
    r"(RENT|HOUSE\s*RENT|MONTHLY\s*RENT|LANDLORD|RENTAL\s*PAYMENT|"
    r"NOBROKER|NESTAWAY|MAGICBRICKS)",
    re.IGNORECASE,
)
MAINTENANCE_PATTERN = re.compile(
    r"(MAINTENANCE\s*CHARGE|SOCIETY\s*CHARGE|APARTMENT\s*MAINT|"
    r"RWA|FLAT\s*MAINTENANCE|ASSOCIATION\s*FEE)",
    re.IGNORECASE,
)

# ─── INCOME ──────────────────────────────────────────────────────────────────

SALARY_PATTERN = re.compile(
    r"(SALARY|SAL\s*CREDIT|SAL\s*CR|PAYROLL|MONTHLY\s*SAL|STIPEND)",
    re.IGNORECASE,
)
REFUND_PATTERN = re.compile(
    r"(REFUND|REVERSAL|CASHBACK|CASH\s*BACK|RETURN\s*CREDIT|"
    r"CREDIT\s*REVERSAL|MERCHANT\s*REFUND)",
    re.IGNORECASE,
)
INTEREST_PATTERN = re.compile(
    r"(INTEREST\s*CREDIT|INT\s*CR|FD\s*INTEREST|SAVINGS\s*INT|"
    r"INTEREST\s*ON\s*DEPOSIT|NEFT\s*INT)",
    re.IGNORECASE,
)

# ─── INVESTMENTS ─────────────────────────────────────────────────────────────

MUTUAL_FUND_PATTERN = re.compile(
    r"(MUTUAL\s*FUND|SIP|GROWW|ZERODHA\s*COIN|KUVERA|"
    r"PAYTM\s*MONEY|ET\s*MONEY|COIN\s*ZERODHA|MF\s*UTILITY)",
    re.IGNORECASE,
)
STOCKS_PATTERN = re.compile(
    r"(ZERODHA|UPSTOX|ANGEL\s*BROKING|ANGEL\s*ONE|GROWW\s*INVEST|"
    r"5PAISA|ICICI\s*DIRECT|HDFC\s*SEC|KOTAK\s*SEC|MOTILAL)",
    re.IGNORECASE,
)

# ─── CASH ────────────────────────────────────────────────────────────────────

ATM_PATTERN = re.compile(
    r"(ATM\s*WDL|ATM\s*WITHDRAWAL|ATM\s*CASH|CASH\s*WITHDRAWAL|"
    r"SELF\s*WDL|NFS\s*ATM|ATM\s*DR)",
    re.IGNORECASE,
)

# ─── TRANSFERS ───────────────────────────────────────────────────────────────

UPI_PATTERN = re.compile(
    r"(UPI[-/]|@[A-Z]+|PHONEPE|GOOGLE\s*PAY|GPAY|PAYTM|CRED\s*UPI|"
    r"BHIM|SAMSUNG\s*PAY|WHATSAPP\s*PAY)",
    re.IGNORECASE,
)
BANK_TRANSFER_PATTERN = re.compile(
    r"(NEFT[-/]|RTGS[-/]|IMPS[-/]|FUND\s*TRANSFER|"
    r"NEFT\s*CR|NEFT\s*DR|RTGS\s*CR|IMPS\s*CR)",
    re.IGNORECASE,
)

# ─── INTERNATIONAL / EUROPEAN ────────────────────────────────────────────────

INTL_SUPERMARKET_PATTERN = re.compile(
    r"(LIDL|ALDI|TESCO|CARREFOUR|MERCADONA|ALBERT\s*HEIJN|REWE|EDEKA|"
    r"SAINSBURY|WAITROSE|MARKS\s*SPENCER|SPAR\b|PENNY\b|NETTO\b|"
    r"KAUFLAND|BIEDRONKA|ASDA|MORRISONS|COOP\b|MIGROS)",
    re.IGNORECASE,
)
INTL_SHOPPING_PATTERN = re.compile(
    r"(WALMART|TARGET|COSTCO|PRIMARK|TK\s*MAXX|ACTION\b|HEMA\b|FLYING\s*TIGER)",
    re.IGNORECASE,
)
INTL_FOOD_DELIVERY_PATTERN = re.compile(
    r"(DELIVEROO|UBER\s*EATS|JUST\s*EAT|DOORDASH|GRUBHUB|GLOVO|"
    r"WOLT|THUISBEZORGD|LIEFERANDO|FOODORA)",
    re.IGNORECASE,
)
INTL_TRANSPORT_PATTERN = re.compile(
    r"(UBER\b|LYFT|BOLT\b|TFL\b|TRAINLINE|RYANAIR|EASYJET|"
    r"WIZZ\s*AIR|VUELING|FLIXBUS|BVG|DB\s*BAHN|SNCF|NS\b|"
    r"EUROSTAR|LIME\b|TIER\b|VOI\b)",
    re.IGNORECASE,
)
INTL_SUBSCRIPTION_PATTERN = re.compile(
    r"(NETFLIX|SPOTIFY|APPLE\.COM|APPLE\s*COM|GOOGLE\s*STORAGE|"
    r"AMAZON\s*PRIME|DISNEY\s*PLUS|DISNEY\+|YOUTUBE\s*PREMIUM|"
    r"HBO\s*MAX|PARAMOUNT|DAZN|CRUNCHYROLL|NOTION|FIGMA|"
    r"OPENAI|CHATGPT|MIDJOURNEY|CANVA)",
    re.IGNORECASE,
)
INTL_UTILITIES_PATTERN = re.compile(
    r"(VODAFONE|O2\b|THREE\b|EE\b|T-MOBILE|ORANGE\b|"
    r"MOVISTAR|TELEKOM|KPN|TELE2|ZIGGO|VATTENFALL|ENECO|"
    r"ENEL|ENDESA|NATURGY|EON\b|INNOGY|RWE\b)",
    re.IGNORECASE,
)

# ─── MASTER PATTERN REGISTRY ────────────────────────────────────────────────
# Maps: (compiled_pattern, category, subcategory, merchant_extract_group)

MERCHANT_PATTERNS: list[tuple[re.Pattern, str, str]] = [
    # Food & Dining
    (FOOD_DELIVERY_PATTERN, "Food & Dining", "Food Delivery"),
    (FAST_FOOD_PATTERN, "Food & Dining", "Fast Food"),
    (CAFES_PATTERN, "Food & Dining", "Cafes & Coffee"),
    (GROCERIES_PATTERN, "Food & Dining", "Groceries"),
    (RESTAURANTS_PATTERN, "Food & Dining", "Restaurants"),
    (ALCOHOL_PATTERN, "Food & Dining", "Alcohol & Bars"),
    # Transportation
    (RIDE_SHARING_PATTERN, "Transportation", "Ride Sharing"),
    (FUEL_PATTERN, "Transportation", "Fuel"),
    (PARKING_PATTERN, "Transportation", "Parking"),
    (PUBLIC_TRANSIT_PATTERN, "Transportation", "Public Transit"),
    (FLIGHTS_PATTERN, "Transportation", "Flights"),
    (TOLLS_PATTERN, "Transportation", "Tolls"),
    # Shopping
    (ECOMMERCE_PATTERN, "Shopping", "E-commerce"),
    (FASHION_PATTERN, "Shopping", "Fashion & Clothing"),
    (ELECTRONICS_PATTERN, "Shopping", "Electronics"),
    (HOME_FURNITURE_PATTERN, "Shopping", "Home & Furniture"),
    (BEAUTY_PATTERN, "Shopping", "Beauty & Cosmetics"),
    # Entertainment
    (STREAMING_PATTERN, "Entertainment", "Streaming"),
    (MOVIES_EVENTS_PATTERN, "Entertainment", "Movies & Events"),
    (GAMING_PATTERN, "Entertainment", "Gaming"),
    (SPORTS_FITNESS_PATTERN, "Entertainment", "Sports & Fitness"),
    (TRAVEL_PATTERN, "Entertainment", "Travel & Vacation"),
    # Healthcare
    (PHARMACY_PATTERN, "Healthcare", "Pharmacy"),
    (HOSPITAL_PATTERN, "Healthcare", "Hospital & Clinic"),
    (DOCTOR_PATTERN, "Healthcare", "Doctor Consultation"),
    # Utilities
    (ELECTRICITY_PATTERN, "Utilities", "Electricity"),
    (WATER_PATTERN, "Utilities", "Water"),
    (INTERNET_PATTERN, "Utilities", "Internet & Broadband"),
    (MOBILE_RECHARGE_PATTERN, "Utilities", "Mobile Recharge"),
    (GAS_PATTERN, "Utilities", "Gas"),
    # Bills & Fees
    (CREDIT_CARD_BILL_PATTERN, "Bills & Fees", "Credit Card Bill"),
    (INSURANCE_PATTERN, "Bills & Fees", "Insurance"),
    (EMI_PATTERN, "Bills & Fees", "EMI & Loans"),
    (BANK_CHARGES_PATTERN, "Bills & Fees", "Bank Charges"),
    # Education
    (EDUCATION_PATTERN, "Education", "Courses & Training"),
    (SCHOOL_FEES_PATTERN, "Education", "School & College Fees"),
    # Personal Care
    (SALON_PATTERN, "Personal Care", "Salon & Spa"),
    # Home
    (RENT_PATTERN, "Home", "Rent"),
    (MAINTENANCE_PATTERN, "Home", "Maintenance"),
    # Income
    (SALARY_PATTERN, "Income", "Salary"),
    (REFUND_PATTERN, "Income", "Refund"),
    (INTEREST_PATTERN, "Income", "Interest"),
    # Investments
    (MUTUAL_FUND_PATTERN, "Investments", "Mutual Funds"),
    (STOCKS_PATTERN, "Investments", "Stocks"),
    # Cash
    (ATM_PATTERN, "Cash", "ATM Withdrawal"),
    # Transfers (lower priority — often supplementary info)
    (UPI_PATTERN, "Transfers", "UPI Transfer"),
    (BANK_TRANSFER_PATTERN, "Transfers", "Bank Transfer"),
    # International / European
    (INTL_SUPERMARKET_PATTERN, "Food & Dining", "Supermarket"),
    (INTL_SHOPPING_PATTERN, "Shopping", "Retail"),
    (INTL_FOOD_DELIVERY_PATTERN, "Food & Dining", "Food Delivery"),
    (INTL_TRANSPORT_PATTERN, "Transportation", "Transport"),
    (INTL_SUBSCRIPTION_PATTERN, "Entertainment", "Subscription"),
    (INTL_UTILITIES_PATTERN, "Utilities", "Telecom & Utilities"),
]


# Canonical merchant names extracted from pattern matches
MERCHANT_CANONICALIZATION: dict[str, str] = {
    "swiggy": "Swiggy",
    "zomato": "Zomato",
    "dunzo": "Dunzo",
    "dominos": "Domino's",
    "domino's": "Domino's",
    "pizza hut": "Pizza Hut",
    "kfc": "KFC",
    "mcdonald": "McDonald's",
    "mcdonalds": "McDonald's",
    "burger king": "Burger King",
    "subway": "Subway",
    "starbucks": "Starbucks",
    "cafe coffee day": "Cafe Coffee Day",
    "ccd": "Cafe Coffee Day",
    "barista": "Barista",
    "blue tokai": "Blue Tokai Coffee",
    "third wave": "Third Wave Coffee",
    "chaayos": "Chaayos",
    "bigbasket": "BigBasket",
    "big basket": "BigBasket",
    "blinkit": "Blinkit",
    "zepto": "Zepto",
    "instamart": "Swiggy Instamart",
    "dmart": "DMart",
    "d mart": "DMart",
    "reliance fresh": "Reliance Fresh",
    "uber": "Uber",
    "ola": "Ola Cabs",
    "rapido": "Rapido",
    "irctc": "IRCTC",
    "indigo": "IndiGo Airlines",
    "makemytrip": "MakeMyTrip",
    "mmt": "MakeMyTrip",
    "amazon": "Amazon",
    "amzn": "Amazon",
    "flipkart": "Flipkart",
    "myntra": "Myntra",
    "ajio": "AJIO",
    "meesho": "Meesho",
    "croma": "Croma",
    "reliance digital": "Reliance Digital",
    "nykaa": "Nykaa",
    "netflix": "Netflix",
    "spotify": "Spotify",
    "hotstar": "Disney+ Hotstar",
    "youtube premium": "YouTube Premium",
    "prime video": "Amazon Prime Video",
    "pvr": "PVR Cinemas",
    "inox": "INOX",
    "bookmyshow": "BookMyShow",
    "apollo pharmacy": "Apollo Pharmacy",
    "medplus": "MedPlus",
    "1mg": "Tata 1mg",
    "netmeds": "Netmeds",
    "pharmeasy": "PharmEasy",
    "practo": "Practo",
    "bescom": "BESCOM",
    "tata power": "Tata Power",
    "airtel": "Airtel",
    "jio": "Jio",
    "act fiber": "ACT Fibernet",
    "zerodha": "Zerodha",
    "groww": "Groww",
    "udemy": "Udemy",
    "coursera": "Coursera",
    "oyo": "OYO Rooms",
    "airbnb": "Airbnb",
    "urban company": "Urban Company",
    "phonepe": "PhonePe",
    "gpay": "Google Pay",
    "google pay": "Google Pay",
    "paytm": "Paytm",
    "cred": "CRED",
    "decathlon": "Decathlon",
    "ikea": "IKEA",
    "lic": "LIC",
    "nobroker": "NoBroker",
    "cult fit": "Cult.fit",
    "cure fit": "Cult.fit",
    # International merchants
    "lidl": "Lidl",
    "aldi": "Aldi",
    "tesco": "Tesco",
    "carrefour": "Carrefour",
    "mercadona": "Mercadona",
    "albert heijn": "Albert Heijn",
    "rewe": "REWE",
    "edeka": "EDEKA",
    "sainsbury": "Sainsbury's",
    "waitrose": "Waitrose",
    "marks spencer": "Marks & Spencer",
    "walmart": "Walmart",
    "target": "Target",
    "costco": "Costco",
    "deliveroo": "Deliveroo",
    "uber eats": "Uber Eats",
    "just eat": "Just Eat",
    "doordash": "DoorDash",
    "grubhub": "Grubhub",
    "bolt": "Bolt",
    "tfl": "TfL",
    "trainline": "Trainline",
    "ryanair": "Ryanair",
    "easyjet": "easyJet",
    "lyft": "Lyft",
    "vodafone": "Vodafone",
    "disney plus": "Disney+",
    "amazon prime": "Amazon Prime",
    "youtube premium": "YouTube Premium",
    "apple.com": "Apple",
    "apple com": "Apple",
    "google storage": "Google One",
}


def extract_merchant_name(description: str, match: re.Match) -> Optional[str]:
    """Extract and canonicalize merchant name from a regex match."""
    matched_text = match.group(1).strip().lower()

    # Direct canonicalization lookup
    if matched_text in MERCHANT_CANONICALIZATION:
        return MERCHANT_CANONICALIZATION[matched_text]

    # Try partial match on canonical keys
    for key, canonical in MERCHANT_CANONICALIZATION.items():
        if key in matched_text or matched_text in key:
            return canonical

    # Fall back to title-casing the match
    return match.group(1).strip().title()
