"""Make a concise human-readable GitHub Actions summary from v27 output."""
import argparse
import json
from pathlib import Path

STATES = {
    "MATCH_LIVE_SECOND_ISSUER_DOCUMENT": "一致（別の企業公式資料）",
    "MISMATCH": "不一致・要調査",
    "NOT_VERIFIED": "未検証",
}

def format_report(data):
    lines = [
        "# VALUE HUNTER AI — SGX財務照合 v27",
        "",
        "※ 同一企業の別の開示資料との照合。第三者機関による独立監査ではない。",
        "※ **投資ランキングはまだ無効**。未確認値をランキングに使用しない。",
        "",
        "| 銘柄 | 指標 | 元データ | 別資料 | 判定 |",
        "|---|---|---:|---:|---|",
    ]
    for item in data.get("records", []):
        symbol = item.get("symbol", "?")
        checks = item.get("checks", [])
        if item.get("error"):
            lines.append(f"| {symbol} | PDF取得/解析 | — | — | エラー：{item['error'][:90].replace('|', '／')} |")
        elif not checks:
            lines.append(f"| {symbol} | — | — | — | 未検証 |")
        for check in checks:
            status = STATES.get(check.get("status"), "未検証")
            lines.append("| {} | {} | {} | {} | {} |".format(
                symbol,
                check.get("metric", "-"),
                check.get("financial_value") if check.get("financial_value") is not None else "—",
                check.get("reference_value") if check.get("reference_value") is not None else "—",
                status,
            ))
    lines.extend(["", f"**ランキング対象：{data.get('ranking_eligible_count', 0)}社**", ""])
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", required=True)
    parser.add_argument("--output", required=True)
    options = parser.parse_args()
    report = format_report(json.loads(Path(options.audit).read_text(encoding="utf-8")))
    Path(options.output).write_text(report, encoding="utf-8")
    print(report)

if __name__ == "__main__":
    main()
