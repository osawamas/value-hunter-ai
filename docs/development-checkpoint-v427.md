# VALUE HUNTER AI v427

IBM's 30 June 2026 exact common shares (942,134,390) were verified against
the SEC 10-Q linked in the market snapshot. The filing date is 23 July 2026.
The original file SHA-256 is recorded and the source checker replays the exact
XBRL context, unit and value. Both the research screen and CLI can now match
this date in addition to the September 30 figures.

    python3 scripts/check-ibm-personal-refresh.py --demo --separate-requests 2026-06-30 2026-09-30

The live demo run used two separate HTTP requests and completed local
market-cap, PER and PBR calculations on both dates. This is a pair of historical
dates, with share counts published after their respective sessions. It does
not establish scheduled daily refresh, adjacent trading-date coverage or
permission to publish Alpha Vantage market data. Public ranking remains empty.
