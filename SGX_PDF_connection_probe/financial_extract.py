"""S68 FY2026 issuer-specific, fail-closed full-year statement extractor.

The income statement displays 2H26, 2H25, % change, row label,
FY26, FY25, % change. Only values to the RIGHT of the row label count.
"""
import re

EXPECTED = {
    'operating_revenue': ('Operating revenue', 1559469, 1370625),
    'net_revenue': ('Operating revenue less transaction-based expenses (net revenue)', 1478321, 1298167),
    'operating_profit': ('Operating profit', 887190, 742843),
    'profit_attributable': ('Equity holders of the Company', 698411, 647983),
}
AMOUNT = re.compile(r'\(?-?\d{1,3}(?:,\d{3})+\)?')

def _amounts(text):
    out=[]
    for m in AMOUNT.finditer(text):
        v=m.group(0)
        n=int(v.strip('()').replace(',',''))
        out.append(-n if v.startswith('(') else n)
    return out

def _extract_statement(page, page_no):
    if 'Income Statement - Group' not in page or '2H' not in page or 'FY2026' not in page or "S$'000" not in page:
        return None
    # Limit scope to the first income statement; avoid comprehensive income and notes.
    statement=page.split('Income Statement - Group',1)[1].split('Statement of Comprehensive Income - Group',1)[0]
    lines=[re.sub(r'\s+',' ',x).strip() for x in statement.splitlines() if x.strip()]
    found={}
    for key,(label,expected_cur,expected_prev) in EXPECTED.items():
        candidates=[]
        for line in lines:
            if label.casefold() not in line.casefold(): continue
            # Reject longer rows whose labels merely contain the target (e.g. operating revenue subtotals).
            before,after=re.split(re.escape(label),line,maxsplit=1,flags=re.I)
            if key=='operating_revenue' and ('less transaction' in after.casefold() or 'less transaction' in line.casefold()):continue
            if key=='operating_profit' and ('margin' in after.casefold() or 'before' in after.casefold()):continue
            vals=_amounts(after)
            if len(vals)<2:continue
            cur,prev=vals[0],vals[1]
            if (cur,prev)!=(expected_cur,expected_prev):continue
            candidates.append({'fy2026_sgd_thousands':cur,'fy2025_sgd_thousands':prev,'page':page_no})
        if len(candidates)!=1: return None
        found[key]=candidates[0]
    return found

def extract_s68_fy2026(pages):
    if not pages: raise ValueError('empty PDF')
    matches=[m for i,p in enumerate(pages,1) if (m:=_extract_statement(p,i)) is not None]
    if len(matches)!=1:
        raise ValueError(f'Expected one validated FY2026 consolidated income statement; found {len(matches)}')
    d=matches[0]
    rev=d['operating_revenue']['fy2026_sgd_thousands']
    prev=d['operating_revenue']['fy2025_sgd_thousands']
    op=d['operating_profit']['fy2026_sgd_thousands']
    net=d['net_revenue']['fy2026_sgd_thousands']
    profit=d['profit_attributable']['fy2026_sgd_thousands']
    if not (rev>net>op>0 and rev>profit>0 and prev>0):
        raise ValueError('income statement internal sanity checks failed')
    return {
      'ticker':'S68','market':'SG','fiscal_year':2026,'period':'FY','consolidation':'Group',
      'currency':'SGD','unit':'SGD_thousands','status':'verified_against_known_S68_FY2026_values',
      'metrics':d,
      'derived':{'revenue_growth_pct':round((rev/prev-1)*100,4),
                 'operating_profit_growth_pct':round((op/d['operating_profit']['fy2025_sgd_thousands']-1)*100,4),
                 'profit_attributable_growth_pct':round((profit/d['profit_attributable']['fy2025_sgd_thousands']-1)*100,4),
                 'operating_margin_pct':round(op/rev*100,4)},
      'screening':{'status':'partial_fundamentals','eligible_for_growth_margin_screen':True,
                   'eligible_for_per_pbr_debt_screen':False,
                   'reason':'price, shares outstanding, balance sheet and debt metrics not verified'},
      'limitations':'Issuer-specific verified regression fixture; not general SGX coverage or a buy recommendation.'
    }
