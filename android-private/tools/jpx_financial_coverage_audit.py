"""Audit issuer-PDF manifest coverage against a private JPX code universe.

Inputs are local JSON, not uploaded prices or verified financial statements.
Universe: ["1234", "5678"] or {"codes": ["1234", "5678"]}.
Manifest: [{"code": "1234", "url": "...", "sha256": "..."}].
Acquisition report: {"sources": [{"code": "1234", "status": "downloaded"}]}.
No source acquisition or financial validation is performed here.
"""
import argparse
import json
from pathlib import Path
import re

CODE = re.compile(r"[0-9]{4}[0-9A-Z]?\Z")


def read_codes(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(value, dict):
        value = value.get("codes")
    if not isinstance(value, list) or any(not isinstance(x, str) or not CODE.fullmatch(x) for x in value):
        raise ValueError("Universe must be a JSON array of valid JPX codes")
    if len(value) != len(set(value)):
        raise ValueError("Universe contains duplicate codes")
    return set(value)


def audit(universe, manifest, report=None):
    if not isinstance(manifest, list) or any(not isinstance(x, dict) or
                                             not isinstance(x.get("code"), str) or
                                             not CODE.fullmatch(x["code"]) for x in manifest):
        raise ValueError("Invalid source manifest")
    sourced = {x["code"] for x in manifest}
    # Reports must correspond to the exact original in the manifest, not just
    # another PDF from the same issuer. This prevents stale or unrelated
    # acquisition records from inflating coverage.
    manifest_sources = {(x["code"], x.get("sha256")) for x in manifest}
    if len(manifest_sources) != len(manifest):
        raise ValueError("Duplicate source identity in manifest")
    if any(not isinstance(x.get("sha256"), str) or
           not re.fullmatch(r"[0-9a-f]{64}", x["sha256"]) for x in manifest):
        raise ValueError("Manifest must contain source SHA256")
    acquired = set()
    failed = set()
    acquired_sources = set()
    failed_sources = set()
    attempted_sources = set()
    if report is not None:
        sources = report.get("sources") if isinstance(report, dict) else None
        if not isinstance(sources, list):
            raise ValueError("Invalid acquisition report")
        for item in sources:
            if (not isinstance(item, dict) or
                    (item.get("code"), item.get("sha256")) not in manifest_sources):
                raise ValueError("Report contains a source not in manifest")
            source_identity = (item["code"], item["sha256"])
            if source_identity in attempted_sources:
                raise ValueError("Duplicate acquisition result for the same original PDF")
            attempted_sources.add(source_identity)
            status = item.get("status")
            if status in ("cached", "downloaded"):
                acquired.add(item["code"])
                acquired_sources.add(source_identity)
            elif status == "failed":
                failed.add(item["code"])
                failed_sources.add(source_identity)
            else:
                raise ValueError("Unknown acquisition status")
    attempted_codes = acquired | failed
    unattempted_sources = manifest_sources - attempted_sources
    # Count missing originals per issuer, without exporting private PDF URLs or prices.
    unattempted_source_counts_by_code = {
        code: sum(source_code == code for source_code, _ in unattempted_sources)
        for code in sorted(universe)
        if any(source_code == code for source_code, _ in unattempted_sources)
    }
    # One exclusive reason per issuer. Acquiring a PDF never grants notification
    # eligibility; financial and corporate-action checks happen downstream.
    hold_reasons = {}
    for code in sorted(universe):
        if code not in sourced:
            reason = "manifest_missing"
        elif code in acquired and code in failed:
            reason = "partial_acquisition_failure"
        elif code in failed:
            reason = "acquisition_failed"
        elif code not in attempted_codes:
            reason = "acquisition_not_attempted"
        elif code in acquired and any((item["code"] == code and
                (item["code"], item["sha256"]) not in attempted_sources)
                for item in manifest):
            reason = "source_acquisition_incomplete"
        else:
            reason = "financial_and_corporate_actions_unverified"
        hold_reasons[code] = reason
    hold_reason_counts = {reason: sum(value == reason for value in hold_reasons.values())
                          for reason in sorted(set(hold_reasons.values()))}
    assert sum(hold_reason_counts.values()) == len(universe)
    return {
        "market": "JP",
        "hold_reasons_by_code": hold_reasons,
        "hold_reason_counts": hold_reason_counts,
        "universe_count": len(universe),
        "manifest_source_records": len(manifest),
        "manifest_codes_in_universe": len(sourced & universe),
        "missing_manifest_codes": sorted(universe - sourced),
        "manifest_codes_outside_universe": sorted(sourced - universe),
        "acquired_codes_in_universe": len(acquired & universe),
        "unattempted_manifest_codes_in_universe": sorted((sourced & universe) - attempted_codes),
        "unattempted_manifest_code_count": len((sourced & universe) - attempted_codes),
        "acquisition_attempted_source_count": len(attempted_sources),
        "acquired_source_count": len(acquired_sources),
        "failed_source_count": len(failed_sources),
        "unattempted_source_counts_by_code": unattempted_source_counts_by_code,
        "failed_codes_in_universe": len(failed & universe),
        "failed_only_codes": sorted((failed - acquired) & universe),
        "mixed_acquisition_codes": sorted((acquired & failed) & universe),
        "acquired_only_codes": sorted((acquired - failed) & universe),
        "unattempted_manifest_source_count": len(manifest_sources - attempted_sources),
        "mixed_acquisition_codes_in_universe": len(acquired & failed & universe),
        "financial_verified_count": 0,
        "notification_eligible_count": 0,
        "note": "Acquired PDF is not verified finance; zero means not assessed, not no eligible stocks.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("universe", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--acquisition-report", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    universe = read_codes(args.universe)
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    report = json.loads(args.acquisition_report.read_text(encoding="utf-8")) if args.acquisition_report else None
    result = audit(universe, manifest, report)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
