"""G13 FY2025 Group balance sheet via SGX annual-report segment note.

Only accept exact Group/year columns and line items; arithmetic must reconcile
to independently extracted Group total equity from the same annual report.
Different pages of one issuer PDF are NOT independent third-party verification.
"""
import argparse
import hashlib
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SOURCE = "https://links.sgx.com/FileOpen/Annual%20Report%202025.ashx?App=Announcement&FileID=880160"
PAGE_INDEX = 61
NUMBER = re.compile(r"^(?:[0-9][0-9,]*|\([0-9][0-9,]*\))$")
LABELS = ("Consolidated total assets", "Consolidated total liabilities")


def amount(token):
    if not NUMBER.fullmatch(token):
        return None
    token = token.replace(",", "")
    return -int(token[1:-1]) if token.startswith("(") else int(token)


def rows(words, tolerance=2.1):
    # PDF text can place a label and its number in different text blocks.
    # Rebuild the visual row by y-coordinate, *inside one Group-year half*.
    result = []
    for word in sorted(words, key=lambda w: (float(w[1]), float(w[0]))):
        x0, y0, _, _, text, *_ = word
        y0 = float(y0)
        if result and abs(result[-1]["y"] - y0) <= tolerance:
            result[-1]["tokens"].append((float(x0), str(text)))
        else:
            result.append({"y": y0, "tokens": [(float(x0), str(text))]})
    return [" ".join(token for _, token in sorted(row["tokens"]))
            for row in result]


def extract_half(page, left, right, year):
    # Strictly restrict to one of the two Group year columns. A Company column
    # from the balance sheet cannot be accepted here.
    words = [word for word in page.get_text("words")
             if left <= (float(word[0]) + float(word[2])) / 2 < right]
    all_rows = rows(words)
    normalized = [" ".join(row.split()).lower() for row in all_rows]
    if "group" not in normalized or str(year) not in normalized:
        raise ValueError(f"Group {year} heading missing")
    text = " ".join(normalized)
    if "segment information" not in text:
        raise ValueError("Not an annual segment information table")
    extracted = {}
    for label in LABELS:
        found = []
        for row in all_rows:
            tokens = row.split()
            label_tokens = label.lower().split()
            if [token.lower() for token in tokens[:len(label_tokens)]] != label_tokens:
                continue
            rest = tokens[len(label_tokens):]
            if len(rest) != 1:
                continue
            val = amount(rest[0])
            if val is not None and val > 0:
                found.append({"value": val, "row": row})
        if len(found) != 1:
            raise ValueError(f"Ambiguous/missing {year} {label}: {len(found)} matches")
        extracted["assets" if label.endswith("assets") else "liabilities"] = found[0]
    return extracted


def parse_pdf(raw, equity_by_year, *, page_index=PAGE_INDEX):
    import fitz
    if not isinstance(raw, bytes) or not raw.startswith(b"%PDF"):
        raise ValueError("Invalid PDF")
    doc = fitz.open(stream=raw, filetype="pdf")
    try:
        if len(doc) <= page_index:
            raise ValueError("Annual report missing financial note page")
        page = doc[page_index]
        split = page.rect.width / 2
        periods = {
            "2025": extract_half(page, 0, split, 2025),
            "2024": extract_half(page, split, page.rect.width, 2024),
        }
        metrics = {"assets": {}, "liabilities": {}, "equity": {}}
        checks = {}
        for year, extracted in periods.items():
            equity = equity_by_year.get(year)
            if not isinstance(equity, int) or isinstance(equity, bool) or equity <= 0:
                raise ValueError(f"Original Group equity {year} not available")
            assets = extracted["assets"]["value"]
            liabilities = extracted["liabilities"]["value"]
            difference = assets - liabilities - equity
            if difference != 0:
                raise ValueError(f"Group balance equation mismatch {year}: {difference}")
            metrics["assets"][year] = {"value": assets, "status": "EXTRACTED_GROUP_SEGMENT_NOTE_ARITHMETIC_MATCHED",
                                       "page": page_index + 1}
            metrics["liabilities"][year] = {"value": liabilities, "status": "EXTRACTED_GROUP_SEGMENT_NOTE_ARITHMETIC_MATCHED",
                                            "page": page_index + 1}
            metrics["equity"][year] = {"value": equity, "status": "EXTRACTED_GROUP_FINANCIAL_POSITION"}
            checks[year] = {
                "assets_minus_liabilities_minus_equity": difference,
                "assets_row": extracted["assets"]["row"],
                "liabilities_row": extracted["liabilities"]["row"],
                "matched": True,
            }
        return {"metrics": metrics, "checks": checks, "page_pdf_number": page_index + 1,
                "scope": "Group only", "currency": "SGD", "unit": "SGD_thousands"}
    finally:
        doc.close()


def download(timeout=60):
    req = urllib.request.Request(SOURCE, headers={
        "User-Agent": "Mozilla/5.0 (VALUE-HUNTER-AI/0.42; issuer financial research)",
        "Accept": "application/pdf",
    })
    with urllib.request.urlopen(req, timeout=timeout) as response:
        data = response.read(35_000_001)
    if len(data) > 35_000_000 or not data.startswith(b"%PDF"):
        raise ValueError("Invalid or overlarge financial PDF")
    return data


def run(original_path, output, *, raw=None):
    original = json.loads(Path(original_path).read_text(encoding="utf-8"))
    if original.get("symbol") != "G13":
        raise ValueError("Not the G13 primary financial record")
    record = {
        "symbol": "G13",
        "status": "NOT_VERIFIED",
        "source_url": SOURCE,
        "pdf_sha256": None,
        "reference_type": "SAME_ANNUAL_REPORT_DIFFERENT_PAGES",
        "metrics": {},
        "error": None,
    }
    try:
        data = raw if raw is not None else download()
        sha = hashlib.sha256(data).hexdigest()
        record["pdf_sha256"] = sha
        if sha != original.get("pdf_sha256"):
            raise ValueError("Annual PDF differs from upstream v18 SHA256")
        src = original["data"]["balance"]["equity"]
        if src.get("scope") != "Group":
            raise ValueError("Upstream equity is not consolidated Group")
        equity_by_year = {str(y): point["value"] for y, point in src["periods"].items()}
        report = parse_pdf(data, equity_by_year)
        record.update(report)
        record["status"] = "EXTRACTED_GROUP_BALANCE_ARITHMETIC_MATCHED"
    except Exception as exc:
        record["error"] = f"{type(exc).__name__}: {str(exc)[:250]}"
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"g13_balance_status": record["status"], "error": record["error"]}))
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--original", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--offline-pdf")
    opts = parser.parse_args()
    raw = Path(opts.offline_pdf).read_bytes() if opts.offline_pdf else None
    run(opts.original, opts.output, raw=raw)


if __name__ == "__main__":
    main()
