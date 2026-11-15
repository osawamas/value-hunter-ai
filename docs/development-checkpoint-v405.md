# VALUE HUNTER AI v405 — Run personal J-Quants retrieval and comparison together

Run with a local personal J-Quants API key and a date covered by the account:

    python3 scripts/refresh-jquants-personal.py --output-dir baseline --date 2026-09-30 7203
    python3 scripts/refresh-jquants-personal.py --previous-dir baseline --output-dir next --date 2026-09-30 7203

Each successful run saves the CSV, receipt and report in a new directory. The first run verifies its receipt. Subsequent runs also check the previous receipt, retrieval order and matching security coverage, then produce the existing valuation comparison. A failed retrieval or comparison leaves the previous directory available and does not save a partial result.

The regression runs two synthetic retrievals through the actual receipt verifier and valuation command. Public closing-price usage rights and real authenticated successive refreshes remain open.
