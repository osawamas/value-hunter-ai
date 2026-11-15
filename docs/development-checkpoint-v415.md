# VALUE HUNTER AI v415 — Verify that all three quote snapshots advanced

    node scripts/check-representative-valuations.js --require-new-sessions --compare previous.csv current.csv

This optional local acceptance check requires each representative's newest current close to have a later trading date than its previous observation and a matching published share count, with market cap, PER and PBR available. The report includes `previousDate`, `hasNewSession` and the valuation status per security. A failed check returns exit status 2 and preserves the diagnostics.

Synthetic tests cover identical snapshots, corrections to existing closes, a newer close without shares, and a passing update across all three markets. Provider authentication, public usage rights and successive live refreshes remain open.
