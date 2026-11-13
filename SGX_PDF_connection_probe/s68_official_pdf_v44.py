"""S68 FY2026 issuer PDF financial extraction. Reject ambiguous rows and mismatches.

Issuer-issued statements are not independent third-party verification.
"""
import argparse
import hashlib
import json
import re
import urllib.request
from pathlib import Path

SOURCE = "https://investorrelations.sgx.com/static-files/dcbd5905-9373-4dc9-80f5-8dbff6b8d584"
YEARS = ("2026", "2025")
SPEC = {
    "revenue": (8, "Operating revenue", (1559469, 1370625)),
    "operating_profit": (8, "Operating profit", (887190, 742843)),
    "attributable_profit": (8, "Equity holders of the Company", (698411, 647983)),
    "assets": (12, "Total assets", (4547470, 4143988)),
    "liabilities": (12, "Total liabilities", (2184488, 1944067)),
    "equity": (12, "Total equity", (2362982, 2199921)),
}
NUMBER = re.compile(r"^[0-9][0-9,]*$")


def download(timeout=60):
    request = urllib.request.Request(SOURCE, headers={
        "User-Agent": "Mozilla/5.0 (VALUE-HUNTER-AI financial research)",
        "Accept": "application/pdf",
    })
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read(20_000_001)
    if len(raw) > 20_000_000 or not raw.startswith(b"%PDF"):
        raise ValueError("S68 source not a valid size-limited PDF")
    return raw


def extract_row(page, label, page_number):
    """Read the two FY amounts from the Group columns on the known report page."""
    w = float(page.rect.width)
    hits = [rect for rect in page.search_for(label)
            if rect.x0 < 0.72 * w and (page_number != 8 or rect.y0 < 0.60 * page.rect.height)]
    candidates = []
    for rect in hits:
        middle_y = (rect.y0 + rect.y1) / 2
        words = [word for word in page.get_text("words")
                 if 0.71 * w <= (word[0] + word[2]) / 2 < 0.98 * w
                 and abs((word[1] + word[3]) / 2 - middle_y) <= 4
                 and NUMBER.fullmatch(str(word[4]))]
        # Income statement has a third numeric column for YoY changes.
        words.sort(key=lambda word: word[0])
        amounts = [int(word[4].replace(",", "")) for word in words[:2]]
        if len(amounts) == 2:
            candidates.append(tuple(amounts))
    if len(candidates) != 1:
        raise ValueError(f"Ambiguous Group row '{label}' at PDF page {page_number}: {len(candidates)}")
    return candidates[0]


def parse_pdf(raw):
    import fitz
    if not isinstance(raw, bytes) or not raw.startswith(b"%PDF"):
        raise ValueError("Invalid PDF")
    pdf = fitz.open(stream=raw, filetype="pdf")
    try:
        if len(pdf) <= 12:
            raise ValueError("Missing FY2026 financial pages")
        income = " ".join(pdf[8].get_text().lower().split())
        balance = " ".join(pdf[12].get_text().lower().split())
        if ("income statement - group" not in income or
                "statement of financial position - group" not in balance or
                "30 june 2026" not in balance):
            raise ValueError("Unexpected issuer report layout/scope/period")
        metrics = {}
        for key, (page_index, label, expected) in SPEC.items():
            actual = extract_row(pdf[page_index], label, page_index)
            if actual != expected:
                raise ValueError(f"FY2026 regression mismatch {key}: {actual} vs {expected}")
            metrics[key] = {
                year: {"value": value, "page": page_index + 1,
                       "status": "EXTRACTED_ISSUER_PDF_REGRESSION_MATCHED"}
                for year, value in zip(YEARS, actual)
            }
        for year in YEARS:
            a, l, e = (metrics[k][year]["value"]
                       for k in ("assets", "liabilities", "equity"))
            if a - l != e:
                raise ValueError(f"Group balance equation mismatch {year}")
        return metrics
    finally:
        pdf.close()


def run(output, raw=None):
    result = {"symbol": "S68", "issuer": "Singapore Exchange Limited",
              "status": "NOT_VERIFIED", "source_url": SOURCE,
              "source_kind": "LIVE_ISSUER_FY2026_PDF",
              "pdf_sha256": None, "fiscal_year": 2026,
              "currency": "SGD", "unit": "SGD_thousands",
              "metrics": {}, "error": None,
              "independent_verification": False}
    try:
        data = download() if raw is None else raw
        result["pdf_sha256"] = hashlib.sha256(data).hexdigest()
        result["metrics"] = parse_pdf(data)
        result["status"] = "EXTRACTED_ISSUER_PDF_REGRESSION_MATCHED"
    except Exception as exc:
        result["error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--offline-pdf")
    args = parser.parse_args()
    result = run(args.output, Path(args.offline_pdf).read_bytes()
                 if args.offline_pdf else None)
    print(result["status"], result["error"])
    raise SystemExit(0 if result["status"] == "EXTRACTED_ISSUER_PDF_REGRESSION_MATCHED" else 1)
