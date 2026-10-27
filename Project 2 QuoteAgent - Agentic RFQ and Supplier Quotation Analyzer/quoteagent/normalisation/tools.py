"""
Normalisation tools for QuoteAgent.
Pure Python deterministic functions called by the agent workflow:
1. convert_unit: normalises units of weight, length, and counts.
2. convert_currency: converts currencies using standard FX rates.
3. compute_landed_cost: computes true landed cost taking base price, VAT, freight and incoterms into account.
4. evaluate_spec_match: evaluates technical compliance of quoted steel grades and dimensions against RFQ requirements.
"""

from typing import Dict, Any, Tuple
from quoteagent.config import FX_RATES_TO_USD, DEFAULT_FREIGHT_ADDERS


# Unit conversion factors to base unit (kg for weight, meter for length)
WEIGHT_FACTORS_TO_KG = {
    "KG": 1.0,
    "KGS": 1.0,
    "KILOGRAM": 1.0,
    "KILOGRAMS": 1.0,
    "MT": 1000.0,
    "TON": 1000.0,
    "TONS": 1000.0,
    "TONNE": 1000.0,
    "TONNES": 1000.0,
    "METRIC TON": 1000.0,
    "METRIC TONS": 1000.0,
    "LBS": 0.45359237,
    "LB": 0.45359237,
    "POUND": 0.45359237,
    "POUNDS": 0.45359237,
    "G": 0.001,
    "GRAM": 0.001,
}

LENGTH_FACTORS_TO_METERS = {
    "M": 1.0,
    "MTR": 1.0,
    "METER": 1.0,
    "METERS": 1.0,
    "MM": 0.001,
    "MILLIMETER": 0.001,
    "MILLIMETERS": 0.001,
    "CM": 0.01,
    "CENTIMETER": 0.01,
    "INCH": 0.0254,
    "INCHES": 0.0254,
    "IN": 0.0254,
    "\"": 0.0254,
    "FT": 0.3048,
    "FOOT": 0.3048,
    "FEET": 0.3048,
    "YD": 0.9144,
    "YARD": 0.9144,
}

COUNT_UNITS = {"PCS", "PC", "NO", "NOS", "EA", "EACH", "SET", "SETS", "BUNDLE", "BUNDLES", "PACK", "PACKS"}


def clean_unit_name(unit: str) -> str:
    """Normalises unit strings by stripping whitespace and punctuation."""
    if not unit:
        return "PCS"
    cleaned = unit.strip().upper().replace(".", "").replace("-", "")
    return cleaned


def convert_unit(quantity: float, from_unit: str, to_unit: str, nominal_weight_kg_per_piece: float = None) -> float:
    """
    Normalises quantity from one unit to another.
    Handles weight conversions (e.g. KG -> MT), length conversions (e.g. MM -> M),
    and count-to-weight conversions if a nominal weight per piece is supplied.
    """
    if quantity <= 0:
        return 0.0

    u_from = clean_unit_name(from_unit)
    u_to = clean_unit_name(to_unit)

    if u_from == u_to:
        return round(quantity, 4)

    # Weight to Weight
    if u_from in WEIGHT_FACTORS_TO_KG and u_to in WEIGHT_FACTORS_TO_KG:
        kg_val = quantity * WEIGHT_FACTORS_TO_KG[u_from]
        res = kg_val / WEIGHT_FACTORS_TO_KG[u_to]
        return round(res, 4)

    # Length to Length
    if u_from in LENGTH_FACTORS_TO_METERS and u_to in LENGTH_FACTORS_TO_METERS:
        m_val = quantity * LENGTH_FACTORS_TO_METERS[u_from]
        res = m_val / LENGTH_FACTORS_TO_METERS[u_to]
        return round(res, 4)

    # Piece to Weight (if piece weight provided)
    if u_from in COUNT_UNITS and u_to in WEIGHT_FACTORS_TO_KG and nominal_weight_kg_per_piece:
        kg_val = quantity * nominal_weight_kg_per_piece
        res = kg_val / WEIGHT_FACTORS_TO_KG[u_to]
        return round(res, 4)

    # Weight to Piece (if piece weight provided)
    if u_from in WEIGHT_FACTORS_TO_KG and u_to in COUNT_UNITS and nominal_weight_kg_per_piece:
        kg_val = quantity * WEIGHT_FACTORS_TO_KG[u_from]
        res = kg_val / nominal_weight_kg_per_piece
        return round(res, 2)

    # Both count units (e.g. EA vs PCS)
    if u_from in COUNT_UNITS and u_to in COUNT_UNITS:
        return round(quantity, 4)

    # Fallback if unknown conversion
    return round(quantity, 4)


def convert_currency(amount: float, from_currency: str, to_currency: str, custom_rates: Dict[str, float] = None) -> float:
    """
    Converts monetary amount between currencies using USD as intermediate standard anchor.
    Supported: AED, USD, INR, EUR, GBP, SAR.
    """
    if amount == 0:
        return 0.0

    c_from = from_currency.strip().upper()
    c_to = to_currency.strip().upper()

    if c_from == c_to:
        return round(amount, 2)

    rates = custom_rates or FX_RATES_TO_USD

    if c_from not in rates:
        raise ValueError(f"Unsupported source currency '{c_from}'. Supported: {list(rates.keys())}")
    if c_to not in rates:
        raise ValueError(f"Unsupported target currency '{c_to}'. Supported: {list(rates.keys())}")

    # Amount in USD = Amount in From * (USD / From)
    amount_in_usd = amount * rates[c_from]
    # Amount in To = Amount in USD / (USD / To)
    amount_in_to = amount_in_usd / rates[c_to]

    return round(amount_in_to, 2)


def compute_landed_cost(
    unit_price: float,
    quantity: float,
    currency: str,
    incoterm: str = "EXW",
    vat_included: bool = False,
    vat_percentage: float = 0.05,
    freight_charges: float = 0.0,
    target_currency: str = "AED",
    custom_fx_rates: Dict[str, float] = None,
) -> Dict[str, float]:
    """
    Computes total landed cost including:
    - Base quotation price in source & target currency
    - Freight and logistics adjustment based on Incoterms (EXW, FOB, CIF, DAP, DDP)
    - Applicable VAT/tax calculation (handling VAT-included vs VAT-excluded quotes)
    - Normalized landed unit price and total cost in target currency.
    """
    base_quoted_total = round(unit_price * quantity, 2)

    # 1. Convert base price to target currency
    base_target = convert_currency(base_quoted_total, currency, target_currency, custom_fx_rates)

    # 2. Freight calculation
    inco = incoterm.strip().upper()
    freight_rate = DEFAULT_FREIGHT_ADDERS.get(inco, 0.05)

    if freight_charges and freight_charges > 0:
        freight_target = convert_currency(freight_charges, currency, target_currency, custom_fx_rates)
    else:
        # Estimated freight adder if supplier quoted EXW or FOB
        freight_target = round(base_target * freight_rate, 2)

    # 3. VAT calculation
    # If VAT is already included in unit price, extract the VAT portion
    if vat_included:
        # base_target already contains VAT
        net_before_vat = round(base_target / (1.0 + vat_percentage), 2)
        vat_target = round(base_target - net_before_vat, 2)
        landed_total = round(base_target + freight_target, 2)
    else:
        # VAT is excluded, so buyer must pay VAT on (goods + freight)
        vat_target = round((base_target + freight_target) * vat_percentage, 2)
        landed_total = round(base_target + freight_target + vat_target, 2)

    landed_unit_price = round(landed_total / quantity, 2) if quantity > 0 else 0.0

    return {
        "base_quoted_original": base_quoted_total,
        "base_target_currency": base_target,
        "freight_target_currency": freight_target,
        "vat_target_currency": vat_target,
        "landed_total_target_currency": landed_total,
        "landed_unit_price_target_currency": landed_unit_price,
        "target_currency": target_currency,
    }


# Steel Grade Equivalence and Hierarchy Matrix
# Higher rank = higher structural tensile/yield performance
GRADE_RANKS = {
    "S235": 1,
    "S235JR": 1,
    "A36": 2,
    "ASTM A36": 2,
    "S275": 3,
    "S275JR": 3,
    "S275J0": 3,
    "S275J2": 3,
    "S355": 4,
    "S355JR": 4,
    "S355J0": 5,
    "S355J2": 5,
    "S355J2+N": 5,
    "S355K2": 5,
    "A572-50": 4,
    "ASTM A572 GR 50": 4,
    # Stainless
    "SS304": 6,
    "304": 6,
    "SS316": 7,
    "SS316L": 8,
    "316L": 8,
    # Fastener Grades
    "GRADE 4.6": 1,
    "4.6": 1,
    "GRADE 8.8": 2,
    "8.8": 2,
    "8.8 HDG": 2,
    "GRADE 10.9": 3,
    "10.9": 3,
    "10.9 HDG": 3,
}


def evaluate_spec_match(rfq_grade: str, quoted_grade: str, rfq_desc: str = "", quoted_desc: str = "") -> Tuple[str, float, str]:
    """
    Compares the quoted steel specification/grade against the RFQ specification.
    Returns:
    - status: "EXACT_MATCH", "ACCEPTABLE_ALTERNATIVE", "DEVIATION_DISQUALIFIED", "MISSING"
    - score: float between 0.0 and 100.0
    - notes: human-readable rationale
    """
    if not quoted_grade and not quoted_desc:
        return "MISSING", 0.0, "No specification or description provided."

    rfq_g = (rfq_grade or "").strip().upper()
    quo_g = (quoted_grade or "").strip().upper()

    if not quo_g and quoted_desc:
        # Attempt to find grade in description
        for g in GRADE_RANKS:
            if g in quoted_desc.upper():
                quo_g = g
                break

    if not quo_g:
        return "ACCEPTABLE_ALTERNATIVE", 70.0, "Grade not explicitly stated; assumed standard commercial grade."

    if rfq_g == quo_g or rfq_g in quo_g or quo_g in rfq_g:
        return "EXACT_MATCH", 100.0, f"Exact match for grade {rfq_g}."

    rfq_rank = GRADE_RANKS.get(rfq_g, 0)
    quo_rank = GRADE_RANKS.get(quo_g, 0)

    # Stainless vs Carbon Steel safety check
    is_rfq_ss = "316" in rfq_g or "304" in rfq_g
    is_quo_ss = "316" in quo_g or "304" in quo_g

    if is_rfq_ss != is_quo_ss:
        return (
            "DEVIATION_DISQUALIFIED",
            0.0,
            f"Material mismatch: RFQ requested {'Stainless' if is_rfq_ss else 'Carbon'} steel, vendor quoted {'Stainless' if is_quo_ss else 'Carbon'} steel.",
        )

    # Carbon steel structural grades
    if rfq_rank > 0 and quo_rank > 0:
        if quo_rank >= rfq_rank:
            return (
                "ACCEPTABLE_ALTERNATIVE",
                95.0,
                f"Quoted {quo_g} exceeds or equals requested {rfq_g} (higher or equal yield strength).",
            )
        else:
            return (
                "DEVIATION_DISQUALIFIED",
                20.0,
                f"CRITICAL DEFECT: Quoted {quo_g} has lower structural yield strength than specified {rfq_g}.",
            )

    # Fasteners HDG requirement check
    if "HDG" in rfq_desc.upper() and "HDG" not in quoted_desc.upper() and "GALV" not in quoted_desc.upper():
        return (
            "ACCEPTABLE_ALTERNATIVE",
            60.0,
            "Quoted bolts may lack Hot-Dip Galvanizing (HDG) coating required by RFQ.",
        )

    return "ACCEPTABLE_ALTERNATIVE", 85.0, f"Alternative grade {quo_g} offered for {rfq_g}."
