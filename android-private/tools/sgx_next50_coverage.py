"""Compare SGX candidates with the official October 2026 iEdge Next 50 table."""
from collections import defaultdict
from hashlib import sha256
import re
import subprocess
from urllib.request import Request, urlopen

REPORT_URL = (
    "https://links.sgx.com/FileOpen/SGX%20Monthly%20Statistics%20Report%20"
    "Update_Oct%202026.ashx?App=Announcement&FileID=911153"
)
MAX_REPORT = 4_000_000

# The directory uses these abbreviated trading names instead of the names in the PDF.
TRADING_NAMES = {
    "CapitaLand China Trust": "CapLand China T",
    "Centurion Accommodation Reit": "Cent Accom REIT",
    "Lendlease Global Commercial REIT": "Lendlease Reit",
    "NTT DC REIT": "NTT DC REIT USD",
    "Parkway Life Real Estate Investment Trust": "ParkwayLife Reit",
    "Sasseur Real Estate Investment Trust": "Sasseur Reit",
    "SIA Engineering Co Ltd": "SIA Engineering Company Limited",
    "Starhill Global REIT": "StarhillGbl Reit",
    "Suntec Real Estate Investment Trust": "Suntec Reit",
    "UI Boustead REIT": "UIBREIT",
}


def parse_constituents(text):
    pages = [page for page in text.split("\f") if re.search(r"(?m)^iEdge Singapore Next 50\s*$", page)]
    if len(pages) != 2 or any("SGX Monthly Market Statistics October 2026" not in page for page in pages):
        raise ValueError("expected both official October 2026 constituent pages")
    names = []
    for page in pages:
        match = re.search(r"(?m)^Constituent Name[ \t]+Closing Price[ \t]*$", page)
        if match is None:
            raise ValueError("constituent table header missing")
        rows = []
        for line in page[match.end():].splitlines():
            row = re.fullmatch(r"\s*(\S.*?)\s{2,}[0-9,]+\.[0-9]+\s*", line)
            if row:
                rows.append(row[1])
        if len(rows) != 25:
            raise ValueError("constituent page did not contain 25 rows")
        names.extend(rows)
    if len(set(names)) != 50:
        raise ValueError("duplicate index constituent name")
    return names


def normalized_name(name):
    without_suffixes = re.sub(r"\b(?:limited|ltd|corp|corporation|co|pte|bhd)\b", "", name.casefold())
    return re.sub(r"[^a-z0-9]", "", without_suffixes)


def compare_constituents(names, candidates, trading_names=TRADING_NAMES):
    by_name = defaultdict(list)
    for row in candidates.values():
        by_name[normalized_name(row["issuer"])].append(row)

    matches, missing, ambiguous = {}, [], []
    for name in names:
        rows = by_name[normalized_name(name)]
        if not rows and name in trading_names:
            rows = by_name[normalized_name(trading_names[name])]
        if not rows:
            missing.append(name)
        elif len({row["isin"] for row in rows}) != 1:
            ambiguous.append(name)
        else:
            matches[name] = sorted(row["symbol"] for row in rows)
    return {
        "constituent_count": len(names), "matched_count": len(matches),
        "missing_count": len(missing), "missing_names": missing, "ambiguous_names": ambiguous,
        "matches": matches,
    }


def fetch_pdf_layout(url, first_page, last_page):
    request = Request(url, headers={"Accept": "application/pdf"})
    with urlopen(request, timeout=25) as response:
        if response.geturl() != url:
            raise ValueError("unexpected reference PDF URL")
        body = response.read(MAX_REPORT + 1)
    if len(body) > MAX_REPORT or not body.startswith(b"%PDF-"):
        raise ValueError("invalid reference PDF")
    result = subprocess.run(
        ["pdftotext", "-layout", "-f", str(first_page), "-l", str(last_page), "-", "-"],
        input=body, capture_output=True, check=True, timeout=20,
    )
    return result.stdout.decode("utf-8"), sha256(body).hexdigest()


def verify_next50(candidates):
    layout, digest = fetch_pdf_layout(REPORT_URL, 11, 12)
    report = compare_constituents(parse_constituents(layout), candidates)
    return {"source_url": REPORT_URL, "pdf_sha256": digest, **report}
