# VALUE HUNTER AI v403 — Compare two receipt-verified personal snapshots

    node scripts/check-representative-valuations.js --compare-jquants previous.csv previous.json current.csv current.json

The command checks both CSVs against their v401 J-Quants receipts using the v402 offline verifier and matches their hashes to the input bytes before calculating. An invalid receipt or modified CSV stops the comparison before any valuation report is emitted. The existing CSV-only comparison remains available for local trials in all three markets.

CI exercises both receipt checks and Toyota's market cap, PER and PBR with synthetic snapshots. The receipts describe personal-use exports. Live authenticated refreshes and public price usage rights remain open.
