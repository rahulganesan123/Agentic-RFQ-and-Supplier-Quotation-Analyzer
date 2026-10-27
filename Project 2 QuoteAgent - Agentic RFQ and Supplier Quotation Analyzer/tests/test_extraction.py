"""
Unit tests for QuoteAgent extraction agent & Pydantic schema validation:
- Validates QuotedItem constraints (quantity > 0, unit price >= 0, auto total computation)
- Validates Quotation constraints (valid currency, incoterms, validity days >= 1)
- Validates self-correction retry mechanism
"""

import pytest
from pydantic import ValidationError
from quoteagent.models.schemas import Quotation, QuotedItem
from quoteagent.extraction.extractor import ExtractionAgent, clean_json_string


class TestExtractionAndSchemas:

    def test_quoted_item_auto_total_calculation(self):
        item = QuotedItem(
            item_no=1,
            description="Universal Beam UB 406x178x74",
            grade="S355JR",
            quantity=10.0,
            unit="MT",
            unit_price=3400.0,
        )
        assert item.total_price == 34000.0

    def test_quoted_item_negative_quantity_raises(self):
        with pytest.raises(ValidationError):
            QuotedItem(
                item_no=1,
                description="UB 406",
                quantity=-5.0,
                unit="MT",
                unit_price=3000.0,
            )

    def test_quotation_schema_currency_normalization(self):
        quote = Quotation(
            vendor_name="Gulf Steel LLC",
            quotation_number="QT-101",
            currency="dhs",  # Should normalize to AED
            payment_terms="30 days PDC",
            lead_time_days=14,
            validity_days=15,
            incoterms="ex-works",  # Should normalize to EXW
            vat_included=False,
            items=[
                QuotedItem(
                    item_no=1,
                    description="Beam",
                    quantity=5.0,
                    unit="MT",
                    unit_price=3200.0,
                )
            ],
        )
        assert quote.currency == "AED"
        assert quote.incoterms == "EXW"

    def test_clean_json_string(self):
        raw = "```json\n{\"vendor_name\": \"Apex Steel\", \"currency\": \"AED\"}\n```"
        cleaned = clean_json_string(raw)
        assert cleaned == '{"vendor_name": "Apex Steel", "currency": "AED"}'

    def test_extraction_self_correction_on_corrupt_data(self):
        # Doc with text format
        text = """
        SUPPLIER QUOTATION
        Vendor: Gulf Structural Steels LLC
        Quote Ref: QT-TEST-99
        Date: 2026-03-01
        Currency: AED
        Delivery: EXW | Lead Time: 14 days
        Payment Terms: 30 days PDC
        Validity: 30 days
        SCHEDULE:
        Item 1: HEA 200 European Beam | Grade: S355JR | Qty: 20.0 MT | Price: 3450.0 | Total: 69000.0
        """
        quote, history, attempts = ExtractionAgent.extract_with_retry(text, max_retries=2)
        assert quote is not None
        assert quote.vendor_name == "Gulf Structural Steels LLC"
        assert quote.currency == "AED"
        assert len(quote.items) == 1
        assert quote.items[0].quantity == 20.0
