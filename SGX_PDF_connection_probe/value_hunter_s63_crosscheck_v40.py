"""v40: S63 cross-check of REPORTED FY2025 income against a second issuer PDF.

Reject BOP/adjusted, 2H and percentage columns. This is cross-document
issuer corroboration, never an independent third-party verification.
"""
import argparse
import hashlib
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SOURCE = ("https://www.stengg.com/getmedia/"
          "636a7ee6-a8b8-4200-870f-09c626cfbec2/"
          "ST-Engineering-FY2025-Results-Financial-Statements.pdf")
LABELS = {
    "revenue": "Revenue",
    "operating_profit": "Profit from operations",
    "attributable_profit": "Shareholders of the Company",
}
AMOUNT = re.compile(r"^(?:\d[\d,]*|-\d[\d,]*|\(\d[\d,]*\))$")


def amount(text):
    text = str(text).strip()
    if not AMOUNT.fullmatch(text):
        return None
    clean = text.replace(",", "")
    return -int(clean[1:-1]) if clean.startswith("(") else int(clean)


def rows_from_words(words, tolerance=2.4):
    rows = []
    for w in sorted(words, key=lambda x: (float(x[1]), float(x[0]))):
        x, y, text = float(w[0]), float(w[1]), str(w[4])
        if rows and abs(rows[-1]["y"] - y) <= tolerance:
            rows[-1]["tokens"].append((x, text))
        else:
            rows.append({"y": y, "tokens": [(x, text)]})
    for row in rows:
        row["tokens"].sort()
        row["text"] = " ".join(token for _, token in row["tokens"])
    return rows


def extract_reported(rows, page_text):
    heading = re.sub(r"\s+", " ", page_text.upper())
    if ("CONSOLIDATED INCOME STATEMENT" not in heading
            or "2025" not in heading or "REPORTED" not in heading):
        raise ValueError("Not a FY2025 reported consolidated income statement")
    if "BASE OPERATING PERFORMANCE" in heading[:500] or "UNAUDITED" in heading[:500]:
        raise ValueError("BOP or unaudited scope in reported page heading")

    headers = []
    for i, row in enumerate(rows):
        positions = {value.upper(): x for x, value in row["tokens"]
                     if value.upper() in ("2H2025", "2H2024", "FY2025", "FY2024")}
        if set(positions) == {"2H2025", "2H2024", "FY2025", "FY2024"}:
            if not positions["2H2025"] < positions["2H2024"] < positions["FY2025"] < positions["FY2024"]:
                continue
            headers.append((i, positions))
    if len(headers) != 1:
        raise ValueError("Ambiguous/missing 2H and FY column headings")

    header_idx, columns = headers[0]
    evidence = {}
    for field, label in LABELS.items():
        matches = []
        for i, row in enumerate(rows[header_idx + 1:], header_idx + 1):
            numbers = [(x, amount(token)) for x, token in row["tokens"]
                       if amount(token) is not None]
            if len(numbers) < 4:
                continue
            first = min(x for x, _ in numbers)
            left = " ".join(word for x, word in row["tokens"] if x < first)
            if re.sub(r"\s+", " ", left).strip().casefold() != label.casefold():
                continue
            if field == "attributable_profit":
                near = " ".join(r["text"].lower() for r in rows[max(header_idx, i-7):i])
                if "attributable to" not in near:
                    continue
            chosen = {}
            for year in (2025, 2024):
                column = columns["FY" + str(year)]
                nearby = sorted((abs(x-column), x, val) for x, val in numbers)
                if not nearby or nearby[0][0] > 38:
                    break
                chosen[year] = nearby[0]
            if len(chosen) == 2 and chosen[2025][1] != chosen[2024][1]:
                matches.append({"value": chosen[2025][2], "prior_year": chosen[2024][2],
                                "row": row["text"], "year_header": rows[header_idx]["text"]})
        if len(matches) != 1:
            raise ValueError(f"Missing/ambiguous REPORTED FY2025 {field}, rows={len(matches)}")
        evidence[field] = matches[0]
    return evidence


def from_pdf(data):
    import fitz
    if not isinstance(data, bytes) or not data.startswith(b"%PDF"):
        raise ValueError("Response is not PDF")
    document = fitz.open(stream=data, filetype="pdf")
    try:
        # PDF 1st page is contents; 2nd page is reported FY table.
        if len(document) < 2:
            raise ValueError("PDF missing reported income page")
        page = document[1]
        rows = rows_from_words(page.get_text("words"))
        found = extract_reported(rows, page.get_text("text"))
        return {name: dict(entry, page_pdf_number=2, currency="SGD",
                           unit="SGD_thousands", scope="Group REPORTED",
                           fiscal_year=2025) for name, entry in found.items()}
    finally:
        document.close()


def download(timeout=35):
    request = urllib.request.Request(SOURCE, headers={
        "User-Agent": "Mozilla/5.0 VALUE-HUNTER-AI/0.40 (public financial disclosures)",
        "Accept": "application/pdf",
    })
    with urllib.request.urlopen(request, timeout=timeout) as stream:
        data = stream.read(25_000_001)
    if len(data) > 25_000_000:
        raise ValueError("PDF exceeds 25MB limit")
    return data


def compare(financials, pdf_bytes):
    result = {
        "symbol": "S63",
        "url": SOURCE,
        "reference_type": "LIVE_SECOND_ISSUER_DOCUMENT_NOT_THIRD_PARTY",
        "pdf_sha256": None,
        "checks": [],
        "error": None,
        "investment_ranking_eligible": False,
    }
    try:
        if pdf_bytes is None:
            raise ValueError("PDF download not available")
        result["pdf_sha256"] = hashlib.sha256(pdf_bytes).hexdigest()
        reference = from_pdf(pdf_bytes)
        lookup = {row["symbol"]: row for row in financials.get("records", [])}
        original = lookup.get("S63", {})
        if original.get("fiscal_year") != 2025:
            raise ValueError("S63 original fiscal year not exactly 2025")
        for key, evidence in reference.items():
            entry = original.get("metrics", {}).get(key, {}).get("2025", {})
            original_value = entry.get("value") if isinstance(entry, dict) else None
            check = ("MATCH_LIVE_SECOND_ISSUER_DOCUMENT" if original_value == evidence["value"]
                     else "MISMATCH" if isinstance(original_value, int) else "NOT_VERIFIED")
            result["checks"].append({
                "metric": key,
                "year": 2025,
                "financial_value": original_value,
                "reference_value": evidence["value"],
                "status": check,
                "reference_extraction": {
                    "status": "EXTRACTED_UNAMBIGUOUS",
                    "value": evidence["value"],
                    "evidence": [{"page": evidence["page_pdf_number"],
                                  "row": evidence["row"],
                                  "year_header": evidence["year_header"]}],
                },
            })
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {str(exc)[:250]}"
    return result


def join(audit, s63):
    result = dict(audit)
    rows = [row for row in result.get("records", []) if row.get("symbol") != "S63"]
    rows.append(s63)
    result["records"] = rows
    result["s63_cross_check_version"] = "v40_reported_only"
    result["ranking_eligible_count"] = 0
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--financials", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--offline-pdf", help="Optional local PDF used in regression tests")
    args = parser.parse_args()
    finances = json.loads(Path(args.financials).read_text(encoding="utf-8"))
    original = json.loads(Path(args.audit).read_text(encoding="utf-8"))
    try:
        pdf = Path(args.offline_pdf).read_bytes() if args.offline_pdf else download()
        checked = compare(finances, pdf)
    except Exception as exc:
        checked = {
            "symbol": "S63", "url": SOURCE,
            "reference_type": "LIVE_SECOND_ISSUER_DOCUMENT_NOT_THIRD_PARTY",
            "pdf_sha256": None, "checks": [],
            "error": f"{type(exc).__name__}: {str(exc)[:250]}",
            "investment_ranking_eligible": False,
        }
    combined = join(original, checked)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(combined, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"s63_pdf_error": checked["error"],
                      "s63_matched": sum(c["status"] == "MATCH_LIVE_SECOND_ISSUER_DOCUMENT"
                                         for c in checked.get("checks", [])),
                      "ranking_eligible_count": 0}))


if __name__ == "__main__":
    main()
