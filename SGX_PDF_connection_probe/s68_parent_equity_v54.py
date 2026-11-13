"""S68 FY2026 audited Group owner-equity reconciliation (official PDF p.27).

Read the *Group* columns of the section explicitly attributable to the
Company's equity holders. Verify the eleven component rows and both annual
totals. The issuer financial statement is not third-party financial verification.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
from s68_official_pdf_v44 import SOURCE, download

COMPONENTS = {
    "Share capital": (416656, 419198),
    "Capital reserve": (3989, 3989),
    "Treasury shares": (-51053, -33386),
    "Cash flow hedge reserve": (-1897, 3374),
    "Currency translation reserve": (-22124, -23493),
    "Fair value reserve": (47869, 100560),
    "Securities clearing fund reserve": (25000, 25000),
    "Derivatives clearing fund reserve": (34021, 34021),
    "Share-based payment reserve": (40580, 33493),
    "Retained profits": (1613473, 1524941),
    "Proposed dividends": (256468, 112224),
}
TOTALS = {"2026": 2362982, "2025": 2199921}


def fmt(value):
    return f"({abs(value):,})" if value < 0 else f"{value:,}"


def parse_pdf(raw):
    import fitz
    if not isinstance(raw, bytes) or not raw.startswith(b"%PDF"):
        raise ValueError("S68 parent equity source is not PDF")
    doc=fitz.open(stream=raw,filetype="pdf")
    try:
        if len(doc)<27 or "Singapore Exchange Limited" not in doc[0].get_text():
            raise ValueError("Issuer/report identity mismatch")
        page=doc[26]
        text=" ".join(page.get_text("text").split())
        lowercase=text.lower().replace("’","'")
        if not ("statement of financial position (continued)" in lowercase
                and "as at 30 june 2026" in lowercase
                and "group" in lowercase and "company" in lowercase
                and "capital and reserves attributable to the company's equity holders" in lowercase):
            raise ValueError("Parent attribution/report date/Group scope not explicit")
        section=text[text.lower().replace("’","'").index("capital and reserves attributable"):]
        if "Non-controlling interests" in section.split("Total equity")[0]:
            raise ValueError("Non-controlling interest line requires separate reconciliation")
        matched={}
        for label,expected in COMPONENTS.items():
            # Values immediately after the label, with optional numbered note.
            pattern=(re.escape(label)+r"\s+(?:\d{1,2}\s+)?"
                     +re.escape(fmt(expected[0]))+r"\s+"+re.escape(fmt(expected[1])))
            hits=list(re.finditer(pattern,section,re.I))
            if len(hits)!=1:
                raise ValueError(f"S68 Group parent-equity row missing/ambiguous: {label}, count={len(hits)}")
            matched[label]={"2026":expected[0],"2025":expected[1]}
        for ix,year in enumerate(("2026","2025")):
            total=sum(row[year] for row in matched.values())
            if total!=TOTALS[year]:
                raise ValueError(f"Owner components do not cross-foot {year}: {total}")
        if len(re.findall(r"Total equity\s+"+re.escape(fmt(TOTALS["2026"]))
                          +r"\s+"+re.escape(fmt(TOTALS["2025"])), section, re.I))!=1:
            raise ValueError("Group equity statement total missing/ambiguous")
        return {"symbol":"S68","fiscal_year":2026,
                "statement":"audited Group financial position",
                "attributable_to":"Company equity holders",
                "page_pdf_number":27,"currency":"SGD","unit":"SGD_thousands",
                "parent_equity":{"2026":TOTALS["2026"],"2025":TOTALS["2025"]},
                "components":matched,
                "reconciliation":"OWNER_COMPONENTS_EQUAL_GROUP_TOTAL_EQUITY"}
    finally:
        doc.close()


def run(output, raw=None):
    result={"symbol":"S68","source_url":SOURCE,"pdf_sha256":None,
            "status":"NOT_VERIFIED","record":None,"error":None,
            "independent_verification":False}
    try:
        data=download() if raw is None else raw
        result["pdf_sha256"]=hashlib.sha256(data).hexdigest()
        result["record"]=parse_pdf(data)
        result["status"]="AUDITED_ISSUER_GROUP_OWNER_COMPONENTS_RECONCILED"
    except Exception as exc:
        result["error"]=f"{type(exc).__name__}: {str(exc)[:300]}"
    dest=Path(output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return result


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True)
    p.add_argument("--offline-pdf")
    args=p.parse_args()
    rec=run(args.output,Path(args.offline_pdf).read_bytes() if args.offline_pdf else None)
    print(rec["status"],rec["error"])
    raise SystemExit(0 if rec["status"]=="AUDITED_ISSUER_GROUP_OWNER_COMPONENTS_RECONCILED" else 1)
