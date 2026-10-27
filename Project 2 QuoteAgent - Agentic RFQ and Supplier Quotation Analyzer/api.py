"""
FastAPI Backend for QuoteAgent.
Exposes REST endpoints for:
- RFQ creation and document upload
- Running agentic analysis pipeline up to human checkpoint
- Retrieving paused checkpoint state
- Resuming workflow upon human approval/review
- Exporting final award reports
"""

import os
import sys
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware

# Ensure quoteagent is on path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from quoteagent.models.schemas import RFQ, RFQItem, HumanReviewInput, FinalReport, ComparisonMatrix
from quoteagent.graph.workflow import QuoteAgentWorkflow
from quoteagent.ingest.parser import DocumentParser

app = FastAPI(
    title="QuoteAgent REST API",
    description="Agentic RFQ and Supplier Quotation Analyzer with LangGraph and Human-in-the-Loop Checkpoints",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session tracking (backed by SQLite/PostgreSQL LangGraph checkpointer)
workflow_engine = QuoteAgentWorkflow()


@app.get("/")
def root():
    return {
        "service": "QuoteAgent API",
        "status": "operational",
        "description": "Agentic RFQ and Supplier Quotation Analyzer",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {"status": "ok", "checkpointer": "active"}


@app.post("/analyze")
def start_rfq_analysis(
    rfq: RFQ,
    thread_id: Optional[str] = None,
):
    """
    Initiates LangGraph workflow:
    Runs Ingestion -> Extraction with Retry -> Normalisation -> Comparison Matrix.
    Halts at human_checkpoint_node interrupt and returns thread_id for human review.
    """
    tid = thread_id or f"api-{uuid.uuid4().hex[:8]}"

    # Locate default sample quotes for this RFQ if none uploaded
    quotes_dir = BASE_DIR / "benchmark" / "quotations"
    matching = sorted(list(quotes_dir.glob(f"QUOTE_{rfq.rfq_id.replace('-', '_')}_*.*")))
    quote_paths = [str(p) for p in matching[:5]]

    if not quote_paths:
        raise HTTPException(status_code=400, detail=f"No quotations found for RFQ {rfq.rfq_id}. Please upload quotes.")

    try:
        run_res = workflow_engine.start_analysis(
            rfq=rfq,
            file_paths=quote_paths,
            thread_id=tid,
        )
        return {
            "thread_id": tid,
            "status": "PAUSED_AT_HUMAN_CHECKPOINT",
            "message": "Comparison matrix generated. Awaiting human procurement approval.",
            "comparison_matrix": run_res["comparison_matrix"],
            "extracted_quotes_count": len(run_res.get("extracted_quotations", [])),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/checkpoint/{thread_id}")
def get_checkpoint_state(thread_id: str):
    """Retrieves current paused checkpoint state from the LangGraph checkpointer."""
    config = {"configurable": {"thread_id": thread_id}}
    state_snapshot = workflow_engine.graph.get_state(config)
    if not state_snapshot or not state_snapshot.values:
        raise HTTPException(status_code=404, detail=f"Session thread '{thread_id}' not found.")

    return {
        "thread_id": thread_id,
        "next_nodes": state_snapshot.next,
        "comparison_matrix": state_snapshot.values.get("comparison_matrix"),
        "checkpoint_status": state_snapshot.values.get("checkpoint_status", "PENDING_APPROVAL"),
    }


@app.post("/resume/{thread_id}")
def resume_with_human_decision(
    thread_id: str,
    review: HumanReviewInput,
):
    """
    Resumes LangGraph execution after human decision:
    Completes human_checkpoint_node and report_node, drafting final award report and clarification emails.
    """
    try:
        res = workflow_engine.resume_after_review(
            thread_id=thread_id,
            human_review=review,
        )
        return {
            "thread_id": thread_id,
            "status": "COMPLETED",
            "final_report": res["final_report"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
