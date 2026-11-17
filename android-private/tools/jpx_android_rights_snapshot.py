"""Build the Android share-event snapshot from audited JPX originals."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from jpx_daily_probe import CODE
from jpx_daily_rights import read_daily_rights
from jpx_rights_sources import official_url
from jpx_share_basis import read_monthly_rights


def original(path, provenance):
    body = path.read_bytes()
    source = provenance["official_url"]
    if not official_url(source) or sha256(body).hexdigest() != provenance["sha256"]:
        raise ValueError(f"Original differs from the audited JPX file: {path.name}")
    return body, source


def snapshot(audit, directory, codes):
    months = {}
    notices = {}
    for key, provenance in sorted(audit["monthly_report_provenance"].items()):
        body, source = original(directory / f"rights-{key}.pdf", provenance)
        month, by_code = read_monthly_rights(body)
        if month.strftime("%Y-%m") != key:
            raise ValueError("The JPX monthly report does not match the audit month")
        months[key] = source
        for code in codes:
            for event in by_code.get(code, ()):
                notices[code, event.ex_on.isoformat()] = source
    for key, provenance in sorted(audit["daily_workbooks"].items()):
        name = key.replace("-", "") + ".xls"
        body, source = original(directory / name, provenance)
        _, by_code, _ = read_daily_rights(body, name)
        # A daily workbook provides positive evidence only. It does not add coverage.
        for code in codes:
            for event in by_code.get(code, ()):
                notices.setdefault((code, event.ex_on.isoformat()), source)
    return {
        "coveredCodes": sorted(codes),
        "monthlySources": months,
        "notices": [{"code": code, "exDay": day, "source": source}
                    for (code, day), source in sorted(notices.items())],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audit", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("codes", nargs="+")
    args = parser.parse_args()
    if any(not CODE.fullmatch(code) for code in args.codes):
        parser.error("Each code must be a four-character JPX security code")
    data = snapshot(json.loads(args.audit.read_text()), args.audit.parent, set(args.codes))
    args.output.write_text(json.dumps(data, indent=2) + "\n")


if __name__ == "__main__":
    main()
