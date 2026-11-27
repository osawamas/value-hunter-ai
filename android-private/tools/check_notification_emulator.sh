#!/usr/bin/env bash
set -euo pipefail
trap 'timeout 15 adb logcat -b crash -d -t 150 AndroidRuntime:E "*:S" || true' ERR

app=${APP_PACKAGE:-jp.valuehunter.privatewatch.diagnostic19}
runner="$app.test/jp.valuehunter.privatewatch.JpxPdfGeometryProbe"
adb install android-private/app/build/outputs/apk/debug/app-debug.apk
adb install android-private/app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk
grant_notifications() {
  if (( PROBE_API >= 33 )); then
    timeout 30 adb shell pm grant "$app" android.permission.POST_NOTIFICATIONS
  fi
}

run_phase() {
  local phase=$1 file=$2
  timeout 150 adb shell am instrument -w -e alert_phase "$phase" "$runner" | tee "$RUNNER_TEMP/$file"
}

grant_notifications
adb shell settings put global stay_on_while_plugged_in 0
run_phase delivery_core alert-core.txt
tr -d '\r' < "$RUNNER_TEMP/alert-core.txt" | grep -x 'ALERT_CORE_DELIVERY_OK'
timeout 30 adb shell pm clear "$app"
grant_notifications
run_phase post alert-post.txt
tr -d '\r' < "$RUNNER_TEMP/alert-post.txt" | grep -x 'ALERT_SILENT_WAKE_AND_HISTORY_OK'
tr -d '\r' < "$RUNNER_TEMP/alert-post.txt" | grep -x 'MARKET_WIFI_SWITCH_OK'

adb reboot
timeout 120 adb wait-for-device
timeout 180 bash -c 'until [[ $(adb shell getprop sys.boot_completed 2>/dev/null | tr -d "\r") == 1 ]]; do sleep 2; done'
adb shell input keyevent KEYCODE_WAKEUP
adb shell wm dismiss-keyguard
run_phase restore alert-reboot.txt
tr -d '\r' < "$RUNNER_TEMP/alert-reboot.txt" | grep -x 'ALERT_HISTORY_AFTER_REBOOT_OK'

tr -d '\r' < "$RUNNER_TEMP/alert-reboot.txt" | grep -x 'US_LISTING_ARCHIVE_AFTER_REBOOT_OK'

run_phase recovery market-recovery.txt
tr -d '\r' < "$RUNNER_TEMP/market-recovery.txt" | grep -x 'MARKET_WIFI_RECOVERY_OK'

run_phase archive_repair_prep archive-repair-prep.txt
tr -d '\r' < "$RUNNER_TEMP/archive-repair-prep.txt" | grep -x 'US_ARCHIVE_REPAIR_BEFORE_REBOOT_OK'

run_phase interrupted_prepare interrupted-prep.txt
tr -d '\r' < "$RUNNER_TEMP/interrupted-prep.txt" | grep -x 'INTERRUPTED_NOTIFICATION_BEFORE_REBOOT_OK'

adb reboot
timeout 120 adb wait-for-device
timeout 180 bash -c 'until [[ $(adb shell getprop sys.boot_completed 2>/dev/null | tr -d "\r") == 1 ]]; do sleep 2; done'
adb shell input keyevent KEYCODE_WAKEUP
adb shell wm dismiss-keyguard
run_phase archive_repair_resume archive-repair-resume.txt
tr -d '\r' < "$RUNNER_TEMP/archive-repair-resume.txt" | grep -x 'US_ARCHIVE_REPAIR_AFTER_REBOOT_OK'


run_phase interrupted_resume interrupted-resume.txt
tr -d '\r' < "$RUNNER_TEMP/interrupted-resume.txt" | grep -x 'INTERRUPTED_NOTIFICATION_AFTER_REBOOT_OK'
