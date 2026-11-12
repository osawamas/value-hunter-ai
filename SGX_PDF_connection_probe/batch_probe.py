"""Exploratory multi-document SGX PDF audit; NEVER asserts generic financial verification."""
import csv
import datetime as dt
import hashlib
import io
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request

import pymupdf

ROOT = pathlib.Path(__file__).resolve().parent
OUT = pathlib.Path('batch_results')
MAX_BYTES = 20_000_000
LABELS = {
    'revenue': r'\b(?:operating\s+revenue|total\s+revenue|net\s+revenue|revenue)\b',
    'operating_profit': r'\b(?:operating\s+profit|profit\s+from\s+operations)\b',
    'net_profit': r'\b(?:profit\s+attributable|net\s+profit|profit\s+for\s+the\s+(?:year|period))\b',
    'assets': r'\btotal\s+assets\b',
    'liabilities': r'\btotal\s+liabilities\b',
    'equity': r'\btotal\s+equity\b',
}
NUMBER = re.compile(r'(?<![A-Za-z])\(?-?\d{1,3}(?:,\d{3})+(?:\.\d+)?\)?')

def validate_manifest(manifest):
    if not isinstance(manifest, dict) or not isinstance(manifest.get('documents'), list):
        raise ValueError('manifest requires documents array')
    if not manifest['documents']:
        raise ValueError('manifest must contain at least one document')
    ids = set()
    for item in manifest['documents']:
        for key in ('ticker', 'document_id', 'url'):
            if not isinstance(item.get(key), str) or not item[key].strip():
                raise ValueError(f'missing {key}')
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', item['document_id']):
            raise ValueError('document_id must be alphanumeric/underscore/hyphen')
        if item['document_id'] in ids:
            raise ValueError('duplicate document_id')
        ids.add(item['document_id'])
        if not item['url'].startswith('https://'):
            raise ValueError('only https URLs allowed')
    return manifest['documents']

def candidates(pages):
    """Evidence candidates, not audited values; retain page and raw text."""
    found = []
    for pno, page in enumerate(pages, 1):
        for line in page.splitlines():
            normalized = ' '.join(line.split())
            if not normalized or len(normalized) > 300:
                continue
            for metric, pattern in LABELS.items():
                if re.search(pattern, normalized, re.I):
                    values = NUMBER.findall(normalized)
                    if values:
                        found.append({'metric_hint':metric,'page':pno,'line':normalized[:260], 'number_tokens':values[:12], 'status':'unverified_candidate'})
    return found[:500]

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0 (compatible; ValueHunterBatch/9.0)','Accept':'application/pdf,*/*;q=0.5'})
    with urllib.request.urlopen(req, timeout=40) as response:
        status = response.status
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES or not data.startswith(b'%PDF-'):
        raise ValueError('invalid PDF or exceeds 20 MB')
    return data, status

def run(manifest_path, out_dir=OUT, downloader=fetch):
    documents = validate_manifest(json.loads(pathlib.Path(manifest_path).read_text(encoding='utf-8')))
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for item in documents:
        record = {k:item.get(k) for k in ('ticker','document_id','url','expected_fiscal_year','document_type')}
        record['tested_at'] = dt.datetime.now(dt.timezone.utc).isoformat()
        record['status'] = 'failed'
        record['financial_validation'] = 'not_attempted_generic'
        try:
            data, status = downloader(item['url'])
            with pymupdf.open(stream=data, filetype='pdf') as doc:
                pages = [page.get_text(sort=True) for page in doc]
            evidence = candidates(pages)
            record.update({'status':'pdf_text_extracted','http_status':status,'pdf_bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'pages':len(pages),'extracted_chars':sum(map(len,pages)),'candidate_count':len(evidence),'metric_hints':sorted(set(c['metric_hint'] for c in evidence))})
            (out_dir / f"{item['document_id']}_candidates.json").write_text(json.dumps({'document':item,'candidates':evidence,'warning':'Candidates are not verified financial values'},ensure_ascii=False,indent=2),encoding='utf-8')
        except Exception as exc:
            record['error'] = f'{type(exc).__name__}: {exc}'
        records.append(record)
        print(json.dumps(record,ensure_ascii=False),flush=True)
    summary = {'schema_version':'v9.0.0','document_count':len(records),'pdf_success_count':sum(r['status']=='pdf_text_extracted' for r in records),'pdf_failure_count':sum(r['status']=='failed' for r in records),'generic_financial_verification':'NOT_IMPLEMENTED','records':records}
    (out_dir/'batch_report.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    with (out_dir/'batch_summary.csv').open('w',encoding='utf-8',newline='') as f:
        keys = ['ticker','document_id','document_type','status','http_status','pages','extracted_chars','candidate_count','financial_validation','error']
        writer=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore');writer.writeheader();writer.writerows(records)
    return summary

if __name__ == '__main__':
    try:
        report=run(sys.argv[1] if len(sys.argv)>1 else ROOT/'batch_manifest.json')
    except Exception as exc:
        OUT.mkdir(exist_ok=True)
        (OUT/'fatal_error.txt').write_text(f'{type(exc).__name__}: {exc}\n',encoding='utf-8')
        raise
    sys.exit(0 if report['pdf_success_count'] else 1)
