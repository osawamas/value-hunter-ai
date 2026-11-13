"""v25: date-anchored S20 share count extraction, no arbitrary PDF number selection."""
import argparse
import csv
import datetime as dt
import json
import re
from pathlib import Path

from value_hunter_v23 import S20_PDF, fetch_s20_pdf_text
from value_hunter_shares_v21 import SHARES, calc
from value_hunter_v22 import owner_equity

N = r'(\d{1,3}(?:,\d{3}){2,})'
MONTH = r'(?:June|December)'
DATE = rf'(\d{{1,2}}\s+{MONTH}\s+20\d{{2}})'

def number(s):
    return int(s.replace(',', ''))

def iso_date(s):
    return dt.datetime.strptime(re.sub(r'\s+', ' ', s.strip()), '%d %B %Y').date().isoformat()

def parse_s20_shares(text, target_date='2026-06-30'):
    # Financial PDF often wraps a sentence across 2-3 lines. Preserve original
    # evidence separately; normalize only whitespace for matching.
    normalized = re.sub(r'\s+', ' ', text).replace('’', "'")
    evidence = []
    candidates = {}
    # Anchor each value to a date appearing in the same grammatical statement.
    # The prior-year values are in parentheses and must not become current values.
    pattern = re.compile(
        rf'As\s+at\s+{DATE}\s*,?\s*the\s+Company\s+held\s+{N}\s+treasury\s+shares'
        rf'\s*\(\s*{DATE}\s*:\s*{N}\s*\)'
        rf'.{{0,360}}?total\s+number\s+of\s+issued\s+shares\s+{N}'
        rf'\s*\(\s*{DATE}\s*:\s*{N}\s*\)\s*\(\s*excluding\s+treasury\s+shares\s*\)',
        re.IGNORECASE,
    )
    for match in pattern.finditer(normalized):
        current_date, current_treasury, prior_date, prior_treasury, current_net, prior_date2, prior_net = match.groups()
        a, b, c = iso_date(current_date), iso_date(prior_date), iso_date(prior_date2)
        if b != c or a == b:
            evidence.append({'status':'DATE_LABEL_CONFLICT', 'text':match.group()[:650]})
            continue
        for date, treasury, net, role in [(a,current_treasury,current_net,'current'),(b,prior_treasury,prior_net,'comparison')]:
            t, n = number(treasury), number(net)
            if not (100_000_000 <= n <= 2_000_000_000 and 0 < t < 50_000_000):
                continue
            entry={'as_of_date':date,'treasury_shares':t,'shares_outstanding':n,
                   'issued_shares_including_treasury':n+t,'role':role,
                   'evidence_text':match.group()[:650]}
            candidates.setdefault(date, []).append(entry)
            evidence.append(entry)
    audit={'target_date':target_date,'dates_found':sorted(candidates), 'evidence':evidence,
           'status':'DATE_ANCHORED_EVIDENCE_NOT_FOUND'}
    found=candidates.get(target_date,[])
    unique={(x['shares_outstanding'],x['treasury_shares'],x['issued_shares_including_treasury']) for x in found}
    if len(unique)!=1:
        audit['status']='TARGET_DATE_MISSING' if not found else 'CONFLICTING_TARGET_DATE_VALUES'
        return None,audit
    n,t,g=next(iter(unique))
    # Independent corroboration: a share-capital note should show gross issued
    # shares for the same reporting period. Do not accept figures from unrelated
    # pages without an identifiable share-capital heading.
    share_note = re.search(r'15\.\s*Share\s+capital\b(.{0,2200}?)(?=16\.\s*Treasury\s+shares\b|$)',normalized,re.I)
    gross_confirmed = bool(share_note and re.search(rf'(?<![\d,]){g:,}(?![\d,])',share_note.group(1)))
    audit.update(status='DATE_ANCHORED_RECONCILED' if gross_confirmed else 'DATE_ANCHORED_NET_AND_TREASURY_ONLY',
                 target={'shares_outstanding':n,'treasury_shares':t,'issued_shares_including_treasury':g},
                 gross_confirmed_in_share_capital_note=gross_confirmed)
    shares={'symbol':'S20','shares_outstanding':n,'issued_shares_including_treasury':g,
            'treasury_shares':t,'as_of_date':target_date,'source_url':S20_PDF,
            'source_detail':'S20 1H2026 official PDF; dated share count disclosure',
            'share_count_basis':'issued_excluding_treasury','verification_status':audit['status']}
    return shares,audit

def official_s68_share_snapshot(path):
    record=json.loads(Path(path).read_text(encoding='utf-8'))
    if record.get('symbol')!='S68' or record.get('status')!='OFFICIAL_ANNUAL_SHAREHOLDINGS_RECONCILED':
        raise ValueError('S68 official annual shareholding evidence is not verified')
    data=record.get('snapshot') or {}
    if not record.get('pdf_sha256') or data.get('share_count_basis')!='issued_excluding_treasury':
        raise ValueError('S68 official share count provenance missing')
    if data.get('as_of_date')!='2026-09-01':
        raise ValueError('S68 share snapshot wrong as-of date')
    gross, treasury, net=(data.get(k) for k in ('issued_shares_including_treasury','treasury_shares','shares_outstanding'))
    if (any(not isinstance(v,int) or isinstance(v,bool) for v in (gross,treasury,net))
            or gross<=0 or not 0<=treasury<gross or gross-treasury!=net):
        raise ValueError('S68 official treasury arithmetic failed')
    return {**data, 'symbol':'S68', 'source_url':record['source_url'],
            'source_detail':'FY2026 SGX annual report dated shareholding table',
            'source_pdf_sha256':record['pdf_sha256'],
            'verification_status':'LIVE_OFFICIAL_ANNUAL_SHAREHOLDINGS_RECONCILED'}

def run(financials,market,output,pdf_text=None,s68_shares=None):
    fin=json.loads(Path(financials).read_text(encoding='utf-8'))
    quotes=json.loads(Path(market).read_text(encoding='utf-8'))
    lookup={r['symbol']:r for r in quotes.get('records',[])}
    shares=None
    try:
        raw=Path(pdf_text).read_text(encoding='utf-8') if pdf_text else fetch_s20_pdf_text()
        shares,audit=parse_s20_shares(raw)
    except Exception as e:
        audit={'status':'FETCH_OR_PDF_PARSE_FAILED','error':f'{type(e).__name__}: {e}'}
    rows=[]
    for f in fin.get('records',[]):
        sym=f['symbol']; sh=shares if sym=='S20' else (official_s68_share_snapshot(s68_shares) if sym=='S68' and s68_shares else (dict(SHARES[sym],symbol=sym) if sym in SHARES else None))
        if sh and sh.get('share_count_basis') == 'issued_excluding_treasury':
            issued, treasury = sh.get('issued_shares_including_treasury'), sh.get('treasury_shares')
            if issued is not None or treasury is not None:
                if (not isinstance(issued, int) or not isinstance(treasury, int)
                        or isinstance(issued, bool) or isinstance(treasury, bool)
                        or issued <= treasury or treasury < 0
                        or issued - treasury != sh.get('shares_outstanding')):
                    raise ValueError(f'{sym} treasury subtraction invalid')
        r=calc(f,lookup.get(sym),sh)
        r['pbr_estimate']=None
        eq,eq_status,eq_source=owner_equity(f)
        r.update(parent_equity_sgd_thousands=eq,parent_equity_status=eq_status,parent_equity_source=eq_source)
        if r['market_cap_sgd'] is not None and eq and eq>0:
            r['pbr_estimate']=round(r['market_cap_sgd']/(eq*1000),4)
            r['warnings'].append('PARENT_EQUITY_REFERENCE_NOT_INDEPENDENTLY_VERIFIED')
        else:
            r['warnings'].append('PARENT_EQUITY_UNAVAILABLE_PBR_SUPPRESSED')
        if sym=='S20':
            r['warnings'].append(audit['status'])
            if shares and shares['as_of_date'] != '2026-06-30':
                raise ValueError('S20 wrong share count reference date')
        r['ranking_eligible']=False
        rows.append(r)
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    payload={'schema_version':'value_hunter_v25','generated_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
             's20_share_reconciliation':shares,'records':rows,'ranking_eligible_count':0,
             'note':'Indicative only. Financials and parent equity not independently verified.'}
    (out/'valuation_v25.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'s20_share_audit_v25.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (out/'valuation_v25.csv').open('w',encoding='utf-8',newline='') as fp:
        cols=['symbol','price_sgd','shares_ex_treasury','share_date','market_cap_sgd','per_estimate','pbr_estimate','ranking_eligible','warnings']
        w=csv.DictWriter(fp,fieldnames=cols);w.writeheader()
        for r in rows:
            s=r.get('shares') or {}
            w.writerow(dict(symbol=r['symbol'],price_sgd=r['quote'].get('price_sgd'),shares_ex_treasury=s.get('shares_outstanding'),
                            share_date=s.get('as_of_date'),market_cap_sgd=r['market_cap_sgd'],per_estimate=r['per_estimate'],
                            pbr_estimate=r['pbr_estimate'],ranking_eligible=False,warnings=';'.join(r['warnings'])))
    print('v25',audit['status'],'S20:',(shares or {}).get('shares_outstanding'),'ranking eligible: 0')
    return payload

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--financials',required=True);p.add_argument('--market',required=True)
    p.add_argument('--output',required=True);p.add_argument('--pdf-text');p.add_argument('--s68-shares');a=p.parse_args()
    run(a.financials,a.market,a.output,a.pdf_text,a.s68_shares)
