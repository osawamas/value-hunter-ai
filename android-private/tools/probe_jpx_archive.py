"""Capture a small, reproducible sample of the public JPX archive transport."""
import http.cookiejar
import json
import xml.etree.ElementTree as ET
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener
from pathlib import Path
import sys

ROOT = "https://www2.jpx.co.jp/tseHpFront/"
HOME = ROOT + "StockSearch.do"
DETAIL = ROOT + "JJK010030Action.do"


def inspect(out):
    opener = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
    observed = []

    def fetch(url, code=None):
        item = {"source": url, "symbol": code}
        observed.append(item)
        params = (urlencode({"BaseJh": "BaseJh", "mgrCd": code + "0",
                            "jjHisiFlg": "1", "sniMtGmnId": "JJK010010"}).encode()
                  if code is not None else None)
        try:
            with opener.open(Request(url, data=params, headers={"Referer": HOME}), timeout=12) as response:
                raw = response.read(2_000_001)
                item.update(http=response.status, bytes=len(raw))
                if not raw or len(raw) > 2_000_000:
                    return
                if code:
                    try:
                        page = raw.decode("utf-8")
                    except UnicodeDecodeError:
                        page = raw.decode("cp932", errors="replace")
                    (out / f"jpx-archive-{code}.html").write_text(page, encoding="utf-8")
                    item.update(issuer_cell=bool(re.search(r"<td[^>]*>\s*" + code + r"0\s*</td>", page)),
                                detail_title="上場会社詳細（適時開示情報）" in page,
                                display_more=page.count("displayMore("),
                                sections=re.findall(r"displayMore\(['\"]?(110[1-4])", page),
                                annual_titles=page.count("決算短信"),
                                ixbrl_links=page.lower().count("-ixbrl.htm"))
        except (HTTPError, URLError, TimeoutError) as error:
            item["error"] = type(error).__name__
            if isinstance(error, HTTPError):
                item["http"] = error.code

    fetch(HOME)
    for code in ("7203", "6758", "1301"):
        fetch(DETAIL, code)
    print(json.dumps(observed, ensure_ascii=False))
    (out / "jpx-archive-transport.json").write_text(json.dumps(observed, ensure_ascii=False, indent=2),
                                                    encoding="utf-8")


def verify_storage(preferences, audit_file):
    audit = json.loads(audit_file.read_text(encoding="utf-8"))
    saved = {row.get("name", ""): row.text for row in ET.parse(preferences).getroot().findall("string")}
    for symbol, row in audit["issuer"].items():
        record = saved.get("annual-" + symbol)
        try:
            stored = json.loads(record) if record is not None else None
        except json.JSONDecodeError:
            row["persisted"] = "invalid"
        else:
            row["persisted"] = isinstance(stored, dict)
            if row["persisted"]:
                row["persisted_hold"] = stored.get("hold", "")
    audit_file.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--storage"]:
        verify_storage(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        inspect(Path(sys.argv[1]))
