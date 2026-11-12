"""v13: conservatively merge v10 arithmetic and v12 explicit scope evidence.

No company-specific financial figures are embedded. Missing/ambiguous evidence
produces NOT_VERIFIED, never a fabricated verified statement.
"""
import json
import re
import sys
from pathlib import Path

VERSION = 'v13.0.0'
DATE_RE = re.compile(r'\b30\s+June\s+(20\d{2})\b', re.I)
UNIT_RE = re.compile(r"\bS\$\s*['’]\s*000\b", re.I)


def verify(audit, headings):
    result = {'schema_version': VERSION, 'document_id': audit.get('document_id'),
              'financial_validation': 'NOT_VERIFIED', 'consolidated_balance_sheet': None,
              'rejections': [], 'excluded_company_pages': [], 'scope_evidence': []}
    tables = audit.get('balance_sheet_tables', [])
    evidence = headings.get('page_scope_evidence', [])
    bypage = {e.get('page'): e for e in evidence if isinstance(e.get('page'), int)}
    approved = []
    for table in tables:
        page = table.get('page')
        ev = bypage.get(page, {})
        scope = ev.get('scope')
        if scope == 'company' and ev.get('status') == 'EXPLICIT_HEADING_FOUND':
            result['excluded_company_pages'].append(page)
            continue
        if scope != 'consolidated' or ev.get('status') != 'EXPLICIT_HEADING_FOUND':
            result['rejections'].append({'page': page, 'reason': 'NO_EXPLICIT_CONSOLIDATED_HEADING'})
            continue
        # Ensure heading line itself names the scope; not merely a keyword in the page.
        heading_lines = [e for e in ev.get('heading_evidence', [])
                         if e.get('position') == 'page_start' and e.get('scope') == 'consolidated'
                         and re.search(r'\b(?:statement of financial position|balance sheet)\s*[-–:]?\s*(?:group|consolidated)\b', e.get('text', ''), re.I)]
        if len(heading_lines) != 1:
            result['rejections'].append({'page': page, 'reason': 'HEADING_NOT_UNIQUE_OR_EXPLICIT'})
            continue
        start = ev.get('page_start', [])
        texts = [x.get('text', '') for x in start]
        # Require two distinct year dates on same date header, and consistent with fiscal year.
        date_lines = [DATE_RE.findall(s) for s in texts]
        years = [int(y) for line in date_lines if len(line) == 2 for y in line]
        expected = audit.get('expected_fiscal_year')
        if len(years) != 2 or len(set(years)) != 2 or not isinstance(expected, int) or years != [expected, expected - 1]:
            result['rejections'].append({'page': page, 'reason': 'YEAR_COLUMNS_NOT_VERIFIED'})
            continue
        if not any(UNIT_RE.search(s) and len(UNIT_RE.findall(s)) == 2 for s in texts):
            result['rejections'].append({'page': page, 'reason': 'SGD_THOUSANDS_UNIT_NOT_VERIFIED'})
            continue
        vals = table.get('values', {})
        if not all(isinstance(vals.get(k), list) and len(vals[k]) == 2 and
                   all(isinstance(v, int) and not isinstance(v, bool) and v >= 0 for v in vals[k])
                   for k in ('assets', 'liabilities', 'equity')):
            result['rejections'].append({'page': page, 'reason': 'INVALID_BALANCE_VALUES'})
            continue
        if table.get('checks') != {'year_column_1': True, 'year_column_2': True} or not all(
            vals['assets'][i] == vals['liabilities'][i] + vals['equity'][i] for i in range(2)
        ):
            result['rejections'].append({'page': page, 'reason': 'BALANCE_EQUATION_FAILED'})
            continue
        # Cross-check numbers against the page text as an independent source from v10 candidates.
        mismatched = []
        for metric, label in [('assets', 'Total assets'), ('liabilities', 'Total liabilities'), ('equity', 'Total equity')]:
            row = [s for s in texts if re.match(r'^' + re.escape(label) + r'\s+', s, re.I)]
            if len(row) > 1 or (len(row) == 1 and [int(x.replace(',', '')) for x in re.findall(r'\b\d[\d,]*\b', row[0][len(label):])] != vals[metric]):
                mismatched.append(metric)
            source = table.get('source_lines', {}).get(metric, '')
            if not re.match(r'^' + re.escape(label) + r'\s+', source, re.I) or [int(x.replace(',', '')) for x in re.findall(r'\b\d[\d,]*\b', source[len(label):])] != vals[metric]:
                mismatched.append(metric)
        if mismatched:
            result['rejections'].append({'page': page, 'reason': 'PAGE_TEXT_CROSSCHECK_FAILED', 'metrics': mismatched})
            continue
        approved.append({'page': page, 'fiscal_years': years, 'currency': 'SGD', 'unit_multiplier': 1000,
                         'values_thousands_sgd': vals, 'heading': heading_lines[0]['text'],
                         'source_lines': table.get('source_lines', {})})
        result['scope_evidence'].append({'page': page, 'heading': heading_lines[0]['text']})
    if len(approved) == 1:
        result['consolidated_balance_sheet'] = approved[0]
        result['financial_validation'] = 'VERIFIED_CONSOLIDATED_BALANCE_SHEET_ONLY'
    elif len(approved) > 1:
        result['rejections'].append({'reason': 'MULTIPLE_CONSOLIDATED_TABLES', 'pages': [x['page'] for x in approved]})
    if not tables:
        result['rejections'].append({'reason': 'NO_BALANCE_TABLES'})
    result['warning'] = 'Verification covers consolidated balance sheet only; income statement, market data and other issuers are not verified.'
    return result


def run(directory):
    directory = Path(directory)
    results = []
    for ap in sorted(directory.glob('*_financial_audit.json')):
        docid = ap.name[:-len('_financial_audit.json')]
        hp = directory / f'{docid}_heading_evidence.json'
        audit = json.loads(ap.read_text(encoding='utf-8'))
        headings = json.loads(hp.read_text(encoding='utf-8')) if hp.exists() else {}
        res = verify(audit, headings)
        (directory / f'{docid}_consolidated_v13.json').write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding='utf-8')
        results.append(res)
    summary = {'schema_version': VERSION, 'results': results,
               'verified_consolidated_balance_sheets': sum(r['financial_validation'] == 'VERIFIED_CONSOLIDATED_BALANCE_SHEET_ONLY' for r in results)}
    (directory / 'consolidated_v13_summary.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'version': VERSION, 'documents': len(results), 'verified_balance_sheets': summary['verified_consolidated_balance_sheets']}))
    return summary


if __name__ == '__main__':
    summary = run(sys.argv[1] if len(sys.argv) > 1 else 'batch_results')
    sys.exit(0 if summary['verified_consolidated_balance_sheets'] > 0 else 1)
