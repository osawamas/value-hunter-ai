# VALUE HUNTER AI v385 — Preserve the SGX share reference date

The v384 browser regression detected an undefined date in the S63 ranking exclusion details. The supplemental share record now uses the same as_of field in both the ranking details and the retrospective valuation flow. The direct-open and HTTP browser suites check the exclusion date and the after-close display together.
