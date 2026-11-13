"""Best-effort, free SGX price snapshots and conservative valuation join.
Yahoo Finance chart is an unofficial public endpoint; failures are non-fatal and logged.
"""
import argparse
import csv
import datetime as dt
import json
import math
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SYMBOLS = {'S68': 'S68.SI', 'G13': 'G13.SI', 'S20': 'S20.SI', 'S63': 'S63.SI'}

def fetch_price(symbol, timeout=15):
    ticker = SYMBOLS[symbol]
    url = 'https://query1.finance.yahoo.com/v8/finance/chart/' + urllib.parse.quote(ticker) + '?interval=1d&range=5d'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 VALUE-HUNTER-AI/0.20', 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.load(resp)
    result = payload['chart']['result'][0]
    meta = result['meta']
    price = meta.get('regularMarketPrice')
    if not isinstance(price, (float, int)) or not math.isfinite(price) or price <= 0:
        raise ValueError('No valid regularMarketPrice')
    currency = meta.get('currency')
    if currency != 'SGD':
        raise ValueError('Unexpected currency: ' + str(currency))
    market_time = meta.get('regularMarketTime')
    if not isinstance(market_time, int) or market_time <= 0:
        raise ValueError('Missing quote timestamp')
    return {'symbol': symbol, 'provider_ticker': ticker, 'price_sgd': float(price),
            'market_timestamp_utc': dt.datetime.fromtimestamp(market_time, dt.timezone.utc).isoformat(),
            'retrieved_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
            'source': 'YAHOO_FINANCE_UNOFFICIAL_CHART', 'source_url': url,
            'price_status': 'UNVERIFIED_EXTERNAL_QUOTE'}

def finite_positive(x):
    return isinstance(x, (float, int)) and not isinstance(x, bool) and math.isfinite(x) and x > 0

def join_record(financial, quote, shares_record=None):
    """Share counts must have independently supplied source/date; financial units SGD thousands."""
    sym = financial['symbol']
    out = {'symbol': sym, 'fiscal_year': financial.get('fiscal_year'),
           'price': quote, 'shares': shares_record, 'market_cap_sgd': None,
           'per': None, 'pbr': None, 'eligible_for_investment_ranking': False,
           'warnings': []}
    if not quote or not finite_positive(quote.get('price_sgd')):
        out['warnings'].append('PRICE_MISSING'); return out
    if not shares_record or not finite_positive(shares_record.get('shares_outstanding')):
        out['warnings'].append('VERIFIED_SHARES_MISSING'); return out
    if shares_record.get('symbol') != sym or not shares_record.get('as_of_date') or not shares_record.get('source_url') or shares_record.get('verification_status') != 'INDEPENDENTLY_VERIFIED':
        out['warnings'].append('SHARES_PROVENANCE_INCOMPLETE'); return out
    cap = quote['price_sgd'] * shares_record['shares_outstanding']
    out['market_cap_sgd'] = round(cap, 2)
    year = str(financial.get('fiscal_year'))
    metrics = financial.get('metrics', {})
    def metric(key):
        return metrics.get(key, {}).get(year, {}).get('value')
    profit = metric('attributable_profit')
    equity = metric('equity')
    if finite_positive(profit):
        out['per'] = round(cap / (profit * 1000), 4)
    else: out['warnings'].append('POSITIVE_ATTRIBUTABLE_PROFIT_MISSING')
    if finite_positive(equity):
        out['pbr'] = round(cap / (equity * 1000), 4)
    else: out['warnings'].append('POSITIVE_EQUITY_MISSING')
    out['warnings'].append('SOURCE_FINANCIALS_NOT_INDEPENDENTLY_VERIFIED')
    out['warnings'].append('QUOTE_PROVIDER_UNOFFICIAL')
    return out

def run(financials_path, output_dir, shares_path=None, offline_quotes_path=None):
    feed = json.loads(Path(financials_path).read_text(encoding='utf-8'))
    shares = json.loads(Path(shares_path).read_text(encoding='utf-8')) if shares_path else {}
    offline = json.loads(Path(offline_quotes_path).read_text(encoding='utf-8')) if offline_quotes_path else None
    output = Path(output_dir); output.mkdir(parents=True, exist_ok=True)
    records = []; errors = []
    for record in feed.get('records', []):
        sym = record['symbol']
        try:
            quote = offline.get(sym) if offline is not None else fetch_price(sym)
            if quote is None: raise ValueError('No offline quote for ' + sym)
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError, IndexError, OSError, json.JSONDecodeError) as exc:
            errors.append({'symbol': sym, 'error': str(exc)}); quote = None
        records.append(join_record(record, quote, shares.get(sym)))
    result = {'schema_version': 'value_hunter_market_v20', 'generated_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
              'records': records, 'fetch_errors': errors,
              'note': 'Price data is unofficial/unverified; no record is investment-ranking eligible.'}
    (output/'market_valuation_v20.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    with (output/'market_valuation_v20.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['symbol','price_sgd','quote_time_utc','shares_outstanding','market_cap_sgd','per','pbr','ranking_eligible','warnings'])
        writer.writeheader()
        for r in records:
            writer.writerow({'symbol':r['symbol'], 'price_sgd':(r['price'] or {}).get('price_sgd'),
                            'quote_time_utc':(r['price'] or {}).get('market_timestamp_utc'),
                            'shares_outstanding':(r['shares'] or {}).get('shares_outstanding'),
                            'market_cap_sgd':r['market_cap_sgd'], 'per':r['per'], 'pbr':r['pbr'],
                            'ranking_eligible':False, 'warnings':';'.join(r['warnings'])})
    print('Market v20:',len(records),'records;',len(errors),'quote errors')
    return result

if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--financials',required=True);p.add_argument('--output',required=True)
    p.add_argument('--shares');p.add_argument('--offline-quotes')
    a=p.parse_args();run(a.financials,a.output,a.shares,a.offline_quotes)
