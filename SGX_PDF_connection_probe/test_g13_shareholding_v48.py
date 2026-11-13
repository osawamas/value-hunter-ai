"""G13 half-year treasury count must balance two independent arithmetic equations."""
import tempfile
import unittest
from pathlib import Path
import fitz
from g13_shareholding_v48 import parse_pdf,run


def document(*, wrong_treasury=False, wrong_net=False, wrong_period=False):
    doc=fitz.open()
    a=doc.new_page(width=1100,height=950)
    b=doc.new_page(width=1100,height=950)
    lines_a=[
       "11. SHARE CAPITAL AND TREASURY SHARES",
       "As at 30 June 2025, the number of ordinary shares in issue was 12,094,026,824 of which 30,384,550 were held by the Company as treasury shares" if wrong_period else
       "As at 30 June 2026, the number of ordinary shares in issue was 12,094,026,824 of which "+("30,384,551" if wrong_treasury else "30,384,550")+" were held by the Company as treasury shares",
       "As at 30 June 2026, total number of issued shares (excluding treasury shares) was "+
         ("12,063,642,275" if wrong_net else "12,063,642,274"),
    ]
    lines_b=[
      "11. SHARE CAPITAL AND TREASURY SHARES (CONTINUED)",
      "The movement in the Company's treasury shares during the six months period ended 30 June 2026:",
      "As at 1 January 2026 8,121,350",
      "Independent Non-Executive Directors of the Company (500,000)",
      "Employees of the Company (1,171,444)",
      "Employees of a subsidiary of the Company (5,895,556)",
      "Repurchase of shares 29,830,200",
      "As at 30 June 2026 30,384,550",
    ]
    for page, lines in [(a,lines_a),(b,lines_b)]:
        for i,line in enumerate(lines):
            page.insert_text((20,35+i*45),line,fontsize=9)
    raw=doc.tobytes()
    doc.close()
    return raw


class G13ShareholdingTests(unittest.TestCase):
    def test_exact_share_and_treasury_reconciliation(self):
        x=parse_pdf(document())
        self.assertEqual(x["shares_outstanding"],12063642274)
        self.assertEqual(x["treasury_shares"],30384550)
        self.assertEqual(x["treasury_rollforward"]["repurchased"],29830200)
        self.assertEqual(x["as_of_date"],"2026-06-30")
    def test_incorrect_net_rejected(self):
        with self.assertRaises(ValueError):parse_pdf(document(wrong_net=True))
    def test_incorrect_treasury_rejected(self):
        with self.assertRaises(ValueError):parse_pdf(document(wrong_treasury=True))
    def test_period_anchor_required(self):
        with self.assertRaises(ValueError):parse_pdf(document(wrong_period=True))
    def test_failure_does_not_promote_shares(self):
        with tempfile.TemporaryDirectory() as t:
            x=run(Path(t)/"bad.json",raw=b"broken")
            self.assertEqual(x["status"],"NOT_VERIFIED")
            self.assertIsNone(x["snapshot"])

if __name__=="__main__":
    unittest.main()
