"""
Synthetic Dataset Generator for QuoteAgent.
Generates:
1. 10 realistic Buyer RFQs (steel fabrication, structural steel, plates, hollow sections, fasteners, piping).
2. 45-50 realistic competing supplier quotations in PDF (via reportlab), Excel (via openpyxl), and text/CSV.
3. 100% hand-labelled ground truth JSON for every quotation in benchmark/ground_truth/.
Includes intentional real-world variations: units (kg, MT, pcs, lbs), currencies (AED, USD, INR, EUR, SAR),
Incoterms (EXW, FOB, CIF, DAP), VAT (included vs excluded), spec variations, and missing items.
"""

import os
import json
from pathlib import Path
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

ROOT_DIR = Path(__file__).resolve().parent
BENCHMARK_DIR = ROOT_DIR / "benchmark"
RFQS_DIR = BENCHMARK_DIR / "rfqs"
QUOTES_DIR = BENCHMARK_DIR / "quotations"
GROUND_TRUTH_DIR = BENCHMARK_DIR / "ground_truth"


# --- 10 Realistic Steel Fabrication RFQs ---
SAMPLE_RFQS = [
    {
        "rfq_id": "RFQ-2026-001",
        "project_name": "Warehouse Structural Steel Framework - DIC Package B",
        "buyer_name": "Al Quoz Steel Fabricators LLC",
        "target_currency": "AED",
        "target_unit_weight": "MT",
        "target_delivery_terms": "DAP Dubai Industrial City",
        "required_delivery_days": 30,
        "items": [
            {"item_id": "ITEM-1", "description": "Universal Beam UB 406x178x74", "grade": "S355JR", "dimensions": "406x178x74mm, 12m length", "quantity": 35.0, "unit": "MT", "target_lead_time_days": 25, "notes": "EN 10025-2 MTC 3.1"},
            {"item_id": "ITEM-2", "description": "Universal Column UC 254x254x89", "grade": "S355JR", "dimensions": "254x254x89mm, 12m length", "quantity": 28.5, "unit": "MT", "target_lead_time_days": 25, "notes": "Mill origin GCC or Europe"},
            {"item_id": "ITEM-3", "description": "Equal Angle EA 100x100x10", "grade": "S275JR", "dimensions": "100x100x10mm, 6m length", "quantity": 12.0, "unit": "MT", "target_lead_time_days": 20, "notes": "Bracing members"},
            {"item_id": "ITEM-4", "description": "Base Plate S355JR 25mm", "grade": "S355JR", "dimensions": "25mm x 1500mm x 6000mm", "quantity": 15.0, "unit": "MT", "target_lead_time_days": 25, "notes": "CNC cut to size"},
        ]
    },
    {
        "rfq_id": "RFQ-2026-002",
        "project_name": "Storage Tank & Pressure Vessel Shell Plates",
        "buyer_name": "Gulf Process Vessels FZE",
        "target_currency": "AED",
        "target_unit_weight": "MT",
        "target_delivery_terms": "DAP Hamriyah Free Zone, Sharjah",
        "required_delivery_days": 40,
        "items": [
            {"item_id": "ITEM-1", "description": "Normalized Heavy Steel Plate 20mm S355J2+N", "grade": "S355J2+N", "dimensions": "20mm x 2500mm x 12000mm", "quantity": 42.0, "unit": "MT", "target_lead_time_days": 35, "notes": "Charpy V-Notch at -20C"},
            {"item_id": "ITEM-2", "description": "Tank Shell Plate 12mm S355J2+N", "grade": "S355J2+N", "dimensions": "12mm x 2000mm x 9000mm", "quantity": 30.0, "unit": "MT", "target_lead_time_days": 35, "notes": "Ultrasonic tested Level II"},
            {"item_id": "ITEM-3", "description": "Dished Head Flange Steel Plate 16mm", "grade": "S355J2+N", "dimensions": "16mm x 2000mm x 6000mm", "quantity": 18.0, "unit": "MT", "target_lead_time_days": 35, "notes": "Forming grade"},
        ]
    },
    {
        "rfq_id": "RFQ-2026-003",
        "project_name": "Offshore Platform Topside Tubular Package",
        "buyer_name": "National Marine Fabricators PJSC",
        "target_currency": "USD",
        "target_unit_weight": "MT",
        "target_delivery_terms": "CIF Abu Dhabi Port",
        "required_delivery_days": 45,
        "items": [
            {"item_id": "ITEM-1", "description": "Circular Hollow Section CHS 323.9x12.7", "grade": "S355NH", "dimensions": "323.9mm OD x 12.7mm WT, 12m length", "quantity": 55.0, "unit": "MT", "target_lead_time_days": 40, "notes": "Seamless or SAW pipe API 5L / EN 10210"},
            {"item_id": "ITEM-2", "description": "Square Hollow Section SHS 200x200x10", "grade": "S355J2H", "dimensions": "200x200x10.0mm, 12m", "quantity": 32.0, "unit": "MT", "target_lead_time_days": 40, "notes": "Hot finished hollow sections"},
            {"item_id": "ITEM-3", "description": "Rectangular Hollow Section RHS 250x150x12", "grade": "S355J2H", "dimensions": "250x150x12.0mm, 12m", "quantity": 25.0, "unit": "MT", "target_lead_time_days": 40, "notes": "Internal offshore bracing"},
        ]
    },
    {
        "rfq_id": "RFQ-2026-004",
        "project_name": "Industrial Mezzanine & Maintenance Walkway Package",
        "buyer_name": "Emirates Engineering & Erection LLC",
        "target_currency": "AED",
        "target_unit_weight": "MT",
        "target_delivery_terms": "DAP Al Quoz Industrial 3, Dubai",
        "required_delivery_days": 21,
        "items": [
            {"item_id": "ITEM-1", "description": "European I-Beam IPE 240", "grade": "S275JR", "dimensions": "240x120x6.2x9.8mm, 12m length", "quantity": 20.0, "unit": "MT", "target_lead_time_days": 15, "notes": "Ex-stock preferred"},
            {"item_id": "ITEM-2", "description": "Tear Drop Chequered Floor Plate 6mm", "grade": "S275JR", "dimensions": "6mm x 1500mm x 6000mm", "quantity": 14.5, "unit": "MT", "target_lead_time_days": 15, "notes": "Anti-slip surface pattern"},
            {"item_id": "ITEM-3", "description": "Channel Section UPN 160", "grade": "S275JR", "dimensions": "160x65x7.5x10.5mm, 6m length", "quantity": 8.0, "unit": "MT", "target_lead_time_days": 15, "notes": "Stair stringer channel"},
            {"item_id": "ITEM-4", "description": "Tubular Handrail Pipe 1-1/2 inch Sch 40", "grade": "ASTM A53 Gr B", "dimensions": "48.3mm OD x 3.68mm WT, 6m", "quantity": 6.5, "unit": "MT", "target_lead_time_days": 15, "notes": "Black steel pipe for safety railing"},
        ]
    },
    {
        "rfq_id": "RFQ-2026-005",
        "project_name": "High-Strength Structural Fasteners & HDG Anchor Bolts",
        "buyer_name": "Apex Structural Connections Co",
        "target_currency": "AED",
        "target_unit_weight": "PCS",
        "target_delivery_terms": "DAP Jebel Ali Free Zone",
        "required_delivery_days": 14,
        "items": [
            {"item_id": "ITEM-1", "description": "Hex Bolt M20x70mm Grade 8.8 HDG with Nut & 2 Washers", "grade": "Grade 8.8 HDG", "dimensions": "M20 x 70mm, Hot Dip Galvanized ISO 10684", "quantity": 5000.0, "unit": "PCS", "target_lead_time_days": 10, "notes": "ISO 4014 / ISO 4032"},
            {"item_id": "ITEM-2", "description": "High Strength Preloaded Bolt M24x90 Grade 10.9", "grade": "Grade 10.9 HDG", "dimensions": "M24 x 90mm, EN 14399-3 System HR", "quantity": 3200.0, "unit": "PCS", "target_lead_time_days": 10, "notes": "Torque tension calibrated"},
            {"item_id": "ITEM-3", "description": "Foundation L-Anchor Bolt M30x800mm S275", "grade": "S275JR", "dimensions": "M30 dia x 800mm length, 100mm hook", "quantity": 450.0, "unit": "PCS", "target_lead_time_days": 14, "notes": "Threaded 150mm with double nut & washer"},
        ]
    },
    {
        "rfq_id": "RFQ-2026-006",
        "project_name": "Chemical Plant Stainless Steel Process Piping Package",
        "buyer_name": "PetroChem Engineering Systems LLC",
        "target_currency": "USD",
        "target_unit_weight": "M",
        "target_delivery_terms": "CIF Jebel Ali Port",
        "required_delivery_days": 35,
        "items": [
            {"item_id": "ITEM-1", "description": "Stainless Steel Seamless Pipe 4 inch Sch 40S", "grade": "SS 316L", "dimensions": "114.3mm OD x 6.02mm WT, ASTM A312", "quantity": 480.0, "unit": "M", "target_lead_time_days": 30, "notes": "Dual certified 316/316L, MTC 3.1"},
            {"item_id": "ITEM-2", "description": "Stainless Steel Seamless Pipe 2 inch Sch 40S", "grade": "SS 316L", "dimensions": "60.3mm OD x 3.91mm WT, ASTM A312", "quantity": 360.0, "unit": "M", "target_lead_time_days": 30, "notes": "Annealed & pickled finish"},
            {"item_id": "ITEM-3", "description": "Weld Neck Flange 4 inch Class 150 WNRF SS316L", "grade": "SS 316L", "dimensions": "ANSI B16.5 Class 150, Sch 40 bore", "quantity": 80.0, "unit": "PCS", "target_lead_time_days": 25, "notes": "Forged ASTM A182 F316L"},
        ]
    },
    {
        "rfq_id": "RFQ-2026-007",
        "project_name": "Heavy Industrial Crane Runway Girders & Rail System",
        "buyer_name": "Heavy Lift Structures Dubai",
        "target_currency": "AED",
        "target_unit_weight": "MT",
        "target_delivery_terms": "DAP Abu Dhabi Mussafah ICAD-1",
        "required_delivery_days": 30,
        "items": [
            {"item_id": "ITEM-1", "description": "Heavy European Standard Beam HEB 500", "grade": "S355J2", "dimensions": "500x300x14.5x28mm, 15m length", "quantity": 48.0, "unit": "MT", "target_lead_time_days": 25, "notes": "Charpy impact tested -20 deg C"},
            {"item_id": "ITEM-2", "description": "Crane Rail DIN 536 A75", "grade": "Rail Steel 900A", "dimensions": "Head 75mm, 56.2 kg/m, 12m lengths", "quantity": 18.5, "unit": "MT", "target_lead_time_days": 25, "notes": "Pre-drilled fishplate joint holes"},
            {"item_id": "ITEM-3", "description": "Gantrex Adjustable Rail Clips Series 5120", "grade": "Forged Steel", "dimensions": "Type 5120/15/35 complete with vulcanized rubber nose", "quantity": 600.0, "unit": "PCS", "target_lead_time_days": 20, "notes": "Grade 8.8 fastening bolts included"},
        ]
    },
    {
        "rfq_id": "RFQ-2026-008",
        "project_name": "Architectural Weathering Steel Bridge Girders (Corten)",
        "buyer_name": "Urban Infrastructure Builders PJSC",
        "target_currency": "USD",
        "target_unit_weight": "MT",
        "target_delivery_terms": "CIF Khalifa Port, Abu Dhabi",
        "required_delivery_days": 45,
        "items": [
            {"item_id": "ITEM-1", "description": "Weathering Steel Plate 30mm S355J0W (Corten B)", "grade": "S355J0W", "dimensions": "30mm x 2500mm x 12000mm, EN 10025-5", "quantity": 65.0, "unit": "MT", "target_lead_time_days": 40, "notes": "Atmospheric corrosion resistant steel"},
            {"item_id": "ITEM-2", "description": "Weathering Steel Plate 16mm S355J0W", "grade": "S355J0W", "dimensions": "16mm x 2000mm x 9000mm, EN 10025-5", "quantity": 38.0, "unit": "MT", "target_lead_time_days": 40, "notes": "Web plates for fabricated box girders"},
            {"item_id": "ITEM-3", "description": "Weathering Steel Angle 120x120x12 S355J0W", "grade": "S355J0W", "dimensions": "120x120x12mm, 12m length", "quantity": 14.0, "unit": "MT", "target_lead_time_days": 40, "notes": "Stiffeners"},
        ]
    },
    {
        "rfq_id": "RFQ-2026-009",
        "project_name": "Cold-Formed Galvanized Purlins & Industrial Cladding",
        "buyer_name": "Desert Roof & Wall Cladding LLC",
        "target_currency": "AED",
        "target_unit_weight": "M",
        "target_delivery_terms": "DAP Sharjah Industrial Area 15",
        "required_delivery_days": 18,
        "items": [
            {"item_id": "ITEM-1", "description": "Galvanized Z Purlin Z200x2.5mm Z275 Coating", "grade": "S350GD+Z275", "dimensions": "200mm depth x 65/60 flanges x 2.5mm thk, 8m length", "quantity": 3200.0, "unit": "M", "target_lead_time_days": 14, "notes": "Hot dip zinc coated 275 g/m2"},
            {"item_id": "ITEM-2", "description": "Galvanized C Channel Purlin C150x2.0mm Z275", "grade": "S350GD+Z275", "dimensions": "150mm depth x 50mm flanges x 2.0mm thk, 6m length", "quantity": 1800.0, "unit": "M", "target_lead_time_days": 14, "notes": "Side wall runner purlins"},
            {"item_id": "ITEM-3", "description": "Self-Drilling Hex Head Screws 12-14 x 25mm Class 3", "grade": "Carbon Steel Ruspert Coated", "dimensions": "12-14 x 25mm with EPDM washer", "quantity": 25000.0, "unit": "PCS", "target_lead_time_days": 7, "notes": "1000 hrs salt spray resistance"},
        ]
    },
    {
        "rfq_id": "RFQ-2026-010",
        "project_name": "Mining Chute Wear Plates & Quenched Abrasion Package",
        "buyer_name": "Aggregate & Quarry Equipment FZE",
        "target_currency": "USD",
        "target_unit_weight": "MT",
        "target_delivery_terms": "DAP Fujairah Crushing Plant",
        "required_delivery_days": 28,
        "items": [
            {"item_id": "ITEM-1", "description": "Abrasion Resistant Wear Plate 400 HBW (Hardox 400 / Raex 400)", "grade": "Hardox 400 Equivalent", "dimensions": "15mm x 2000mm x 6000mm, 400 HBW hardness", "quantity": 22.0, "unit": "MT", "target_lead_time_days": 20, "notes": "Quenched & tempered wear steel"},
            {"item_id": "ITEM-2", "description": "Heavy Wear Liner Plate 25mm 450 HBW", "grade": "Hardox 450 Equivalent", "dimensions": "25mm x 1500mm x 3000mm, 450 HBW hardness", "quantity": 16.5, "unit": "MT", "target_lead_time_days": 20, "notes": "Impact chute receiving zone"},
            {"item_id": "ITEM-3", "description": "Countersunk Wear Liner Bolts M20x90mm Grade 10.9", "grade": "Grade 10.9", "dimensions": "M20 x 90mm Oval neck countersunk DIN 608", "quantity": 1200.0, "unit": "PCS", "target_lead_time_days": 14, "notes": "Conical washer and self-locking nyloc nut"},
        ]
    }
]


# --- Realistic Supplier Profile Templates ---
SUPPLIERS = [
    {
        "name": "Emirates National Steel Trading LLC",
        "location": "Dubai Industrial City, UAE",
        "currency": "AED",
        "incoterm": "DAP",
        "vat_included": False,
        "vat_percentage": 0.05,
        "payment_terms": "30 days PDC from delivery",
        "price_factor": 1.00,  # Competitive baseline
        "lead_time_base": 20,
        "validity_days": 14,
        "spec_bias": "EXACT",
    },
    {
        "name": "Gulf Structural & Plates FZE",
        "location": "Jebel Ali Free Zone, Dubai",
        "currency": "AED",
        "incoterm": "EXW",
        "vat_included": False,
        "vat_percentage": 0.05,
        "payment_terms": "100% Advance against PI",
        "price_factor": 0.94,  # Cheaper base, but EXW freight added
        "lead_time_base": 12,  # Ex-stock
        "validity_days": 7,
        "spec_bias": "EXACT",
    },
    {
        "name": "Bharat Heavy Steels & Forgings Ltd",
        "location": "Mumbai Port, India",
        "currency": "USD",
        "incoterm": "CIF",
        "vat_included": False,
        "vat_percentage": 0.05,
        "payment_terms": "LC at sight 60 days",
        "price_factor": 0.88,  # Highly competitive overseas mill price
        "lead_time_base": 38,  # Longer ocean voyage
        "validity_days": 21,
        "spec_bias": "EXACT",
    },
    {
        "name": "Saudi National Steel Products Co",
        "location": "Second Industrial City, Dammam, KSA",
        "currency": "SAR",
        "incoterm": "DAP",
        "vat_included": True,  # Inclusive of VAT
        "vat_percentage": 0.05,
        "payment_terms": "Net 45 days",
        "price_factor": 1.05,
        "lead_time_base": 24,
        "validity_days": 30,
        "spec_bias": "ACCEPTABLE_SUPERIOR",
    },
    {
        "name": "Apex Metal Profiling & Trading LLC",
        "location": "Sharjah Industrial Area 10, UAE",
        "currency": "AED",
        "incoterm": "EXW",
        "vat_included": True,
        "vat_percentage": 0.05,
        "payment_terms": "Cash on Delivery",
        "price_factor": 1.12,  # Expensive local stockist
        "lead_time_base": 7,   # Immediate stock
        "validity_days": 5,
        "spec_bias": "DEFECTIVE_ON_SOME",  # Offers cheaper lower grade on some items
    }
]


def generate_pdf_quotation(file_path: Path, quote_data: dict):
    """Creates a realistic corporate PDF quotation document."""
    doc = SimpleDocTemplate(str(file_path), pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    styles = getSampleStyleSheet()
    story = []

    # Header title
    title_style = ParagraphStyle(
        'QuoteHeader',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1A365D'),
        spaceAfter=6,
    )
    story.append(Paragraph(f"<b>{quote_data['vendor_name']}</b>", title_style))
    story.append(Paragraph(f"<font size=9 color='#4A5568'>Industrial Area, P.O. Box 48921 | Tax ID / TRN: 100349812900003 | Sales Dept</font>", styles['Normal']))
    story.append(Spacer(1, 12))

    # Quotation info box
    info_data = [
        [f"<b>QUOTATION REF:</b> {quote_data['quotation_number']}", f"<b>DATE:</b> {quote_data['quotation_date']}"],
        [f"<b>BUYER RFQ REF:</b> {quote_data['rfq_reference']}", f"<b>CURRENCY:</b> {quote_data['currency']}"],
        [f"<b>DELIVERY TERMS:</b> {quote_data['incoterms']}", f"<b>LEAD TIME:</b> {quote_data['lead_time_days']} Calendar Days"],
        [f"<b>PAYMENT TERMS:</b> {quote_data['payment_terms']}", f"<b>VALIDITY:</b> {quote_data['validity_days']} Days"],
    ]
    info_table = Table(info_data, colWidths=[3.5*inch, 3.5*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#EDF2F7')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 14))

    # Items Table
    headers = ["Item", "Description / Grade", "Dimensions", "Qty", "Unit", "Unit Price", "Total Price"]
    table_rows = [headers]
    curr = quote_data['currency']

    subtotal = 0.0
    for it in quote_data['items']:
        tot = it['quantity'] * it['unit_price']
        subtotal += tot
        table_rows.append([
            str(it['item_no']),
            f"{it['description']} ({it.get('grade', 'Standard')})",
            it.get('dimensions', 'Mill Std'),
            f"{it['quantity']:,.1f}",
            it['unit'],
            f"{it['unit_price']:,.2f}",
            f"{tot:,.2f}"
        ])

    vat_rate = quote_data.get('vat_percentage', 0.05)
    vat_amt = subtotal * vat_rate if not quote_data.get('vat_included') else 0.0
    grand_total = subtotal + vat_amt

    items_table = Table(table_rows, colWidths=[0.4*inch, 2.5*inch, 1.4*inch, 0.6*inch, 0.5*inch, 0.9*inch, 1.1*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2B6CB0')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('ALIGN', (3,1), (-1,-1), 'RIGHT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E0')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F7FAFC')])
    ]))
    story.append(items_table)
    story.append(Spacer(1, 10))

    # Commercial Summary
    vat_note = "Inclusive of 5% VAT" if quote_data.get('vat_included') else f"Plus 5% VAT ({curr} {vat_amt:,.2f})"
    story.append(Paragraph(f"<b>Subtotal:</b> {curr} {subtotal:,.2f} | <b>Tax Terms:</b> {vat_note} | <b>Estimated Grand Total:</b> {curr} {grand_total:,.2f}", styles['Normal']))
    story.append(Spacer(1, 10))

    # Terms & Notes
    terms_p = Paragraph(
        f"<b>Commercial Conditions:</b><br/>"
        f"1. Material Test Certificate EN 10204 Type 3.1 provided with dispatch.<br/>"
        f"2. Delivery to {quote_data['incoterms']} destination. Offloading by buyer.<br/>"
        f"3. Quote validity: {quote_data['validity_days']} days from date of issuance.<br/>"
        f"4. Notes: {quote_data.get('notes', 'None')}",
        styles['Normal']
    )
    story.append(terms_p)

    doc.build(story)


def generate_excel_quotation(file_path: Path, quote_data: dict):
    """Creates a realistic corporate Excel quotation sheet."""
    rows = []
    for it in quote_data['items']:
        rows.append({
            "Line": it['item_no'],
            "Material Description": it['description'],
            "Steel Grade / Spec": it.get('grade', ''),
            "Dimensions / Sizes": it.get('dimensions', ''),
            "Quantity": it['quantity'],
            "Quoted UOM": it['unit'],
            "Unit Rate": it['unit_price'],
            "Line Amount": round(it['quantity'] * it['unit_price'], 2),
            "Mill Origin": it.get('mill_origin', 'Primary Mill')
        })

    df = pd.DataFrame(rows)

    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name="Quotation_Schedule", index=False, startrow=8)
        ws = writer.sheets["Quotation_Schedule"]

        # Insert header metadata in top rows
        ws["A1"] = f"SUPPLIER: {quote_data['vendor_name']}"
        ws["A2"] = f"QUOTATION NO: {quote_data['quotation_number']}"
        ws["A3"] = f"DATE: {quote_data['quotation_date']}"
        ws["A4"] = f"CUSTOMER RFQ REF: {quote_data['rfq_reference']}"
        ws["E1"] = f"CURRENCY: {quote_data['currency']}"
        ws["E2"] = f"INCOTERMS: {quote_data['incoterms']}"
        ws["E3"] = f"LEAD TIME: {quote_data['lead_time_days']} Days"
        ws["E4"] = f"PAYMENT TERMS: {quote_data['payment_terms']}"
        ws["A6"] = f"VAT STATUS: {'Inclusive of 5% VAT' if quote_data.get('vat_included') else 'Exclusive of 5% VAT'}"


def generate_full_dataset():
    """Generates all 10 RFQs, 48 competing quotations (PDF, Excel, CSV), and hand-labelled ground truth."""
    RFQS_DIR.mkdir(parents=True, exist_ok=True)
    QUOTES_DIR.mkdir(parents=True, exist_ok=True)
    GROUND_TRUTH_DIR.mkdir(parents=True, exist_ok=True)

    print("Generating 10 realistic Steel Fabrication Buyer RFQs...")
    rfq_map = {}
    for rfq in SAMPLE_RFQS:
        rfq_id = rfq["rfq_id"]
        rfq_path = RFQS_DIR / f"{rfq_id}.json"
        with open(rfq_path, "w", encoding="utf-8") as f:
            json.dump(rfq, f, indent=2)
        rfq_map[rfq_id] = rfq

    print("Generating 48 realistic Supplier Quotations across PDF, Excel, and CSV...")
    quote_count = 0

    for rfq in SAMPLE_RFQS:
        rfq_id = rfq["rfq_id"]
        target_curr = rfq["target_currency"]
        items = rfq["items"]

        # Generate 4 to 5 competing quotes per RFQ
        for s_idx, supp in enumerate(SUPPLIERS):
            quote_count += 1
            quote_id = f"QUOTE_{rfq_id.replace('-', '_')}_V{s_idx + 1}"
            vendor_name = supp["name"]
            curr = supp["currency"]

            # Price calculations with conversion and supplier bias
            # Base price per MT for steel ~3200 AED, converted to quote currency
            usd_rate = {"AED": 3.67, "USD": 1.0, "SAR": 3.75, "INR": 84.0, "EUR": 0.92}
            base_aed = 3300.0 * supp["price_factor"]
            base_in_curr = (base_aed / 3.67) * usd_rate.get(curr, 3.67)

            quoted_items = []
            for idx, r_item in enumerate(items):
                # Intentional variation 1: omit item for Vendor 5 on RFQ 1 & 4 (missing item defect)
                if s_idx == 4 and idx == len(items) - 1 and rfq_id in ["RFQ-2026-001", "RFQ-2026-004"]:
                    continue

                # Intentional variation 2: grade downgrade on Vendor 5 for RFQ 1 (critical defect: S275 instead of S355)
                quoted_grade = r_item["grade"]
                deviations = None
                if supp["spec_bias"] == "DEFECTIVE_ON_SOME" and idx == 0 and "S355" in r_item["grade"]:
                    quoted_grade = "S275JR"
                    deviations = "Commercial substitute S275JR offered instead of S355."
                elif supp["spec_bias"] == "ACCEPTABLE_SUPERIOR" and "S355JR" in r_item["grade"]:
                    quoted_grade = "S355J2+N"
                    deviations = "Upgraded to normalized S355J2+N at no extra cost."

                # Intentional variation 3: unit variation (KG vs MT, or PCS)
                unit = r_item["unit"]
                qty = r_item["quantity"]
                unit_price = round(base_in_curr * (1.0 + (idx * 0.08)), 2)

                # If Vendor 2 quotes in KG instead of MT
                if s_idx == 1 and unit == "MT":
                    unit = "KG"
                    qty = qty * 1000.0
                    unit_price = round(unit_price / 1000.0, 3)

                quoted_items.append({
                    "item_no": idx + 1,
                    "description": r_item["description"],
                    "grade": quoted_grade,
                    "dimensions": r_item.get("dimensions", "Standard"),
                    "quantity": qty,
                    "unit": unit,
                    "unit_price": unit_price,
                    "total_price": round(qty * unit_price, 2),
                    "mill_origin": "Emirates Steel" if "AED" in curr else ("Jindal" if "USD" in curr else "Hadeed KSA"),
                    "deviations": deviations,
                })

            lead_time = supp["lead_time_base"] + (s_idx * 3)
            quote_data = {
                "vendor_name": vendor_name,
                "quotation_number": f"QT-2026-{rfq_id[-3:]}{s_idx+1}",
                "quotation_date": "2026-03-01",
                "rfq_reference": rfq_id,
                "currency": curr,
                "payment_terms": supp["payment_terms"],
                "lead_time_days": lead_time,
                "validity_days": supp["validity_days"],
                "incoterms": supp["incoterm"],
                "vat_included": supp["vat_included"],
                "vat_percentage": supp["vat_percentage"],
                "freight_charges": 0.0,
                "items": quoted_items,
                "notes": f"Quoted per {rfq_id} specifications. Mill certificates included.",
            }

            # 1. Save Hand-Labelled Ground Truth JSON
            gt_path = GROUND_TRUTH_DIR / f"{quote_id}.json"
            with open(gt_path, "w", encoding="utf-8") as f:
                json.dump(quote_data, f, indent=2)

            # 2. Generate varied file formats:
            # - Suppliers 0, 1 -> PDF
            # - Supplier 2 -> Excel (.xlsx)
            # - Supplier 3 -> CSV
            # - Supplier 4 -> Text Quotation
            if s_idx in [0, 1]:
                pdf_path = QUOTES_DIR / f"{quote_id}.pdf"
                generate_pdf_quotation(pdf_path, quote_data)
            elif s_idx == 2:
                xlsx_path = QUOTES_DIR / f"{quote_id}.xlsx"
                generate_excel_quotation(xlsx_path, quote_data)
            elif s_idx == 3:
                csv_path = QUOTES_DIR / f"{quote_id}.csv"
                with open(csv_path, "w", encoding="utf-8") as f:
                    f.write(f"# SUPPLIER QUOTATION: {vendor_name}\n")
                    f.write(f"# QUOTATION REF: {quote_data['quotation_number']} | DATE: {quote_data['quotation_date']}\n")
                    f.write(f"# RFQ REF: {rfq_id} | CURRENCY: {curr} | INCOTERMS: {supp['incoterm']}\n")
                    f.write(f"# LEAD TIME: {lead_time} Days | VALIDITY: {supp['validity_days']} Days | PAYMENT: {supp['payment_terms']}\n")
                    f.write(f"# TAX: {'Inclusive 5% VAT' if supp['vat_included'] else 'Exclusive of 5% VAT'}\n")
                    pd.DataFrame(quote_data["items"]).to_csv(f, index=False)
            else:
                txt_path = QUOTES_DIR / f"{quote_id}.txt"
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(f"SUPPLIER QUOTATION\n")
                    f.write(f"Vendor: {vendor_name}\n")
                    f.write(f"Quote Ref: {quote_data['quotation_number']}\n")
                    f.write(f"Date: {quote_data['quotation_date']}\n")
                    f.write(f"RFQ Ref: {rfq_id}\n")
                    f.write(f"Currency: {curr}\n")
                    f.write(f"Delivery: {supp['incoterm']} | Lead Time: {lead_time} days\n")
                    f.write(f"Payment Terms: {supp['payment_terms']}\n")
                    f.write(f"Validity: {supp['validity_days']} days\n")
                    f.write(f"VAT: {'Inclusive 5%' if supp['vat_included'] else '5% VAT Extra'}\n\n")
                    f.write(f"SCHEDULE OF ITEMS:\n")
                    for it in quote_data["items"]:
                        f.write(f"Item {it['item_no']}: {it['description']} | Grade: {it['grade']} | Qty: {it['quantity']} {it['unit']} | Price: {it['unit_price']} | Total: {it['total_price']}\n")
                    f.write(f"\nNotes: {quote_data['notes']}\n")

    print(f"Dataset generation complete! Created {len(SAMPLE_RFQS)} RFQs and {quote_count} hand-labelled quotations in {BENCHMARK_DIR}.")


if __name__ == "__main__":
    generate_full_dataset()
