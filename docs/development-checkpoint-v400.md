# VALUE HUNTER AI v400 — Report newly observed trading dates

The representative valuation comparison now reports `newTradingDates` per issuer. It lists dates from the current CSV that are later than the issuer's last observed date in the previous CSV. A first appearance without prior issuer coverage has an empty list. The session change list still includes older backfill and price revisions.

    node scripts/check-representative-valuations.js --compare previous.csv current.csv

Tests cover newly observed dates for IBM and ST Engineering, a Toyota backfill and correction, and an issuer without a baseline. The comparison concerns the supplied inputs. Authenticated consecutive refreshes, public daily-close usage rights and formal ranking eligibility remain open.
