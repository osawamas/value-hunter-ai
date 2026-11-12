"""Fetch actual S68 FY2026 PDF, emit reproducible layout diagnostics and safe validation."""
import datetime
import hashlib
import json
import pathlib
import sys
import urllib.request
import pymupdf
from financial_extract import extract_s68_fy2026
from layout_probe import inspect_document

URLS = {
    'S68_FY2026_results':'https://investorrelations.sgx.com/static-files/dcbd5905-9373-4dc9-80f5-8dbff6b8d584',
    'S68_FY2026_release':'https://links.sgx.com/FileOpen/1.%20SGX%20Group%20reports%20FY2026%20net%20profit%20of%20S%24759%20million.ashx?App=Announcement&FileID=898861',
}
OUT=pathlib.Path('results');OUT.mkdir(exist_ok=True)

def fetch(url):
    request=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; ValueHunterProbe/4.0)','Accept':'application/pdf,*/*;q=0.5'})
    with urllib.request.urlopen(request,timeout=35) as resp:
        data=resp.read(20_000_001)
        status=resp.status
    if len(data)>20_000_000 or not data.startswith(b'%PDF-'):
        raise ValueError('Response is not a valid PDF within 20MB')
    return data,status

def main():
    records=[];verified=False
    for name,url in URLS.items():
        record={'name':name,'url':url,'tested_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
        try:
            data,status=fetch(url)
            with pymupdf.open(stream=data,filetype='pdf') as doc:
                pages=[p.get_text(sort=True) for p in doc]
                record.update({'http_status':status,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'pages':len(doc),'extracted_chars':sum(map(len,pages)),'pdf_extraction':'passed'})
                if name=='S68_FY2026_results':
                    diagnostics=inspect_document(doc,OUT)
                    record['layout_pages_with_labels']=len(diagnostics)
                    try:
                        result=extract_s68_fy2026(pages)
                        result['document_sha256']=record['sha256'];result['document_url']=url
                        (OUT/'S68_verified_financials.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
                        record['financial_validation']='passed';verified=True
                    except ValueError as exc:
                        record['financial_validation']='not_verified';record['validation_error']=str(exc)
        except Exception as exc:
            record['pdf_extraction']='failed';record['error']=str(exc)
        records.append(record)
        print(json.dumps(record,ensure_ascii=False),flush=True)
    (OUT/'report.json').write_text(json.dumps({'success':verified,'records':records},indent=2,ensure_ascii=False),encoding='utf-8')
    if not verified:
        print('Financial verification pending. See results/layout_diagnostics.json and page text.',file=sys.stderr)
        return 1
    return 0
if __name__=='__main__':sys.exit(main())
