#!/bin/sh
# 電源オフ(shutdown/poweroff)時だけDSI液晶とバックライトを消灯する。root権限で実行する。
#
# DSI液晶はOS停止後も最後のフレームを保持するため、電源オフ時は消灯する。
# ただし再起動時に消灯すると、LCDの電源が落ちたまま次の起動に入り、
# ファームウェアがLCDを検出できず /dev/fb0 とバックライトが作られない
# (画面が暗いまま・起動メニューが "no screens available" で起動できない)。
# 実機(カーネル6.18、レガシーフレームバッファ)で確認したため、再起動時は何もしない。

if systemctl list-jobs 2>/dev/null | grep -q -E '(reboot|kexec)\.target'; then
  exit 0
fi

if [ -e /sys/class/graphics/fb0/blank ]; then
  echo 4 > /sys/class/graphics/fb0/blank 2>/dev/null
fi
for p in /sys/class/backlight/*/bl_power; do
  [ -e "$p" ] && echo 4 > "$p" 2>/dev/null
done
exit 0
