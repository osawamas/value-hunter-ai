"""S68 PDF live verification; records deployed version and source fingerprints."""
import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import urllib.request

import pymupdf
from financial_extract import extract_s68_fy2026
from layout_probe import inspect_document

VERSION = 'v7.0.0'
ROOT = pathlib.Path(__file__).resolve().parent
OUT = pathlib.Path('results')
OUT.mkdir(parents=True, exist_ok=True)
URLS = {
    'S68_FY2026_results': 'https://investorrelations.sgx.com/static-files/dcbd5905-9373-4dc9-80f5-8dbff6b8d584',
    'S68_FY2026_release': 'https://links.sgx.com/FileOpen/1.%20SGX%20Group%20reports%20FY2026%20net%20profit%20of%20S%24759%20million.ashx?App=Announcement&FileID=898861',
}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def fetch(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; ValueHunterProbe/7.0)',
        'Accept': 'application/pdf,*/*;q=0.5',
    })
    with urllib.request.urlopen(req, timeout=40) as response:
        status = response.status
        data = response.read(20_000_001)
    if len(data) > 20_000_000 or not data.startswith(b'%PDF-'):
        raise ValueError('Invalid PDF response or PDF over 20 MB')
    return data, status

def main():
    metadata = {
        'probe_version': VERSION,
        'python': sys.version.split()[0],
        'git_commit': subprocess.run(['git','rev-parse','HEAD'], capture_output=True, text=True).stdout.strip() or None,
        'source_sha256': {name: sha(ROOT / name) for name in ['probe.py','financial_extract.py','layout_probe.py']},
        'success': False,
        'records': [],
    }
    print('RUNNING_PROBE_VERSION=' + VERSION, flush=True)
    verified = False
    for name, url in URLS.items():
        record = {'name': name, 'url': url, 'tested_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}
        try:
            data, status = fetch(url)
            with pymupdf.open(stream=data, filetype='pdf') as doc:
                pages = [page.get_text(sort=True) for page in doc]
                record.update({'http_status': status, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'pages': len(doc), 'extracted_chars': sum(map(len,pages)), 'pdf_extraction': 'passed'})
                if name == 'S68_FY2026_results':
                    diagnostics = inspect_document(doc, OUT)
                    record['layout_pages_with_labels'] = len(diagnostics)
                    for page_num in [9,10,11]:
                        if page_num <= len(pages):
                            (OUT / f'page_{page_num:02d}_text.txt').write_text(pages[page_num-1], encoding='utf-8')
                    try:
                        result = extract_s68_fy2026(pages)
                        result.update({'document_sha256': record['sha256'], 'document_url': url, 'extractor_version': VERSION})
                        (OUT/'S68_verified_financials.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
                        record['financial_validation'] = 'passed'
                        record['metrics_found'] = sorted(result['metrics'])
                        verified = True
                    except Exception as exc:
                        record['financial_validation'] = 'not_verified'
                        record['validation_error'] = f'{type(exc).__name__}: {exc}'
        except Exception as exc:
            record['pdf_extraction'] = 'failed'
            record['error'] = f'{type(exc).__name__}: {exc}'
        metadata['records'].append(record)
        print(json.dumps(record, ensure_ascii=False), flush=True)
    metadata['success'] = verified
    (OUT/'report.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
    if not verified:
        print('Financial verification failed; inspect results/report.json', file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
