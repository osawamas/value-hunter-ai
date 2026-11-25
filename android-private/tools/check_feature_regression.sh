#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
src=android-private/app/src/main/java/jp/valuehunter/privatewatch
manifest=android-private/app/src/main/AndroidManifest.xml
required=(BrandEmblem BrandHeader BrandNav BrandLaunchWidget SplashActivity
  MainActivity CurrentCandidatesActivity RecentAlertsActivity DebugDiagnosticsActivity
  MarketNetwork ScanWorker JpxWatchWorker UsDailyWorker UsSecFinanceWorker
  NotificationScreenWake NotificationHistory ValueAlertMeter ValueAlertPreview
  UsDeviceFinancials DiagnosticLog SecAccess)
for item in "${required[@]}"; do
  test -s "$src/$item.java" || { echo "MISSING FUNCTIONAL COMPONENT: $item" >&2; exit 1; }
done
grep -Fq 'BrandHeader.create(this)' "$src/MainActivity.java"
grep -Fq 'BrandNav.create(this' "$src/MainActivity.java"
grep -Fq 'getStringExtra("focus")' "$src/MainActivity.java"
grep -Fq 'brand_header.webp' "$src/BrandHeader.java"
grep -Fq 'brand_splash.webp' "$src/SplashActivity.java"
grep -Fq 'brand_widget.webp' "$src/BrandLaunchWidget.java"
grep -Fq 'setOnClickPendingIntent' "$src/BrandLaunchWidget.java"
grep -Fq 'android:targetCellWidth="2" android:targetCellHeight="1"' android-private/app/src/main/res/xml/brand_widget_info.xml
grep -Fq 'android:scaleType="fitCenter"' android-private/app/src/main/res/layout/brand_widget.xml
grep -Fq 'android:name=".SplashActivity" android:exported="true"' "$manifest"
grep -Fq 'android:icon="@mipmap/ic_launcher"' "$manifest"
grep -Fq 'android:name=".BrandLaunchWidget"' "$manifest"
grep -Fq 'android:name=".CurrentCandidatesActivity"' "$manifest"
grep -Fq 'android:name=".RecentAlertsActivity"' "$manifest"
grep -Fq 'android:name=".DebugDiagnosticsActivity"' "$manifest"
grep -Fq 'ValueAlertMeter.assess' "$src/UsDeviceFinancials.java" || grep -Fq 'ValueAlertMeter.assessUs' "$src/UsDeviceFinancials.java"
grep -Fq 'PRIVATE_SCREEN_RECEIPT' "$src/UsDailyWorker.java"
grep -Fq 'BrandHeader.create(this)' "$src/MainActivity.java"
echo "Verified ${#required[@]} retained Java components, 2x1 widget, original asset routes, navigation, notification and SEC screen receipt"
