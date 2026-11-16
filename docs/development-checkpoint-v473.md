# VALUE HUNTER AI v473

Toyota's June and September closing-price checks can run together with a
personal J-Quants V2 key. The command automatically downloads exact-date
unadjusted closes, verifies both receipts and evaluates each session
against the corresponding Toyota shares.

    python3 scripts/refresh-jquants-personal.py --output-dir toyota-pair --toyota-sessions 2026-06-30 2026-09-30

The output directory contains the earlier and later local snapshots.
Both are preserved for an incomplete valuation (exit 2). A retrieval
or receipt error leaves the destination absent. The free J-Quants plan
has a 12-week delay, so both requested sessions must be within the
account's coverage. The regression injects test closes and executes the
real receipt and valuation commands. Authenticated price retrieval and
public ranking eligibility are still pending.
