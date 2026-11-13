"""v81: tests prevent mixing Q3, 9M and FY2025 prior year results."""
import unittest,tempfile
from pathlib import Path
import fitz
from bank_q3_yoy_v81 import COMPARISONS,SCHEMAS,parse_pdf,run

def fake(symbol,*,wrong_year=False,bad_prior=False,duplicate=False):
 config=SCHEMAS[symbol]
 doc=fitz.open()
 for _ in range(max(config["pages"].values())):doc.new_page(width=1400,height=1300)
 doc[0].insert_text((20,27),{"D05":"DBS","O39":"OCBC","U11":"UOB"}[symbol]+" results for third quarter 2026")
 for period,page_index in config["pages"].items():
  if period=="9M" and config["pages"]["Q3"]==config["pages"]["9M"]:continue
  if symbol=="D05":
   head=["3rd Qtr","2026","3rd Qtr","2024" if wrong_year else "2025","9 Mths","2026","9 Mths","2025"]
  elif symbol=="O39":
   head=["3Q26","3Q24" if wrong_year else "3Q25"] if period=="Q3" else ["9M26","9M24" if wrong_year else "9M25"]
  else:
   head=["9M26","9M25","3Q26","3Q24" if wrong_year else "3Q25"]
  lines=list(head)
  for key in ("total_income",COMPARISONS[symbol]["profit_key"]):
   label,q3,m9=config["rows"][key]
   q3previous=COMPARISONS[symbol]["prior"]["Q3"][key]
   m9previous=COMPARISONS[symbol]["prior"]["9M"][key]
   if bad_prior and key=="total_income":q3previous+=1
   if symbol=="D05":
    values=[q3,q3previous,0,q3,0,m9,m9previous,0]
   elif symbol=="O39":
    values=[q3,q3previous,0,q3,0] if period=="Q3" else [m9,m9previous,0]
   else:
    values=[m9,m9previous,0,q3,q3,0,q3previous,0]
   lines.extend([label,*[str(v) for v in values]])
   if duplicate and key=="total_income":lines.extend([label,*[str(v) for v in values]])
  for i,text in enumerate(lines):
   doc[page_index-1].insert_text((20,35+20*i),text,fontsize=9)
 raw=doc.tobytes();doc.close()
 return raw

class YoYTests(unittest.TestCase):
 def test_all_banks_quarter_and_nine_month_compared_only_to_same_period(self):
  for symbol in COMPARISONS:
   x=parse_pdf(symbol,fake(symbol))
   self.assertEqual(x["q3"]["duration"],"THREE_MONTHS")
   self.assertEqual(x["nine_months"]["duration"],"NINE_MONTHS_YTD")
   self.assertEqual(x["q3"]["period_start_2025"],"2025-07-01")
   self.assertEqual(x["nine_months"]["period_start_2025"],"2025-01-01")
   self.assertEqual(x["q3"]["prior_year"]["total_income"],COMPARISONS[symbol]["prior"]["Q3"]["total_income"])
   self.assertFalse(x["ranking_eligible"])
 def test_changed_historical_number_rejected(self):
  for symbol in COMPARISONS:
   with self.assertRaises(ValueError):parse_pdf(symbol,fake(symbol,bad_prior=True))
 def test_wrong_year_header_rejected(self):
  for symbol in COMPARISONS:
   with self.assertRaises(ValueError):parse_pdf(symbol,fake(symbol,wrong_year=True))
 def test_duplicate_rows_rejected(self):
  for symbol in COMPARISONS:
   with self.assertRaises(ValueError):parse_pdf(symbol,fake(symbol,duplicate=True))
 def test_invalid_pdf_not_verified(self):
  with tempfile.TemporaryDirectory() as tmp:
   record=run("O39",Path(tmp)/"yoy.json",raw=b"blocked")
   self.assertEqual(record["status"],"NOT_VERIFIED")
   self.assertIsNone(record["record"])

if __name__=="__main__":unittest.main()
