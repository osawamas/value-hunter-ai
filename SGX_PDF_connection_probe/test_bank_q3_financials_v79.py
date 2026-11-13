"""v79: fail-closed period schema and real-PDF regression fixtures."""
import tempfile,unittest
from pathlib import Path
import fitz
from bank_q3_financials_v79 import SCHEMAS,parse_pdf,run

def fixture(symbol,*,bad_q3=False,bad_9m=False,wrong_year=False,duplicate=False):
 schema=SCHEMAS[symbol]
 pdf=fitz.open()
 for _ in range(max(schema["pages"].values())):pdf.new_page(width=1200,height=1500)
 pdf[0].insert_text((20,30),("DBS" if symbol=="D05" else "OCBC" if symbol=="O39" else "UOB")+" 3Q 2026 report")
 for period,page_num in schema["pages"].items():
  page=pdf[page_num-1]
  if symbol=="D05":
   header=["3rd Qtr","2025" if wrong_year else "2026","9 Mths","2026"]
  elif symbol=="O39":
   header=["Third Quarter 2026 Performance","3Q26","3Q25"] if period=="Q3" else ["Nine Months 2026 Performance","9M26","9M25"]
   if wrong_year:header=[s.replace("2026","2024").replace("26","24") for s in header]
  else:
   header=["9M26","9M25","3Q26","3Q25"]
   if wrong_year:header=["9M24","9M25","3Q24","3Q25"]
  data=list(header)
  for key,(label,q3,nine) in schema["rows"].items():
   q3value=q3+(1 if bad_q3 and key=="total_income" else 0)
   mvalue=nine+(1 if bad_9m and key=="total_income" else 0)
   if symbol=="D05":values=[q3value,q3value,0,q3value,0,mvalue,mvalue,0]
   elif symbol=="O39":
    values=[q3value,q3value,0,q3value,0] if period=="Q3" else [mvalue,mvalue,0]
   else:values=[mvalue,mvalue,0,q3value,q3value,0,q3value,0]
   def fmt(v):return f"({abs(v):,})" if v<0 else f"{v:,}"
   if symbol=="D05" or symbol=="U11":
    if period=="9M" and schema["pages"]["Q3"]==schema["pages"]["9M"]:continue
   data.extend([label,*[fmt(v) for v in values]])
   if duplicate and key=="total_income":data.extend([label,*[fmt(v) for v in values]])
  for i,line in enumerate(data):page.insert_text((20,35+i*19),line,fontsize=9)
 raw=pdf.tobytes();pdf.close()
 return raw

class QuarterlyPeriodTests(unittest.TestCase):
 def test_three_bank_periods_separated(self):
  for symbol in SCHEMAS:
   result=parse_pdf(symbol,fixture(symbol))
   self.assertEqual(result["Q3"]["duration"],"THREE_MONTHS")
   self.assertEqual(result["9M"]["duration"],"NINE_MONTHS_YTD")
   self.assertEqual(result["Q3"]["period_start"],"2026-07-01")
   self.assertEqual(result["9M"]["period_start"],"2026-01-01")
   self.assertEqual(result["Q3"]["metrics"]["total_income"],SCHEMAS[symbol]["rows"]["total_income"][1])
   self.assertEqual(result["9M"]["metrics"]["total_income"],SCHEMAS[symbol]["rows"]["total_income"][2])
   self.assertFalse(result["ranking_eligible"])
 def test_wrong_quarter_income_fails(self):
  for symbol in SCHEMAS:
   with self.assertRaises(ValueError):parse_pdf(symbol,fixture(symbol,bad_q3=True))
 def test_wrong_nine_month_income_fails(self):
  for symbol in SCHEMAS:
   with self.assertRaises(ValueError):parse_pdf(symbol,fixture(symbol,bad_9m=True))
 def test_wrong_year_fails(self):
  for symbol in SCHEMAS:
   with self.assertRaises(ValueError):parse_pdf(symbol,fixture(symbol,wrong_year=True))
 def test_ambiguous_row_fails(self):
  for symbol in SCHEMAS:
   with self.assertRaises(ValueError):parse_pdf(symbol,fixture(symbol,duplicate=True))
 def test_invalid_pdf_never_published(self):
  with tempfile.TemporaryDirectory() as d:
   rec=run("D05",Path(d)/"x.json",raw=b"not-pdf")
   self.assertEqual(rec["status"],"NOT_VERIFIED")
   self.assertIsNone(rec["record"])

if __name__=="__main__":unittest.main()
