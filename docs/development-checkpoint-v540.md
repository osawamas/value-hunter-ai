# VALUE HUNTER AI v540 — Android private baseline safety

2026-11-17 JST. Started from main `91660410e526a9dc40c006a74277c57d83f27890` (v539); latest data `docs/data/latest.json` retains SGX registered 7 and public ranking eligible 0. Latest prior checkpoint file is v526, while later commits v527–v539 carry development history.

## Android-only change
- `WatchTransitions.newEntrants` treats malformed or impossible persisted trading dates as a baseline reset rather than throwing an unchecked exception. It never announces every existing candidate as newly qualified when local history is corrupt.
- Added regression cases for malformed and impossible dates; first scan, same-day retry, old session, unchanged and re-entry behavior remain covered.
- Implementation commit: `a86f5fff92752620ea69c87741a68a455b575d36`.
- Regression-test commit: `9d7de3d63492d6a4331c2b879babde4bd59590ff`.
- Android CI for test commit: https://github.com/osawamas/value-hunter-ai/actions/runs/43975003256 (queued at checkpoint write; do not mark passed until completed).
- Previous Android successful run: https://github.com/osawamas/value-hunter-ai/actions/runs/43973422013 (older SHA only).

## Next work
1. Check latest Android CI status and repair any failure; verify APK assembly and packaging without publishing artifacts.
2. Validate mock two-session transitions, silent notifications on a real device, and each user's independent J-Quants credentials; actual API connection remains unverified.
3. Prioritize Tokyo ordinary shares purchasable in 100-share lots for <= JPY 100,000; display J-Quants free-tier data session dates and delay. No paid feeds, shared quote distribution, or public APK.
4. Keep Web and ZIP regression testing required if changing Web sources; this checkpoint changes Android only.
