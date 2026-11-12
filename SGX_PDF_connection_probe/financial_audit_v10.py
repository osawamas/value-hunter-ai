"""Conservative evidence audit of SGX PDF candidate lines; not an audited financial feed."""
import json
import re
from collections import defaultdict
from pathlib import Path

NUM = re.compile(r'(?<![A-Za-z0-9])\(?-?\d+(?:,\d{3})*(?:\.\d+)?\)?')
LABELS = {'assets': re.compile(r'\btotal assets\b', re.I), 'liabilities': re.compile(r'\btotal liabilities\b', re.I), 'equity': re.compile(r'\btotal equity\b', re.I)}
INCOME = {
 'operating_revenue': re.compile(r'\bOperating revenue\b(?!\s+less)', re.I),
 'net_operating_revenue': re.compile(r'\bOperating revenue less transaction-based expenses', re.I),
 'operating_profit': re.compile(r'\bOperating profit\b', re.I),
 'attributable_profit': re.compile(r'\bNet profit after tax attributable to equity holders of the Company\b', re.I),
}

def ints(line):
    return [int(x.replace(',', '')) for x in NUM.findall(line) if '.' not in x]

def audit(payload):
    doc = payload.get('document', {})
    candidates = payload.get('candidates', [])
    bypage = defaultdict(lambda: defaultdict(list))
    for c in candidates:
        line = c.get('line', '')
        p = c.get('page')
        if not isinstance(p, int):
            continue
        for metric, regex in LABELS.items():
            if regex.search(line):
                # Balance-sheet row must have only two integer values after the label.
                tail = line[regex.search(line).end():]
                values = ints(tail)
                if len(values) == 2:
                    bypage[p][metric].append({'values': values, 'line': line})
    balances = []
    for page, metrics in sorted(bypage.items()):
        if not all(len(metrics.get(k, [])) == 1 for k in LABELS):
            continue
        a, l, e = (metrics[k][0]['values'] for k in ('assets', 'liabilities', 'equity'))
        matches = [a[i] == l[i] + e[i] for i in range(2)]
        balances.append({'page': page, 'values': {'assets': a, 'liabilities': l, 'equity': e},
                         'checks': {'year_column_1': matches[0], 'year_column_2': matches[1]},
                         'status': 'arithmetic_consistent_unclassified' if all(matches) else 'arithmetic_mismatch',
                         'scope': 'unclassified', 'source_lines': {k: metrics[k][0]['line'] for k in LABELS}})
    income = []
    for c in candidates:
        line = c.get('line', '')
        for metric, regex in INCOME.items():
            match = regex.search(line)
            if not match:
                continue
            if metric == 'attributable_profit' and re.search(r'\badjusted\b', line[:match.start()], re.I):
                continue
            # Four integer amounts, two for half-year and two for full-year.
            # A percentage after the amounts may be present; keep only integer tokens.
            before = ints(line[:match.start()]); after = ints(line[match.end():])
            if len(before) == 2 and len(after) >= 2:
                income.append({'metric': metric, 'page': c.get('page'), 'half_year_columns': before,
                               'full_year_columns': after[:2], 'status': 'layout_inferred_unverified', 'source_line': line})
    # Avoid silently choosing one of multiple statements or duplicate candidates.
    dedup = {(r['metric'], r['page'], tuple(r['full_year_columns'])): r for r in income}
    income = sorted(dedup.values(), key=lambda x: (x['page'], x['metric']))
    return {'schema_version': 'v10.0.0', 'document_id': doc.get('document_id'),
            'expected_fiscal_year': doc.get('expected_fiscal_year'),
            'balance_sheet_tables': balances, 'income_statement_candidates': income,
            'balance_consistent_tables': sum(x['status'] == 'arithmetic_consistent_unclassified' for x in balances),
            'financial_validation': 'NOT_VERIFIED',
            'warning': 'Arithmetic consistency does not establish consolidated scope, units, year order or official financial validity.'}

def audit_directory(directory):
    directory = Path(directory)
    results = []
    for path in sorted(directory.glob('*_candidates.json')):
        result = audit(json.loads(path.read_text(encoding='utf-8')))
        (directory / (path.stem.replace('_candidates', '') + '_financial_audit.json')).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        results.append(result)
    (directory / 'financial_audit_summary.json').write_text(json.dumps({'schema_version':'v10.0.0', 'results':results}, ensure_ascii=False, indent=2), encoding='utf-8')
    return results

if __name__ == '__main__':
    import sys
    audits = audit_directory(sys.argv[1] if len(sys.argv) > 1 else 'batch_results')
    print(json.dumps({'version':'v10.0.0','audited_documents':len(audits),'balance_consistent_tables':sum(x['balance_consistent_tables'] for x in audits),'financial_validation':'NOT_VERIFIED'}))
