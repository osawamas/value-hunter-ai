# Android private JPX watch checkpoint — 2026-11-18 03:56 JST

- Starting main: `47dad8a80f1faac8268511d157e0da8a124a4887` (NYSE TAQ follow-up); SGX `docs/data/latest.json`: 7 registered, ranking eligible 0.
- Android `JpxDailyCheck.readReport` now rejects PDFs yielding no valid close among the three monitored codes. Previously a syntactically valid but unreadable JPX table could be treated as a successful session and advance the notification baseline. Individual missing/ambiguous codes remain held, not silently accepted.
- Regression tests cover empty, missing, ambiguous and valid morning-only samples. Code `e64396a3`, tests `b2ada4c3`.
- Android CI for test commit: queued at review (`44153402868`); do not claim success yet. Earlier Android CI for `b1d484cc` succeeded (`44151634462`).
- No public APK artifact or Release intentionally created; Web files unchanged.
- Outstanding: actual JPX data for two successive sessions, share-basis/rights confirmation, live-device silent notification, private APK handoff. Check Android CI and PDF geometry probe, then address any failures.
