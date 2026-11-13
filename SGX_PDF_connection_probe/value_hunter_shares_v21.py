"""v21: dated, source-backed share-count snapshots; conservative valuation estimates.
Not a live share-count crawler. Never labels snapshots independently verified.
"""
import argparse, csv, datetime as dt, json, math
from pathlib import Path

SHARES = {
 'S68': {'shares_outstanding': 1070843484, 'as_of_date': '2026-09-01', 'source_url': 'https://investorrelations.sgx.com/financial-information/annual-reports', 'source_detail': 'FY2026 annual report, shareholding statistics: 1,071,642,400 issued less 798,916 treasury', 'verification_status': 'DOCUMENTED_SNAPSHOT_NOT_LIVE_VERIFIED'},
 'G13': {'shares_outstanding': 12063642274, 'as_of_date': '2026-08-14', 'source_url': 'https://gentingsingapore.listedcompany.com/share-quote-and-chart.html', 'source_detail': 'Issuer IR quote page, issued and paid-up shares, updated 14 Aug 2026', 'verification_status': 'DOCUMENTED_SNAPSHOT_NOT_LIVE_VERIFIED'},
}

def positive(x):
 return isinstance(x, (int,float)) and not isinstance(x,bool) and math.isfinite(x) and x>0

def calc(fin, market, share):
 symbol=fin['symbol']; year=str(fin['fiscal_year']); quote=(market or {}).get('price') or {}; price=quote.get('price_sgd')
 result={'symbol':symbol,'fiscal_year':year,'quote':quote,'shares':share,'market_cap_sgd':None,'per_estimate':None,'pbr_estimate':None,'ranking_eligible':False,'warnings':[]}
 if not positive(price): result['warnings'].append('PRICE_MISSING'); return result
 if not share or not positive(share.get('shares_outstanding')): result['warnings'].append('SHARES_MISSING'); return result
 if not share.get('source_url') or not share.get('as_of_date'): result['warnings'].append('SHARES_SOURCE_MISSING'); return result
 try:
  share_date=dt.date.fromisoformat(share['as_of_date']); quote_date=dt.datetime.fromisoformat(quote['market_timestamp_utc'].replace('Z','+00:00')).date()
 except (ValueError,KeyError,TypeError): result['warnings'].append('DATE_MISSING'); return result
 if share_date>quote_date: result['warnings'].append('SHARE_COUNT_NEWER_THAN_QUOTE'); return result
 age=(quote_date-share_date).days
 if age>90: result['warnings'].append('SHARES_STALE_OVER_90_DAYS')
 cap=price*share['shares_outstanding']; result['market_cap_sgd']=round(cap,2)
 metrics=fin.get('metrics',{})
 def val(name): return (metrics.get(name,{}).get(year) or {}).get('value')
 profit=val('attributable_profit'); equity=val('equity')
 if positive(profit): result['per_estimate']=round(cap/(profit*1000),4)
 else: result['warnings'].append('POSITIVE_ATTRIBUTABLE_PROFIT_MISSING')
 if positive(equity): result['pbr_estimate']=round(cap/(equity*1000),4)
 else: result['warnings'].append('POSITIVE_EQUITY_MISSING')
 result['warnings'] += ['SHARE_COUNT_SNAPSHOT_NOT_LIVE_VERIFIED','FINANCIALS_NOT_INDEPENDENTLY_VERIFIED','UNOFFICIAL_PRICE_FEED']
 return result

def run(financials,market,output):
 fin=json.loads(Path(financials).read_text(encoding='utf-8'))
 prices=json.loads(Path(market).read_text(encoding='utf-8'))
 lookup={r['symbol']:r for r in prices.get('records',[])}
 rows=[calc(f,lookup.get(f['symbol']),dict(SHARES[f['symbol']],symbol=f['symbol']) if f['symbol'] in SHARES else None) for f in fin.get('records',[])]
 output=Path(output);output.mkdir(parents=True,exist_ok=True)
 payload={'schema_version':'value_hunter_v21','generated_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'records':rows,'ranking_eligible_count':0,'note':'Indicative valuations only; share snapshots may be stale and are not live-verified.'}
 (output/'valuation_v21.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 with (output/'valuation_v21.csv').open('w',encoding='utf-8',newline='') as fh:
  writer=csv.DictWriter(fh,fieldnames=['symbol','price_sgd','shares_outstanding','shares_as_of','market_cap_sgd','per_estimate','pbr_estimate','ranking_eligible','warnings']);writer.writeheader()
  for r in rows:
   writer.writerow({'symbol':r['symbol'],'price_sgd':r['quote'].get('price_sgd'),'shares_outstanding':(r['shares'] or {}).get('shares_outstanding'),'shares_as_of':(r['shares'] or {}).get('as_of_date'),'market_cap_sgd':r['market_cap_sgd'],'per_estimate':r['per_estimate'],'pbr_estimate':r['pbr_estimate'],'ranking_eligible':False,'warnings':';'.join(r['warnings'])})
 print('v21',len(rows),'records;',sum(r['market_cap_sgd'] is not None for r in rows),'indicative market caps; 0 ranking eligible')
 return payload

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--financials',required=True);p.add_argument('--market',required=True);p.add_argument('--output',required=True);a=p.parse_args();run(a.financials,a.market,a.output)
