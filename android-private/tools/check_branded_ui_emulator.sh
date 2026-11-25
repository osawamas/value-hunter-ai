#!/usr/bin/env bash
set -euo pipefail
app="jp.valuehunter.privatewatch.diagnostic19"
apk="android-private/app/build/outputs/apk/debug/app-debug.apk"
adb install "$apk"
mkdir -p brand-ui-artifacts
adb shell am force-stop "$app" || true
adb shell am start -n "$app/jp.valuehunter.privatewatch.SplashActivity"
sleep 1
adb shell screencap -p /sdcard/vh-splash.png
adb pull /sdcard/vh-splash.png "brand-ui-artifacts/splash-${PROBE_API}.png"
sleep 3
adb shell screencap -p /sdcard/vh-home.png
adb pull /sdcard/vh-home.png "brand-ui-artifacts/home-${PROBE_API}.png"
# ImageView test and bundle hashes run separately in the notification emulator suite.
python3 - <<'PY'
import struct,pathlib
for f in pathlib.Path('brand-ui-artifacts').glob('*.png'):
    data=f.read_bytes()
    assert data[:8]==bytes([137,80,78,71,13,10,26,10])
    w,h=struct.unpack('>II',data[16:24])
    assert w>=300 and h>=600,(f,w,h)
    print(f, w,h)
PY
