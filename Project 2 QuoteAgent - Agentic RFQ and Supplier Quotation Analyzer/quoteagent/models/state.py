"""
LangGraph state definitions for QuoteAgent workflow.
Tracks state across ingestion, extraction, normalisation, comparison, human checkpoint, and reporting.
"""

from typing import List, Dict, Any, Optional
from typing_extensions import TypedDict
from quoteagent.models.schemas import RFQ, Quotation, ComparisonMatrix, HumanReviewInput, FinalReport


class GraphState(TypedDict, total=False):
    # RFQ details
    rfq: RFQ
    rfq_raw: Dict[str, Any]

    # Input file paths
    file_paths: List[str]

    # Ingestion node output
    raw_documents: List[Dict[str, Any]]  # [{"file_name": str, "file_type": str, "content": str, "tables": list}]

    # Extraction node output
    extracted_quotations: List[Quotation]
    extraction_history: List[Dict[str, Any]]  # logs extraction attempts, retries, and errors

    # Comparison node output
    comparison_matrix: ComparisonMatrix

    # Human checkpoint node
    human_review: HumanReviewInput
    checkpoint_status: str  # "PENDING_APPROVAL", "APPROVED", "REJECTED", "EDITED"

    # Report node output
    final_report: FinalReport

    # Tracking & workflow metadata
    current_step: str
    error: Optional[str]
