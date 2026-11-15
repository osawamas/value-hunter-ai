# VALUE HUNTER AI v399 — Identify missing closes within overlapping snapshot dates

The local valuation comparison reports the intersection of the two observed date ranges per issuer. It lists dates with a close in the previous file and no close in the current file inside that intersection. A disjoint range or a missing issuer has no intersection. A close outside the intersection can still appear as removed from the supplied file in the existing session list.

    node scripts/check-representative-valuations.js --compare previous.csv current.csv

This operates on the supplied files. Market calendars and provider deletion status are not inferred. Tests cover disjoint ranges, a missing issuer, a shifted endpoint and a missing observation inside the overlap. Public daily-close usage rights and authenticated consecutive refreshes remain open.
