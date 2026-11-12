"""v12: capture scope headings with provenance; only explicit unambiguous headings can verify scope."""
import json, re, sys
from pathlib import Path

HEADING = re.compile(r'\b(?:statements? of financial position|balance sheets?|financial position)\b',re.I)
GROUP = re.compile(r'\b(?:consolidated|group)\b',re.I)
COMPANY = re.compile(r'\b(?:company|separate|parent company)\b',re.I)

def compact(text):
    return ' '.join(text.split())

def classify_heading(text):
    """Require financial-position heading and exclusive explicit scope in same line."""
    if not HEADING.search(text): return None
    g=bool(GROUP.search(text)); c=bool(COMPANY.search(text))
    if g == c: return None
    return 'consolidated' if g else 'company'

def inspect(pages, balance_pages, head_lines=28, tail_lines=12):
    out=[]
    for page_no in sorted(set(balance_pages)):
        if page_no<1 or page_no>len(pages):
            out.append({'page':page_no,'status':'PAGE_OUT_OF_RANGE','scope':'unclassified'});continue
        lines=[compact(x) for x in pages[page_no-1].splitlines() if compact(x)]
        prior=[compact(x) for x in pages[page_no-2].splitlines() if compact(x)] if page_no>1 else []
        # Both page beginning and previous page end are diagnostic evidence, not interchangeable headings.
        evidence=[{'page':page_no,'position':'page_start','line':i+1,'text':s} for i,s in enumerate(lines[:head_lines])]
        evidence += [{'page':page_no-1,'position':'previous_page_end','line':len(prior)-len(prior[-tail_lines:])+i+1,'text':s} for i,s in enumerate(prior[-tail_lines:])]
        matches=[dict(e,scope=classify_heading(e['text'])) for e in evidence if HEADING.search(e['text']) or GROUP.search(e['text']) or COMPANY.search(e['text'])]
        # Only same-page explicit heading can certify; previous-page evidence always requires review.
        explicit=[m for m in matches if m['position']=='page_start' and m['scope']]
        scopes={m['scope'] for m in explicit}
        scope=next(iter(scopes)) if len(scopes)==1 else 'unclassified'
        out.append({'page':page_no,'scope':scope,'status':'EXPLICIT_HEADING_FOUND' if scope!='unclassified' else 'REVIEW_REQUIRED',
                    'heading_evidence':matches,'page_start':evidence[:head_lines],
                    'previous_page_end':[e for e in evidence if e['position']=='previous_page_end'],
                    'warning':'Scope is heading evidence only; period, unit, table alignment and numeric checks are still required.'})
    return {'schema_version':'v12.0.0','financial_validation':'NOT_VERIFIED','page_scope_evidence':out}

def run(manifest_path, prior_dir, output_dir):
    from batch_probe import fetch
    import pymupdf
    manifest=json.loads(Path(manifest_path).read_text(encoding='utf-8'))['documents']
    prior_dir=Path(prior_dir);output_dir=Path(output_dir);output_dir.mkdir(parents=True,exist_ok=True)
    reports=[]
    for item in manifest:
        name=item['document_id']; row={'document_id':name,'status':'failed'}
        try:
            old=prior_dir/f'{name}_financial_audit.json'
            prior=json.loads(old.read_text(encoding='utf-8')) if old.exists() else {}
            target_pages=[x['page'] for x in prior.get('balance_sheet_tables',[])]
            raw,http=fetch(item['url'])
            with pymupdf.open(stream=raw,filetype='pdf') as doc:
                pages=[p.get_text(sort=True) for p in doc]
            result=inspect(pages,target_pages)
            result.update({'document_id':name,'http_status':http,'pdf_page_count':len(pages)})
            (output_dir/f'{name}_heading_evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
            row.update({'status':'extracted','balance_pages':target_pages})
        except Exception as e: row['error']=f'{type(e).__name__}: {e}'
        reports.append(row)
    summary={'schema_version':'v12.0.0','financial_validation':'NOT_VERIFIED','reports':reports}
    (output_dir/'heading_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False))
    return summary

if __name__=='__main__':
    root=Path(__file__).resolve().parent
    summary=run(root/'batch_manifest.json','batch_results','batch_results')
    sys.exit(0 if any(r['status']=='extracted' for r in summary['reports']) else 1)
