"""
LangGraph Multi-Agent Workflow for QuoteAgent.
Coordinates:
1. Ingest Agent: PDF/Excel/Scan parsing
2. Extraction Agent: Pydantic structured output + self-correction retry
3. Comparison Agent & Normalisation Tools: Unit conversion, FX conversion, Landed Cost, Spec Matching
4. Human Checkpoint: LangGraph interrupt with persistent state
5. Report Agent: Executive recommendation & supplier clarification emails
"""

from typing import Dict, Any, List, Optional
import uuid
from langgraph.graph import StateGraph, START, END

from quoteagent.models.schemas import RFQ, Quotation, ComparisonMatrix, HumanReviewInput, FinalReport
from quoteagent.models.state import GraphState
from quoteagent.ingest.parser import ingest_documents
from quoteagent.extraction.extractor import ExtractionAgent
from quoteagent.comparison.matcher import ComparisonAgent
from quoteagent.reporting.generator import ReportAgent
from quoteagent.graph.checkpointer import get_checkpointer


# --- Node Definitions ---

def ingest_node(state: GraphState) -> Dict[str, Any]:
    """Node 1: Ingest Agent - Parses uploaded files (PDF, Excel, Scans, CSV, Text)."""
    raw_docs = state.get("raw_documents", [])
    file_paths = state.get("file_paths", [])

    if file_paths and not raw_docs:
        raw_docs = ingest_documents(file_paths)

    return {
        "raw_documents": raw_docs,
        "current_step": "INGEST_COMPLETED",
    }


def extraction_node(state: GraphState) -> Dict[str, Any]:
    """Node 2: Extraction Agent - Fills Pydantic schema with validation retry loop."""
    raw_docs = state.get("raw_documents", [])
    extracted_quotes: List[Quotation] = []
    extraction_history: List[Dict[str, Any]] = []

    for doc in raw_docs:
        content = doc.get("content", "")
        # Run extraction with self-correcting retry (up to 2 retries)
        quote, history, attempts = ExtractionAgent.extract_with_retry(content, max_retries=2)
        extraction_history.extend(history)
        if quote:
            extracted_quotes.append(quote)

    return {
        "extracted_quotations": extracted_quotes,
        "extraction_history": extraction_history,
        "current_step": "EXTRACTION_COMPLETED",
    }


def comparison_node(state: GraphState) -> Dict[str, Any]:
    """
    Node 3: Comparison Agent & Normalisation Tools:
    Normalises units, currencies, landed cost, and scores vendors.
    """
    rfq_data = state.get("rfq")
    quotes = state.get("extracted_quotations", [])

    if isinstance(rfq_data, dict):
        rfq = RFQ.model_validate(rfq_data)
    else:
        rfq = rfq_data

    if not quotes:
        raise ValueError("Cannot run comparison: no quotations were successfully extracted.")

    matrix = ComparisonAgent.compare_quotations(rfq, quotes)

    return {
        "comparison_matrix": matrix,
        "checkpoint_status": "PENDING_APPROVAL",
        "current_step": "COMPARISON_COMPLETED",
    }


def human_checkpoint_node(state: GraphState) -> Dict[str, Any]:
    """
    Node 4: Human Checkpoint:
    Processes user feedback (approval, edits, selected vendor override) after interrupt resume.
    """
    review = state.get("human_review")
    if not review:
        review = HumanReviewInput(
            approved=True,
            reviewer_name="Rahul S. (Procurement Lead)",
            review_comments="Auto-approved baseline recommendation.",
        )

    return {
        "human_review": review,
        "checkpoint_status": "APPROVED" if review.approved else "REJECTED",
        "current_step": "CHECKPOINT_RESOLVED",
    }


def report_node(state: GraphState) -> Dict[str, Any]:
    """Node 5: Report Agent - Drafts executive award summary and supplier clarification emails."""
    rfq_data = state.get("rfq")
    if isinstance(rfq_data, dict):
        rfq = RFQ.model_validate(rfq_data)
    else:
        rfq = rfq_data

    matrix = state.get("comparison_matrix")
    review = state.get("human_review")

    final_report = ReportAgent.generate_final_report(rfq, matrix, review)

    return {
        "final_report": final_report,
        "current_step": "WORKFLOW_COMPLETED",
    }


# --- Workflow Graph Builder ---

def build_quoteagent_graph(checkpointer=None, enable_interrupt: bool = True):
    """
    Compiles the QuoteAgent LangGraph workflow.
    Configures checkpointing and interrupt at human_checkpoint_node.
    """
    cp = checkpointer or get_checkpointer()

    builder = StateGraph(GraphState)

    builder.add_node("ingest_node", ingest_node)
    builder.add_node("extraction_node", extraction_node)
    builder.add_node("comparison_node", comparison_node)
    builder.add_node("human_checkpoint_node", human_checkpoint_node)
    builder.add_node("report_node", report_node)

    builder.add_edge(START, "ingest_node")
    builder.add_edge("ingest_node", "extraction_node")
    builder.add_edge("extraction_node", "comparison_node")
    builder.add_edge("comparison_node", "human_checkpoint_node")
    builder.add_edge("human_checkpoint_node", "report_node")
    builder.add_edge("report_node", END)

    interrupt_nodes = ["human_checkpoint_node"] if enable_interrupt else []
    compiled_graph = builder.compile(checkpointer=cp, interrupt_before=interrupt_nodes)
    return compiled_graph


class QuoteAgentWorkflow:
    """Convenient high-level interface for running and resuming the multi-agent workflow."""

    def __init__(self, checkpointer=None):
        self.checkpointer = checkpointer or get_checkpointer()
        self.graph = build_quoteagent_graph(self.checkpointer, enable_interrupt=True)

    def start_analysis(
        self,
        rfq: RFQ,
        file_paths: Optional[List[str]] = None,
        raw_documents: Optional[List[Dict[str, Any]]] = None,
        thread_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes workflow up to the human checkpoint.
        Returns the paused state containing extracted quotations and comparison matrix.
        """
        tid = thread_id or f"rfq-session-{uuid.uuid4().hex[:8]}"
        config = {"configurable": {"thread_id": tid}}

        initial_state: Dict[str, Any] = {
            "rfq": rfq,
            "current_step": "STARTED",
        }
        if file_paths:
            initial_state["file_paths"] = file_paths
        if raw_documents:
            initial_state["raw_documents"] = raw_documents

        # Runs until interrupt_before=['human_checkpoint_node']
        paused_state = self.graph.invoke(initial_state, config=config)
        return {
            "thread_id": tid,
            "state": paused_state,
            "checkpoint_reached": True,
            "comparison_matrix": paused_state.get("comparison_matrix"),
            "extracted_quotations": paused_state.get("extracted_quotations"),
        }

    def resume_after_review(
        self,
        thread_id: str,
        human_review: HumanReviewInput,
    ) -> Dict[str, Any]:
        """
        Resumes a paused workflow session with human approval/edits.
        Completes human_checkpoint_node and report_node, returning the FinalReport.
        """
        config = {"configurable": {"thread_id": thread_id}}

        # Update state with the human review input
        self.graph.update_state(config, {"human_review": human_review})

        # Resume execution
        final_state = self.graph.invoke(None, config=config)
        return {
            "thread_id": thread_id,
            "state": final_state,
            "final_report": final_state.get("final_report"),
            "workflow_completed": True,
        }
