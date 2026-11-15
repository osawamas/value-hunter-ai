# VALUE HUNTER AI v386 — Compare consecutive price snapshots by trading date

The local three-market CLI comparison now reports every observed trading date for Toyota, IBM and ST Engineering. Each entry identifies a newly added, unchanged, revised or removed closing price and whether an exact-date share count is on file. Any omissions are relative to the two supplied snapshots. The report preserves the latest exact-share valuation and lists newer unmatched dates, so a revision outside that valuation date remains visible.

Run with two local snapshots covering the same period:

    node scripts/check-representative-valuations.js --compare previous.csv current.csv

The regression uses successive synthetic snapshots and checks an unchanged matched close alongside a revised newer close, a newly supplied older close with exact shares, and a removed observation. Public price rights, authenticated provider refreshes and formal ranking eligibility remain open.
