"""
Comparison Agent: Matches quoted items to RFQ requirements,
flags spec mismatches and missing items, normalises landed costs,
and scores vendors on total landed cost, lead time, and technical compliance.
"""

from typing import List, Dict, Any, Tuple
import re
from quoteagent.models.schemas import (
    RFQ,
    RFQItem,
    Quotation,
    QuotedItem,
    NormalizedLineMatch,
    VendorSummary,
    ComparisonMatrix,
)
from quoteagent.normalisation.tools import (
    convert_unit,
    convert_currency,
    compute_landed_cost,
    evaluate_spec_match,
)


def match_item_to_rfq(quoted_item: QuotedItem, rfq_items: List[RFQItem]) -> Tuple[RFQItem, float]:
    """
    Finds the best matching RFQ line item for a quoted item.
    Uses token overlap and steel dimension matching.
    """
    best_item = rfq_items[0]
    best_score = -1.0

    q_text = f"{quoted_item.description} {quoted_item.grade or ''} {quoted_item.dimensions or ''}".lower()
    q_tokens = set(re.findall(r"[a-z0-9]+", q_text))

    for rfq_item in rfq_items:
        r_text = f"{rfq_item.description} {rfq_item.grade} {rfq_item.dimensions or ''}".lower()
        r_tokens = set(re.findall(r"[a-z0-9]+", r_text))

        overlap = len(q_tokens.intersection(r_tokens))
        score = overlap / max(len(r_tokens), 1)

        # Dimension / section code boost (e.g. 406x178, 200, 100x100)
        for tok in q_tokens:
            if "x" in tok and tok in r_text:
                score += 0.5
            if tok in ["hea", "heb", "ipe", "ub", "uc", "shs", "rhs", "chs"] and tok in r_text:
                score += 0.4

        if score > best_score:
            best_score = score
            best_item = rfq_item

    return best_item, best_score


class ComparisonAgent:
    """
    Evaluates competing quotations against an RFQ and constructs the ComparisonMatrix.
    """

    @classmethod
    def compare_quotations(cls, rfq: RFQ, quotations: List[Quotation]) -> ComparisonMatrix:
        target_currency = rfq.target_currency
        target_unit = rfq.target_unit_weight
        vendor_summaries: List[VendorSummary] = []

        for quote in quotations:
            line_matches: List[NormalizedLineMatch] = []
            matched_rfq_ids = set()
            total_landed_cost = 0.0
            spec_scores = []
            spec_mismatches = 0

            # Match quoted items to RFQ
            for q_item in quote.items:
                rfq_item, match_score = match_item_to_rfq(q_item, rfq.items)
                matched_rfq_ids.add(rfq_item.item_id)

                # 1. Spec evaluation
                status, score, notes = evaluate_spec_match(
                    rfq_grade=rfq_item.grade,
                    quoted_grade=q_item.grade,
                    rfq_desc=rfq_item.description,
                    quoted_desc=q_item.description,
                )
                if status == "DEVIATION_DISQUALIFIED":
                    spec_mismatches += 1
                spec_scores.append(score)

                # 2. Unit Normalisation
                norm_qty = convert_unit(q_item.quantity, q_item.unit, rfq_item.unit)
                # Compute landed cost for this line
                cost_calc = compute_landed_cost(
                    unit_price=q_item.unit_price,
                    quantity=norm_qty,
                    currency=quote.currency,
                    incoterm=quote.incoterms,
                    vat_included=quote.vat_included,
                    vat_percentage=quote.vat_percentage,
                    freight_charges=0.0,  # line level
                    target_currency=target_currency,
                )

                line_landed_total = cost_calc["landed_total_target_currency"]
                line_landed_unit_price = cost_calc["landed_unit_price_target_currency"]
                norm_base_unit = round(cost_calc["base_target_currency"] / norm_qty, 2) if norm_qty > 0 else 0.0

                total_landed_cost += line_landed_total

                line_match = NormalizedLineMatch(
                    rfq_item_id=rfq_item.item_id,
                    rfq_description=rfq_item.description,
                    rfq_grade=rfq_item.grade,
                    rfq_quantity=rfq_item.quantity,
                    rfq_unit=rfq_item.unit,
                    vendor_name=quote.vendor_name,
                    quoted_description=q_item.description,
                    quoted_grade=q_item.grade,
                    quoted_quantity=q_item.quantity,
                    quoted_unit=q_item.unit,
                    quoted_unit_price=q_item.unit_price,
                    quoted_currency=quote.currency,
                    normalized_quantity=norm_qty,
                    normalized_unit=rfq_item.unit,
                    normalized_base_unit_price=norm_base_unit,
                    normalized_base_total=cost_calc["base_target_currency"],
                    landed_unit_price=line_landed_unit_price,
                    landed_total_cost=line_landed_total,
                    target_currency=target_currency,
                    spec_status=status,
                    spec_score=score,
                    spec_notes=notes,
                )
                line_matches.append(line_match)

            # Check missing items
            missing_items = [r for r in rfq.items if r.item_id not in matched_rfq_ids]
            missing_count = len(missing_items)

            # If supplier omitted items, penalize spec score
            for m in missing_items:
                spec_scores.append(0.0)

            avg_spec_score = round(sum(spec_scores) / max(len(spec_scores), 1), 1)

            # Check lead time compliance
            req_days = rfq.required_delivery_days
            quote_days = quote.lead_time_days
            if quote_days <= req_days:
                lead_time_score = 100.0
            else:
                overdue = quote_days - req_days
                lead_time_score = max(0.0, round(100.0 - (overdue * 2.5), 1))

            # Commercial score (validity & payment terms)
            comm_score = 80.0
            if "advance" in quote.payment_terms.lower():
                comm_score -= 15.0
            if quote.validity_days >= 30:
                comm_score += 10.0
            elif quote.validity_days < 7:
                comm_score -= 10.0
            comm_score = min(100.0, max(20.0, comm_score))

            # Disqualification conditions
            disqualified = False
            disq_reasons = []
            if missing_count > 0:
                disqualified = True
                disq_reasons.append(f"Incomplete quote: missing {missing_count} required RFQ line item(s).")
            if spec_mismatches > 0:
                disqualified = True
                disq_reasons.append(f"Critical specification defect: {spec_mismatches} item(s) failed yield/material criteria.")
            if quote_days > (req_days + 30):
                disqualified = True
                disq_reasons.append(f"Excessive lead time: {quote_days} days exceeds project deadline ({req_days} days).")

            # Original total in quoted currency
            orig_total = sum(i.quantity * i.unit_price for i in quote.items)

            summary = VendorSummary(
                vendor_name=quote.vendor_name,
                quotation_number=quote.quotation_number,
                currency=quote.currency,
                original_total=round(orig_total, 2),
                total_landed_cost_target_currency=round(total_landed_cost, 2),
                lead_time_days=quote.lead_time_days,
                payment_terms=quote.payment_terms,
                validity_days=quote.validity_days,
                incoterms=quote.incoterms,
                spec_compliance_score=avg_spec_score,
                lead_time_score=lead_time_score,
                commercial_score=comm_score,
                overall_score=0.0,  # calculated below
                cost_rank=1,
                overall_rank=1,
                disqualified=disqualified,
                disqualification_reason="; ".join(disq_reasons) if disq_reasons else None,
                missing_items_count=missing_count,
                spec_mismatch_count=spec_mismatches,
                line_matches=line_matches,
            )
            vendor_summaries.append(summary)

        # Rank vendors on cost
        valid_vendors = [v for v in vendor_summaries if not v.disqualified]
        candidate_pool = valid_vendors if valid_vendors else vendor_summaries

        min_cost = min((v.total_landed_cost_target_currency for v in candidate_pool), default=1.0)
        sorted_by_cost = sorted(vendor_summaries, key=lambda v: v.total_landed_cost_target_currency)
        for rank_idx, v in enumerate(sorted_by_cost):
            v.cost_rank = rank_idx + 1

        # Calculate balanced overall score:
        # Cost Score (45%), Spec Score (30%), Lead Time Score (15%), Commercial Score (10%)
        for v in vendor_summaries:
            cost_ratio = (min_cost / v.total_landed_cost_target_currency) if v.total_landed_cost_target_currency > 0 else 0
            cost_score = min(100.0, cost_ratio * 100.0)
            overall = (cost_score * 0.45) + (v.spec_compliance_score * 0.30) + (v.lead_time_score * 0.15) + (v.commercial_score * 0.10)
            if v.disqualified:
                overall *= 0.5  # Penalize disqualified
            v.overall_score = round(overall, 1)

        # Overall ranking
        sorted_by_overall = sorted(vendor_summaries, key=lambda v: (not v.disqualified, v.overall_score), reverse=True)
        for rank_idx, v in enumerate(sorted_by_overall):
            v.overall_rank = rank_idx + 1

        # Recommended vendor (highest overall among non-disqualified)
        recommended = sorted_by_overall[0]
        max_cost = max((v.total_landed_cost_target_currency for v in vendor_summaries), default=recommended.total_landed_cost_target_currency)
        savings_amount = round(max_cost - recommended.total_landed_cost_target_currency, 2)
        savings_pct = round((savings_amount / max_cost) * 100, 1) if max_cost > 0 else 0.0

        key_findings = [
            f"Recommended Vendor: {recommended.vendor_name} with Landed Cost of {recommended.total_landed_cost_target_currency:,.2f} {target_currency}.",
            f"Delivers cost savings of {savings_amount:,.2f} {target_currency} ({savings_pct}%) vs highest quotation.",
            f"Technical compliance score: {recommended.spec_compliance_score}% (Lead time: {recommended.lead_time_days} days).",
        ]
        for v in vendor_summaries:
            if v.disqualified:
                key_findings.append(f"FLAGGED: {v.vendor_name} disqualified: {v.disqualification_reason}")

        return ComparisonMatrix(
            rfq_id=rfq.rfq_id,
            target_currency=target_currency,
            target_unit_weight=target_unit,
            vendors=vendor_summaries,
            recommended_vendor=recommended.vendor_name,
            cost_savings_amount=savings_amount,
            cost_savings_percentage=savings_pct,
            key_findings=key_findings,
        )
