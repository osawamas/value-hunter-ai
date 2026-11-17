"""Check counter-code coverage against the SGX Q3 2026 property trust report."""
import re

from sgx_next50_coverage import fetch_pdf_layout

REPORT_URL = (
    "https://api2.sgx.com/sites/default/files/2026-10/SGX%20Research%20-%20"
    "SREIT%20%26%20Property%20Trusts%20Chartbook%20-%20Q3%202026%20-%20v3.pdf"
)
ROW = re.compile(r"^\s*([A-Z0-9][A-Z0-9 &^#./()-]+?)\s{2,}([A-Z0-9]{3,5})\s{2,}[A-Za-z]", re.M)


def parse_counter_codes(layout):
    pages = [page for page in layout.split("\f") if "Stock code" in page]
    if len(pages) != 2 or "Key Statistics for S-REITs & Property Trusts" not in pages[0]:
        raise ValueError("expected both property trust statistics pages")
    codes = {}
    for page in pages:
        if "data as of 30 September 2026" not in page:
            raise ValueError("unexpected property trust statistics date")
        for name, code in ROW.findall(page):
            if code in codes:
                raise ValueError(f"duplicate property trust counter: {code}")
            codes[code] = name.rstrip("^#")
    if len(codes) != 39:
        raise ValueError("expected 39 property trust counters")
    return codes


def verify_property_trusts(candidates):
    layout, digest = fetch_pdf_layout(REPORT_URL, 16, 17)
    codes = parse_counter_codes(layout)
    matched = {name: [code] for code, name in codes.items() if code in candidates}
    missing = {code: name for code, name in codes.items() if code not in candidates}
    return {
        "source_url": REPORT_URL, "source_as_of": "2026-09-30", "pdf_sha256": digest,
        "counter_count": len(codes), "matched_count": len(codes) - len(missing),
        "missing_count": len(missing), "missing_codes": sorted(missing), "matches": matched,
    }
