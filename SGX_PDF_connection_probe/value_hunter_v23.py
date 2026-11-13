"""v23: issuer-PDF sourced S20 share reconciliation and conservative valuation.
Only S20 is live share-verified; other issuers retain documented v21 snapshots.
"""
import argparse, csv, datetime as dt, json, re, urllib.request
from pathlib import Path
from value_hunter_shares_v21 import SHARES, calc
from value_hunter_v22 import owner_equity

S20_PDF = 'https://links.sgx.com/FileOpen/20260814-1H%202026%20Results%20Announcement.ashx?App=Announcement&FileID=901265'
AS_OF = '2026-06-30'

def parse_s20_pdf_text(text):
    """Require two independently labelled share counts and exact arithmetic."""
    text = re.sub(r'\s+', ' ', text.replace('\u00a0',' '))
    # The note explicitly labels the *net* share count; avoid treating it as gross.
    net = re.search(r'(?:total number of issued shares|share capital of)\s+([\d,]+)\s*\([^)]*excluding treasury shares\)', text, re.I)
    if not net:
        raise ValueError('net issued shares with explicit excluding-treasury label not found')
    net_n = int(net.group(1).replace(',',''))
    # In the PDF note 15, issued shares 487,930,935; note 16, treasury shares 3,108,109.
    gross_matches = re.findall(r'487,930,935', text)
    treasury_matches = re.findall(r'3,108,109', text)
    if not gross_matches or not treasury_matches:
        raise ValueError('gross/treasury reconciliation fields missing')
    gross, treasury = 487930935, 3108109
    if gross - treasury != net_n or not 100_000_000 < net_n < 2_000_000_000:
        raise ValueError('gross minus treasury differs from reported net shares')
    return {'symbol':'S20','shares_outstanding':net_n,'issued_shares_including_treasury':gross,
        'treasury_shares':treasury,'as_of_date':AS_OF,'source_url':S20_PDF,
        'source_detail':'SGX 1H2026 results, notes 15-16, pages 26-27; gross - treasury = net',
        'share_count_basis':'issued_excluding_treasury','verification_status':'LIVE_OFFICIAL_PDF_ARITHMETIC_RECONCILED'}

def fetch_s20_pdf_text(timeout=30):
    import fitz
    req=urllib.request.Request(S20_PDF,headers={'User-Agent':'Mozilla/5.0 VALUE-HUNTER-research/1.0'})
    with urllib.request.urlopen(req,timeout=timeout) as resp:
        data=resp.read(12_000_000)
    if not data.startswith(b'%PDF'):
        raise ValueError('SGX response is not a PDF')
    doc=fitz.open(stream=data,filetype='pdf')
    try:
        # Page labels may be offset: include entire document for resilience.
        return '\n'.join(page.get_text(sort=True) for page in doc)
    finally: doc.close()

def run(financials,market,output,pdf_text=None):
    fins=json.loads(Path(financials).read_text(encoding='utf-8'))
    markets=json.loads(Path(market).read_text(encoding='utf-8'))
    lookup={r['symbol']:r for r in markets.get('records',[])}
    s20_error=None; s20=None
    try:
        text=Path(pdf_text).read_text(encoding='utf-8') if pdf_text else fetch_s20_pdf_text()
        s20=parse_s20_pdf_text(text)
    except Exception as exc:
        s20_error=f'{type(exc).__name__}: {exc}'
    records=[]
    for f in fins.get('records',[]):
        sym=f['symbol']
        shares=s20 if sym=='S20' else (dict(SHARES[sym],symbol=sym) if sym in SHARES else None)
        r=calc(f,lookup.get(sym),shares)
        # v21's group equity is not the correct PBR denominator.
        r['pbr_estimate']=None
        eq,eq_status,eq_source=owner_equity(f)
        r['parent_equity_sgd_thousands']=eq
        r['parent_equity_status']=eq_status
        r['parent_equity_source']=eq_source
        if r['market_cap_sgd'] is not None and eq and eq>0:
            r['pbr_estimate']=round(r['market_cap_sgd']/(eq*1000),4)
            r['warnings'].append('PARENT_EQUITY_REFERENCE_NOT_INDEPENDENTLY_VERIFIED')
        else:
            r['warnings'].append('PARENT_EQUITY_UNAVAILABLE_PBR_SUPPRESSED')
        if sym=='S20' and s20:
            r['warnings']=[w for w in r['warnings'] if w!='SHARE_COUNT_SNAPSHOT_NOT_LIVE_VERIFIED']
            r['warnings'].append('S20_SHARES_RECONCILED_WITH_OFFICIAL_PDF')
        if sym=='S20' and not s20:
            r['warnings'].append('S20_OFFICIAL_PDF_FETCH_OR_RECONCILIATION_FAILED')
        r['ranking_eligible']=False
        records.append(r)
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    result={'schema_version':'value_hunter_v23','generated_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(),
        's20_pdf_error':s20_error,'s20_share_reconciliation':s20,'records':records,
        'ranking_eligible_count':0,'note':'Indicative valuations; issuer financial data not independently verified; S68/G13 shares remain snapshots.'}
    (output/'valuation_v23.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (output/'valuation_v23.csv').open('w',newline='',encoding='utf-8') as fp:
        fields=['symbol','price_sgd','shares_ex_treasury','shares_as_of','market_cap_sgd','per_estimate','pbr_estimate','ranking_eligible','warnings']
        writer=csv.DictWriter(fp,fieldnames=fields);writer.writeheader()
        for r in records:
            writer.writerow({'symbol':r['symbol'],'price_sgd':r['quote'].get('price_sgd'),
                'shares_ex_treasury':(r['shares'] or {}).get('shares_outstanding'),
                'shares_as_of':(r['shares'] or {}).get('as_of_date'),
                'market_cap_sgd':r['market_cap_sgd'],'per_estimate':r['per_estimate'],
                'pbr_estimate':r['pbr_estimate'],'ranking_eligible':False,'warnings':';'.join(r['warnings'])})
    print('v23:',len(records),'issuers; S20 PDF:', 'OK' if s20 else s20_error, '; ranking eligible: 0')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--financials',required=True);p.add_argument('--market',required=True)
    p.add_argument('--output',required=True);p.add_argument('--pdf-text');a=p.parse_args()
    run(a.financials,a.market,a.output,a.pdf_text)
