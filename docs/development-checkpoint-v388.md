# VALUE HUNTER AI v388 — Retain an earlier trial when the latest close is missing

The representative valuation CLI keeps the latest exact share observation and its quote status at the top level. If that date cannot be valued and an earlier date in the supplied CSV has a valid same-date filing match, `latestAvailableTrial` includes the earlier date, close, share count, filing links, disclosure timing when known, market cap, PER and PBR. In comparison mode the trial is calculated from the current CSV. The session change list identifies a removed or restored close on its own date.

    node scripts/check-representative-valuations.js --compare previous.csv current.csv

The regression removes Toyota's September 30 close, leaves an October 1 close without matching shares, and retains a valid March 31 close. It verifies the separate March trial against the share count from the [Toyota annual results](https://global.toyota/pages/global_toyota/ir/financial-results/2026_4q_summary_en.pdf). Restoring the September close restores the primary trial.

Public price-feed usage rights, authenticated consecutive live updates and formal ranking eligibility remain open.
