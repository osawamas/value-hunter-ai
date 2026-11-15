# VALUE HUNTER AI — v292 checkpoint (2026-11-15 JST)

## Resume
- Check current main, Actions, docs/data/latest.json, this checkpoint. Existing hourly automation can write concurrently; do not duplicate task.
- Prior v291 dated local CSV SGX master diff 81/81 PASS; no full official universe or licensed quotes; ranking eligible 0/7.

## New actual source work v292
- Found issuer-owned SGX Group official 2026-11-12 October release: https://www.sgxgroup.com/media-centre/20261112-sgx-groups-derivatives-volume-hits-six-month-high-securities . Source explicitly names TWO October equity IPOs: Deluge Corporation and Mi Material Holding. It does **not** provide verified stock trading codes in the retrieved release.
- SGX October report located by document title in secondary SGXNet mirror and SGX statistics landing page, but actual original October SGXNet PDF URL and SHA still NOT located. Third-party Tiger Brokers reported 605 listed securities end-October vs 604 September; this numeric claim is marked SECONDARY_UNVERIFIED, not primary certified.
- Previous authentic SGX August monthly report https://links.sgx.com/FileOpen/SGX%20Monthly%20Statistics%20Report%20Update_Aug%202026.ashx?App=Announcement&FileID=903915 confirms August 406 Mainboard + 198 Catalist = 604 listed securities (count scope excludes GDRs, hedge funds and debt securities).
- New `docs/data/sgx-october-release-v292.json` records source classifications explicitly. October original PDF fields null, both ranking/price rights false.
- New `scripts/assess-sgx-october-release-v292.js`: fail-closed source scope checker, preserves October 2 IPO names as issuer-released, treats 605 as secondary only, refuses invented IPO stock codes, no mix of counter records and monthly listed securities totals.
- New `docs/test_sgx_october_release_v292.js`: tests true research JSON, unsafe alterations and local staged CSV comparison. Wired into evidence suite and workflow watched files.
- First CI #43670309881 and #43670307622 failed 81/82 because code used `issuer_release_confirmed_ipo_count` while evidence JSON uses `issuer_release_ipo_count`. Fixed at f143fc36..., then test negative mutation updated at e721874b...
- Final real CI **#43670407022 SUCCESS 82/82**. ZIP/browser HTTP workflow #43670407046 SUCCESS, dashboard publish workflow #43670407065 SUCCESS. file:// Chrome #43670406988 in progress when last observed; check before claiming success.
- Final code commits include 21ab59cc research, 2c85b3d2 checker, 44ccd4c3 test, 690587e2 suite, 18cfafc4 workflow, f143fc36 and e721874b fixes.

## Remaining essential development
1. Locate the SGX original monthly statistics October PDF and replay SHA + correctly scoped listing counts, ideally original SGX corporate announcement dated Nov 12.
2. Get permitted, dated complete active SGX instrument/issuer master and browser display plus backend non-display licensed quote source; permissions remain absent.
3. Independent accounting corroboration, dated latest UOB/OCBC ex-treasury original SGX shares filings (UOB Nov13 SG261113OTHRHOAF, OCBC Nov12 SG261112OTHRXH64) unresolved. 
4. Formal ranking eligible **0/7**. Source research progress is not proof of an automatic investable rank.

## Japanese handoff
VALUE HUNTER AI `osawamas/value-hunter-ai` v292から継続。最新main・Actions・latest.json・development-checkpoint-v292.mdを読む。11/12 SGX公式リリースで2026年10月IPOのDeluge CorporationとMi Material Holdingの2社を確認。月末上場数605は第三者報道のみでSGX月次原本PDF未確認。v292では出典の種別とイベント/銘柄コード/集計数の推論を厳格に分離するJSON・検査・テストを実装、CI #43670407022 82/82 PASS。投資適格0/7、SGX全銘柄・株価両用途許諾・独立財務検証未完。次はSGX10月月次PDF原本取得と株数・財務裏取りを優先。毎時開発タスク有効。
