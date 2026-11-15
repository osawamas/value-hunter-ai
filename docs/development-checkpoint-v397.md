# VALUE HUNTER AI v397 — Recompute ranking valuations from the evidence

The SGX ranking validator now verifies that eligible records reproduce market cap, PER and PBR from the quoted price, same-date ex-treasury share count, reported parent-attributable profit and parent equity. It allows the feed's rounding to cents and four decimal places. Tests reject missing or inconsistent metrics, zero prices, negative earnings and use of total equity in place of parent equity.

Daily refresh and distribution use this validator. The current feed has zero eligible records. Public daily-price usage rights and two consecutive authenticated refreshes remain open.
