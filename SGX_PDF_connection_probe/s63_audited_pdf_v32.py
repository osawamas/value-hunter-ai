"""S63 audited 2025 annual-report extractor, strict 2025/2024 table columns.

Only consolidated statement pages are accepted. Numeric estimates are NEVER
backfilled from FY highlights, which can use adjusted base operating performance.
"""
import argparse
import hashlib
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PDF_URL = ("https://links.sgx.com/FileOpen/"
           "ST%20Engineering%20Annual%20Report%202025.ashx"
           "?App=Announcement&FileID=880328")
COMPANY = "Singapore Technologies Engineering Ltd"
N = re.compile(r"^(?:\d[\d,]*|-\d[\d,]*|\(\d[\d,]*\))$")
NOTE = re.compile(r"\s+[A-G]\d{1,2}$", re.I)
FIELDS = {
    "income": {
        "revenue": "Revenue",
        "operating_profit": "Profit from operations",
        "attributable_profit": "Shareholders of the Company",
        "profit_after_tax": "Profit after taxation",
        "minority_profit": "Non-controlling interests",
        "gross_profit": "Gross profit",
        "cost_of_sales": "Cost of sales",
    },
    "assets": {"assets": "Total assets"},
    "liabilities": {
        "liabilities": "Total liabilities",
        "equity": "Net assets",
        "parent_equity": "Equity attributable to owners of the Company",
        "minority_equity": "Non-controlling interests",
    },
}
CORE = ("revenue", "operating_profit", "attributable_profit", "assets",
        "liabilities", "equity", "parent_equity")


def amount(word):
    text = str(word).replace(",", "").strip()
    if not N.fullmatch(text):
        return None
    return -int(text[1:-1]) if text.startswith("(") else int(text)


def lines(words, tolerance=2.5):
    result = []
    for w in sorted(words, key=lambda x: (float(x[1]), float(x[0]))):
        x0, y0, x1, _y1, text = w[:5]
        if result and abs(result[-1]["y"] - float(y0)) <= tolerance:
            result[-1]["tokens"].append((float(x0), float(x1), str(text)))
        else:
            result.append({"y": float(y0), "tokens": [(float(x0), float(x1), str(text))]})
    for line in result:
        line["tokens"].sort()
        line["text"] = " ".join(v for a, b, v in line["tokens"])
    return result


def column_headers(rows, row_index):
    matches = []
    for index in range(max(0, row_index-55), row_index):
        row = rows[index]
        years = [(end, int(t)) for start, end, t in row["tokens"] if t in ("2025", "2024")]
        if len(years) == 2 and {y for x, y in years} == {2025, 2024}:
            # Restrict to the table's upper quarter: narrative date references
            # and note descriptions aren't valid period column labels.
            matches.append((index, {year: x for x, year in years}))
    return matches[-1] if matches else None


def extract_row(rows, label, *, require_context=None):
    candidates = []
    for idx, row in enumerate(rows):
        nums = [(x1, amount(token)) for x0, x1, token in row["tokens"]
                if amount(token) is not None]
        if len(nums) < 2:
            continue
        first_number_x = min(x1 for x1, value in nums)
        left_text = " ".join(token for x0, x1, token in row["tokens"]
                             if x1 < first_number_x).strip()
        left_text = NOTE.sub("", left_text).strip()
        if left_text.casefold() != label.casefold():
            continue
        if require_context:
            recent = " ".join(x["text"].casefold() for x in rows[max(0, idx-10):idx])
            if require_context.casefold() not in recent:
                continue
        header = column_headers(rows, idx)
        if not header:
            continue
        year_row, anchor = header
        chosen = {}
        for year in (2025, 2024):
            ordered = sorted((abs(x-anchor[year]), x, v) for x, v in nums)
            if not ordered or ordered[0][0] > 55:
                break
            chosen[year] = ordered[0]
        if len(chosen) != 2 or chosen[2025][1] == chosen[2024][1]:
            continue
        candidates.append({
            "periods": {str(year): chosen[year][2] for year in (2025, 2024)},
            "label_row": row["text"],
            "header_row": rows[year_row]["text"],
            "row_y": round(row["y"], 2),
        })
    if len(candidates) != 1:
        raise ValueError(f"Missing/ambiguous consolidated row: {label}, count={len(candidates)}")
    return candidates[0]


def select_page(doc, kind):
    patterns = {
        "income": ("CONSOLIDATED INCOME STATEMENT", "Profit from operations", "Revenue"),
        "assets": ("CONSOLIDATED STATEMENT OF FINANCIAL POSITION", "Total assets"),
        "liabilities": ("CONSOLIDATED STATEMENT OF FINANCIAL POSITION",
                        "Equity attributable to owners of the Company", "Total liabilities"),
    }
    found = []
    page_required_labels = {
        "income": ["Revenue", "Profit from operations", "Shareholders of the Company"],
        "assets": ["Total assets"],
        "liabilities": ["Total liabilities", "Net assets",
                        "Equity attributable to owners of the Company",
                        "Non-controlling interests"],
    }
    for n, page in enumerate(doc):
        text = " ".join(page.get_text("text").upper().split())
        if not all(pattern.upper() in text for pattern in patterns[kind]):
            continue
        # Annual-report TOC pages can contain all these words but no financial
        # table. Require the exact row and 2025/2024 coordinate evidence.
        rows = lines(page.get_text("words"))
        try:
            for label in page_required_labels[kind]:
                extract_row(rows, label)
        except ValueError:
            continue
        found.append(n)
    if len(found) != 1:
        raise ValueError(f"Consolidated {kind} statement table pages ambiguous: {found}")
    return found[0]


def parse_document(data):
    import fitz
    if not isinstance(data, bytes) or not data.startswith(b"%PDF"):
        raise ValueError("Not a PDF file")
    doc = fitz.open(stream=data, filetype="pdf")
    try:
        pages = {kind: select_page(doc, kind) for kind in FIELDS}
        extracted = {}
        evidence = {}
        for kind, names in FIELDS.items():
            page_index = pages[kind]
            page = doc[page_index]
            page_text = " ".join(page.get_text("text").upper().split())
            if not all(t in page_text for t in ("2025", "2024", "GROUP")):
                raise ValueError(f"Missing period/group scope on {kind} page")
            rows = lines(page.get_text("words"))
            for field, label in names.items():
                evidence[field] = {
                    **extract_row(rows, label, require_context="Attributable to:"
                                  if field == "attributable_profit" else None),
                    "page_pdf_index": page_index,
                    "page_pdf_number": page_index+1,
                    "scope": "Group",
                    "unit": "SGD_thousands",
                    "source_url": PDF_URL,
                }
                extracted[field] = evidence[field]["periods"]
        checks = {}
        for yr in ("2025", "2024"):
            checks[yr] = {
                "balance_difference": (extracted["assets"][yr] -
                                       extracted["liabilities"][yr] -
                                       extracted["equity"][yr]),
                "profit_attribution_difference": (extracted["profit_after_tax"][yr] -
                                                  extracted["attributable_profit"][yr] -
                                                  extracted["minority_profit"][yr]),
                "equity_attribution_difference": (extracted["equity"][yr] -
                                                  extracted["parent_equity"][yr] -
                                                  extracted["minority_equity"][yr]),
                "gross_profit_difference": (extracted["revenue"][yr] +
                                            extracted["cost_of_sales"][yr] -
                                            extracted["gross_profit"][yr]),
            }
        if any(value != 0 for ch in checks.values() for value in ch.values()):
            raise ValueError(f"Consolidated financial statements fail arithmetic: {checks}")
        metrics = {}
        for key in CORE:
            metrics[key] = {
                year: {
                    "value": value,
                    "status": "EXTRACTED_AUDITED_ISSUER_PDF_ARITHMETIC_MATCHED",
                    "page": evidence[key]["page_pdf_number"],
                }
                for year, value in extracted[key].items()
            }
        return {
            "schema_version": "s63_audited_pdf_v32",
            "status": "EXTRACTED_AUDITED_ISSUER_PDF_ARITHMETIC_MATCHED",
            "source_url": PDF_URL, "pdf_sha256": hashlib.sha256(data).hexdigest(),
            "page_indices": pages, "financial_checks": checks,
            "evidence": evidence,
            "record": {
                "symbol": "S63", "issuer": COMPANY, "fiscal_year": 2025,
                "source_kind": "LIVE_S63_AUDITED_ANNUAL_REPORT_V32",
                "source_url": PDF_URL,
                "pdf_sha256": hashlib.sha256(data).hexdigest(),
                "metrics": metrics,
            },
        }
    finally:
        doc.close()


def fetch(timeout=90):
    request = urllib.request.Request(
        PDF_URL, headers={"User-Agent": "Mozilla/5.0 (ValueHunterAI audit)",
                          "Accept": "application/pdf,*/*"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = response.read(35_000_001)
    if len(data) > 35_000_000 or not data.startswith(b"%PDF"):
        raise ValueError("S63 source was not a valid PDF or exceeded 35MB")
    return data


def run(output, *, document=None):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        parsed = parse_document(document if document is not None else fetch())
        parsed["fetched_at_utc"] = datetime.now(timezone.utc).isoformat()
    except Exception as exc:
        parsed = {"schema_version": "s63_audited_pdf_v32",
                  "status": "NOT_VERIFIED",
                  "source_url": PDF_URL,
                  "record": None,
                  "error": f"{type(exc).__name__}: {str(exc)[:350]}"}
    output.write_text(json.dumps(parsed, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"symbol": "S63", "status": parsed["status"],
                      "error": parsed.get("error")}, ensure_ascii=False))
    return parsed


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    run(args.output)
