"""Compare SGX candidates with the FTSE Russell STI constituent PDF."""
from datetime import datetime
import re

from sgx_next50_coverage import compare_constituents, fetch_pdf_layout

STI_PDF_URL = (
    "https://research.ftserussell.com/analytics/factsheets/Home/"
    "DownloadConstituentsWeights/?indexdetails=STI"
)
TRADING_NAMES = {
    "CapitaLand Ascendas REIT": "CapLand Ascendas REIT",
    "CapitaLand Integrated Commercial Trust": "CapLand IntCom T",
    "Frasers Centrepoint Trust": "Frasers Cpt Tr",
    "Frasers Logistics & Commercial Trust": "Frasers L&C Tr",
    "Mapletree Industrial Trust": "Mapletree Ind Tr",
    "Mapletree Logistics Trust": "Mapletree Log Tr",
    "Mapletree Pan Asia Commercial Trust": "Mapletree PanAsia Com Tr",
    "Thai Beverage": "Thai Beverage Public Co Ltd",
    "Yangzijiang Shipbuilding Holdings (S Chip)": "Yangzijiang Shipbuilding (Holdings) Ltd.",
}


def parse_sti_pdf_layout(layout):
    lines = layout.splitlines()
    if not re.search(r"(?m)^STI\s+", layout) or "FTSE Russell Publications" not in layout:
        raise ValueError("expected an STI constituent PDF")
    dates = re.findall(r"Indicative Index Weight Data as at Closing on (\d{1,2} [A-Za-z]+ \d{4})", layout)
    headers = [index for index, line in enumerate(lines) if line.count("Constituent") == 3]
    if len(dates) != 1 or len(headers) != 1:
        raise ValueError("STI PDF date or three-column table header missing")
    as_of = datetime.strptime(dates[0], "%d %B %Y").date().isoformat()
    header = headers[0]
    starts = [match.start() for match in re.finditer("Constituent", lines[header])]
    slices = list(zip(starts, [*starts[1:], None]))
    groups = [[], [], []]
    for line in lines[header + 2:]:
        if line.startswith("Source:"):
            break
        for group, (start, end) in zip(groups, slices):
            cell = line[start:end].strip()
            if not cell:
                continue
            row = re.fullmatch(r"(.+?)\s{2,}<?[0-9]+(?:\.[0-9]+)?\s{2,}[A-Z][A-Z ]*", cell)
            if row:
                group.append(row[1])
            elif group and re.fullmatch(r"[A-Za-z][A-Za-z .()&-]*\)?", cell):
                group[-1] += " " + cell
            else:
                raise ValueError("unexpected content in STI constituent table")
    names = [name for group in groups for name in group]
    if len(names) != 30 or len(set(names)) != 30:
        raise ValueError("STI PDF did not contain 30 distinct constituents")
    return as_of, names


def verify_sti(candidates):
    layout, digest = fetch_pdf_layout(STI_PDF_URL, 1, 1)
    as_of, names = parse_sti_pdf_layout(layout)
    report = compare_constituents(names, candidates, TRADING_NAMES)
    return {"source_url": STI_PDF_URL, "source_as_of": as_of, "pdf_sha256": digest, **report}
