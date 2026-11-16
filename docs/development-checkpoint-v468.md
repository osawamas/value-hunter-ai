# VALUE HUNTER AI v468

SGX close ingestion calculates the ranking score from the same verified
financials and same-session shares used for PER and PBR. The score is the
average of earnings yield and book-to-market, expressed as a percentage
and rounded to six decimals before sorting. The calculation uses the raw
close and unrounded denominators. A close provider only supplies quote
fields. Its optional legacy ranking score has no effect. The score is a
relative valuation measure.

The publication validator checks the score for records carrying the new
calculation method. Legacy records remain readable. The dashboard shows
the calculation basis next to the score. Price permission and independent
financial checks still apply, and the public feed has zero eligible rows.
