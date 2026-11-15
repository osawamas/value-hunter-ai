# VALUE HUNTER AI v381 — real historical close replay

The representative CLI was run locally with reported historical closes on the exact dates of the documented share observations. All three rows calculated market cap, PER and PBR. The local input was transcribed from published historical pages and excludes the adjusted-close column where distinct. The result establishes reproducibility with real historical observations, not provider authentication, independent upstream feed agreement, redistribution rights or a live refresh.

| Representative | Session | Historical references |
| --- | --- | --- |
| Toyota | 2026-09-30 | [Traders Web](https://www.traders.co.jp/stocks/61_7203/historical), [Minkabu](https://minkabu.jp/stock/7203/daily_bar?page=2&selected_platform=pc) |
| IBM | 2026-09-30 | [Stock Analysis](https://stockanalysis.com/stocks/ibm/history/), [Yahoo Finance](https://finance.yahoo.com/quote/IBM/history/?ltr=1) |
| ST Engineering | 2026-11-13 | [FT historical data](https://markets.ptc.ft.markitdigital.com/data/equities/tearsheet/historical?s=S63%3ASES), [I3investor](https://sgx.i3investor.com/web/stock/historical-chart/S63) |

The report identifies itself as retrospective and carries the filing date when the matched interim observation provides one. Toyota and IBM's share counts were disclosed after the trading session. They cannot be treated as known at that session. CI checks these flags and the prior refresh regression using synthetic quotes. No observed closing price is embedded in the repository or distributed via the app. Public close provider access, data-use verification, successive live refreshes and formal ranking are still pending.

A second local snapshot with the October 1 closes for Toyota and IBM was also replayed. The check detected each newer date without matching shares and retained the September 30 comparison. This is a local replay, not two autonomous provider refreshes.
