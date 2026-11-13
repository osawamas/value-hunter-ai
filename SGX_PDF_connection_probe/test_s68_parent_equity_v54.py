"""v54 S68 audited parent-equity scope and cross-foot tests."""
import unittest
import fitz
from s68_parent_equity_v54 import COMPONENTS, TOTALS, parse_pdf


def sample(*, wrong_amount=False, nci=False, bad_heading=False):
    pdf=fitz.open()
    for _ in range(27):
        pdf.new_page(width=1100,height=900)
    pdf[0].insert_text((20,30),"Singapore Exchange Limited")
    lines=[
        "Statement of financial position (continued)",
        "As at 30 June 2026",
        "Group Company 2026 2025",
        "Capital and reserves attributable to the Company's equity holders"
           if not bad_heading else "Company only equity",
    ]
    for label,(a,b) in COMPONENTS.items():
        def fmt(v):
            return f"({-v:,})" if v<0 else f"{v:,}"
        first=a+(1 if wrong_amount and label=="Share capital" else 0)
        lines.append(f"{label} {fmt(first)} {fmt(b)}")
    if nci:lines.append("Non-controlling interests 100 200")
    lines.append("Total equity 2,362,982 2,199,921")
    page=pdf[26]
    for idx,line in enumerate(lines):
        page.insert_text((20,25+25*idx),line,fontsize=10)
    raw=pdf.tobytes()
    pdf.close()
    return raw


class OwnerEquityTests(unittest.TestCase):
    def test_valid_owner_component_reconciliation(self):
        record=parse_pdf(sample())
        self.assertEqual(record["parent_equity"],TOTALS)
        self.assertEqual(record["page_pdf_number"],27)
        self.assertEqual(record["reconciliation"],"OWNER_COMPONENTS_EQUAL_GROUP_TOTAL_EQUITY")
    def test_bad_component_rejected(self):
        with self.assertRaises(ValueError):parse_pdf(sample(wrong_amount=True))
    def test_nci_requires_separate_reconciliation(self):
        with self.assertRaises(ValueError):parse_pdf(sample(nci=True))
    def test_missing_owner_scope_rejected(self):
        with self.assertRaises(ValueError):parse_pdf(sample(bad_heading=True))

if __name__=="__main__":unittest.main()
