"""S68-only fail-closed integration of independently audited FY2026 income and balance sheets."""
import json
import sys
from pathlib import Path

VERSION = 'v14.0.0'
REQUIRED = ('operating_revenue', 'net_revenue', 'operating_profit', 'profit_attributable')

def integrate(balance, income):
    if balance.get('financial_validation') != 'VERIFIED_CONSOLIDATED_BALANCE_SHEET_ONLY':
        raise ValueError('Consolidated balance sheet is not verified')
    if balance.get('document_id') != 'S68_FY2026_results':
        raise ValueError('Unexpected balance sheet document')
    bs = balance['consolidated_balance_sheet']
    if bs.get('fiscal_years') != [2026, 2025] or bs.get('currency') != 'SGD' or bs.get('unit_multiplier') != 1000:
        raise ValueError('Balance sheet fiscal year or units mismatch')
    if 'Group' not in bs.get('heading', ''):
        raise ValueError('Consolidated Group heading not verified')
    vals = bs['values_thousands_sgd']
    for i in (0, 1):
        if vals['assets'][i] != vals['liabilities'][i] + vals['equity'][i]:
            raise ValueError('Balance equation mismatch')
    if (income.get('ticker'), income.get('fiscal_year'), income.get('period'), income.get('consolidation'), income.get('currency'), income.get('unit')) != ('S68', 2026, 'FY', 'Group', 'SGD', 'SGD_thousands'):
        raise ValueError('Income scope/year/unit mismatch')
    if income.get('status') != 'verified_against_known_S68_FY2026_values':
        raise ValueError('Income statement is not S68 verified regression output')
    m = income['metrics']
    if set(REQUIRED) - m.keys():
        raise ValueError('Missing income metrics')
    amounts = {k: [m[k]['fy2026_sgd_thousands'], m[k]['fy2025_sgd_thousands']] for k in REQUIRED}
    if not all(all(isinstance(x, int) and not isinstance(x, bool) and x > 0 for x in pair) for pair in amounts.values()):
        raise ValueError('Invalid income amounts')
    if not (amounts['operating_revenue'][0] > amounts['net_revenue'][0] > amounts['operating_profit'][0] > 0):
        raise ValueError('Income sanity check failed')
    def growth(key):
        a, b = amounts[key]
        return round((a / b - 1) * 100, 4)
    return {
        'schema_version': VERSION,
        'ticker': 'S68', 'fiscal_years': [2026, 2025], 'currency': 'SGD', 'unit': 'SGD_thousands',
        'validation': 'VERIFIED_S68_INCOME_KNOWN_VALUES_AND_CONSOLIDATED_BALANCE',
        'scope': 'S68 FY2026 only; income verified against known issuer-specific amounts',
        'balance_sheet': vals, 'income_statement': amounts,
        'derived': {
            'revenue_growth_pct': growth('operating_revenue'),
            'operating_profit_growth_pct': growth('operating_profit'),
            'profit_attributable_growth_pct': growth('profit_attributable'),
            'operating_margin_pct': round(amounts['operating_profit'][0] / amounts['operating_revenue'][0] * 100, 4),
            'equity_to_assets_pct': round(vals['equity'][0] / vals['assets'][0] * 100, 4),
            'liabilities_to_assets_pct': round(vals['liabilities'][0] / vals['assets'][0] * 100, 4),
            'roe_simple_end_year_pct': round(amounts['profit_attributable'][0] / vals['equity'][0] * 100, 4),
        },
        'screening': {'eligible_for_growth_margin_equity_ratio': True, 'eligible_for_per_pbr': False},
        'limitations': ['Not a general SGX issuer parser', 'No verified market price or shares outstanding', 'ROE uses end-of-year total equity, not average parent-attributable equity'],
        'evidence': {'balance_page': bs['page'], 'income_pages': {k: m[k]['page'] for k in REQUIRED}}
    }

def run(directory):
    directory = Path(directory)
    out = directory / 'S68_FY2026_integrated_v14.json'
    try:
        balance = json.loads((directory / 'S68_FY2026_results_consolidated_v13.json').read_text())
        income = json.loads((directory / 'S68_verified_financials.json').read_text())
        result = integrate(balance, income)
        out.write_text(json.dumps(result, indent=2, ensure_ascii=False))
        print('SGX V14 VERIFIED:', out)
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        failure = {'schema_version': VERSION, 'validation': 'NOT_VERIFIED', 'error': str(exc)}
        (directory / 'v14_failure.json').write_text(json.dumps(failure, indent=2))
        print('SGX V14 NOT VERIFIED:', exc, file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(run(sys.argv[1] if len(sys.argv) > 1 else 'batch_results'))
