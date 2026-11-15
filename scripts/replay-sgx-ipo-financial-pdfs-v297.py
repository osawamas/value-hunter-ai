#!/usr/bin/env python3
"""v297 direct SGX first-party IPO PDF replay with byte digests + textual evidence.
Never republishes source PDF; original files stored only transiently in Action workspace.
PDF inclusion of audited history is NOT independent contemporary financial verification.
"""
import datetime as dt
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.parse
import urllib.request

ROOT=pathlib.Path(__file__).resolve().parent.parent
MANIFEST=ROOT/"docs/data/sgx-ipo-financial-documents-v297.json"
MAX_BYTES=16_000_000

def validate_manifest(data):
    if (data.get("schema_version")!="sgx-ipo-original-pdf-replay-v297"
      or data.get("ranking_enabled") is not False
      or data.get("ranking_eligible_count")!=0
      or data.get("quote_feed_license_verified") is not False
      or data.get("up_to_date_independent_financial_verification_complete") is not False
      or data.get("full_current_sgx_master_verified") is not False):
        raise ValueError("Manifest source/safety boundary invalid")
    sources=data.get("sources")
    if not isinstance(sources,list) or len(sources)!=3:raise ValueError("Expected three official PDFs")
    types=[(s.get("symbol"),s.get("document_type")) for s in sources]
    if types!=[("9DC","REGISTERED_IPO_PROSPECTUS"),("MIM","REGISTERED_IPO_PROSPECTUS"),("MIM","ISSUER_9M2026_BUSINESS_UPDATE")]:
        raise ValueError("Wrong document types or codes")
    ids=[]
    for s in sources:
        u=urllib.parse.urlparse(s.get("url",""))
        qs=urllib.parse.parse_qs(u.query)
        fid=qs.get("FileID",[])
        if (u.scheme!="https" or u.netloc!="links.sgx.com" or
            u.path.lower().startswith("/fileopen/") is False or
            len(fid)!=1 or not fid[0].isdigit() or
            qs.get("App") not in (["IPO"],["Announcement"]) or
            not isinstance(s.get("expected_headline_terms"),list) or
            len(s["expected_headline_terms"])<2 or
            not isinstance(s.get("historical_audited_periods"),list)):
            raise ValueError("Unapproved SGX original PDF source/verification terms")
        digest=s.get("github_actions_confirmed_sha256")
        expected_bytes=s.get("github_actions_confirmed_original_bytes")
        if (not isinstance(digest,str) or not re.fullmatch(r"[a-f0-9]{64}",digest)
            or not isinstance(expected_bytes,int) or expected_bytes<25000
            or expected_bytes>MAX_BYTES or s.get("original_replay_run_id")!=43676027936):
            raise ValueError("Original source SHA/byte proof must be from verified 43676027936")
        ids.append(fid[0])
    if len(set(ids))!=3:raise ValueError("Duplicate source FileID")
    return sources

def extract_checks(raw, terms):
    if not isinstance(raw,bytes) or not raw.startswith(b"%PDF-") or len(raw)<25000 or len(raw)>MAX_BYTES:
        raise ValueError("Original response is not a reasonable sized PDF")
    pdf_tool=shutil.which("pdftotext")
    if not pdf_tool:raise RuntimeError("pdftotext required for source verification")
    with tempfile.TemporaryDirectory(prefix="sgx-v297-") as tmp:
        file=pathlib.Path(tmp)/"source.pdf"
        file.write_bytes(raw)
        proc=subprocess.run([pdf_tool,"-layout",str(file),"-"],
          stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=40)
        if proc.returncode!=0:raise ValueError("PDF text extraction failed")
        content=proc.stdout.decode("utf-8",errors="replace")
    normalized=" ".join(content.split()).casefold()
    terms_found={term: " ".join(term.split()).casefold() in normalized for term in terms}
    return {"required_text_checks":terms_found,
      "all_required_text_found":all(terms_found.values()),
      "source_pdf_sha256":hashlib.sha256(raw).hexdigest(),
      "source_pdf_bytes":len(raw),
      "pdf_text_extractable":bool(content.strip()),
      "reproduced_raw_financial_values":False,
      "independent_current_audit_verified":False,
      "licensed_market_quotes":False,
      "ranking_eligible":False}

def acquire(doc):
    body=b"";reason=None;checks=None
    try:
        req=urllib.request.Request(doc["url"],headers={
          "User-Agent":"VALUE-HUNTER-AI-source-validation/1.0 (+https://github.com/osawamas/value-hunter-ai)",
          "Accept":"application/pdf"})
        with urllib.request.urlopen(req,timeout=45) as response:
            actual=urllib.parse.urlparse(response.geturl())
            if actual.scheme!="https" or actual.hostname!="links.sgx.com":
                raise ValueError("Redirect out of SGX original domain")
            body=response.read(MAX_BYTES+1)
        if hashlib.sha256(body).hexdigest()!=doc["github_actions_confirmed_sha256"]:
            raise ValueError("SGX PDF original digest drift")
        if len(body)!=doc["github_actions_confirmed_original_bytes"]:
            raise ValueError("SGX PDF original byte length drift")
        checks=extract_checks(body,doc["expected_headline_terms"])
    except (OSError,urllib.error.URLError,ValueError,RuntimeError,subprocess.TimeoutExpired) as ex:
        reason=type(ex).__name__
    result={
      "symbol":doc["symbol"],"document_type":doc["document_type"],
      "source_url":doc["url"],"source_date":doc["document_date"],
      "raw_pdf_bytes":len(body),
      "raw_pdf_sha256":hashlib.sha256(body).hexdigest() if body else None,
      "fetch_or_parse_error":reason,
      "verified_text":checks,
      "original_pdf_headline_confirmed":checks is not None and checks["all_required_text_found"],
      "audit_scope":"HISTORICAL_ANNUAL_ONLY" if doc["historical_audited_periods"] else "UNCONFIRMED_UNAUDITED_ISSUER_UPDATE",
      "investment_eligibility":False}
    return result

def main():
    sources=validate_manifest(json.loads(MANIFEST.read_text(encoding="utf-8")))
    results=[acquire(s) for s in sources]
    report={
      "schema_version":"sgx-ipo-original-pdf-live-evidence-v297",
      "retrieved_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
      "source_count":len(results),
      "original_pdf_confirmed_count":sum(bool(s["original_pdf_headline_confirmed"]) for s in results),
      "files":results,
      "complete_original_ipo_document_validation":all(s["original_pdf_headline_confirmed"] for s in results),
      "financial_amounts_automatically_independently_verified":False,
      "current_ex_treasury_share_count_verified":False,
      "licensed_quote_data_present":False,
      "ranking_eligible_count":0}
    out=ROOT/"build/research/sgx-ipo-original-financial-pdfs-v297.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    for s in results:
        print("v297 "+s["symbol"]+" "+s["document_type"]+" "+("PASS" if s["original_pdf_headline_confirmed"] else "UNVERIFIED")+
         " bytes="+str(s["raw_pdf_bytes"])+" sha256="+str(s["raw_pdf_sha256"])+
         " details="+str(s["verified_text"]["required_text_checks"] if s["verified_text"] else s["fetch_or_parse_error"]))
    if not report["complete_original_ipo_document_validation"]:
        raise SystemExit(1)
if __name__=="__main__":main()
