# VALUE HUNTER AI v457

Check Toyota (7203) and IBM across two locally obtained closing-price snapshots:

```sh
node scripts/check-representative-valuations.js --require-jp-us-refresh --compare previous.csv current.csv
```

Each security must advance to a later trading date and have a complete market
cap, PER and PBR calculation on both dates using same-day shares. The report
shows the result for each security and returns status 2 if either check fails.
`--previous-filing-dir` can select the financial and share inputs saved with
the earlier snapshot.

This is a local trial. Public closing-price rights, production daily updates
and formal ranking remain pending.
