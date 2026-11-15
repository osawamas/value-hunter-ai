# VALUE HUNTER AI v404 — Check the order and scope of personal J-Quants refreshes

The `--compare-jquants` command requires valid UTC retrieval timestamps in both receipts and identical requested security sets. The current retrieval must be strictly later than the previous retrieval. The report includes both timestamps and still permits sliding date windows and unchanged prices. Older receipts without timestamps can still pass individual CSV verification or be used with the CSV-only comparison.

CI covers reversed and equal retrieval times, missing and malformed timestamps, differing security sets and two timestamps within the same millisecond. The timestamps are recorded by the local exporter. Authenticated live refreshes and public usage rights remain open.
