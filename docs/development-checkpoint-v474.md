# VALUE HUNTER AI v474

Run the Toyota local comparison with a personal J-Quants V2 key:

    python3 scripts/refresh-jquants-personal.py --output-dir toyota-pair --toyota-free-latest

The command selects the latest two exact-date Toyota share observations
within the free plan's estimated two-year window and at least 12 weeks
before today's Japan date, using the same share checks
as the valuation tool. On 16 November 2026 the selected dates are
31 March and 30 June. The September observation enters the delay window
on 23 December. The API still determines whether both closes are
available to the account. EDINET October month-end reference data do
not enter exact-date selection. The explicit-date option remains usable.

Selection and the local comparison have regression coverage. No personal
API key was available for a live run. Public close access is pending.
