# VALUE HUNTER AI v410 — Identify the filing snapshots behind valuation reports

The representative valuation command now reports SHA-256 hashes of the bundled financial and share-evidence JSON it actually read. Two-snapshot reports include the previous and current quote CSV hashes alongside them. This lets a reviewer reproduce a report against the same inputs even after the bundled data changes.

CI runs the actual comparison command with synthetic prices for Toyota, IBM and ST Engineering. It checks valuations in all three markets, an IBM close correction and a newer ST Engineering close that still lacks matching shares.

These hashes identify local inputs. Public daily-price usage rights and two successive authenticated price refreshes remain open.
