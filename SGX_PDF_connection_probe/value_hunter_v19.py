import argparse,csv,json
from pathlib import Path
from datetime import datetime,timezone

def ratio(a,b):
 return round(a/b*100,4) if a is not None and b is not None and b!=0 else None

def normalize_s68(path):
 d=json.loads(Path(path).read_text()); years=d['fiscal_years']; fields={'revenue':('income_statement','operating_revenue'),'operating_profit':('income_statement','operating_profit'),'attributable_profit':('income_statement','profit_attributable'),'assets':('balance_sheet','assets'),'liabilities':('balance_sheet','liabilities'),'equity':('balance_sheet','equity')}
 return {'symbol':'S68','issuer':'Singapore Exchange Limited','fiscal_year':years[0],'source_kind':'HISTORICAL_V14_ISSUER_SPECIFIC_FIXTURE','source_url':'https://investorrelations.sgx.com/static-files/dcbd5905-9373-4dc9-80f5-8dbff6b8d584','pdf_sha256':None,'metrics':{k:{str(y):{'value':v,'status':'ISSUER_SPECIFIC_REFERENCE_CHECK'} for y,v in zip(years,d[sec][key])} for k,(sec,key) in fields.items()}}

def normalize_s68_official(path):
    """Only replace the S68 fixture with a successful official FY2026 PDF parse."""
    record=json.loads(Path(path).read_text(encoding='utf-8'))
    if record.get('symbol')!='S68' or record.get('status')!='EXTRACTED_ISSUER_PDF_REGRESSION_MATCHED':
        raise ValueError('S68 official PDF evidence is not verified')
    metrics=record.get('metrics') or {}
    if not record.get('pdf_sha256') or not record.get('source_url'):
        raise ValueError('S68 official PDF provenance missing')
    for key in ('revenue','operating_profit','attributable_profit','assets','liabilities','equity'):
        for year in ('2026','2025'):
            entry=metrics.get(key,{}).get(year,{})
            if (not isinstance(entry.get('value'),int) or entry.get('value')<=0
                    or entry.get('status')!='EXTRACTED_ISSUER_PDF_REGRESSION_MATCHED'):
                raise ValueError('S68 PDF missing authenticated field '+key+'/'+year)
    return {key:record[key] for key in ('symbol','issuer','fiscal_year','source_kind','source_url','pdf_sha256','metrics')}

def normalize_v18(path,symbol):
 d=json.loads(Path(path).read_text()); assert d['symbol']==symbol
 fields={'revenue':('income','revenue'),'operating_profit':('income','operating_profit'),'attributable_profit':('income','attributable_profit'),'assets':('balance','assets'),'liabilities':('balance','liabilities'),'equity':('balance','equity')}
 metrics={}
 for key,(section,name) in fields.items():
  src=d['data'].get(section,{}).get(name)
  if src and 'periods' in src:metrics[key]={str(y):{'value':p['value'],'status':src['status'],'page':d.get('pages',[None])[0 if section=='income' else -1]} for y,p in src['periods'].items()}
 return {'symbol':symbol,'issuer':{'G13':'Genting Singapore Limited','S20':'The Straits Trading Company Limited'}[symbol],'fiscal_year':2025,'source_kind':'LIVE_V18_PDF_EXTRACT','source_url':d.get('source_url'),'pdf_sha256':d.get('pdf_sha256'),'metrics':metrics}

def merge_g13_balance(record, evidence_path):
    """Only merge audited-equation values from the exact upstream annual PDF."""
    balance=json.loads(Path(evidence_path).read_text(encoding='utf-8'))
    if (record.get('symbol')!='G13' or balance.get('symbol')!='G13'):
        raise ValueError('Wrong issuer for G13 balance evidence')
    if (balance.get('status')!='EXTRACTED_GROUP_BALANCE_ARITHMETIC_MATCHED'):
        return record
    if record.get('pdf_sha256') != balance.get('pdf_sha256'):
        raise ValueError('Different annual PDF SHA256')
    for year in ('2025','2024'):
        if balance.get('checks',{}).get(year,{}).get('matched') is not True:
            raise ValueError('G13 balance checks incomplete')
        items=balance['metrics']
        assets=items['assets'][year]['value']
        liabilities=items['liabilities'][year]['value']
        equity=record['metrics']['equity'][year]['value']
        if balance['metrics']['parent_equity'][year]['value'] != equity:
            raise ValueError('G13 parent equity does not match Group statement')
        if assets-liabilities != equity:
            raise ValueError('G13 balance equation failed')
    for key in ('assets','liabilities','parent_equity'):
        record['metrics'][key]=balance['metrics'][key]
    record['g13_balance_evidence']={
        'page_pdf_number':balance.get('page_pdf_number'),
        'status':balance['status'],
        'scope':'Group',
        'unit':'SGD_thousands',
    }
    return record

def get(r,key,year):return r['metrics'].get(key,{}).get(str(year),{}).get('value')

def derive(r):
 y=r['fiscal_year'];rev=get(r,'revenue',y);prior=get(r,'revenue',y-1);op=get(r,'operating_profit',y);p_op=get(r,'operating_profit',y-1);profit=get(r,'attributable_profit',y);p_profit=get(r,'attributable_profit',y-1);a=get(r,'assets',y);l=get(r,'liabilities',y);e=get(r,'equity',y)
 r['derived']={'revenue_growth_pct':ratio(rev-prior,prior) if rev is not None and prior is not None and prior>0 else None,'operating_profit_growth_pct':ratio(op-p_op,p_op) if op is not None and p_op is not None and p_op>0 else None,'attributable_profit_growth_pct':ratio(profit-p_profit,p_profit) if profit is not None and p_profit is not None and p_profit>0 else None,'operating_margin_pct':ratio(op,rev),'equity_to_assets_pct':ratio(e,a),'balance_equation_difference':a-l-e if None not in (a,l,e) else None,'per':None,'pbr':None,'market_cap':None}
 r['quality']={'eligible_for_investment_ranking':False,'reason':'Source data not independently verified; market price/share-date checks remain required.'}
 return r

def main():
 p=argparse.ArgumentParser();p.add_argument('--v18-dir',required=True);p.add_argument('--s68',required=True);p.add_argument('--s68-official');p.add_argument('--s63');p.add_argument('--g13-balance');p.add_argument('--output',required=True);args=p.parse_args();out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
 records=[];errors=[]
 for sym in ['S68','G13','S20']:
  try:
   rec = (normalize_s68_official(args.s68_official) if args.s68_official else normalize_s68(args.s68)) if sym=='S68' else normalize_v18(Path(args.v18_dir)/f'{sym}_financial_v18.json',sym)
   if sym=='G13' and args.g13_balance:
    rec=merge_g13_balance(rec,args.g13_balance)
   records.append(derive(rec))
  except (OSError,KeyError,ValueError,AssertionError,TypeError) as ex:errors.append({'symbol':sym,'error':str(ex)})

 s63_status=None
 if args.s63:
  try:
   source=json.loads(Path(args.s63).read_text(encoding='utf-8'))
   s63_status=source.get('status')
   if s63_status=='EXTRACTED_AUDITED_ISSUER_PDF_ARITHMETIC_MATCHED' and source.get('record'):
    records.append(derive(source['record']))
  except (OSError,ValueError,KeyError,TypeError) as ex:
   s63_status='NOT_VERIFIED: '+str(ex)[:180]
 
 (out/'value_hunter_financials.json').write_text(json.dumps({'schema_version':'value_hunter_financials_v1','generated_at_utc':datetime.now(timezone.utc).isoformat(),'records':records,'errors':errors},indent=2)+'\n')
 with (out/'value_hunter_summary.csv').open('w',newline='') as f:
  columns=['symbol','year','revenue','revenue_growth_pct','operating_profit','operating_margin_pct','attributable_profit','assets','liabilities','equity','equity_to_assets_pct','balance_equation_difference','ranking_eligible'];w=csv.DictWriter(f,fieldnames=columns);w.writeheader()
  for r in records:
   y=r['fiscal_year'];w.writerow({'symbol':r['symbol'],'year':y,**{k:get(r,k,y) for k in ['revenue','operating_profit','attributable_profit','assets','liabilities','equity']},**{k:r['derived'][k] for k in ['revenue_growth_pct','operating_margin_pct','equity_to_assets_pct','balance_equation_difference']},'ranking_eligible':False})
 (out/'integration_report.json').write_text(json.dumps({'processed':len(records),'errors':errors,'s63_status':s63_status},indent=2)+'\n');print('Processed:',len(records),'errors:',errors)
 return bool(errors)
if __name__=='__main__':raise SystemExit(main())
