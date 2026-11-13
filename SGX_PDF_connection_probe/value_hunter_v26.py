"""Conservative cross-document audit of VALUE HUNTER SGX financial metrics.

References are explicitly curated issuer disclosures, not live-fetched independent audits.
Never marks any security as investment-ranking eligible.
"""
import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

# SGD thousands. Independent document means a DIFFERENT issuer publication,
# not an independent third-party audit. All reference values are dated snapshots.
REFERENCE = {
    'G13': {
        'source': 'https://gentingsingapore.listedcompany.com/newsroom/20260224_173326_G13_A7CVA3KL4JFGECGT.3.pdf',
        'document': 'FY2025 results announcement, Statement of Comprehensive Income',
        'year': '2025',
        'metrics': {'revenue': 2452053, 'operating_profit': 506609, 'attributable_profit': 390346},
    },
    'S20': {
        'source': 'https://links.sgx.com/1.0.0/corporate-announcements/4MEGIOQF57KJ8YNB/876892_20260227%202H2025%20Condensed%20interim%20FS.pdf',
        'document': 'FY2025 condensed financial statements / results announcement',
        'year': '2025',
        'metrics': {'revenue': 623300, 'attributable_profit': -249133},
    },
}

def extract(financial_record, metric, year):
    entry = financial_record.get('metrics', {}).get(metric, {}).get(year)
    if isinstance(entry, dict):
        return entry.get('value')
    return None

def audit(financials, valuation):
    by_symbol = {r['symbol']: r for r in financials.get('records', [])}
    market = {r['symbol']: r for r in valuation.get('records', [])}
    results = []
    for symbol in ('S68', 'G13', 'S20'):
        record = by_symbol.get(symbol, {})
        ref = REFERENCE.get(symbol)
        checks = []
        if ref:
            for metric, expected in ref['metrics'].items():
                actual = extract(record, metric, ref['year'])
                status = ('MATCH_SECOND_ISSUER_DOCUMENT' if actual == expected else
                          'MISSING' if actual is None else 'MISMATCH')
                checks.append({'metric': metric, 'year': ref['year'], 'extracted_sgd_thousands': actual,
                               'reference_sgd_thousands': expected, 'status': status,
                               'reference_document': ref['document'], 'reference_url': ref['source']})
        else:
            checks.append({'metric': None, 'status': 'NO_SECOND_DOCUMENT_REFERENCE',
                           'note': 'S68 uses historical fixed regression data; cannot certify by this audit.'})
        quote = market.get(symbol, {})
        warnings = list(quote.get('warnings') or [])
        all_match = bool(ref) and all(c['status'] == 'MATCH_SECOND_ISSUER_DOCUMENT' for c in checks)
        results.append({'symbol': symbol, 'checks': checks,
                        'cross_document_subset_matched': all_match,
                        'all_financials_independently_verified': False,
                        'investment_ranking_eligible': False,
                        'valuation_reference': {
                            'market_cap_sgd': quote.get('market_cap_sgd'),
                            'per_estimate': quote.get('per_estimate'),
                            'pbr_estimate': quote.get('pbr_estimate')},
                        'warnings': warnings + ['NOT_INDEPENDENT_THIRD_PARTY_VERIFICATION',
                                                'NOT_ALL_REQUIRED_METRICS_VERIFIED']})
    return {'schema_version': 'value_hunter_v26_cross_document_audit',
            'generated_at_utc': datetime.now(timezone.utc).isoformat(),
            'reference_type': 'MANUALLY_CURATED_SECOND_ISSUER_DOCUMENT_SNAPSHOT',
            'reference_values_live_refreshed': False,
            'ranking_eligible_count': 0,
            'records': results}

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--financials', required=True)
    p.add_argument('--valuation', required=True)
    p.add_argument('--output', default='value_hunter_v26_results')
    args = p.parse_args()
    fin = json.loads(Path(args.financials).read_text(encoding='utf-8'))
    val = json.loads(Path(args.valuation).read_text(encoding='utf-8'))
    result = audit(fin, val)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    (out/'audit_v26.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    with (out/'audit_v26.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['symbol','metric','year','extracted_sgd_thousands',
                                                'reference_sgd_thousands','status','reference_url'])
        writer.writeheader()
        for rec in result['records']:
            for check in rec['checks']:
                writer.writerow({k: (rec['symbol'] if k == 'symbol' else check.get(k, ''))
                                 for k in writer.fieldnames})
    print(json.dumps({'symbols': 3, 'checks': sum(len(r['checks']) for r in result['records']),
                      'matched_metrics': sum(c['status']=='MATCH_SECOND_ISSUER_DOCUMENT'
                                             for r in result['records'] for c in r['checks']),
                      'ranking_eligible_count': 0}, indent=2))

if __name__ == '__main__':
    main()
