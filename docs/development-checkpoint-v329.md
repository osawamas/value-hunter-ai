# VALUE HUNTER AI v329 — handle JPX month-end rollover

The JPX URL points to a rolling workbook. Verification accepts an equal or newer month-end and still checks every selected Japanese listing's name and market section against the workbook. An earlier workbook or mismatched listing still fails. The report now includes both dates and a flag that distinguishes an exact replay from checking the same names against a newer workbook. This allows recurring verification to continue through the next month-end without claiming that the older workbook was replayed. A listing change still needs review before updating the research snapshot.

16 research companies are listed across Japan, the US and SGX. 12 can be compared on annual financials and zero are ranked. See v327 and v328 for hosted SEC behavior and tests. Continue with monthly identity snapshots, recurring filing discovery, and dated quotes/shares before formal ranking.
