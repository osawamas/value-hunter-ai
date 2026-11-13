"""S68 FY2026/2025 annual report cross-check against issuer results PDF.

Evidence from a second issuer document is not independent third-party verification.
"""
import argparse
import hashlib
import json
import re
import urllib.request
from pathlib import Path

SOURCE="https://links.sgx.com/FileOpen/2026%20SGX%20Annual%20Report.ashx?App=Announcement&FileID=905317"
TARGET={
    "revenue": {"label":"operating revenue","2026":1559469,"2025":1370625},
    "attributable_profit":{"label":"equity holders of the company","2026":698411,"2025":647983},
}
NUM=re.compile(r"^[0-9][0-9,]*$")


def download(timeout=75):
    req=urllib.request.Request(SOURCE,headers={"User-Agent":"Mozilla/5.0 (VALUE-HUNTER-AI cross-doc audit)"})
    with urllib.request.urlopen(req,timeout=timeout) as resp:
        b=resp.read(45_000_001)
    if not b.startswith(b"%PDF") or len(b)>45_000_000:raise ValueError("Invalid annual PDF")
    return b


def rows(words):
    groups=[]
    for word in sorted(words,key=lambda x:(x[1],x[0])):
        x,y,_,_,txt,*_=word
        if groups and abs(y-groups[-1]["y"])<=2.5:
            groups[-1]["tokens"].append((x,txt))
        else: groups.append({"y":y,"tokens":[(x,txt)]})
    for row in groups:
        row["tokens"].sort()
        row["text"]=" ".join(str(t) for _,t in row["tokens"])
        row["numbers"]=[int(t.replace(",","")) for x,t in row["tokens"] if NUM.fullmatch(str(t))]
    return groups


def parse_pdf(raw):
    import fitz
    if not isinstance(raw,bytes) or not raw.startswith(b"%PDF"):raise ValueError("Invalid PDF")
    doc=fitz.open(stream=raw,filetype="pdf")
    try:
        matches={key:[] for key in TARGET}
        for idx,page in enumerate(doc):
            full=" ".join(page.get_text("text").lower().split())
            if not ("statement of comprehensive income" in full
                    and "financial year ended 30 june 2026" in full):
                continue
            if "group" not in full or "2025" not in full or "2026" not in full:
                continue
            for row in rows(page.get_text("words")):
                label=" ".join(row["text"].lower().split())
                for metric,spec in TARGET.items():
                    values=row["numbers"]
                    pair=[spec["2026"],spec["2025"]]
                    if spec["label"] not in label:continue
                    if not any(values[j:j+2]==pair for j in range(max(0,len(values)-1))):
                        continue
                    matches[metric].append({"page_pdf_number":idx+1,
                        "row":row["text"],"2026":spec["2026"],"2025":spec["2025"]})
        for metric,hits in matches.items():
            if len(hits)!=1:
                raise ValueError(f"Annual report {metric} not unique on consolidated income statement: {len(hits)}")
        return matches
    finally:
        doc.close()


def run(output,raw=None):
    data={"symbol":"S68","status":"NOT_VERIFIED","source_url":SOURCE,
          "pdf_sha256":None,"checks":[],"error":None,
          "reference_type":"SECOND_ISSUER_DOCUMENT_NOT_THIRD_PARTY"}
    try:
        pdf=download() if raw is None else raw
        data["pdf_sha256"]=hashlib.sha256(pdf).hexdigest()
        rows_by_metric=parse_pdf(pdf)
        data["checks"]=[{"metric":metric,"year":2026,
            "status":"MATCH_LIVE_SECOND_ISSUER_DOCUMENT",
            "reference_value":hits[0]["2026"],
            "reference_extraction":{"status":"EXTRACTED_UNAMBIGUOUS","evidence":hits}}
                for metric,hits in rows_by_metric.items()]
        data["status"]="SECOND_ISSUER_ANNUAL_REPORT_MATCHED"
    except Exception as exc:
        data["error"]=f"{type(exc).__name__}: {str(exc)[:300]}"
    dest=Path(output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return data


if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--output",required=True)
    a.add_argument("--offline-pdf")
    opts=a.parse_args()
    r=run(opts.output,Path(opts.offline_pdf).read_bytes() if opts.offline_pdf else None)
    print(r["status"],r["error"])
    raise SystemExit(0 if r["status"]=="SECOND_ISSUER_ANNUAL_REPORT_MATCHED" else 1)
