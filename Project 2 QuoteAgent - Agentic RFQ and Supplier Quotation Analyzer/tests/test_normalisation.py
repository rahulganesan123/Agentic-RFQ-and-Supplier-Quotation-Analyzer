"""
Unit tests for QuoteAgent normalisation tools:
- convert_unit (weight, length, count)
- convert_currency (USD, AED, INR, EUR, SAR)
- compute_landed_cost (Incoterms, VAT, freight)
- evaluate_spec_match (steel grades and tolerances)
"""

import pytest
from quoteagent.normalisation.tools import (
    convert_unit,
    convert_currency,
    compute_landed_cost,
    evaluate_spec_match,
    clean_unit_name,
)


class TestNormalisationTools:

    def test_clean_unit_name(self):
        assert clean_unit_name("  mt. ") == "MT"
        assert clean_unit_name("kgs") == "KGS"
        assert clean_unit_name("Pcs-") == "PCS"

    def test_convert_unit_weight(self):
        # 1 MT = 1000 KG
        assert convert_unit(1.0, "MT", "KG") == 1000.0
        assert convert_unit(2500.0, "KG", "MT") == 2.5
        # 1 Tonne = 1000 KG
        assert convert_unit(5.0, "ton", "kg") == 5000.0
        # Zero or negative
        assert convert_unit(0, "MT", "KG") == 0.0

    def test_convert_unit_length(self):
        # 1000 mm = 1 m
        assert convert_unit(12000.0, "mm", "m") == 12.0
        # 1 meter = 1000 mm
        assert convert_unit(6.0, "m", "mm") == 6000.0

    def test_convert_unit_count_with_nominal_weight(self):
        # 10 pieces with nominal weight 25 kg/pc = 250 kg = 0.25 MT
        assert convert_unit(10.0, "PCS", "MT", nominal_weight_kg_per_piece=25.0) == 0.25

    def test_convert_currency(self):
        # Same currency
        assert convert_currency(1000.0, "AED", "AED") == 1000.0
        # USD to AED (1 USD = ~3.67 AED)
        aed = convert_currency(100.0, "USD", "AED")
        assert 360.0 < aed < 375.0
        # AED to USD
        usd = convert_currency(367.25, "AED", "USD")
        assert 95.0 < usd < 105.0

    def test_unsupported_currency_raises(self):
        with pytest.raises(ValueError):
            convert_currency(100.0, "XYZ", "USD")

    def test_compute_landed_cost_exw_vat_excluded(self):
        # EXW: Freight adder is 6%, VAT 5% added to (base + freight)
        res = compute_landed_cost(
            unit_price=1000.0,
            quantity=10.0,
            currency="AED",
            incoterm="EXW",
            vat_included=False,
            vat_percentage=0.05,
            target_currency="AED",
        )
        assert res["base_quoted_original"] == 10000.0
        assert res["freight_target_currency"] == 600.0  # 6% of 10000
        # VAT = 5% of (10000 + 600) = 530.0
        assert res["vat_target_currency"] == 530.0
        assert res["landed_total_target_currency"] == 11130.0
        assert res["landed_unit_price_target_currency"] == 1113.0

    def test_compute_landed_cost_dap_vat_included(self):
        # DAP: Delivered at Place (0% freight added), VAT already included
        res = compute_landed_cost(
            unit_price=1050.0,
            quantity=2.0,
            currency="AED",
            incoterm="DAP",
            vat_included=True,
            vat_percentage=0.05,
            target_currency="AED",
        )
        assert res["base_target_currency"] == 2100.0
        assert res["freight_target_currency"] == 0.0
        # Landed total = 2100.0
        assert res["landed_total_target_currency"] == 2100.0

    def test_evaluate_spec_match_exact(self):
        status, score, notes = evaluate_spec_match("S355JR", "S355JR")
        assert status == "EXACT_MATCH"
        assert score == 100.0

    def test_evaluate_spec_match_superior(self):
        # S355J2+N is superior to S355JR
        status, score, notes = evaluate_spec_match("S355JR", "S355J2+N")
        assert status == "ACCEPTABLE_ALTERNATIVE"
        assert score >= 90.0

    def test_evaluate_spec_match_critical_defect(self):
        # S275JR has lower structural yield strength than specified S355
        status, score, notes = evaluate_spec_match("S355JR", "S275JR")
        assert status == "DEVIATION_DISQUALIFIED"
        assert score <= 30.0

    def test_evaluate_spec_match_material_class_mismatch(self):
        # Quoting stainless steel when carbon requested or vice versa
        status, score, notes = evaluate_spec_match("S355JR", "SS 316L")
        assert status == "DEVIATION_DISQUALIFIED"
        assert score == 0.0
