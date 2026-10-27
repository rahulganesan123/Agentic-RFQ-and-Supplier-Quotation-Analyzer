"""
Unit tests for QuoteAgent LangGraph Workflow:
- End-to-end execution up to human checkpoint
- State persistence in checkpointer
- Human review checkpoint interrupt and resumption
- Final report generation and draft clarification emails
"""

import pytest
from quoteagent.models.schemas import RFQ, RFQItem, Quotation, QuotedItem, HumanReviewInput
from quoteagent.graph.workflow import QuoteAgentWorkflow
from quoteagent.graph.checkpointer import get_checkpointer


class TestWorkflowExecution:

    @pytest.fixture
    def test_setup(self):
        rfq = RFQ(
            rfq_id="RFQ-TEST-WF",
            project_name="Bridge Structural Framing",
            buyer_name="Gulf Steel Works LLC",
            target_currency="AED",
            target_unit_weight="MT",
            target_delivery_terms="DAP Dubai",
            required_delivery_days=25,
            items=[
                RFQItem(
                    item_id="ITEM-1",
                    description="Heavy European Standard Beam HEB 400",
                    grade="S355JR",
                    quantity=30.0,
                    unit="MT",
                )
            ],
        )

        raw_docs = [
            {
                "file_name": "quote_1.txt",
                "file_type": "text",
                "content": """
                SUPPLIER QUOTATION
                Vendor: Emirates Prime Steel Trading LLC
                Quote Ref: QT-TEST-001
                Date: 2026-03-01
                RFQ Ref: RFQ-TEST-WF
                Currency: AED
                Delivery: DAP Dubai | Lead Time: 20 days
                Payment Terms: 30 days PDC
                Validity: 30 days
                VAT: 5% VAT Extra
                SCHEDULE OF ITEMS:
                Item 1: Heavy European Standard Beam HEB 400 | Grade: S355JR | Qty: 30.0 MT | Price: 3400.0 | Total: 102000.0
                """,
            },
            {
                "file_name": "quote_2.txt",
                "file_type": "text",
                "content": """
                SUPPLIER QUOTATION
                Vendor: Gulf Heavy Plates & Sections FZE
                Quote Ref: QT-TEST-002
                Date: 2026-03-01
                RFQ Ref: RFQ-TEST-WF
                Currency: AED
                Delivery: EXW Jebel Ali | Lead Time: 10 days
                Payment Terms: 100% Advance
                Validity: 14 days
                VAT: Inclusive 5%
                SCHEDULE OF ITEMS:
                Item 1: Heavy European Standard Beam HEB 400 | Grade: S355JR | Qty: 30.0 MT | Price: 3550.0 | Total: 106500.0
                """,
            },
        ]
        return rfq, raw_docs

    def test_workflow_runs_to_checkpoint_and_resumes(self, test_setup):
        rfq, raw_docs = test_setup

        wf = QuoteAgentWorkflow()
        thread_id = "test-session-unit-1"

        # 1. Run until human checkpoint
        start_result = wf.start_analysis(rfq=rfq, raw_documents=raw_docs, thread_id=thread_id)

        assert start_result["checkpoint_reached"] is True
        assert start_result["comparison_matrix"] is not None
        assert len(start_result["comparison_matrix"].vendors) == 2

        # 2. Provide Human Review Input
        human_review = HumanReviewInput(
            approved=True,
            selected_vendor="Emirates Prime Steel Trading LLC",
            reviewer_name="Rahul S. (Procurement Lead)",
            review_comments="Selected lowest landed cost with 100% spec compliance.",
        )

        # 3. Resume workflow
        resume_result = wf.resume_after_review(thread_id=thread_id, human_review=human_review)

        assert resume_result["workflow_completed"] is True
        final_report = resume_result["final_report"]
        assert final_report is not None
        assert final_report.recommended_vendor == "Emirates Prime Steel Trading LLC"
        assert len(final_report.clarification_emails) == 2
        assert "Intent of Award" in final_report.clarification_emails["Emirates Prime Steel Trading LLC"]
