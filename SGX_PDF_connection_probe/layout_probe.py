"""Inspect text positions in real SGX PDF without assuming extraction order.

Diagnostic only. Does not certify financial statements or create trading signals.
"""
import json
import re
from pathlib import Path

LABELS = {
    'operating_revenue': re.compile(r'operating\s+revenue', re.I),
    'net_revenue': re.compile(r'net\s+revenue', re.I),
    'operating_profit': re.compile(r'operating\s+profit', re.I),
    'profit_attributable': re.compile(r'profit\s+attributable', re.I),
}
NUM = re.compile(r'^\(?-?\d{1,3}(?:,\d{3})+\)?$')


def inspect_document(doc, outdir):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    diagnostics = []
    for index, page in enumerate(doc):
        words = page.get_text('words', sort=False)
        lines = {}
        for x0, y0, x1, y1, word, block, line, wordno in words:
            lines.setdefault((block, line), []).append((float(x0), float(y0), str(word)))
        rows = []
        for cells in lines.values():
            cells.sort(key=lambda c: c[0])
            rowtext = ' '.join(c[2] for c in cells)
            if any(p.search(rowtext) for p in LABELS.values()):
                y = sum(c[1] for c in cells)/len(cells)
                neighbors = [
                    {'x': round(float(x), 2), 'y': round(float(yy), 2), 'text': w}
                    for x, yy, _, _, w, *_ in words
                    if abs(float(yy) - y) < 11 and (NUM.match(str(w)) or re.search(r'\d', str(w)))
                ]
                rows.append({'label': rowtext[:250], 'y': round(y,2), 'numeric_near_row':neighbors[:35]})
        if rows:
            page_text = page.get_text(sort=True)
            headers = [line[:180] for line in page_text.splitlines() if re.search(r'(2026|2025|FY26|FY25|2H26|2H25|S\$.?000|SGD.?000|thousand)', line, re.I)]
            diagnostics.append({'page':index+1,'page_width':round(page.rect.width,2),'page_height':round(page.rect.height,2),'headers':headers[:35],'rows':rows[:30]})
            (outdir / f'page_{index+1:02d}_text.txt').write_text(page_text[:120000],encoding='utf-8')
    (outdir/'layout_diagnostics.json').write_text(json.dumps({'schema_version':1,'pages_with_labels':diagnostics},indent=2,ensure_ascii=False),encoding='utf-8')
    return diagnostics
