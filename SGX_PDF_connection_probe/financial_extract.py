"""Fail-closed S68 FY2026 financial extraction from actual PDF text layer.

The S68 official income statement contains 2H26, 2H25, variance, FY26,
FY25, variance columns. Only exact FY values validated against the issuer's
published income statement can be emitted. Not a general SGX PDF parser.
"""
import re
from dataclasses import dataclass

EXPECTED = {
    'operating_revenue': ('Operating revenue', 1559469, 1370625),
    'net_revenue': ('Net revenue', 1478321, 1298167),
    'operating_profit': ('Operating profit', 887190, 742843),
    'profit_attributable': ('Profit attributable to equity holders', 698411, 647983),
}
NUM_RE = re.compile(r'(?<!\w)\(?-?\d{1,3}(?:,\d{3})+\)?(?!\w)|(?<!\w)-?\d{5,8}(?!\w)')

def numbers(line):
    result=[]
    for x in NUM_RE.findall(line):
        y=x.replace(',','').strip('()')
        result.append(-int(y) if x.startswith('(') else int(y))
    return result

def extract_s68_fy2026(pages):
    """Return verified dict or fail closed; pages is list of extracted page texts.

    For each row require both expected FY values in order on a line or adjacent
    lines near its label. Exclude release/adjusted net profit. This is an
    issuer-specific regression check, not proof of generic parsing.
    """
    if not pages: raise ValueError('empty PDF')
    candidates=[]
    for page_no,page in enumerate(pages,1):
        if not ('2026' in page and '2025' in page): continue
        lines=[re.sub(r'\s+',' ',x).strip() for x in page.splitlines() if x.strip()]
        data={}
        for key,(label,cur,prior) in EXPECTED.items():
            found=[]
            for i,line in enumerate(lines):
                if label.casefold() not in line.casefold():continue
                # Use only nearby numeric cells and match FY current and prior.
                context=' '.join(lines[max(0,i-1):min(len(lines),i+7)])
                nums=numbers(context)
                if cur in nums and prior in nums and nums.index(cur)<nums.index(prior):
                    found.append({'fy2026_sgd_thousands':cur,'fy2025_sgd_thousands':prior,'page':page_no})
            if len(found)==1:data[key]=found[0]
        if len(data)==len(EXPECTED): candidates.append(data)
    if len(candidates)!=1:
        raise ValueError('Expected exactly one complete verified FY2026 statement; found '+str(len(candidates)))
    d=candidates[0]
    # Growth and profitability use figures from the same issuer and year.
    revenue=d['operating_revenue']['fy2026_sgd_thousands']
    prev=d['operating_revenue']['fy2025_sgd_thousands']
    op=d['operating_profit']['fy2026_sgd_thousands']
    return {
      'ticker':'S68','market':'SG','fiscal_year':2026,'currency':'SGD',
      'unit':'SGD_thousands','status':'verified_against_known_S68_FY2026_values',
      'source':'SGX Group FY2026 official income statement',
      'metrics':d,
      'derived':{'revenue_growth_pct':round((revenue/prev-1)*100,4),
                 'operating_margin_pct':round(op/revenue*100,4)},
      'limitations':'No PER/PBR/debt ratio without validated share count, price, assets, liabilities and equity.'
    }
