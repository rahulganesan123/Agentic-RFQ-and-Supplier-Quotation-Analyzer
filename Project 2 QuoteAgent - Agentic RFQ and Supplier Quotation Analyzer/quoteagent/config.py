import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# Model configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Persistence checkpointer
POSTGRES_URI = os.getenv("POSTGRES_URI", "")
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", str(ROOT_DIR / "quoteagent_state.db"))

# Default procurement normalisation targets
DEFAULT_BASE_CURRENCY = os.getenv("DEFAULT_BASE_CURRENCY", "AED")
DEFAULT_TARGET_UNIT_WEIGHT = os.getenv("DEFAULT_TARGET_UNIT_WEIGHT", "MT")
DEFAULT_TARGET_UNIT_LENGTH = os.getenv("DEFAULT_TARGET_UNIT_LENGTH", "m")
DEFAULT_VAT_RATE = float(os.getenv("DEFAULT_VAT_RATE", "0.05"))

# Standard fixed-date FX conversion rates (Base: USD = 1.0)
FX_RATES_TO_USD = {
    "USD": 1.0,
    "AED": 0.2723,    # 1 AED = ~0.2723 USD (1 USD = 3.6725 AED)
    "INR": 0.0119,    # 1 INR = ~0.0119 USD (1 USD = ~84.0 INR)
    "EUR": 1.0850,    # 1 EUR = ~1.085 USD
    "GBP": 1.3020,    # 1 GBP = ~1.302 USD
    "SAR": 0.2664,    # 1 SAR = ~0.2664 USD (1 USD = 3.75 SAR)
}

# Freight estimates by Incoterm (percentage of base price or fixed adder if not explicit)
DEFAULT_FREIGHT_ADDERS = {
    "EXW": 0.06,  # Buyer pays pickup + transport (~6% typical local steel transport)
    "FOB": 0.04,  # Buyer pays ocean/regional freight (~4%)
    "CIF": 0.01,  # Port handling & local clearance (~1%)
    "DAP": 0.00,  # Delivered to site: 0% added
    "DDP": 0.00,  # Delivered duty paid: 0% added
}
