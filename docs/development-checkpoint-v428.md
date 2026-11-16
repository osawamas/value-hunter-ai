# VALUE HUNTER AI v428

IBM personal research can fetch and save a dated snapshot each time the tool
runs. No manual price entry is needed. Run again against the earlier directory.

    python3 scripts/check-ibm-personal-refresh.py --demo --output-dir ibm-june 2026-06-30
    python3 scripts/check-ibm-personal-refresh.py --demo --previous-dir ibm-june --output-dir ibm-september 2026-09-30

Use a destination outside the public web data directory. The snapshot retains
the automatically fetched observation, the filing inputs, a receipt with their
hashes, and the separate historical valuation results. The receipt checks local
integrity and retrieval order. Incomplete valuation returns 2 and saves the
report. A failed retrieval or a mismatched receipt leaves no new snapshot.
The snapshots are for personal research. Daily production updates, public
price permission and formal ranking remain pending.
