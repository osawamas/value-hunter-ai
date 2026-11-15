#!/usr/bin/env python3
import importlib.util
import pathlib
p=pathlib.Path(__file__).resolve().with_name("replay-uob-issuer-pdf-v288.py")
spec=importlib.util.spec_from_file_location("uob_pdf_v288",p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
rec=m.get_source()
s="""UOB PERFORMANCE 9M26 9M25 YoY 3Q26 2Q26 QoQ 3Q25 YoY
Net interest income 6,900 7,009 (2) 2,278 2,297 (1) 2,265 1
Net profit 4,165 3,271 27 1,250 1,478 (15) 443 >100"""
x=m.check_text(s,rec)
assert x["exact_labeled_issuer_pdf_table_rows_match"]
assert x["labeled_table_checks"]=={"profit":True,"nii":True}
assert not x["ranking_eligible"]
for old,new in [
 ("Net interest income","Gross interest income"),
 ("6,900","6,901"),
 ("2,278","2,279"),
 ("Net profit","Before-tax profit"),
 ("4,165","4,166"),
 ("1,250","1,251")
]:
 z=m.check_text(s.replace(old,new),rec)
 assert not z["exact_labeled_issuer_pdf_table_rows_match"],old
print("v288 PASS: line-labelled 9M and 3Q numbers in UOB PDF required, no source/audit/ranking promotion")
