import json, urllib.request, hashlib, pathlib, datetime, traceback
import pymupdf
from financial_extract import extract_s68_fy2026

URLS = {
 'S68_FY2026_results':'https://investorrelations.sgx.com/static-files/dcbd5905-9373-4dc9-80f5-8dbff6b8d584',
 'S68_FY2026_release':'https://links.sgx.com/FileOpen/1.%20SGX%20Group%20reports%20FY2026%20net%20profit%20of%20S%24759%20million.ashx?App=Announcement&FileID=898861',
}
root=pathlib.Path('results');root.mkdir(exist_ok=True)
records=[]
for name,url in URLS.items():
    rec={'name':name,'url':url,'time_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Accept':'application/pdf'})
        with urllib.request.urlopen(req,timeout=40) as resp:
            data=resp.read(20_000_001)
            rec['http_status']=resp.status
            rec['content_type']=resp.headers.get('Content-Type','')
        if len(data)>20_000_000:raise ValueError('PDF exceeds size cap')
        if not data.startswith(b'%PDF-'):raise ValueError('Not PDF')
        rec['sha256']=hashlib.sha256(data).hexdigest()
        rec['bytes']=len(data)
        doc=pymupdf.open(stream=data,filetype='pdf')
        pages=[p.get_text(sort=True) for p in doc]
        rec['pages']=len(pages);rec['extracted_chars']=sum(map(len,pages))
        (root/(name+'.txt')).write_text('\n\f\n'.join(pages),encoding='utf-8')
        if name=='S68_FY2026_results':
            try:
                verified=extract_s68_fy2026(pages)
                verified['document_sha256']=rec['sha256'];verified['document_url']=url
                (root/'S68_verified_financials.json').write_text(json.dumps(verified,indent=2),encoding='utf-8')
                rec['financial_validation']='passed'
            except ValueError as exc:
                rec['financial_validation']='not_verified';rec['validation_error']=str(exc)
        rec['pdf_extraction']='passed'
    except Exception as exc:
        rec['error']=str(exc);rec['pdf_extraction']='failed'
    records.append(rec)
    print(json.dumps(rec,ensure_ascii=False))
(root/'report.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
