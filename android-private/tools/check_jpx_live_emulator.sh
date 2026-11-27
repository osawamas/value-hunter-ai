#!/usr/bin/env bash
set -euo pipefail
app=jp.valuehunter.privatewatch.diagnostic19
day=$(python -c 'import json; print(json.load(open("coverage-results/jpx-public-coverage.json"))["trade_date"])')
pdf="jpx-${day//-/}.pdf"
adb install android-private/app/build/outputs/apk/debug/app-debug.apk
adb install android-private/app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk
adb shell -T "run-as $app sh -c 'cat > $pdf'" < coverage-results/jpx-session.pdf
timeout 360 adb shell am instrument -w -e coverage_day "$day" -e coverage_fetch true "$app.test/jp.valuehunter.privatewatch.JpxPdfGeometryProbe" | tee coverage-results/jpx-probe.log
sed -n '/^{.*}/p' coverage-results/jpx-probe.log | tr -d '\r' > coverage-results/jpx-valuation.json
python -m json.tool coverage-results/jpx-valuation.json
