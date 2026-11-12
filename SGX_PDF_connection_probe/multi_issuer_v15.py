"""SGX v15: multi-issuer PDF reconnaissance, not verified financial extraction."""
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import urllib.request
from urllib.parse import urlparse
import fitz

BASE = Path(__file__).resolve().parent
OUT = Path(os.getenv('SGX_V15_OUTPUT', 'sgx_v15_results'))
MAX_BYTES = 16 * 1024 * 1024
LABELS = {
    'revenue': re.compile(r'\b(?:revenue|turnover|net sales|total income)\b', re.I),
    'operating_profit': re.compile(r'\b(?:operating profit|profit from operations|operating income)\b', re.I),
    'attributable_profit': re.compile(r'\b(?:profit attributable to (?:equity holders|owners|shareholders)|net profit attributable)\b', re.I),
    'total_assets': re.compile(r'\btotal assets\b', re.I),
    'total_liabilities': re.compile(r'\btotal liabilities\b', re.I),
    'total_equity': re.compile(r'\b(?:total equity|total shareholders.? equity|total net assets)\b', re.I),
}
SCOPE = re.compile(r'\b(?:consolidated|group|company|parent)\b', re.I)
PERIOD = re.compile(r'\b(?:FY\s?20\d\d|20\d\d|full year|year ended|six months|half year)\b', re.I)


def validate_manifest(items):
    if not isinstance(items, list) or not items:
        raise ValueError('manifest must be a non-empty list')
    for item in items:
        if not all(item.get(k) for k in ('issuer', 'symbol', 'url')):
            raise ValueError('issuer, symbol, url are required')
        u = urlparse(item['url'])
        if u.scheme != 'https' or u.hostname not in ('links.sgx.com', 'investorrelations.sgx.com'):
            raise ValueError('Only official SGX HTTPS PDF URLs are allowed')
    return items


def download_pdf(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible; SGXResearchAudit/15.0)', 'Accept': 'application/pdf,*/*'})
    with urllib.request.urlopen(req, timeout=50) as resp:
        data = resp.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError('PDF exceeds 16MB safety limit')
        if not data.startswith(b'%PDF-'):
            raise ValueError('Response is not a PDF')
        return data, resp.status


def audit_pdf(data, item):
    doc = fitz.open(stream=data, filetype='pdf')
    evidence = []
    for page_index, page in enumerate(doc):
        lines = page.get_text('text').splitlines()
        for idx, line in enumerate(lines):
            matches = [name for name, pat in LABELS.items() if pat.search(line)]
            if not matches:
                continue
            context = ' | '.join(lines[max(0, idx-2):min(len(lines), idx+4)])[:650]
            evidence.append({'page': page_index+1, 'line': idx+1, 'labels': matches,
                             'text': line[:220], 'context': context,
                             'scope_terms': sorted(set(SCOPE.findall(context)), key=str.lower),
                             'period_terms': sorted(set(PERIOD.findall(context)), key=str.lower)})
    return {'issuer': item['issuer'], 'symbol': item['symbol'], 'source_url': item['url'],
            'pdf_sha256': hashlib.sha256(data).hexdigest(), 'pages': len(doc),
            'evidence_count': len(evidence), 'evidence': evidence[:350],
            'status': 'CANDIDATES_ONLY_NOT_VERIFIED'}


def run(manifest, output):
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for item in validate_manifest(manifest):
        row = {'symbol': item['symbol'], 'issuer': item['issuer'], 'status': 'ERROR', 'pages': 0, 'evidence_count': 0, 'error': ''}
        try:
            data, http_status = download_pdf(item['url'])
            result = audit_pdf(data, item)
            result['http_status'] = http_status
            (output / f"{item['symbol']}_evidence.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
            row.update(status=result['status'], pages=result['pages'], evidence_count=result['evidence_count'])
        except Exception as exc:
            row['error'] = f'{type(exc).__name__}: {exc}'[:400]
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    with (output/'summary.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    (output/'report.json').write_text(json.dumps({'version': 'v15.0', 'rows': rows, 'verified_financial_statements': 0,
        'note': 'Candidate detection only; do not use for investment screening without validation'}, indent=2, ensure_ascii=False), encoding='utf-8')
    return rows


if __name__ == '__main__':
    items = json.loads((BASE/'multi_issuer_manifest_v15.json').read_text(encoding='utf-8'))
    rows = run(items, OUT)
    if not any(r['status'] != 'ERROR' for r in rows):
        raise SystemExit('All PDF downloads failed; inspect artifact report.json')
