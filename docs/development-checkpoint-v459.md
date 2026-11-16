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

In v461, run the **JPX, SEC and SGX market source verification** Actions
workflow with `check_ibm_demo` enabled to see these statuses and filing
links in the run summary. If the demo request fails, the job fails. If
the closes are retrieved but the valuation is incomplete, the summary
reports the valuation as pending. It excludes the price values and ratios.

In v462, use the dedicated **IBM demo preflight** Actions workflow for
manual runs. It also runs on main when its definition or IBM refresh
script changes. The run summary contains the same diagnostic statuses.
