# VALUE HUNTER AI v517

The first Android preview is for the owner and a small private circle,
expected to be under ten people. Each user fetches Japanese stock data
with their own J-Quants API key. The app saves its settings,
latest matches and previous qualifying set in Android private app storage
with backups disabled. There is no shared price, account or notification
server. The first successful session establishes the baseline. Subsequent
sessions produce a silent notification when at least one symbol newly
qualifies.

The initial screen uses actual traded closes and official same-date PER
and PBR. It limits domestic ordinary shares on the Prime, Standard and
Growth markets to 100 shares costing no more than JPY 100,000, positive
trailing PER up to 15 and positive PBR up to 1. The thresholds are initial
defaults. Manual refresh and WorkManager's periodic check share the
same session validation. Android may defer background work. Intraday
price alerts and forcing the screen to wake are not implemented.

Free J-Quants data is delayed by 12 weeks. The checkbox selects an
appropriate query window for the user's existing plan. The app contains
no purchase flow. The Android Preview workflow builds a debug-signed
APK and runs the fixture-based screening tests. The APK is distributed
privately. For repeat installations, build with the same signing key to
preserve settings.
Live API authentication and actual phone notification delivery require
a phone test with each user's own account. US, SGX and the single-share
fallback are pending.
