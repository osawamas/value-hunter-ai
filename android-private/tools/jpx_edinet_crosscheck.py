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
REPORT_PERIOD_END = "jpdei_cor:CurrentPeriodEndDateDEI"
SHARES = SUMMARY + "TotalNumberOfIssuedSharesSummaryOfBusinessResults"
PER_SHARE_PAIRS = (
    (EPS, BPS),
    (SUMMARY + "BasicEarningsLossPerShareIFRSSummaryOfBusinessResults",
     SUMMARY + "EquityToAssetRatioIFRSSummaryOfBusinessResults"),
    (SUMMARY + "BasicEarningsLossPerShareUSGAAPSummaryOfBusinessResults",
     SUMMARY + "EquityAttributableToOwnersOfParentPerShareUSGAAPSummaryOfBusinessResults"),
)
EPS_TAGS = {eps for eps, _ in PER_SHARE_PAIRS}
BPS_TAGS = {bps for _, bps in PER_SHARE_PAIRS}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def download(path, query, key, limit):
    url = BASE + path
    request = Request(url + "?" + urlencode({**query, "Subscription-Key": key}))
    try:
        with build_opener(NoRedirect()).open(request, timeout=10) as response:
            if response.geturl() != request.full_url:
                raise ValueError("EDINET changed the source URL")
            body = response.read(limit + 1)
    except HTTPError as error:
        error.close()
        raise HTTPError(url, error.code, "EDINET request failed", None, None) from None
    except (OSError, ValueError):
        raise OSError("EDINET connection failed") from None
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


def facts_from_csv(body, interim=False, interim_schema=None):
    facts = {}
    with ZipFile(io.BytesIO(body)) as archive:
        files = [item for item in archive.infolist() if re.fullmatch(
            r"XBRL_TO_CSV/jpcrp(?:040300-(?:q[1-4]r|ssr)|040000-ssr|030000-asr)-[^/]+\.csv" if interim
            else r"XBRL_TO_CSV/jpcrp030000-asr-[^/]+\.csv", item.filename)]
        if len(files) != 1 or files[0].file_size > 16_000_000:
            raise ValueError("EDINET annual CSV is missing or exceeds size limit")
        with archive.open(files[0]) as raw, io.TextIOWrapper(raw, encoding="utf-16", newline="") as stream:
            rows = csv.DictReader(stream, delimiter="\t")
            if not {"要素ID", "コンテキストID", "ユニットID", "値"} <= set(rows.fieldnames or []):
                raise ValueError("EDINET annual CSV lacks required columns")
            for row in rows:
                tag, context = row["要素ID"], row["コンテキストID"]
                if interim_schema is not None and len(interim_schema) < 32 and re.fullmatch(
                        r"jp[a-z]+_cor:[A-Za-z0-9]*(?:IssuedShares|PerShare)[A-Za-z0-9]*", tag):
                    if re.fullmatch(r"[A-Za-z0-9_]{1,100}", context):
                        interim_schema.add((tag, context))
                if interim and tag == REPORT_PERIOD_END and context == "FilingDateInstant":
                    value = row["値"]
                    if value and re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
                        facts.setdefault((tag, context), set()).add(value)
                    continue
                duration = tag in EPS_TAGS and context in (
                    "CurrentYearDuration", "CurrentYearDuration_NonConsolidatedMember")
                instant = (tag in BPS_TAGS or tag == SHARES) and context in (
                    "CurrentYearInstant", "CurrentYearInstant_NonConsolidatedMember")
                if interim:
                    duration = False
                    instant = (tag in BPS_TAGS or tag == SHARES) and context in (
                        "CurrentInterimInstant", "CurrentInterimInstant_NonConsolidatedMember",
                        "CurrentQuarterInstant", "CurrentQuarterInstant_NonConsolidatedMember")
                if not duration and not instant:
                    continue
                expected = "shares" if tag == SHARES else "JPYPerShares"
                if row["ユニットID"] != expected:
                    continue
                value = row["値"]
                if not value or not re.fullmatch(r"-?[0-9]{1,16}(?:\.[0-9]{1,10})?", value):
                    continue
                facts.setdefault((tag, context), set()).add(Decimal(value))
    return facts


def compare(metrics, facts):
    matches = 0
    for eps_tag, bps_tag in PER_SHARE_PAIRS:
        for suffix in ("", "_NonConsolidatedMember"):
            eps = facts.get((eps_tag, "CurrentYearDuration" + suffix), set())
            bps = facts.get((bps_tag, "CurrentYearInstant" + suffix), set())
            if eps == {metrics.get("eps")} and bps == {metrics.get("bvps")}:
                matches += 1
    shares = set().union(*(facts.get((SHARES, "CurrentYearInstant" + suffix), set())
                           for suffix in ("", "_NonConsolidatedMember")))
    return {
        "per_share_facts_match": matches == 1,
        "original_period_end_share_count_present": len(shares) == 1 and all(
            value > 0 and value == value.to_integral_value() for value in shares),
    }


def compare_latest(values, previous):
    if len(values) != 1 or previous is None:
        return "unverified"
    return "unchanged" if values == {previous} else "changed"


class EdinetAudit:
    def __init__(self, key):
        self.key = key
        self.days = {}
        self.next_request = 0.0

    def request(self, path, query, limit):
        time.sleep(max(0, self.next_request - time.monotonic()))
        self.next_request = time.monotonic() + 1.25
        return download(path, query, self.key, limit)

    def filings(self, filed_on):
        if filed_on not in self.days:
            listing = json.loads(self.request(".json", {"date": filed_on, "type": 2}, 4_000_000))
            status = str(listing.get("metadata", {}).get("status", ""))
            if status in ("401", "403", "429", "503"):
                raise HTTPError(BASE, int(status), "EDINET request failed", None, None)
            self.days[filed_on] = listing["results"]
        return self.days[filed_on]

    def review_newer(self, code, filed_on, annual_period, annual_bps, annual_shares):
        issuer_filings = [row for row in self.filings(filed_on) if row.get("secCode") == code + "0"
                   and row.get("withdrawalStatus") == "0" and row.get("disclosureStatus") == "0"
                   and str(row.get("submitDateTime", ""))[:10] == filed_on]
        types = sorted({str(row.get("docTypeCode", "")) for row in issuer_filings})
        evidence = {"issuer_filing_types": types, "issuer_filing_count": len(issuer_filings)}
        if not issuer_filings:
            return {**evidence, "status": "latest_no_edinet_filing_on_hint_date"}
        if any(kind in types for kind in ("120", "130", "150", "170")):
            return {**evidence, "status": "latest_annual_or_amendment_requires_review"}
        interim = [row for row in issuer_filings if row.get("docTypeCode") in ("140", "160")]
        if len(interim) != 1:
            status = "latest_interim_ambiguous" if interim else "latest_non_interim_requires_review"
            return {**evidence, "status": status}
        item = interim[0]
        kind = item["docTypeCode"]
        doc = item.get("docID", "")
        period = item.get("periodEnd")
        result = {**evidence, "doc_type": kind, "period_end": period, "filed_on": filed_on}
        if not re.fullmatch(r"S[0-9A-Z]{7}", doc):
            return {**result, "status": "latest_interim_document_id_unverified"}
        result["doc_id"] = doc
        if not period or not annual_period < period:
            return {**result, "status": "latest_interim_period_unverified"}
        if item.get("csvFlag") != "1":
            return {**result, "status": "latest_interim_csv_not_offered", "csv_flag": item.get("csvFlag"),
                    "xbrl_flag": item.get("xbrlFlag")}
        result["status"] = "latest_interim_reviewed"
        schema = set()
        try:
            facts = facts_from_csv(self.request("/" + doc, {"type": 5}, 8_000_000), interim=True,
                                   interim_schema=schema)
        except (ValueError, KeyError, BadZipFile):
            return {**result, "status": "latest_interim_csv_unverified"}
        period_dates = facts.get((REPORT_PERIOD_END, "FilingDateInstant"), set())
        if len(period_dates) != 1:
            return {**result, "status": "latest_interim_report_period_unverified"}
        observed_period = next(iter(period_dates))
        try:
            ordered = date.fromisoformat(annual_period) < date.fromisoformat(observed_period) < date.fromisoformat(filed_on)
            within_fiscal_year = date.fromisoformat(observed_period) <= date.fromisoformat(period)
        except ValueError:
            ordered = within_fiscal_year = False
        if not ordered or not within_fiscal_year:
            return {**result, "status": "latest_interim_report_period_unverified"}
        result["report_period_end"] = observed_period
        shares = set().union(*(values for (tag, _), values in facts.items() if tag == SHARES))
        book_values = set().union(*(values for (tag, _), values in facts.items() if tag in BPS_TAGS))
        result["shares"] = compare_latest(shares, annual_shares)
        result["bps"] = compare_latest(book_values, annual_bps)
        if result["shares"] == "unverified" or result["bps"] == "unverified":
            result["observed_schema"] = sorted(schema)
        return result

    def check(self, filing, row):
        filed_on = filing["actual_filing_date"]
        code = filing["code"]
        doc_id = filing["annual_source_id"]
        if not re.fullmatch(r"S[0-9A-Z]{7}", doc_id):
            raise ValueError("Unexpected EDINET document identifier")
        filings = self.filings(filed_on)
        if not metadata_matches(filings, code, doc_id, row["period_end"], filed_on):
            return {"filing_metadata_match": False}
        matched = next(item for item in filings if item.get("docID") == doc_id)
        try:
            duration = (date.fromisoformat(row["period_end"]) - date.fromisoformat(matched["periodStart"])).days + 1
        except (KeyError, TypeError, ValueError):
            duration = 0
        try:
            facts = facts_from_csv(self.request("/" + doc_id, {"type": 5}, 8_000_000))
            checks = compare(row["metrics"], facts)
            shares = set().union(*(values for (tag, _), values in facts.items() if tag == SHARES))
            return {"filing_metadata_match": True, "full_year_verified": 350 <= duration <= 380,
                    **checks, "annual_shares": next(iter(shares))
                    if checks["original_period_end_share_count_present"] else None}
        except HTTPError as error:
            if error.code in (401, 403, 429, 503):
                raise
            return {"filing_metadata_match": True, "original_csv_unverified": True}
        except (ValueError, InvalidOperation, OSError, KeyError, BadZipFile):
            return {"filing_metadata_match": True, "original_csv_unverified": True}
