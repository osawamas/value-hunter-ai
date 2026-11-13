"""v22: live issuer IR share-count discovery for S20 and conservative valuation audit.
No investment-ranking eligibility; no claim of independent validation.
"""
import argparse, csv, datetime as dt, html, json, re, urllib.request
from pathlib import Path
from value_hunter_shares_v21 import SHARES, calc

S20_IR='https://straitstrading.listedcompany.com/stock_fundamentals.html'
S20_OWNER_EQUITY_2025_THOUSANDS=1248331
S20_OWNER_EQUITY_SOURCE='https://straitstrading.listedcompany.com/ar.html'

def parse_s20_ir(raw):
    text=html.unescape(re.sub(r'<[^>]*>', ' ', re.sub(r'(?is)<(script|style)\b.*?</\1>', ' ', raw)))
    text=re.sub(r'\s+', ' ', text)
    m=re.search(r'Issued\s*&(?:amp;)?\s*Paid[- ]up\s*Shares\s*(?:\(c\))?\s*([\d,]{7,})',text,re.I)
    if not m: raise ValueError('Issued & Paid-up Shares not found in issuer IR')
    shares=int(m.group(1).replace(',',''))
    if not 100_000_000<=shares<=2_000_000_000: raise ValueError('implausible S20 share count')
    d=re.search(r'Updated\s+on\s+(\d{1,2})/(\d{1,2})/(20\d\d)',text,re.I)
    if not d: raise ValueError('share count date not found; do not infer date')
    asof=dt.date(int(d.group(3)),int(d.group(2)),int(d.group(1)))
    return {'shares_outstanding':shares,'as_of_date':asof.isoformat(),'source_url':S20_IR,
      'source_detail':'Issuer IR: Issued & Paid-up Shares; treasury shares not explicitly deducted',
      'verification_status':'LIVE_IR_ISSUED_SHARES_TREASURY_NOT_DEDUCTED',
      'share_count_basis':'issued_and_paid_up_including_possible_treasury'}

def fetch_s20_ir(timeout=20):
    req=urllib.request.Request(S20_IR,headers={'User-Agent':'Mozilla/5.0 (compatible; VALUE-HUNTER-research/1.0)'})
    with urllib.request.urlopen(req,timeout=timeout) as res:
        return parse_s20_ir(res.read(1_500_000).decode('utf-8','replace'))

def owner_equity(fin):
    year=str(fin['fiscal_year']); metrics=fin.get('metrics',{})
    if fin['symbol']=='S20' and year=='2025':
        return S20_OWNER_EQUITY_2025_THOUSANDS, 'ISSUER_ANNUAL_REPORT_2025_P52_REFERENCE_NOT_AUTOMATED', S20_OWNER_EQUITY_SOURCE
    for key in ('equity_attributable_to_owners','parent_equity','equity_attributable_to_parent'):
        rec=metrics.get(key,{}).get(year) or {}
        if isinstance(rec.get('value'),(int,float)) and rec['value']>0:
            return rec['value'],rec.get('status','UNVERIFIED'),rec.get('source_url')
    return None,None,None

def run(financials,market,output,ir_html=None):
    fin=json.loads(Path(financials).read_text(encoding='utf-8'))
    prices=json.loads(Path(market).read_text(encoding='utf-8'))
    lookup={r['symbol']:r for r in prices.get('records',[])}
    ir_error=None
    try:
        s20=parse_s20_ir(Path(ir_html).read_text(encoding='utf-8')) if ir_html else fetch_s20_ir()
    except (OSError,ValueError,TimeoutError) as exc:
        s20=None; ir_error=f'{type(exc).__name__}: {exc}'
    rows=[]
    for f in fin.get('records',[]):
        symbol=f['symbol']
        share=s20 if symbol=='S20' else SHARES.get(symbol)
        r=calc(f,lookup.get(symbol),dict(share,symbol=symbol) if share else None)
        r['pbr_estimate']=None  # v21 used total group equity, which can include non-controlling interests
        eq,eq_status,eq_source=owner_equity(f)
        r['parent_equity_sgd_thousands']=eq
        r['parent_equity_source']=eq_source
        r['parent_equity_status']=eq_status
        if r['market_cap_sgd'] is not None and eq and eq>0:
            r['pbr_estimate']=round(r['market_cap_sgd']/(eq*1000),4)
        else: r['warnings'].append('PARENT_EQUITY_UNAVAILABLE_PBR_SUPPRESSED')
        if symbol=='S20' and share:
            r['warnings'].append('ISSUED_SHARES_MAY_INCLUDE_TREASURY_MARKET_CAP_INDICATIVE')
        if symbol=='S20' and not share:
            r['warnings'].append('S20_LIVE_IR_FETCH_OR_PARSE_FAILED')
        if symbol=='S20' and r['per_estimate'] is None:
            r['warnings'].append('NEGATIVE_EARNINGS_PER_NOT_MEANINGFUL')
        r['ranking_eligible']=False
        rows.append(r)
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    payload={'schema_version':'value_hunter_v22','generated_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
      's20_ir_error':ir_error,'records':rows,'ranking_eligible_count':0,
      'note':'S20 issued shares may include treasury; all valuations indicative; S20 parent equity is a dated manual source reference.'}
    (output/'valuation_v22.json').write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    with (output/'valuation_v22.csv').open('w',newline='',encoding='utf-8') as fh:
        fields=['symbol','price_sgd','shares_outstanding','shares_as_of','market_cap_sgd','per_estimate','pbr_estimate','parent_equity_sgd_thousands','ranking_eligible','warnings']
        w=csv.DictWriter(fh,fieldnames=fields);w.writeheader()
        for r in rows:
            w.writerow({'symbol':r['symbol'],'price_sgd':r['quote'].get('price_sgd'),'shares_outstanding':(r['shares'] or {}).get('shares_outstanding'),
            'shares_as_of':(r['shares'] or {}).get('as_of_date'),'market_cap_sgd':r['market_cap_sgd'],
            'per_estimate':r['per_estimate'],'pbr_estimate':r['pbr_estimate'],'parent_equity_sgd_thousands':r['parent_equity_sgd_thousands'],
            'ranking_eligible':False,'warnings':';'.join(r['warnings'])})
    print('v22:',len(rows),'rows; S20 live IR:', 'OK' if s20 else 'FAILED', '; ranking eligible: 0')
    return payload

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--financials',required=True);p.add_argument('--market',required=True);p.add_argument('--output',required=True);p.add_argument('--ir-html');a=p.parse_args()
    run(a.financials,a.market,a.output,a.ir_html)
