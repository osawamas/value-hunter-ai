# VALUE HUNTER AI Android private checkpoint — 2026-11-17 06:00 JST

Starting point: v521 / bfe61fcf956818a8044bb6b3254c1f2454d7ba95.

The private Android app now provides an on-device erase control. It cancels Japanese, US, and SGX periodic/one-shot WorkManager tasks, clears local SharedPreferences including personal API keys, scan baselines and displayed results, removes local notifications, and clears the visible Japanese key input. No account information or market data is sent to other users by this operation. A user can start monitoring again by entering their own key.

Do not distribute APK through public Actions artifacts or Releases. Build and test via Android CI, but deliver APK privately. Never claim a real J-Quants connection or handset notification test from CI alone. J-Quants free tier delayed quotes must remain date-labelled. Japanese multi-stock, <=100000 JPY per 100 shares, newly qualified only, silent alerts are the first release gate; US/SGX are secondary pilots.

Pending: confirm Android Actions result for this commit, test on physical handset, verify real authorized J-Quants credentials and two consecutive dated updates, and privately deliver a signed APK. The existing SGX public ranking remains ineligible (latest.json ranking_eligible_count=0); do not merge unofficial quotes into it.
