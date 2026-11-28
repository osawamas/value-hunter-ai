"""Cross-check Hachiquant annual inputs against FSA EDINET filing records and CSV."""
import csv
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import io
import json
import re
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener
from zipfile import BadZipFile, ZipFile

BASE = "https://api.edinet-fsa.go.jp/api/v2/documents"
SUMMARY = "jpcrp_cor:"
EPS = SUMMARY + "BasicEarningsLossPerShareSummaryOfBusinessResults"
BPS = SUMMARY + "NetAssetsPerShareSummaryOfBusinessResults"
SHARES = SUMMARY + "TotalNumberOfIssuedSharesSummaryOfBusinessResults"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def download(path, query, key, limit):
    request = Request(BASE + path + "?" + urlencode(query),
                      headers={"Subscription-Key": key})
    with build_opener(NoRedirect()).open(request, timeout=10) as response:
        if response.geturl() != request.full_url:
            raise ValueError("EDINET changed the source URL")
        body = response.read(limit + 1)
    if len(body) > limit:
        raise ValueError("EDINET response exceeds size limit")
    return body


def metadata_matches(rows, code, doc_id, period_end, filed_on):
    matches = [row for row in rows if row.get("docID") == doc_id]
    if len(matches) != 1:
        return False
    row = matches[0]
    posted = datetime.fromisoformat(row["submitDateTime"]).date().isoformat()
    return (row.get("secCode") == code + "0" and row.get("periodEnd") == period_end
            and posted == filed_on and row.get("docTypeCode") == "120"
            and row.get("withdrawalStatus") == "0" and row.get("disclosureStatus") == "0"
            and row.get("csvFlag") == "1")


def facts_from_csv(body):
    facts = {}
    with ZipFile(io.BytesIO(body)) as archive:
        files = [item for item in archive.infolist() if re.fullmatch(
            r"XBRL_TO_CSV/jpcrp030000-asr-[^/]+\.csv", item.filename)]
        if len(files) != 1 or files[0].file_size > 16_000_000:
            raise ValueError("EDINET annual CSV is missing or exceeds size limit")
        with archive.open(files[0]) as raw, io.TextIOWrapper(raw, encoding="utf-16", newline="") as stream:
            rows = csv.DictReader(stream, delimiter="\t")
            if not {"要素ID", "コンテキストID", "ユニットID", "値"} <= set(rows.fieldnames or []):
                raise ValueError("EDINET annual CSV lacks required columns")
            for row in rows:
                tag, context = row["要素ID"], row["コンテキストID"]
                duration = tag == EPS and context in (
                    "CurrentYearDuration", "CurrentYearDuration_NonConsolidatedMember")
                instant = tag in (BPS, SHARES) and context in (
                    "CurrentYearInstant", "CurrentYearInstant_NonConsolidatedMember")
                if not duration and not instant:
                    continue
                expected = "Shares" if tag == SHARES else "JPYPerShares"
                if row["ユニットID"] != expected:
                    continue
                value = row["値"]
                if not value or not re.fullmatch(r"-?[0-9]{1,16}(?:\.[0-9]{1,10})?", value):
                    continue
                facts.setdefault((tag, context), set()).add(Decimal(value))
    return facts


def compare(metrics, facts):
    matches = 0
    for suffix in ("", "_NonConsolidatedMember"):
        eps = facts.get((EPS, "CurrentYearDuration" + suffix), set())
        bps = facts.get((BPS, "CurrentYearInstant" + suffix), set())
        if eps == {metrics.get("eps")} and bps == {metrics.get("bvps")}:
            matches += 1
    shares = set().union(*(facts.get((SHARES, "CurrentYearInstant" + suffix), set())
                           for suffix in ("", "_NonConsolidatedMember")))
    return {
        "per_share_facts_match": matches == 1,
        "original_period_end_share_count_present": len(shares) == 1 and all(
            value > 0 and value == value.to_integral_value() for value in shares),
    }


class EdinetAudit:
    def __init__(self, key):
        self.key = key
        self.days = {}
        self.next_request = 0.0

    def request(self, path, query, limit):
        time.sleep(max(0, self.next_request - time.monotonic()))
        self.next_request = time.monotonic() + 1.25
        return download(path, query, self.key, limit)

    def check(self, filing, row):
        filed_on = filing["actual_filing_date"]
        code = filing["code"]
        doc_id = filing["annual_source_id"]
        if not re.fullmatch(r"S[0-9A-Z]{7}", doc_id):
            raise ValueError("Unexpected EDINET document identifier")
        if filed_on not in self.days:
            listing = json.loads(self.request(".json", {"date": filed_on, "type": 2}, 4_000_000))
            self.days[filed_on] = listing["results"]
        if not metadata_matches(self.days[filed_on], code, doc_id, row["period_end"], filed_on):
            return {"filing_metadata_match": False}
        matched = next(item for item in self.days[filed_on] if item.get("docID") == doc_id)
        try:
            duration = (date.fromisoformat(row["period_end"]) - date.fromisoformat(matched["periodStart"])).days + 1
        except (KeyError, TypeError, ValueError):
            duration = 0
        try:
            facts = facts_from_csv(self.request("/" + doc_id, {"type": 5}, 8_000_000))
            return {"filing_metadata_match": True, "full_year_verified": 350 <= duration <= 380,
                    **compare(row["metrics"], facts)}
        except HTTPError as error:
            if error.code in (401, 403, 429, 503):
                raise
            return {"filing_metadata_match": True, "original_csv_unverified": True}
        except (ValueError, InvalidOperation, OSError, KeyError, BadZipFile):
            return {"filing_metadata_match": True, "original_csv_unverified": True}
