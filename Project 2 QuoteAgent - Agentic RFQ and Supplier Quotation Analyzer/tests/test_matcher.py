"""
Unit tests for QuoteAgent Comparison Agent and Spec Matcher:
- Spec matching against RFQ requirements
- Missing item detection and penalization
- Landed cost calculation across competing suppliers
- Supplier multi-criteria scoring and ranking
"""

import pytest
from quoteagent.models.schemas import RFQ, RFQItem, Quotation, QuotedItem
from quoteagent.comparison.matcher import ComparisonAgent, match_item_to_rfq


class TestComparisonAndMatcher:

    @pytest.fixture
    def sample_rfq(self):
        return RFQ(
            rfq_id="RFQ-TEST-001",
            project_name="Warehouse Steel",
            buyer_name="Al Quoz Fabricators",
            target_currency="AED",
            target_unit_weight="MT",
            target_delivery_terms="DAP Dubai",
            required_delivery_days=30,
            items=[
                RFQItem(
                    item_id="ITEM-1",
                    description="Universal Beam UB 406x178x74",
                    grade="S355JR",
                    quantity=20.0,
                    unit="MT",
                ),
                RFQItem(
                    item_id="ITEM-2",
                    description="Equal Angle 100x100x10",
                    grade="S275JR",
                    quantity=10.0,
                    unit="MT",
                ),
            ],
        )

    def test_match_item_to_rfq_profile(self, sample_rfq):
        quoted = QuotedItem(
            item_no=1,
            description="UB 406x178x74mm Beam",
            grade="S355JR",
            quantity=20.0,
            unit="MT",
            unit_price=3300.0,
        )
        matched_item, score = match_item_to_rfq(quoted, sample_rfq.items)
        assert matched_item.item_id == "ITEM-1"

    def test_compare_quotations_ranking_and_disqualification(self, sample_rfq):
        # Vendor 1: Fully compliant, competitive price
        v1 = Quotation(
            vendor_name="Compliant Steel LLC",
            quotation_number="QT-1",
            currency="AED",
            payment_terms="30 days PDC",
            lead_time_days=20,
            validity_days=30,
            incoterms="DAP",
            vat_included=False,
            items=[
                QuotedItem(item_no=1, description="UB 406x178x74", grade="S355JR", quantity=20.0, unit="MT", unit_price=3200.0),
                QuotedItem(item_no=2, description="EA 100x100x10", grade="S275JR", quantity=10.0, unit="MT", unit_price=3100.0),
            ],
        )

        # Vendor 2: Missing Item 2 (Incomplete quotation)
        v2 = Quotation(
            vendor_name="Incomplete Supplier Ltd",
            quotation_number="QT-2",
            currency="AED",
            payment_terms="100% Advance",
            lead_time_days=15,
            validity_days=14,
            incoterms="EXW",
            vat_included=False,
            items=[
                QuotedItem(item_no=1, description="UB 406x178x74", grade="S355JR", quantity=20.0, unit="MT", unit_price=2900.0),
            ],
        )

        matrix = ComparisonAgent.compare_quotations(sample_rfq, [v1, v2])

        assert len(matrix.vendors) == 2
        # Vendor 1 should be recommended
        assert matrix.recommended_vendor == "Compliant Steel LLC"

        # Vendor 2 should be flagged / disqualified for missing item
        v2_summary = next(v for v in matrix.vendors if v.vendor_name == "Incomplete Supplier Ltd")
        assert v2_summary.disqualified is True
        assert "missing 1 required RFQ line item" in v2_summary.disqualification_reason
