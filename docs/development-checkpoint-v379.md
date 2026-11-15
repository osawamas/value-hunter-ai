# VALUE HUNTER AI v379 — compare successive representative price snapshots

Run the representative valuation check with two complete local quote snapshots:

    node scripts/check-representative-valuations.js --compare previous.csv current.csv

The report shows newly available, unchanged, corrected, removed or still absent exact-date closes for Toyota, IBM and ST Engineering. It also lists newer imported quote dates beyond the latest usable share filing. Removal never falls back to the previous file or to a different date. A correction recomputes the valuation from the current snapshot. The report is local and read-only; it does not publish prices or enable rankings.

The regression simulates a corrected Toyota close, missing IBM close with a newer unmatched date, and newly available ST Engineering close. An authenticated public provider and two real refreshes remain open.
