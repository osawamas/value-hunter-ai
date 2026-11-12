"""v16: conservative multi-issuer financial statement triage from v15 evidence.
No ungrounded claim of verified statements; preserves exact page/line provenance.
"""
import csv
import json
import re
from pathlib import Path

NUM = re.compile(r'(?<![\w])\(?-?\d{1,3}(?:,\d{3})+(?:\.\d+)?\)?(?![\w])')
TARGETS = ('revenue', 'operating_profit', 'attributable_profit', 'total_assets', 'total_liabilities', 'total_equity')
BAD = re.compile(r'\b(?:segment|geographical|highlights|notes? to|other operating income|total assets less|total equity and|non.current assets|investment in subsidiaries)\b', re.I)
PERIOD = re.compile(r'\b(?:FY\s?20\d{2}|20\d{2}|year ended|financial year)\b', re.I)
SCOPE = re.compile(r'\b(?:group|consolidated|company)\b', re.I)

def classify(item):
    evidence = item.get('evidence', [])
    by_page = {}
    for e in evidence:
        by_page.setdefault(e['page'], []).append(e)
    rows=[]
    for page, entries in sorted(by_page.items()):
        labels = set().union(*(set(e.get('labels', [])) for e in entries))
        # A page with at least 3 distinct relevant headings is a plausible statement page.
        distinct = len(labels.intersection(TARGETS))
        if distinct < 2: continue
        for e in entries:
            for label in e.get('labels', []):
                if label not in TARGETS: continue
                line=e.get('text','').strip()
                context=e.get('context','')
                # Exclude obvious narrative / notes / subtotals; candidates still not verified.
                if BAD.search(line): continue
                nums=NUM.findall(context)
                if not nums: continue
                rows.append({'symbol':item['symbol'],'issuer':item['issuer'],'page':page,'line':e['line'],
                  'metric':label,'source_text':line,'numeric_tokens':' | '.join(nums[:12]),
                  'period_evidence':' | '.join(sorted(set(PERIOD.findall(context)),key=str.lower)),
                  'scope_evidence':' | '.join(sorted(set(SCOPE.findall(context)),key=str.lower)),
                  'source_url':item['source_url'],'pdf_sha256':item['pdf_sha256'],
                  'status':'CANDIDATE_NOT_VERIFIED','page_metric_count':distinct})
    return rows

def run(source_dir, output_dir):
    source_dir=Path(source_dir);output_dir=Path(output_dir);output_dir.mkdir(parents=True,exist_ok=True)
    summary=[];allrows=[]
    for path in sorted(source_dir.glob('*_evidence.json')):
        item=json.loads(path.read_text(encoding='utf-8'))
        rows=classify(item)
        allrows.extend(rows)
        summary.append({'symbol':item['symbol'],'issuer':item['issuer'],'pages':item['pages'],
           'statement_candidates':len(rows),'candidate_pages':sorted(set(r['page'] for r in rows)),
           'verified_financial_statements':0,'status':'REQUIRES_COLUMN_AND_SCOPE_VALIDATION'})
    fields=['symbol','issuer','page','line','metric','source_text','numeric_tokens','period_evidence','scope_evidence','source_url','pdf_sha256','status','page_metric_count']
    with (output_dir/'candidate_audit.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(allrows)
    report={'version':'v16.0','issuers':summary,'candidate_rows':len(allrows),'verified_financial_statements':0,
      'limitations':['v15 evidence contexts do not preserve full page headers or column coordinates',
       'numeric tokens are NOT mapped to a fiscal year or consolidated scope',
       'download original PDF and inspect statement layout before marking VERIFIED'],
      'next_step':'page-level text/coordinate extraction and accounting reconciliation'}
    (output_dir/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--input',default='sgx_v15_results');p.add_argument('--output',default='sgx_v16_results')
    args=p.parse_args();print(json.dumps(run(args.input,args.output),ensure_ascii=False,indent=2))
