from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent))
from financial_extract import extract_s68_fy2026
import pytest

FIXTURE=Path(__file__).with_name('fixture_page09.txt').read_text(encoding='utf-8')

def test_real_pdf_text_fixture():
    r=extract_s68_fy2026(['cover',FIXTURE])
    assert r['metrics']['operating_revenue']['fy2026_sgd_thousands']==1559469
    assert r['metrics']['operating_profit']['fy2025_sgd_thousands']==742843
    assert r['metrics']['profit_attributable']['fy2025_sgd_thousands']==647983
    assert r['screening']['eligible_for_per_pbr_debt_screen'] is False

def test_missing_statement_fails():
    with pytest.raises(ValueError):extract_s68_fy2026(['hello'])

def test_wrong_year_amount_fails():
    with pytest.raises(ValueError):extract_s68_fy2026([FIXTURE.replace('1,559,469','1,559,470')])

def test_half_year_not_accepted_as_full_year():
    with pytest.raises(ValueError):extract_s68_fy2026([FIXTURE.replace('1,559,469     1,370,625','823,286     688,398')])

def test_duplicated_statement_fails():
    with pytest.raises(ValueError):extract_s68_fy2026([FIXTURE,FIXTURE])
