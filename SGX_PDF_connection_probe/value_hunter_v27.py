"""Conservative live audit against separate issuer disclosure PDFs.

Fail closed: do not claim independent validation or enable investment ranking.
"""
import argparse
import csv
import hashlib
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SOURCES = {
    "G13": "https://links.sgx.com/FileOpen/2.%20GENS%20FY2025%20SGX%20Results%20Announcement.ashx?App=Announcement&FileID=875733",
    "S20": "https://links.sgx.com/1.0.0/corporate-announcements/4MEGIOQF57KJ8YNB/876892_20260227%202H2025%20Condensed%20interim%20FS.pdf",
}
LABELS = {
    "G13": {
        "revenue": [r"^revenue$"],
        "operating_profit": [r"^operating profit$"],
        "attributable_profit": [r"^net profit attributable to (?:ordinary shareholders|owners|equity holders)(?: of the company)?$"],
    },
    "S20": {
        "revenue": [r"^revenue$"],
        "attributable_profit": [r"^(?:profit|loss|profit/\(loss\)|\(loss\)/profit) attributable to (?:owners|equity holders|shareholders)(?: of the company)?$"],
    },
}
NUMBER = re.compile(r"^(?:\d[\d,]*|-\d[\d,]*|\(\d[\d,]*\))$")


def parse_amount(token):
    token = token.strip().replace(",", "")
    if not NUMBER.fullmatch(token):
        return None
    return -int(token[1:-1]) if token.startswith("(") else int(token)


def group_lines(words, tolerance=2.5):
    rows = []
    for word in sorted(words, key=lambda w: (w[1], w[0])):
        x, y, _, _, token, *_ = word
        if rows and abs(rows[-1]["y"] - y) <= tolerance:
            rows[-1]["tokens"].append((float(x), str(token)))
        else:
            rows.append({"y": float(y), "tokens": [(float(x), str(token))]})
    for row in rows:
        row["tokens"].sort()
        row["text"] = " ".join(t for _, t in row["tokens"])
    return rows


def find_year_columns(rows, row_index, symbol):
    """Select FY 2025/2024 columns, excluding interim columns and % change.

    S20 has both 6-month and 12-month columns. Select the LAST 2025/2024 pair
    ONLY when the full-year 12-month heading is present. Fail closed otherwise.
    """
    candidates = []
    for i in range(max(0, row_index - 35), row_index):
        years = [(x, int(token)) for x, token in rows[i]["tokens"]
                 if token in ("2025", "2024")]
        if symbol == "S20" and len(years) == 4:
            if [year for x, year in years] != [2025, 2024, 2025, 2024]:
                continue
            nearby = " ".join(row["text"].lower() for row in rows[max(0, i-9):i+1])
            if "12 months" not in nearby:
                continue
            candidates.append((i, {2025: years[2][0], 2024: years[3][0]}))
        elif symbol == "G13" and len(years) == 2 and {y for x, y in years} == {2025, 2024}:
            candidates.append((i, {year: x for x, year in years}))
    return candidates[-1] if candidates else None


def extract_from_rows(rows, symbol, metric):
    matches = []
    for index, row in enumerate(rows):
        numbers = [(x, value) for x, token in row["tokens"]
                   if (value := parse_amount(token)) is not None]
        if len(numbers) < 2:
            continue
        left = min(x for x, _ in numbers)
        label = " ".join(token for x, token in row["tokens"] if x < left).strip().lower()
        label = re.sub(r"\s+", " ", label)
        if symbol == "S20" and metric == "attributable_profit":
            if label != "owners of the company":
                continue
            nearby = " ".join(x["text"].lower() for x in rows[max(index-5, 0):index])
            if "attributable to" not in nearby:
                continue
        elif not any(re.fullmatch(pattern, label) for pattern in LABELS[symbol][metric]):
            continue
        header = find_year_columns(rows, index, symbol)
        if not header:
            continue
        _, columns = header
        chosen = {}
        for year, x in columns.items():
            ordered = sorted((abs(nx-x), nx, val) for nx, val in numbers)
            if len(ordered) < 2 or ordered[0][0] > 45:
                break
            chosen[year] = ordered[0]
        if len(chosen) != 2 or chosen[2025][1] == chosen[2024][1]:
            continue
        matches.append({
            "value": chosen[2025][2],
            "row": row["text"],
            "year_header": rows[header[0]]["text"],
            "y": row["y"],
            "year_x": columns[2025],
            "value_x": chosen[2025][1],
        })
    return (matches[0] if len(matches) == 1 else None, len(matches))


def extract_pdf(pdf_bytes, symbol):
    import fitz

    document = fitz.open(stream=pdf_bytes, filetype="pdf")
    result = {}
    # Source PDF is issuer's FY2025 official release, amounts are SGD thousands.
    # Constrain to issuer's full-year consolidated income statement, not notes.
    candidate_pages = [2] if symbol == "S20" else list(range(min(len(document), 20)))
    for metric in LABELS[symbol]:
        hits = []
        for page_index in candidate_pages:
            if page_index >= len(document):
                continue
            rows = group_lines(document[page_index].get_text("words"))
            hit, count = extract_from_rows(rows, symbol, metric)
            if hit:
                hits.append({"page": page_index + 1, **hit})
            elif count > 1:
                hits.append({"page": page_index + 1, "ambiguous_candidates": count})
        usable = [hit for hit in hits if "value" in hit]
        unique = len(usable) == 1 and len(hits) == 1
        result[metric] = {
            "status": "EXTRACTED_UNAMBIGUOUS" if unique else "AMBIGUOUS_OR_MISSING",
            "value": usable[0]["value"] if unique else None,
            "evidence": hits[:12],
            "diagnostics": {
                "pages_scanned": len(candidate_pages),
                "candidate_hits": len(hits),
                "extraction_reason": (
                    "one_coordinate_matched_row" if unique
                    else "multiple_candidate_rows" if hits
                    else "no_strict_label_and_year_header_pair"
                ),
            },
        }
    document.close()
    return result


def download_pdf(url, timeout=35):
    request = urllib.request.Request(url, headers={
        "User-Agent": "VALUE-HUNTER-AI/0.27 (public issuer disclosure research)",
        "Accept": "application/pdf",
    })
    with urllib.request.urlopen(request, timeout=timeout) as response:
        pdf = response.read(30_000_001)
    if len(pdf) > 30_000_000 or not pdf.startswith(b"%PDF"):
        raise ValueError("NOT_PDF_OR_TOO_LARGE")
    return pdf


def validate_s68_crosscheck(financials_by_symbol, path):
    """Cross-check one distinct SGX issuer annual PDF, not third-party validation."""
    evidence=json.loads(Path(path).read_text(encoding="utf-8"))
    if (evidence.get("symbol")!="S68" or
            evidence.get("status")!="SECOND_ISSUER_ANNUAL_REPORT_MATCHED" or
            not evidence.get("pdf_sha256") or not evidence.get("source_url")):
        raise ValueError("S68 second issuer PDF not verified")
    source=financials_by_symbol.get("S68") or {}
    if source.get("source_url")==evidence["source_url"] or source.get("pdf_sha256")==evidence["pdf_sha256"]:
        raise ValueError("S68 crosscheck is not a distinct document")
    checks=[]
    seen=set()
    for item in evidence.get("checks",[]):
        metric=item.get("metric")
        if metric not in ("revenue","attributable_profit") or metric in seen or item.get("year")!=2026:
            raise ValueError("Wrong/duplicated S68 reference metric")
        seen.add(metric)
        fin=(source.get("metrics",{}).get(metric,{}).get("2026") or {}).get("value")
        ref=item.get("reference_value")
        if not isinstance(ref,int) or fin!=ref or item.get("status")!="MATCH_LIVE_SECOND_ISSUER_DOCUMENT":
            raise ValueError(f"S68 issuer annual/reference mismatch {metric}")
        checks.append({"metric":metric,"year":2026,
                       "financial_value":fin,"reference_value":ref,
                       "status":"MATCH_LIVE_SECOND_ISSUER_DOCUMENT",
                       "reference_extraction":item.get("reference_extraction")})
    if seen!={"revenue","attributable_profit"}:
        raise ValueError("S68 issuer reference metrics incomplete")
    return {"symbol":"S68","url":evidence["source_url"],"pdf_sha256":evidence["pdf_sha256"],
            "reference_type":"SECOND_ISSUER_DOCUMENT_NOT_THIRD_PARTY",
            "status":"S68_ANNUAL_ISSUER_CROSSCHECK_MATCHED",
            "checks":checks,"investment_ranking_eligible":False}


def run(financials, output, fetch=download_pdf, s68_crosscheck_path=None):
    records = {record["symbol"]: record for record in financials.get("records", [])}
    result = {
        "schema_version": "v27_live_issuer_document_audit",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "reference_type": "LIVE_SECOND_ISSUER_DOCUMENT_NOT_THIRD_PARTY",
        "ranking_eligible_count": 0,
        "records": [],
    }
    for symbol, url in SOURCES.items():
        record = {
            "symbol": symbol, "url": url, "pdf_sha256": None,
            "checks": [], "error": None, "investment_ranking_eligible": False,
        }
        try:
            pdf = fetch(url)
            record["pdf_sha256"] = hashlib.sha256(pdf).hexdigest()
            extracted = extract_pdf(pdf, symbol)
            for metric, detail in extracted.items():
                entry = records.get(symbol, {}).get("metrics", {}).get(metric, {}).get("2025", {})
                actual = entry.get("value") if isinstance(entry, dict) else None
                reference = detail["value"]
                status = (
                    "MATCH_LIVE_SECOND_ISSUER_DOCUMENT" if reference is not None and actual == reference
                    else "MISMATCH" if reference is not None and actual is not None
                    else "NOT_VERIFIED"
                )
                record["checks"].append({
                    "metric": metric, "year": 2025,
                    "financial_value": actual, "reference_value": reference,
                    "status": status, "reference_extraction": detail,
                })
        except Exception as exc:
            record["error"] = f"{type(exc).__name__}: {str(exc)[:250]}"
        result["records"].append(record)
    if s68_crosscheck_path:
        result["records"].append(validate_s68_crosscheck(records,s68_crosscheck_path))
    else:
        result["records"].append({
            "symbol":"S68","status":"SECOND_ISSUER_DOCUMENT_NOT_VERIFIED",
            "investment_ranking_eligible":False,"checks":[],
        })
    directory = Path(output)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "audit_v27.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with (directory / "audit_v27.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=[
            "symbol", "metric", "year", "financial_value",
            "reference_value", "status", "pdf_sha256", "error",
        ])
        writer.writeheader()
        for record in result["records"]:
            for check in record.get("checks", []) or [{}]:
                writer.writerow({
                    "symbol": record["symbol"],
                    "pdf_sha256": record.get("pdf_sha256"),
                    "error": record.get("error"),
                    **{key: check.get(key) for key in (
                        "metric", "year", "financial_value", "reference_value", "status"
                    )},
                })
    print(json.dumps({
        "live_matched": sum(
            check["status"] == "MATCH_LIVE_SECOND_ISSUER_DOCUMENT"
            for record in result["records"] for check in record.get("checks", [])
        ),
        "ranking_eligible_count": 0,
        "download_errors": sum(bool(record.get("error")) for record in result["records"]),
    }))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--financials", required=True)
    parser.add_argument("--output", default="value_hunter_v27_results")
    parser.add_argument("--s68-crosscheck")
    args = parser.parse_args()
    financials = json.loads(Path(args.financials).read_text(encoding="utf-8"))
    run(financials, args.output, s68_crosscheck_path=args.s68_crosscheck)


if __name__ == "__main__":
    main()
