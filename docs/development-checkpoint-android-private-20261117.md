# VALUE HUNTER AI Android private watch — 2026-11-17

Base: v517, `76e72697b5c4d8f91d7b44b757d8b5b6273558e5`.

## This run

- Added `WatchTransitions` to explicitly distinguish the initial baseline from subsequent trading sessions and suppress same-day/older-session notifications.
- Integrated the transition function into `ScanWorker` without changing the stock-selection thresholds or J-Quants access contract.
- Added fixture unit tests covering baseline, second-session new entrants, same-day retry, older data, unchanged sets and re-entry after absence.
- Android-specific CI: https://github.com/osawamas/value-hunter-ai/actions/runs/43944410496 (check conclusion before declaring success).
- No Web/ZIP files changed. Existing Web regression was not rerun for these Android-only changes.
- No APK uploaded to public Artifacts or Release.

## Unverified and next priorities

1. Confirm the Android CI result for commit `e81d7cf0d5e5e5f526c91619197c621fa1a96850`; fix if red.
2. Confirm J-Quants v2 API schema and each user's permitted plan against live responses; no real API key was used in this run.
3. Test two distinct live trading dates, device notification permission, background work and duplicate suppression on Android hardware.
4. Deliver APK privately without placing binary artifacts on the public repository.
5. Continue Japan multi-symbol coverage first, then single shares, US/SGX and news analysis.

The initial SGX public ranking is not a prerequisite for the three-user private Android preview. Do not interpret the fixture tests as proof of live data or device notification delivery.
