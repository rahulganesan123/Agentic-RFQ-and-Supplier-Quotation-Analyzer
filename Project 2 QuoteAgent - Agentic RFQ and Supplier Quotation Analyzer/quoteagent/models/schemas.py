"""
Pydantic schemas for QuoteAgent: RFQ, Quotation, Normalized Items, Comparison & Reports.
Enforces rigorous validation rules reflecting steel fabrication procurement.
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator


class RFQItem(BaseModel):
    item_id: str = Field(..., description="Unique RFQ item identifier, e.g. ITEM-1")
    description: str = Field(..., description="Material or service description, e.g. HEA 200 European Standard Beam")
    grade: str = Field(..., description="Required steel grade or standard, e.g. S355JR, EN 10025-2, ASTM A36")
    dimensions: Optional[str] = Field(None, description="Size or dimensions, e.g. 200x190x6.5x10mm, 12m length")
    quantity: float = Field(..., gt=0, description="Required quantity")
    unit: str = Field(..., description="RFQ unit of measure: MT, KG, PCS, M, etc.")
    target_lead_time_days: Optional[int] = Field(30, description="Target maximum acceptable lead time in calendar days")
    notes: Optional[str] = Field(None, description="Additional buyer requirements (e.g. MTC EN 10204 3.1 required)")


class RFQ(BaseModel):
    rfq_id: str = Field(..., description="RFQ tracking number, e.g. RFQ-2026-001")
    project_name: str = Field(..., description="Project name, e.g. DIC Industrial Warehouse Structural Framework")
    buyer_name: str = Field("Al Quoz Steel Fabricators LLC", description="Issuing buying organization")
    target_currency: str = Field("AED", description="Standardized comparison currency (AED, USD, INR)")
    target_unit_weight: str = Field("MT", description="Target normalized weight unit (MT or KG)")
    target_delivery_terms: str = Field("DAP Dubai Industrial City", description="Target buyer delivery location")
    required_delivery_days: int = Field(30, description="Max delivery deadline in days")
    items: List[RFQItem] = Field(..., min_length=1, description="List of items requested in RFQ")


class QuotedItem(BaseModel):
    item_no: int = Field(..., ge=1, description="Line number in the quotation")
    description: str = Field(..., description="Quoted product description")
    grade: Optional[str] = Field(None, description="Offered steel grade (e.g. S275JR, S355J2, A36)")
    dimensions: Optional[str] = Field(None, description="Quoted dimensions or sizes")
    quantity: float = Field(..., gt=0, description="Quoted quantity (must be strictly positive)")
    unit: str = Field(..., description="Quoted unit of measure: MT, KG, PCS, M, LBS, TON, etc.")
    unit_price: float = Field(..., ge=0, description="Unit price in quotation currency")
    total_price: Optional[float] = Field(None, description="Line total price (quantity * unit_price)")
    mill_origin: Optional[str] = Field(None, description="Country/Mill of manufacture (e.g. Emirates Steel, Jindal, Posco)")
    deviations: Optional[str] = Field(None, description="Notes, exclusions, or deviations from standard specs")

    @model_validator(mode="after")
    def compute_total_if_missing(self) -> "QuotedItem":
        if self.total_price is None or self.total_price <= 0:
            self.total_price = round(self.quantity * self.unit_price, 2)
        return self


class Quotation(BaseModel):
    vendor_name: str = Field(..., min_length=2, description="Legal company name of the supplier")
    quotation_number: str = Field(..., min_length=2, description="Quotation / Reference number")
    quotation_date: Optional[str] = Field(None, description="Date of quotation (YYYY-MM-DD or text)")
    rfq_reference: Optional[str] = Field(None, description="Buyer RFQ reference mentioned in quote")
    currency: str = Field(..., description="Quotation currency: AED, USD, INR, EUR, GBP, SAR")
    payment_terms: str = Field(..., description="Quoted payment terms, e.g. 100% Advance, 30 days PDC, LC at sight")
    lead_time_days: int = Field(..., ge=0, description="Delivery lead time in calendar days (0 = Ex-stock)")
    validity_days: int = Field(..., ge=1, description="Quotation validity in days (e.g. 7, 14, 30)")
    incoterms: str = Field("EXW", description="Delivery term: EXW, FOB, CIF, CFR, DAP, DDP")
    vat_included: bool = Field(False, description="Whether quoted unit prices already include VAT")
    vat_percentage: float = Field(0.05, ge=0.0, le=0.50, description="Applicable tax/VAT rate (e.g. 0.05 for 5%)")
    freight_charges: Optional[float] = Field(0.0, ge=0.0, description="Additional explicit freight/handling charges")
    items: List[QuotedItem] = Field(..., min_length=1, description="Line items quoted by supplier")
    notes: Optional[str] = Field(None, description="General commercial or technical notes")

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        cleaned = v.strip().upper()
        allowed = {"AED", "USD", "INR", "EUR", "GBP", "SAR"}
        if cleaned not in allowed:
            # Map common currency symbols or typos
            mapping = {"$": "USD", "RS": "INR", "RUPEES": "INR", "DIRHAMS": "AED", "DHS": "AED"}
            if cleaned in mapping:
                return mapping[cleaned]
            raise ValueError(f"Unsupported currency: {v}. Allowed currencies are {allowed}")
        return cleaned

    @field_validator("incoterms")
    @classmethod
    def validate_incoterms(cls, v: str) -> str:
        term = v.strip().upper()
        valid = {"EXW", "FOB", "CIF", "CFR", "DAP", "DDP", "FAS", "CPT", "CIP"}
        for t in valid:
            if t in term:
                return t
        return "EXW"


class NormalizedLineMatch(BaseModel):
    rfq_item_id: str
    rfq_description: str
    rfq_grade: str
    rfq_quantity: float
    rfq_unit: str
    vendor_name: str
    quoted_description: str
    quoted_grade: Optional[str] = None
    quoted_quantity: float
    quoted_unit: str
    quoted_unit_price: float
    quoted_currency: str
    normalized_quantity: float
    normalized_unit: str
    normalized_base_unit_price: float
    normalized_base_total: float
    landed_unit_price: float
    landed_total_cost: float
    target_currency: str
    spec_status: Literal["EXACT_MATCH", "ACCEPTABLE_ALTERNATIVE", "DEVIATION_DISQUALIFIED", "MISSING"]
    spec_score: float = Field(..., ge=0.0, le=100.0)
    spec_notes: str


class VendorSummary(BaseModel):
    vendor_name: str
    quotation_number: str
    currency: str
    original_total: float
    total_landed_cost_target_currency: float
    lead_time_days: int
    payment_terms: str
    validity_days: int
    incoterms: str
    spec_compliance_score: float = Field(..., ge=0.0, le=100.0)
    lead_time_score: float = Field(..., ge=0.0, le=100.0)
    commercial_score: float = Field(..., ge=0.0, le=100.0)
    overall_score: float = Field(..., ge=0.0, le=100.0)
    cost_rank: int = 1
    overall_rank: int = 1
    disqualified: bool = False
    disqualification_reason: Optional[str] = None
    missing_items_count: int = 0
    spec_mismatch_count: int = 0
    line_matches: List[NormalizedLineMatch] = []


class ComparisonMatrix(BaseModel):
    rfq_id: str
    target_currency: str
    target_unit_weight: str
    vendors: List[VendorSummary]
    recommended_vendor: Optional[str] = None
    cost_savings_amount: float = 0.0
    cost_savings_percentage: float = 0.0
    key_findings: List[str] = []


class HumanReviewInput(BaseModel):
    approved: bool = Field(True, description="Human approval decision")
    selected_vendor: Optional[str] = Field(None, description="Human chosen vendor override or confirmation")
    edited_line_items: Optional[List[Dict[str, Any]]] = Field(None, description="Manual edits made during checkpoint")
    reviewer_name: str = Field("Rahul S. (Procurement Lead)", description="Reviewer identification")
    review_comments: Optional[str] = Field("Approved based on landed cost and 100% spec compliance.", description="Reviewer notes")


class FinalReport(BaseModel):
    rfq_id: str
    project_name: str
    target_currency: str
    executive_summary: str
    recommended_vendor: str
    total_landed_cost: float
    cost_savings_vs_highest: float
    cost_savings_pct: float
    lead_time_days: int
    payment_terms: str
    human_signoff: HumanReviewInput
    vendor_rankings: List[Dict[str, Any]]
    clarification_emails: Dict[str, str] = Field(default_factory=dict, description="Vendor -> Drafted Clarification Email")
    created_at: Optional[str] = None
