"""v24: evidence-first S20 share count reconciliation. No fixed share counts in parser."""
import argparse, csv, datetime as dt, json, re
from pathlib import Path
from value_hunter_v23 import S20_PDF, fetch_s20_pdf_text
from value_hunter_shares_v21 import SHARES, calc
from value_hunter_v22 import owner_equity

NUMBER = re.compile(r'(?<![\d,])\d{1,3}(?:,\d{3}){2,}(?![\d,])')
GROSS = re.compile(r'(?:issued(?:\s+and\s+(?:fully\s+)?paid(?:-up)?)?\s+(?:ordinary\s+)?shares|total\s+number\s+of\s+issued\s+shares|share\s+capital)',re.I)
TREASURY = re.compile(r'treasury\s+shares',re.I)
NET = re.compile(r'excluding\s+treasury\s+shares|excluding\s+the\s+treasury\s+shares',re.I)

def numbers(s):
    return [int(m.group().replace(',','')) for m in NUMBER.finditer(s)]

def parse_s20_shares(text):
    """Select unique arithmetic match from share-capital sections, not arbitrary PDF figures.

    Only accept 100m..2bn issued, 0..50m treasury, and net if explicitly
    labelled; otherwise require an unambiguous gross/treasury pair and flag it.
    """
    lines=[re.sub(r'\s+',' ',s).strip() for s in text.splitlines() if s.strip()]
    evidence=[]
    for i,line in enumerate(lines):
        if GROSS.search(line) or TREASURY.search(line) or NET.search(line):
            context=' '.join(lines[max(0,i-2):min(len(lines),i+4)])
            evidence.append({'line':i+1,'text':line[:450], 'context':context[:850], 'numbers':numbers(context)})
    # Group nearby lines so multi-line table rows are supported. Do not match numbers
    # from distant unrelated sections.
    gross=set(); treasury=set(); net=set()
    for i,line in enumerate(lines):
        window=' '.join(lines[i:min(len(lines),i+5)])
        nums=numbers(window)
        if GROSS.search(line) and not ('excluding' in line.lower()):
            gross.update(n for n in nums if 100_000_000<=n<=2_000_000_000)
        if TREASURY.search(line) and not NET.search(line):
            treasury.update(n for n in nums if 1<=n<=50_000_000)
        if NET.search(line):
            net.update(n for n in numbers(' '.join(lines[max(0,i-3):min(len(lines),i+3)])) if 100_000_000<=n<=2_000_000_000)
    # Prefer explicit net arithmetic; do not guess if several pairs fit.
    matches=sorted((g,t,g-t) for g in gross for t in treasury if 100_000_000<=g-t<=2_000_000_000 and (not net or g-t in net))
    if len(matches)!=1:
        reason='AMBIGUOUS_OR_MISSING_GROSS_TREASURY_NET_MATCH'
        return None, {'status':reason,'gross_candidates':sorted(gross),'treasury_candidates':sorted(treasury),'net_candidates':sorted(net),'arithmetic_matches':matches[:30],'evidence':evidence[:80]}
    g,t,n=matches[0]
    # If no explicitly labelled net count exists, reconciliation is only arithmetic,
    # not independently confirmed. Never silently promote it to fully verified.
    status='PDF_THREE_WAY_RECONCILED' if net else 'PDF_GROSS_MINUS_TREASURY_ONLY'
    return {'symbol':'S20','shares_outstanding':n,'issued_shares_including_treasury':g,
        'treasury_shares':t,'as_of_date':'2026-06-30','source_url':S20_PDF,
        'source_detail':'S20 SGX 1H2026 PDF; inferred from share-capital/treasury sections',
        'share_count_basis':'issued_excluding_treasury','verification_status':status}, {'status':status,'gross_candidates':sorted(gross),'treasury_candidates':sorted(treasury),'net_candidates':sorted(net),'evidence':evidence[:80]}

def run(financials,market,output,pdf_text=None):
    fin=json.loads(Path(financials).read_text(encoding='utf-8'))
    quotes=json.loads(Path(market).read_text(encoding='utf-8'))
    lookup={r['symbol']:r for r in quotes.get('records',[])}
    error=None; shares=None; audit={}
    try:
        raw=Path(pdf_text).read_text(encoding='utf-8') if pdf_text else fetch_s20_pdf_text()
        shares,audit=parse_s20_shares(raw)
    except Exception as e:
        error=f'{type(e).__name__}: {e}'
        audit={'status':'FETCH_OR_PDF_PARSE_FAILED','error':error}
    rows=[]
    for f in fin.get('records',[]):
        sym=f['symbol']; sh=shares if sym=='S20' else (dict(SHARES[sym],symbol=sym) if sym in SHARES else None)
        r=calc(f,lookup.get(sym),sh)
        r['pbr_estimate']=None
        eq,eq_status,eq_source=owner_equity(f)
        r.update(parent_equity_sgd_thousands=eq,parent_equity_status=eq_status,parent_equity_source=eq_source)
        if r['market_cap_sgd'] is not None and eq and eq>0:
            r['pbr_estimate']=round(r['market_cap_sgd']/(eq*1000),4)
            r['warnings'].append('PARENT_EQUITY_REFERENCE_NOT_INDEPENDENTLY_VERIFIED')
        else: r['warnings'].append('PARENT_EQUITY_UNAVAILABLE_PBR_SUPPRESSED')
        if sym=='S20' and shares:
            r['warnings'].append(shares['verification_status'])
        elif sym=='S20': r['warnings'].append('S20_SHARE_COUNT_UNVERIFIED')
        r['ranking_eligible']=False
        rows.append(r)
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    payload={'schema_version':'value_hunter_v24','generated_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
        's20_error':error,'s20_share_reconciliation':shares,'records':rows,'ranking_eligible_count':0,
        'note':'Indicative only; not independently verified for investment screening.'}
    (out/'valuation_v24.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (out/'s20_share_audit_v24.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (out/'valuation_v24.csv').open('w',encoding='utf-8',newline='') as fp:
        cols=['symbol','price_sgd','shares_ex_treasury','market_cap_sgd','per_estimate','pbr_estimate','ranking_eligible','warnings']
        writer=csv.DictWriter(fp,fieldnames=cols);writer.writeheader()
        for r in rows:
            writer.writerow(dict(symbol=r['symbol'],price_sgd=r['quote'].get('price_sgd'),
                shares_ex_treasury=(r['shares'] or {}).get('shares_outstanding'),market_cap_sgd=r['market_cap_sgd'],
                per_estimate=r['per_estimate'],pbr_estimate=r['pbr_estimate'],ranking_eligible=False,warnings=';'.join(r['warnings'])))
    print('v24',audit.get('status'),'S20:',(shares or {}).get('shares_outstanding'),'ranking eligible: 0')
    return payload

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--financials',required=True);p.add_argument('--market',required=True)
    p.add_argument('--output',required=True);p.add_argument('--pdf-text');a=p.parse_args()
    run(a.financials,a.market,a.output,a.pdf_text)
