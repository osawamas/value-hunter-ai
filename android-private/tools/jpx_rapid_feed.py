"""Publish date-scoped rapid-move exclusions from JPX's daily workbooks."""
import argparse
from datetime import date
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from jpx_rights_sources import DAILY_INDEX, daily_sources, page_links, rapid_exclusion_record


def refresh(output):
    with TemporaryDirectory(dir=output.parent) as staged:
        staging = Path(staged)
        releases, _, _ = daily_sources(page_links(DAILY_INDEX), staging)
        days = sorted(map(date.fromisoformat, releases))
        if not 2 <= len(days) <= 8:
            raise ValueError("Unexpected JPX rights catalog date count")
        pairs = [rapid_exclusion_record(before, after, releases, staging)
                 for before, after in zip(days, days[1:])]
        temporary = staging / output.name
        temporary.write_text(json.dumps({"intervals": pairs}, indent=2) + "\n", encoding="utf-8")
        temporary.replace(output)
    return len(pairs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    print(f"Verified JPX rapid comparison intervals: {refresh(parser.parse_args().output)}")
