# VALUE HUNTER AI v391 — Require same-session SGX share evidence before ranking

The ranking feed validator now requires a valid quote timestamp with an explicit time zone and a valid share-count date. It converts the quote timestamp to the Singapore calendar date and requires the two dates to agree for every ranking-eligible record. The SGX license validity check uses the same date. The Pages workflow runs the validator before packaging and deployment.

Regression cases cover a stale share date, midnight in Singapore, invalid calendar dates, timestamps without time zones, and a grant that starts on the matching Singapore date. The currently published feed has zero ranking-eligible records.

The [SGX Market Data Policy](https://www.datadirect.sgx.com/Market-Data-Policy) remains the source for usage requirements. The app still needs confirmed public daily-close usage rights and consecutive authenticated updates.
