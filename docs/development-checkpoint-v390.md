# VALUE HUNTER AI v390 — Show valuation changes for each revised trading date

The local comparison CLI now includes `valuationImpact.previous` and `valuationImpact.current` for added, revised or removed closes on dates with exact filing share counts. Each available side carries its source links, disclosure timing when known, and the retrospective trial valuation or its calculation status. An absent close has a null side. Unchanged closes and dates without exact shares omit the impact.

    node scripts/check-representative-valuations.js --compare previous.csv current.csv

Both sides use the finance and share evidence currently bundled with the app, so the difference isolates the closing-price change. The regression checks a corrected older Toyota close alongside an unchanged latest Toyota valuation, a removed IBM close, and an added ST Engineering close with an after-close share disclosure.

Public stock-price usage rights, consecutive authenticated refreshes and formal ranking eligibility remain open.
