# VALUE HUNTER AI v459

Run a local IBM check without entering trading dates:

```sh
python3 scripts/check-ibm-personal-refresh.py --demo --latest-two
```

The tool selects the two newest trading dates actually returned by the
provider in one request and checks each for same-day shares and valuation.
Status 2 means the results were reported but at least one valuation was
incomplete. The two dates are provider observations, with no guarantee of
coverage through the latest completed market session. Use a personal Alpha
Vantage key by omitting `--demo` and setting `ALPHA_VANTAGE_API_KEY`.
This manual check stays local. Production scheduling and public price
rights remain pending.

In v460, `preflightChecks` records the price retrieval and valuation
status for each requested observation. When the same-day share count
is missing, it includes the date and source of the earlier disclosure
when available. Saved local snapshot reports include the same fields.
