"""SGX v17: capture PDF text coordinates and headers; never certify financial values."""
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import urllib.request

VERSION = 'v17.0.0'
BASE = Path(__file__).resolve().parent
OUTPUT = Path(os.environ.get('SGX_V17_OUTPUT', 'sgx_v17_results'))
KEYWORDS = re.compile(r'(?i)revenue|operating profit|profit attributable|total assets|total liabilities|total equity|shareholders.? equity|statement of financial|income statement|comprehensive income|group|company|consolidated|FY20\d\d|202[3456]|S\$.?000|\$.?000')

def grouped_lines(words, tolerance=2.5):
    """Group PyMuPDF words by block/line; preserve coordinates and text order."""
    buckets = {}
    for w in words:
        x0,y0,x1,y1,token,block,line,*_ = w
        buckets.setdefault((block,line), []).append((float(x0),float(y0),float(x1),float(y1),str(token)))
    result=[]
    for items in buckets.values():
        items.sort(key=lambda t:t[0]); text=' '.join(t[4] for t in items)
        result.append({'text':text,'x0':round(min(t[0] for t in items),2),'y0':round(min(t[1] for t in items),2),'x1':round(max(t[2] for t in items),2),'y1':round(max(t[3] for t in items),2),'words':[{'text':t[4],'x0':round(t[0],2),'x1':round(t[2],2)} for t in items]})
    result.sort(key=lambda r:(r['y0'],r['x0']))
    return result

def analyze_page(page, number):
    lines=grouped_lines(page.get_text('words'))
    matches=[{'line_index':i, **line} for i,line in enumerate(lines) if KEYWORDS.search(line['text'])]
    return {'page':number,'width':round(page.rect.width,2),'height':round(page.rect.height,2),
            'lines':lines,'matches':matches,'page_header':lines[:35],
            'status':'LAYOUT_EVIDENCE_ONLY_NOT_VERIFIED'}

def fetch(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; ValueHunterAudit/17.0)','Accept':'application/pdf,*/*'})
    with urllib.request.urlopen(req,timeout=75) as r:
        data=r.read(35_000_001)
        if len(data)>35_000_000: raise ValueError('PDF exceeds 35MB safety limit')
        if not data.startswith(b'%PDF-'): raise ValueError('Response is not a PDF')
        return data

def run():
    try: import fitz
    except ImportError as e: raise RuntimeError('PyMuPDF is required: pip install pymupdf') from e
    OUTPUT.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((BASE/'coordinate_manifest_v17.json').read_text())
    summary=[]
    for issuer in manifest['issuers']:
        symbol=issuer['symbol']; result={'symbol':symbol,'issuer':issuer['issuer'],'status':'ERROR','requested_pages':issuer['pages'],'verified_financial_statements':0}
        try:
            data=fetch(issuer['url']); doc=fitz.open(stream=data,filetype='pdf')
            result.update(pdf_sha256=hashlib.sha256(data).hexdigest(),total_pages=len(doc),status='LAYOUT_CAPTURED_NOT_VERIFIED')
            pages=[]
            for p in issuer['pages']:
                if p<1 or p>len(doc): continue
                pages.append(analyze_page(doc[p-1],p))
            result['captured_pages']=[p['page'] for p in pages]
            (OUTPUT/f'{symbol}_layout_v17.json').write_text(json.dumps({'version':VERSION,'source_url':issuer['url'],'issuer':issuer['issuer'],'symbol':symbol,'pdf_sha256':result['pdf_sha256'],'pages':pages,'verified_financial_statements':0},ensure_ascii=False,indent=2))
            doc.close()
        except Exception as exc:
            result['error']=f'{type(exc).__name__}: {exc}'
        summary.append(result)
        print(f"{symbol}: {result['status']} {result.get('captured_pages',[])}",flush=True)
    (OUTPUT/'report.json').write_text(json.dumps({'version':VERSION,'results':summary,'verified_financial_statements':0,'note':'Coordinate evidence only. No values are verified.'},indent=2))
    with (OUTPUT/'summary.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['symbol','issuer','status','total_pages','captured_pages','error'],extrasaction='ignore');writer.writeheader()
        for row in summary:writer.writerow({**row,'captured_pages':str(row.get('captured_pages',[]))})
    return 0 if all(r['status']=='LAYOUT_CAPTURED_NOT_VERIFIED' for r in summary) else 1

if __name__=='__main__': sys.exit(run())
