#!/usr/bin/env bash
set -euo pipefail
app=jp.valuehunter.privatewatch.diagnostic19
day=$(python -c 'import json; print(json.load(open("coverage-results/jpx-public-coverage.json"))["trade_date"])')
pdf="jpx-${day//-/}.pdf"
adb install android-private/app/build/outputs/apk/debug/app-debug.apk
adb install android-private/app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk
adb shell -T "run-as $app sh -c 'cat > $pdf'" < coverage-results/jpx-session.pdf
for name in listings delistings; do
  file="jpx-$name.html"
  if [[ -s "coverage-results/$file" ]]; then
    adb shell -T "run-as $app sh -c 'cat > $file'" < "coverage-results/$file"
  fi
done
cache_name=jpx-automatic-finance-v1.xml
cache_dir=coverage-jpx-cache
if [[ -s "$cache_dir/$cache_name" ]]; then
  adb shell -T "run-as $app sh -c 'mkdir -p shared_prefs && cat > shared_prefs/$cache_name'" < "$cache_dir/$cache_name"
fi
save_public_finance_cache() {
  mkdir -p "$cache_dir"
  local temp
  temp=$(mktemp "$cache_dir/finance.XXXX")
  if timeout 15 adb exec-out run-as "$app" cat "shared_prefs/$cache_name" > "$temp"       && grep -q '^<map>' "$temp"; then
    mv "$temp" "$cache_dir/$cache_name"
  else
    rm -f "$temp"
  fi
}
trap save_public_finance_cache EXIT
timeout 360 adb shell am instrument -w -e coverage_day "$day" -e coverage_fetch true "$app.test/jp.valuehunter.privatewatch.JpxPdfGeometryProbe" | tee coverage-results/jpx-probe.log
sed -n '/^{.*}/p' coverage-results/jpx-probe.log | tr -d '\r' > coverage-results/jpx-valuation.json
if [[ ! -s coverage-results/jpx-valuation.json ]]; then
  rm coverage-results/jpx-valuation.json
  exit 1
fi
adb exec-out run-as "$app" cat jpx-finance-audit.json > coverage-results/jpx-finance-audit.json
python -m json.tool coverage-results/jpx-valuation.json
