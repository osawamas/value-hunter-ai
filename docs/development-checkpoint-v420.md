# VALUE HUNTER AI v420 — Validate both sides of the three-market refresh

    node scripts/check-representative-valuations.js --require-both-trials --compare previous.csv current.csv

This optional check requires complete local valuations for the latest observed trading date in each input for Toyota, IBM and ST Engineering. The current session must advance in each market. The exit status is 2 if either side lacks a usable close, same-date published shares, PER or PBR. The result records the previous and current status separately. Existing current-only acceptance options retain their behavior.

Synthetic tests verify a passing pair and a pair whose current valuations pass but whose previous share evidence is missing. The local check does not establish provider authentication, public daily price usage rights, or two successful live updates.

When using `--filing-dir`, the S63 evidence file can hold one dated record or an array of dated records. The usual bundled record and optional SGXNet notice URLs also work with the check.
