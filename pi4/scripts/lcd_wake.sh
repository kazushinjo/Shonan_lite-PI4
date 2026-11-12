#!/bin/sh
# DSI液晶(rpi_backlight / fb0)を確実に点灯させる。root権限で実行する。
#
# shonan-display-off.serviceは終了・再起動時に画面(fb0 blank=4)と
# バックライト(bl_power=4)を消す。電源を切らずに再起動するとLCD側は消えた
# ままになるが、起動直後のカーネルは「点灯中(0)」と認識しているため、
# 起動時に0を書いても同じ値として無視され、ハードに点灯命令が届かない
# (カーネル6.18で実機確認、LCDが暗いままになる)。
# 一度「消灯」を書いてから「点灯」を書き、必ず点灯命令を送る。

FB_BLANK=/sys/class/graphics/fb0/blank
if [ -e "$FB_BLANK" ]; then
  echo 1 > "$FB_BLANK" 2>/dev/null
  sleep 0.2
  echo 0 > "$FB_BLANK" 2>/dev/null
fi

for d in /sys/class/backlight/*; do
  [ -e "$d/bl_power" ] || continue
  echo 4 > "$d/bl_power" 2>/dev/null
  sleep 0.2
  echo 0 > "$d/bl_power" 2>/dev/null
  max=$(cat "$d/max_brightness" 2>/dev/null)
  [ -n "$max" ] || max=255
  echo "$max" > "$d/brightness" 2>/dev/null
done
exit 0
