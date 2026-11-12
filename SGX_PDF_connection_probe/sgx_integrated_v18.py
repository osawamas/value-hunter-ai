"""Conservative SGX annual-report parser. Only exact, column-aligned financial rows qualify."""
import csv, hashlib, json, os, re, sys, urllib.request
from pathlib import Path

BASE=Path(__file__).resolve().parent
OUT=Path(os.environ.get('SGX_V18_OUTPUT','sgx_v18_results'))
SOURCES={
 'G13':{'issuer':'Genting Singapore Limited','url':'https://links.sgx.com/FileOpen/Annual%20Report%202025.ashx?App=Announcement&FileID=880160','page':36},
 'S20':{'issuer':'The Straits Trading Company Limited','url':'https://links.sgx.com/FileOpen/Annual%20Report%20FY2025.ashx?App=Announcement&FileID=881971','income_page':51,'balance_page':52},
}
NUM=re.compile(r'^\(?-?\d{1,3}(?:,\d{3})*(?:\.\d+)?\)?$|^\(?-?\d+\)?$')

def number(s):
 s=s.strip().replace('−','-')
 if not NUM.fullmatch(s):return None
 neg=s.startswith('(')
 s=s.strip('()').replace(',','')
 try:return -int(s) if neg else int(s)
 except ValueError:return None

def lines(page):
 buckets={}
 for x0,y0,x1,y1,token,block,line,*_ in page.get_text('words'):
  buckets.setdefault((block,line),[]).append((float(x0),float(y0),str(token)))
 out=[]
 for group in buckets.values():
  group.sort();out.append({'x':min(t[0] for t in group),'y':min(t[1] for t in group),'text':' '.join(t[2] for t in group)})
 return sorted(out,key=lambda x:(x['y'],x['x']))

def find_row(ls,label,region,anchors,year,group,unit='SGD_thousands'):
 candidates=[r for r in ls if region[0]<=r['x']<region[1] and r['text'].strip().casefold()==label.casefold()]
 if len(candidates)!=1:return {'status':'UNVERIFIED','reason':f'exact label {label!r} occurs {len(candidates)} times'}
 row=candidates[0];found={}
 for yr,anchor in anchors.items():
  matches=[r for r in ls if abs(r['y']-row['y'])<=1.2 and abs(r['x']-anchor)<=19 and number(r['text']) is not None]
  if len(matches)!=1:return {'status':'UNVERIFIED','reason':f'{label}: {yr} column ambiguous ({len(matches)} matches)','label_y':row['y']}
  found[yr]={'value':number(matches[0]['text']),'value_x':round(matches[0]['x'],2),'label_y':round(row['y'],2)}
 return {'status':'EXTRACTED','label':label,'scope':group,'unit':unit,'periods':found}

def headers_ok(ls, anchors, group_x=None):
 for year,x in anchors.items():
  if not any(r['text'].strip()==str(year) and abs(r['x']-x)<25 and r['y']<185 for r in ls):return False
 if group_x is not None and not any(r['text'].strip().casefold()=='group' and abs(r['x']-group_x)<35 and r['y']<170 for r in ls):return False
 return any('000' in r['text'] and r['y']<185 for r in ls)

def parse_g13(ls):
 a={2025:417,2024:490}; b={2025:866,2024:938}
 valid_income=headers_ok(ls,a,454);valid_balance=headers_ok(ls,b,907)
 inc={k:find_row(ls,v,(40,400),a,2025,'Group') if valid_income else {'status':'UNVERIFIED','reason':'income headers missing'} for k,v in {'revenue':'Revenue','operating_profit':'Operating profit','attributable_profit':'Net profit attributable to ordinary shareholders of the Company'}.items()}
 equity=find_row(ls,'Total equity',(640,830),b,2025,'Group') if valid_balance else {'status':'UNVERIFIED','reason':'balance headers missing'}
 return {'income':inc,'balance':{'equity':equity},'checks':{'balance_equation':'NOT_CHECKABLE_ON_THIS_PAGE'}}

def parse_s20(income,balance):
 ai={2025:439,2024:507};ab={2025:297,2024:364};ar={2025:892,2024:959}
 inc_ok=headers_ok(income,ai);bal_ok=headers_ok(balance,ab,337) and headers_ok(balance,ar,932)
 inc={k:find_row(income,v,(35,350),ai,2025,'Group') if inc_ok else {'status':'UNVERIFIED','reason':'income headers missing'} for k,v in {'revenue':'Revenue','net_profit':'(Loss)/profit for the year','attributable_profit':'Owners of the Company'}.items()}
 bal={k:find_row(balance,v,reg,anchors,2025,'Group') if bal_ok else {'status':'UNVERIFIED','reason':'balance headers missing'} for k,v,reg,anchors in [('assets','Total assets',(35,280),ab),('liabilities','Total liabilities',(630,850),ar),('equity','Total equity',(630,850),ar)]}
 checks={}
 for yr in [2025,2024]:
  if all(bal[k]['status']=='EXTRACTED' for k in ['assets','liabilities','equity']):
   a=bal['assets']['periods'][yr]['value']; l=bal['liabilities']['periods'][yr]['value'];e=bal['equity']['periods'][yr]['value']
   checks[str(yr)]={'assets':a,'liabilities':l,'equity':e,'difference':a-l-e,'passed':a==l+e}
  else:checks[str(yr)]={'passed':False,'reason':'missing balance line'}
 return {'income':inc,'balance':bal,'checks':{'balance_equation':checks}}

def fetch(url):
 req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (ValueHunterAI; financial audit)','Accept':'application/pdf,*/*'})
 with urllib.request.urlopen(req,timeout=90) as r:
  data=r.read(35_000_001)
 if len(data)>35_000_000 or not data.startswith(b'%PDF-'):raise ValueError('PDF invalid or too large')
 return data

def run():
 import fitz
 OUT.mkdir(parents=True,exist_ok=True);summary=[];exports=[]
 for sym,src in SOURCES.items():
  status={'symbol':sym,'issuer':src['issuer'],'status':'ERROR','verified_fields':0}
  try:
   raw=fetch(src['url']);doc=fitz.open(stream=raw,filetype='pdf')
   if sym=='G13': parsed=parse_g13(lines(doc[src['page']-1]));pages=[src['page']]
   else:parsed=parse_s20(lines(doc[src['income_page']-1]),lines(doc[src['balance_page']-1]));pages=[src['income_page'],src['balance_page']]
   checks=parsed['checks']['balance_equation'];balance_pass=(sym=='S20' and all(x.get('passed') for x in checks.values()))
   for section in ('income','balance'):
    for key,field in parsed[section].items():
     if field['status']!='EXTRACTED':continue
     # S20 balance is only certified if both years reconcile; G13 income rows are structurally checked only.
     verified=balance_pass and section=='balance'
     field['status']='VERIFIED_ARITHMETIC' if verified else 'EXTRACTED_NOT_INDEPENDENTLY_VERIFIED'
     if verified:status['verified_fields']+=1
     for yr,point in field['periods'].items():
      exports.append({'symbol':sym,'issuer':src['issuer'],'section':section,'field':key,'year':yr,'value':point['value'],'unit':field['unit'],'scope':field['scope'],'status':field['status'],'source_url':src['url'],'pdf_sha256':hashlib.sha256(raw).hexdigest(),'page':pages[0] if section=='income' else pages[-1]})
   status.update(status='PARSED_WITH_VALIDATION' if balance_pass else 'EXTRACTED_PENDING_VALIDATION',pdf_sha256=hashlib.sha256(raw).hexdigest(),pages=pages)
   (OUT/f'{sym}_financial_v18.json').write_text(json.dumps({'version':'v18.0','symbol':sym,'source_url':src['url'],'pdf_sha256':status['pdf_sha256'],'pages':pages,'data':parsed,'note':'Verified arithmetic means accounting equation matches; not independently audited by this program.'},indent=2))
   doc.close()
  except Exception as exc:status['error']=f'{type(exc).__name__}: {exc}'
  summary.append(status);print(sym,status,flush=True)
 (OUT/'report.json').write_text(json.dumps({'version':'v18.0','results':summary,'warning':'G13 income values extracted but not independently verified. S20 balance fields only certified after arithmetic checks.'},indent=2))
 with (OUT/'financials.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['symbol','issuer','section','field','year','value','unit','scope','status','source_url','pdf_sha256','page']);w.writeheader();w.writerows(exports)
 return 1 if any(s['status']=='ERROR' for s in summary) else 0
if __name__=='__main__':sys.exit(run())
