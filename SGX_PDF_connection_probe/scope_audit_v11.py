"""SGX v11: page-context evidence for scope classification; never silently verifies values."""
import json, re, sys
from pathlib import Path

SCOPE = re.compile(r'\b(consolidated|group|company|separate|parent company)\b', re.I)
PERIOD = re.compile(r'\b(FY\s*20\d\d|20\d\d|full year|year ended|half.year|six months)\b', re.I)
UNITS = re.compile(r'\b(S\$\s*[\'’]?000|SGD\s*[\'’]?000|S\$\s*million|SGD\s*million|in thousands|in millions)\b', re.I)
BALANCE = re.compile(r'\btotal (?:assets|liabilities|equity)\b', re.I)

def context_for_page(page_text, page_number, window=16):
    lines = [' '.join(s.split()) for s in page_text.splitlines()]
    hits = [i for i, line in enumerate(lines) if BALANCE.search(line)]
    tables = []
    for idx in hits:
        preceding = [(j+1, lines[j]) for j in range(max(0, idx-window), idx) if lines[j]]
        scope = [(j, line) for j, line in preceding if SCOPE.search(line)]
        period = [(j, line) for j, line in preceding if PERIOD.search(line)]
        units = [(j, line) for j, line in preceding if UNITS.search(line)]
        tables.append({'page':page_number,'row_line':idx+1,'row_text':lines[idx],
                       'preceding_lines':preceding[-window:], 'scope_mentions':scope,
                       'period_mentions':period,'unit_mentions':units})
    return tables

def audit_pages(pages, expected_balance_pages=None):
    expected_balance_pages = expected_balance_pages or []
    all_tables = [t for p, page in enumerate(pages,1) for t in context_for_page(page,p)]
    by_page = {}
    for t in all_tables:
        by_page.setdefault(t['page'], []).append(t)
    summaries=[]
    for p in sorted(set(expected_balance_pages) | set(by_page)):
        matches=by_page.get(p, [])
        scopes={m.group(1).lower() for t in matches for _,s in t['scope_mentions'] for m in SCOPE.finditer(s)}
        # Scope language in the surrounding text is evidence, not proof of which table it labels.
        summaries.append({'page':p,'scope_words':sorted(scopes), 'scope':'unclassified',
                          'status':'CONTEXT_REVIEW_REQUIRED', 'table_rows':matches,
                          'warning':'Nearby scope words are not sufficient to certify a table as consolidated.'})
    return {'schema_version':'v11.0.0','financial_validation':'NOT_VERIFIED',
            'page_scope_evidence':summaries}

def run(manifest_path, prior_dir, output_dir, downloader=None):
    # Import existing v9 fetch function to keep same PDF sources and limits.
    if downloader is None:
        from batch_probe import fetch
        downloader=fetch
    import pymupdf
    manifest=json.loads(Path(manifest_path).read_text(encoding='utf-8'))['documents']
    output_dir=Path(output_dir);output_dir.mkdir(parents=True,exist_ok=True)
    reports=[]
    for item in manifest:
        name=item['document_id']; report={'document_id':name,'ticker':item['ticker'],'status':'failed'}
        try:
            raw,status=downloader(item['url'])
            with pymupdf.open(stream=raw,filetype='pdf') as doc:
                pages=[page.get_text(sort=True) for page in doc]
            prior=Path(prior_dir)/f'{name}_financial_audit.json'
            balance_pages=[]
            if prior.exists():
                previous=json.loads(prior.read_text(encoding='utf-8'))
                balance_pages=[b['page'] for b in previous.get('balance_sheet_tables',[])]
            result=audit_pages(pages,balance_pages)
            result.update({'document_id':name,'http_status':status,'pdf_page_count':len(pages)})
            (output_dir/f'{name}_scope_evidence.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
            report.update({'status':'context_extracted','scope_pages':len(result['page_scope_evidence'])})
        except Exception as exc:
            report['error']=f'{type(exc).__name__}: {exc}'
        reports.append(report)
    summary={'schema_version':'v11.0.0','reports':reports,'financial_validation':'NOT_VERIFIED'}
    (output_dir/'scope_summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))
    return summary

if __name__=='__main__':
    root=Path(__file__).resolve().parent
    summary=run(root/'batch_manifest.json','batch_results','batch_results')
    sys.exit(0 if any(r['status']=='context_extracted' for r in summary['reports']) else 1)
