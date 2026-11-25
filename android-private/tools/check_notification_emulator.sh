#!/usr/bin/env bash
set -euo pipefail
trap 'adb logcat -b crash -d -t 150 AndroidRuntime:E "*:S" || true' ERR

app=${APP_PACKAGE:-jp.valuehunter.privatewatch.diagnostic15}
runner="$app.test/jp.valuehunter.privatewatch.JpxPdfGeometryProbe"
adb install android-private/app/build/outputs/apk/debug/app-debug.apk
adb install android-private/app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk
if (( PROBE_API >= 33 )); then
  adb shell pm grant "$app" android.permission.POST_NOTIFICATIONS
fi
adb shell settings put global stay_on_while_plugged_in 0
adb shell am instrument -w -e alert_phase post "$runner" | tee "$RUNNER_TEMP/alert-post.txt"
tr -d '\r' < "$RUNNER_TEMP/alert-post.txt" | grep -x 'ALERT_SILENT_WAKE_AND_HISTORY_OK'
tr -d '\r' < "$RUNNER_TEMP/alert-post.txt" | grep -x 'MARKET_WIFI_SWITCH_OK'

adb reboot
timeout 120 adb wait-for-device
timeout 180 bash -c 'until [[ $(adb shell getprop sys.boot_completed 2>/dev/null | tr -d "\r") == 1 ]]; do sleep 2; done'
adb shell input keyevent KEYCODE_WAKEUP
adb shell wm dismiss-keyguard
adb shell am instrument -w -e alert_phase restore "$runner" | tee "$RUNNER_TEMP/alert-reboot.txt"
tr -d '\r' < "$RUNNER_TEMP/alert-reboot.txt" | grep -x 'ALERT_HISTORY_AFTER_REBOOT_OK'

tr -d '\r' < "$RUNNER_TEMP/alert-reboot.txt" | grep -x 'US_LISTING_ARCHIVE_AFTER_REBOOT_OK'

adb shell am instrument -w -e alert_phase recovery "$runner" | tee "$RUNNER_TEMP/market-recovery.txt"
tr -d '\r' < "$RUNNER_TEMP/market-recovery.txt" | grep -x 'MARKET_WIFI_RECOVERY_OK'

adb shell am instrument -w -e alert_phase archive_repair_prep "$runner" | tee "$RUNNER_TEMP/archive-repair-prep.txt"
tr -d '\r' < "$RUNNER_TEMP/archive-repair-prep.txt" | grep -x 'US_ARCHIVE_REPAIR_BEFORE_REBOOT_OK'

adb shell am instrument -w -e alert_phase interrupted_prepare "$runner" | tee "$RUNNER_TEMP/interrupted-prep.txt"
tr -d '\r' < "$RUNNER_TEMP/interrupted-prep.txt" | grep -x 'INTERRUPTED_NOTIFICATION_BEFORE_REBOOT_OK'

adb reboot
timeout 120 adb wait-for-device
timeout 180 bash -c 'until [[ $(adb shell getprop sys.boot_completed 2>/dev/null | tr -d "\r") == 1 ]]; do sleep 2; done'
adb shell input keyevent KEYCODE_WAKEUP
adb shell wm dismiss-keyguard
adb shell am instrument -w -e alert_phase archive_repair_resume "$runner" | tee "$RUNNER_TEMP/archive-repair-resume.txt"
tr -d '\r' < "$RUNNER_TEMP/archive-repair-resume.txt" | grep -x 'US_ARCHIVE_REPAIR_AFTER_REBOOT_OK'


adb shell am instrument -w -e alert_phase interrupted_resume "$runner" | tee "$RUNNER_TEMP/interrupted-resume.txt"
tr -d '\r' < "$RUNNER_TEMP/interrupted-resume.txt" | grep -x 'INTERRUPTED_NOTIFICATION_AFTER_REBOOT_OK'
