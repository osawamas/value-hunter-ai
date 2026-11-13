from official_http_v57 import get_pdf
"""Fail-closed S68 FY2026 issuer audited-PDF financial extraction (v44).

No static fixture is promoted unless all six Group figures are independently
read from the issuer PDF and match expected FY2026/FY2025 regression values.
Issuer disclosure is NOT independent third-party verification.
"""
import argparse
import hashlib
import json
import re
import urllib.request
from pathlib import Path

SOURCE = "https://investorrelations.sgx.com/static-files/3f7a49c0-fc5e-44fa-a851-bf26067249c5"
EXPECTED = {
    "revenue": (1559469, 1370625),
    "operating_profit": (887190, 742843),
    "attributable_profit": (698411, 647983),
    "assets": (4547470, 4143988),
    "liabilities": (2184488, 1944067),
    "equity": (2362982, 2199921),
}
ROW_LABELS = {
    "revenue": None,  # The income statement's total revenue is an unlabelled subtotal.
    "operating_profit": "operating profit",
    "attributable_profit": "equity holders of the company",
    "assets": "total assets",
    "liabilities": "total liabilities",
    "equity": "total equity",
}
NUMBER = re.compile(r"^[0-9][0-9,]*$")


def download(timeout=60):
    return get_pdf(SOURCE,max_bytes=25_000_000,timeout=timeout)


def ordered_rows(page, tolerance=2.6):
    """Group PDF words by visual Y row without assuming exact font spacing."""
    result = []
    for word in sorted(page.get_text("words"), key=lambda x: (x[1], x[0])):
        x0, y0, x1, y1, token, *_ = word
        mid = (y0 + y1) / 2
        if result and abs(result[-1]["y"] - mid) < tolerance:
            result[-1]["words"].append((x0, token))
        else:
            result.append({"y": mid, "words": [(x0, token)]})
    for row in result:
        row["words"].sort()
        row["text"] = " ".join(str(word) for _, word in row["words"])
        row["numbers"] = [int(word.replace(",", "")) for _, word in row["words"]
                          if NUMBER.fullmatch(str(word))]
    return result


def parse_pdf(raw):
    import fitz
    if not isinstance(raw, bytes) or not raw.startswith(b"%PDF"):
        raise ValueError("Invalid PDF")
    pdf = fitz.open(stream=raw, filetype="pdf")
    try:
        # Scope to financial statements rather than note tables later in the report.
        if len(pdf) < 12 or "Singapore Exchange Limited" not in pdf[0].get_text():
            raise ValueError("Unexpected audited financial document")
        metrics = {}
        for key, expected in EXPECTED.items():
            hits = []
            for index in range(min(len(pdf), 36)):
                page = pdf[index]
                heading = " ".join(page.get_text("text").lower().split())
                if not ("financial statements" in heading or "financial year ended" in heading
                        or "financial position" in heading):
                    continue
                for row in ordered_rows(page):
                    vals = row["numbers"]
                    if len(vals) < 2 or not any(tuple(vals[pos:pos+2]) == expected for pos in (0, 1)):
                        continue
                    label = ROW_LABELS[key]
                    # Some labels are wrapped on the preceding visual row.
                    if label is not None:
                        nearby = " ".join(r["text"] for r in ordered_rows(page)
                                          if -17 < r["y"] - row["y"] < 5).lower()
                        if label not in nearby:
                            continue
                    hits.append(index + 1)
            if len(hits) != 1:
                raise ValueError(f"Missing/ambiguous FY2026 Group row {key}: pages {hits}")
            metrics[key] = {
                year: {"value": amount, "page": hits[0],
                       "status": "EXTRACTED_ISSUER_PDF_REGRESSION_MATCHED"}
                for year, amount in zip(("2026", "2025"), expected)
            }
        for year in ("2026", "2025"):
            if (metrics["assets"][year]["value"] -
                metrics["liabilities"][year]["value"] != metrics["equity"][year]["value"]):
                raise ValueError("Group balance equation does not reconcile")
        return metrics
    finally:
        pdf.close()


def run(output, raw=None, verified_pdf_copy=None):
    record = {"symbol": "S68", "issuer": "Singapore Exchange Limited",
              "fiscal_year": 2026, "status": "NOT_VERIFIED",
              "source_kind": "LIVE_ISSUER_FY2026_PDF",
              "source_url": SOURCE, "pdf_sha256": None,
              "currency": "SGD", "unit": "SGD_thousands",
              "metrics": {}, "error": None, "independent_verification": False}
    try:
        data = download() if raw is None else raw
        record["pdf_sha256"] = hashlib.sha256(data).hexdigest()
        record["metrics"] = parse_pdf(data)
        record["status"] = "EXTRACTED_ISSUER_PDF_REGRESSION_MATCHED"
        if verified_pdf_copy is not None:
            Path(verified_pdf_copy).parent.mkdir(parents=True, exist_ok=True)
            Path(verified_pdf_copy).write_bytes(data)
    except Exception as exc:
        record["error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--offline-pdf")
    parser.add_argument("--verified-pdf-copy")
    options = parser.parse_args()
    result = run(options.output, Path(options.offline_pdf).read_bytes()
                 if options.offline_pdf else None, options.verified_pdf_copy)
    print(result["status"], result["error"])
    raise SystemExit(0 if result["status"] == "EXTRACTED_ISSUER_PDF_REGRESSION_MATCHED" else 1)
