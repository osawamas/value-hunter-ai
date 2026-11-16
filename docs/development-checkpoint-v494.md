# VALUE HUNTER AI v494

IBM can automatically select the latest two sessions that have both a
close in the provider's returned series and an exact-date SEC share
filing. It calculates market cap, PER and PBR using the existing
representative valuation checker. The automatic comparison runs with
one provider request and takes no dates or manual CSV input.

    python3 scripts/check-ibm-personal-refresh.py --demo --latest-with-filings

The existing latest-two check still reports the status of the newest
provider sessions. The IBM demonstration is for local research.
Toyota live verification still requires a personal J-Quants key.
Public quote rights and ranking eligibility remain pending.
