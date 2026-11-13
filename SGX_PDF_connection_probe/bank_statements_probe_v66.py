"""Discover FY2025 OCBC/UOB Group financial-statement pages, without values promotion.

No company-specific bank metrics are published until a period-, scope- and
arithmetic-validated parser is added. Respect 403/size limits.
"""
import argparse
import hashlib
import json
from pathlib import Path
from official_http_v57 import get_pdf

SOURCES={
    "O39":{
        "issuer":"Oversea-Chinese Banking Corporation Limited",
        "url":"https://www.ocbc.com/iwov-resources/sg/ocbc/gbc/pdf/investors/annual-reports/2025/2025-annual-report-en.pdf",
        "identity":("OCBC","Oversea-Chinese Banking")
    },
    "U11":{
        "issuer":"United Overseas Bank Limited",
        "url":"https://www.uobgroup.com/investor-relations/assets/pdfs/investor/annual/uob-annual-report-2025.pdf",
        "identity":("UOB","United Overseas Bank")
    }
}
CUES=("income statements","income statement","balance sheets",
      "balance sheet","financial position","statement of financial position",
      "consolidated income","total income","total assets",
      "equity attributable","net profit attributable")


def inspect(symbol,raw):
    import fitz
    config=SOURCES[symbol]
    if not isinstance(raw,bytes) or not raw.startswith(b"%PDF"):
        raise ValueError("Not a valid annual report PDF")
    doc=fitz.open(stream=raw,filetype="pdf")
    try:
        if len(doc)<35:raise ValueError("Annual PDF unexpectedly short")
        head=" ".join(doc[i].get_text("text") for i in range(min(40,len(doc)))).lower()
        if not any(identity.lower() in head for identity in config["identity"]):
            raise ValueError("Wrong issuer identity")
        candidates=[]
        for i,page in enumerate(doc):
            lines=page.get_text("text").splitlines()
            low=" ".join(lines).lower()
            if not ("2025" in low and "2024" in low):
                continue
            heads=[term for term in CUES[:7] if term in low]
            if not heads:continue
            near=[]
            for j,line in enumerate(lines):
                if any(term in line.lower() for term in CUES):
                    near.append(" | ".join(lines[max(0,j-1):min(len(lines),j+6)])[:300])
            candidates.append({"pdf_page_number":i+1,
                               "headings":heads,
                               "nearby_rows":near[:9]})
        return {"symbol":symbol,"issuer":config["issuer"],"status":"DIAGNOSTIC_ONLY",
                "source_url":config["url"],"pdf_pages":len(doc),
                "candidate_pages":candidates[:40],
                "figures_promoted":False,"investment_ranking_eligible":False}
    finally:
        doc.close()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--symbol",choices=tuple(SOURCES),required=True)
    parser.add_argument("--output",required=True)
    a=parser.parse_args()
    config=SOURCES[a.symbol]
    result={"symbol":a.symbol,"status":"NOT_VERIFIED","source_url":config["url"],
            "figures_promoted":False}
    try:
        pdf=get_pdf(config["url"],max_bytes=75_000_000,timeout=90)
        result=inspect(a.symbol,pdf)
        result["pdf_sha256"]=hashlib.sha256(pdf).hexdigest()
    except Exception as exc:
        result["error"]=f"{type(exc).__name__}: {str(exc)[:300]}"
    target=Path(a.output);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"symbol":a.symbol,"status":result["status"],
                      "pages":result.get("candidate_pages",[])[:18],
                      "error":result.get("error")},ensure_ascii=False)[:17000])


if __name__=="__main__":main()
