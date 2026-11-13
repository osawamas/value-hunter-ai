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
    "G13": "https://gentingsingapore.listedcompany.com/newsroom/20260224_173326_G13_A7CVA3KL4JFGECGT.3.pdf",
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
        "attributable_profit": [r"^(?:profit|loss|profit/\\(loss\\)|\\(loss\\)/profit) attributable to (?:owners|equity holders|shareholders)(?: of the company)?$"],
    },
}
NUMBER = re.compile(r"^\\(?-?\\d[\\d,]*\\)?$")


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


def find_year_columns(rows, row_index):
    options = []
    for index in range(max(0, row_index - 28), row_index):
        years = [(x, int(token)) for x, token in rows[index]["tokens"] if token in ("2025", "2024")]
        if len(years) == 2 and {year for _, year in years} == {2025, 2024}:
            options.append((index, {year: x for x, year in years}))
    return options[-1] if options else None


def extract_from_rows(rows, symbol, metric):
    matches = []
    for index, row in enumerate(rows):
        numeric = [(x, parse_amount(token)) for x, token in row["tokens"] if parse_amount(token) is not None]
        if len(numeric) < 2:
            continue
        label = " ".join(token for x, token in row["tokens"] if x < min(nx for nx, _ in numeric)).strip().lower()
        label = re.sub(r"\\s+", " ", label)
        if not any(re.fullmatch(pattern, label) for pattern in LABELS[symbol][metric]):
            continue
        header = find_year_columns(rows, index)
        if not header:
            continue
        _, columns = header
        assigned = {}
        for year, x in columns.items():
            ordered = sorted((abs(nx - x), nx, value) for nx, value in numeric)
            if not ordered or (len(ordered) > 1 and abs(ordered[0][0] - ordered[1][0]) < 5):
                break
            assigned[year] = ordered[0]
        if len(assigned) != 2 or assigned[2025][1] == assigned[2024][1]:
            continue
        matches.append({
            "value": assigned[2025][2],
            "row": row["text"],
            "year_header": rows[header[0]]["text"],
            "y": row["y"],
            "year_x": columns[2025],
            "value_x": assigned[2025][1],
        })
    return (matches[0] if len(matches) == 1 else None, len(matches))


def extract_pdf(pdf_bytes, symbol):
    import fitz

    document = fitz.open(stream=pdf_bytes, filetype="pdf")
    result = {}
    for metric in LABELS[symbol]:
        hits = []
        for page_index in range(len(document)):
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
        }
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


def run(financials, output, fetch=download_pdf):
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
    result["records"].append({
        "symbol": "S68", "status": "HISTORICAL_FIXED_FIXTURE_NOT_VERIFIED",
        "investment_ranking_eligible": False, "checks": [],
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
    args = parser.parse_args()
    financials = json.loads(Path(args.financials).read_text(encoding="utf-8"))
    run(financials, args.output)


if __name__ == "__main__":
    main()
