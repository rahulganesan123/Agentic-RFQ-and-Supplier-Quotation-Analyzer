"""
Report Agent: Drafts executive procurement award recommendation reports,
breakdowns of cost savings, and tailored clarification/inquiry emails
to suppliers regarding missing lines, spec discrepancies, or price negotiations.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List
from quoteagent.models.schemas import RFQ, ComparisonMatrix, HumanReviewInput, FinalReport


class ReportAgent:
    """Produces the final procurement package and supplier communication drafts."""

    @classmethod
    def generate_final_report(
        cls,
        rfq: RFQ,
        comparison: ComparisonMatrix,
        human_review: HumanReviewInput,
    ) -> FinalReport:
        # Determine winning vendor (human selection override or agent recommendation)
        winning_vendor_name = human_review.selected_vendor or comparison.recommended_vendor
        winning_vendor = next(
            (v for v in comparison.vendors if v.vendor_name == winning_vendor_name),
            comparison.vendors[0],
        )

        currency = comparison.target_currency
        savings_amount = comparison.cost_savings_amount
        savings_pct = comparison.cost_savings_percentage

        # Draft Executive Summary
        exec_summary = (
            f"COMMERCIAL & TECHNICAL EVALUATION REPORT\n"
            f"Project: {rfq.project_name} | RFQ Reference: {rfq.rfq_id}\n\n"
            f"Following agentic extraction, unit/currency normalisation, and spec validation across "
            f"{len(comparison.vendors)} competing suppliers, the evaluation recommends awarding the contract to "
            f"'{winning_vendor.vendor_name}' at a total landed cost of {winning_vendor.total_landed_cost_target_currency:,.2f} {currency}.\n\n"
            f"Key Decision Drivers:\n"
            f"1. Total Landed Cost: {winning_vendor.total_landed_cost_target_currency:,.2f} {currency} "
            f"(delivers {savings_amount:,.2f} {currency} / {savings_pct}% savings vs highest quote).\n"
            f"2. Technical Compliance: Achieved {winning_vendor.spec_compliance_score}% specification match with zero critical defects.\n"
            f"3. Delivery Lead Time: {winning_vendor.lead_time_days} days (within requested {rfq.required_delivery_days} days).\n"
            f"4. Commercial Terms: Quoted {winning_vendor.incoterms} with payment terms '{winning_vendor.payment_terms}'.\n"
            f"5. Human Sign-off: Approved by {human_review.reviewer_name}. Notes: \"{human_review.review_comments}\"."
        )

        # Prepare Vendor Rankings table
        rankings = []
        for v in sorted(comparison.vendors, key=lambda x: x.overall_rank):
            rankings.append({
                "Rank": v.overall_rank,
                "Vendor": v.vendor_name,
                "Landed Cost": f"{v.total_landed_cost_target_currency:,.2f} {currency}",
                "Lead Time": f"{v.lead_time_days} days",
                "Spec Score": f"{v.spec_compliance_score}%",
                "Status": "DISQUALIFIED" if v.disqualified else ("AWARDED" if v.vendor_name == winning_vendor_name else "QUALIFIED"),
                "Remarks": v.disqualification_reason or "Compliant",
            })

        # Draft vendor clarification emails
        clarification_emails = cls.draft_clarification_emails(rfq, comparison, winning_vendor_name)

        return FinalReport(
            rfq_id=rfq.rfq_id,
            project_name=rfq.project_name,
            target_currency=currency,
            executive_summary=exec_summary,
            recommended_vendor=winning_vendor_name,
            total_landed_cost=winning_vendor.total_landed_cost_target_currency,
            cost_savings_vs_highest=savings_amount,
            cost_savings_pct=savings_pct,
            lead_time_days=winning_vendor.lead_time_days,
            payment_terms=winning_vendor.payment_terms,
            human_signoff=human_review,
            vendor_rankings=rankings,
            clarification_emails=clarification_emails,
            created_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        )

    @classmethod
    def draft_clarification_emails(
        cls,
        rfq: RFQ,
        comparison: ComparisonMatrix,
        winning_vendor: str,
    ) -> Dict[str, str]:
        """Drafts polite, professional procurement clarification emails to non-winning or non-compliant suppliers."""
        emails = {}
        for v in comparison.vendors:
            if v.vendor_name == winning_vendor:
                # Award notice email
                email = (
                    f"Subject: Intent of Award - {rfq.project_name} ({rfq.rfq_id})\n\n"
                    f"Dear {v.vendor_name} Sales Team,\n\n"
                    f"Thank you for submitting quotation ref {v.quotation_number} in response to {rfq.rfq_id}.\n\n"
                    f"We are pleased to inform you that your quotation has been selected for award, subject to "
                    f"final technical verification of Mill Test Certificates (EN 10204 3.1) and agreement on delivery schedule.\n\n"
                    f"Agreed Commercial Terms:\n"
                    f"- Total Landed Cost: {v.total_landed_cost_target_currency:,.2f} {comparison.target_currency}\n"
                    f"- Delivery Terms: {v.incoterms} to {rfq.target_delivery_terms}\n"
                    f"- Promised Lead Time: {v.lead_time_days} days\n"
                    f"- Payment Terms: {v.payment_terms}\n\n"
                    f"Please confirm acceptance so our procurement division can issue the formal Purchase Order.\n\n"
                    f"Best regards,\n"
                    f"Procurement Operations Team\n"
                    f"{rfq.buyer_name}"
                )
            elif v.missing_items_count > 0:
                # Missing items inquiry
                email = (
                    f"Subject: Clarification Request - Incomplete Quotation for {rfq.rfq_id}\n\n"
                    f"Dear {v.vendor_name} Sales Team,\n\n"
                    f"Thank you for submitting quotation ref {v.quotation_number} for {rfq.project_name}.\n\n"
                    f"Upon initial evaluation, our technical team noted that your submission omitted "
                    f"{v.missing_items_count} mandatory line item(s) specified in our RFQ schedule.\n\n"
                    f"Could you please review and supply a revised quotation covering all required items by "
                    f"tomorrow close of business so that your offer may be considered for final evaluation?\n\n"
                    f"Sincerely,\n"
                    f"Procurement Operations Team\n"
                    f"{rfq.buyer_name}"
                )
            elif v.spec_mismatch_count > 0:
                # Spec deviation clarification
                email = (
                    f"Subject: Technical Specification Clarification - {rfq.rfq_id} ({rfq.project_name})\n\n"
                    f"Dear {v.vendor_name} Sales Team,\n\n"
                    f"We have reviewed your quotation ref {v.quotation_number}.\n\n"
                    f"Our engineering team noted a specification variation on quoted steel grades: "
                    f"{v.disqualification_reason}.\n\n"
                    f"Please clarify whether your offered material meets EN 10025-2 / ASTM requirements and if "
                    f"conforming Mill Test Certificates (MTC Type 3.1) can be provided upon shipment.\n\n"
                    f"Best regards,\n"
                    f"Procurement Operations Team\n"
                    f"{rfq.buyer_name}"
                )
            else:
                # Price / lead time feedback
                email = (
                    f"Subject: Commercial Feedback - Quotation {v.quotation_number} ({rfq.rfq_id})\n\n"
                    f"Dear {v.vendor_name} Sales Team,\n\n"
                    f"Thank you for participating in our bidding process for {rfq.project_name}.\n\n"
                    f"While your technical submission is compliant, your offered pricing of "
                    f"{v.total_landed_cost_target_currency:,.2f} {comparison.target_currency} was higher than competing offers.\n\n"
                    f"We invite you to review your commercial margins and let us know if there is scope for improved pricing "
                    f"or expedited delivery lead time on future requirements.\n\n"
                    f"Thank you for your ongoing partnership.\n\n"
                    f"Sincerely,\n"
                    f"Procurement Operations Team\n"
                    f"{rfq.buyer_name}"
                )

            emails[v.vendor_name] = email

        return emails
