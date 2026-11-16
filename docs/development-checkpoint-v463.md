# VALUE HUNTER AI v463

GitHub Actions now schedules the IBM demo preflight for 23:17 UTC
Monday through Friday, corresponding to 08:17 JST Tuesday through
Saturday. Manual runs and the existing push triggers remain available.

The job checks the latest two observations returned by the demo API
and reports the actual trading dates. Market holidays and provider
delays can leave those dates unchanged. The summary contains retrieval
status and share evidence, with no closing price or valuation ratio.
This schedule runs the preflight only. The public ranking still needs
an authorized price source and same-day share evidence.
