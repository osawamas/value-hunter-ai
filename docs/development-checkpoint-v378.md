# VALUE HUNTER AI v378 — verify representative valuations across all three markets

The read-only command below shows the most recent eligible exact-date filing share observation for Toyota, IBM and ST Engineering, plus its source and the missing closing price when no local input is provided.

    node scripts/check-representative-valuations.js
    node scripts/check-representative-valuations.js /path/to/local-quotes.csv

The CLI uses the application's quote parser, dated share evidence and valuation math. With matching local closes it returns trial market cap, PER and PBR. It never writes public data and does not assert that a supplied close is authorized. The CI regression checks synthetic prices and confirms that a newer or adjacent-date observation cannot substitute for the required close.

Current required quote dates are 2026-09-30 for JP:7203 and US:IBM, and 2026-11-13 for SG:S63. No verified public data connection or ranking is established. Next verify provider access and display rights, run a real first and second refresh for authorized sources, and confirm ranking eligibility on that evidence.
