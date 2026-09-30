"""Langstone V2の設定ファイル(~/Langstone/Langstone_Pluto.conf)の書き換え。

Home画面の背景の衛星をタップしたとき、Langstoneを10GHz受信用のバンドで開く
(screens/home.py)。Langstoneは起動時にこのファイルを読み、終了時に書き戻すため、
Langstoneが停止している間(Shonan_Lite稼働中)に書き換える。

10GHz受信用のバンドは、Langstoneの24バンドのうち通常使われない最後のバンド
(番号23、画面上は24番目)を使う。LNB(局部発振9750MHz)で周波数を下げて受信する
前提で、表示は10236.5MHz、Plutoの受信周波数は486.5MHz(=10236.5-9750)にする。
486.5MHzはアマチュアバンド外のため、このバンドは受信専用(bandRxOnly)にして
Langstone側で送信を禁止する(LangstoneGUI_Pluto.cのbandRxOnly参照)。
"""
from __future__ import annotations

from pathlib import Path

CONF_PATH = Path.home() / "Langstone" / "Langstone_Pluto.conf"
# 衛星から開いた直前にLangstoneで使っていたバンド。普通の「Langstone」カードで
# 開くときに、このバンドへ戻す。
PREV_BAND_PATH = Path.home() / ".config" / "shonan-pi4" / "langstone_prev_band"

SATELLITE_BAND = 23
SATELLITE_DISPLAY_MHZ = 10236.5
LNB_LO_MHZ = 9750.0


def _read(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []


def _get(lines: list[str], key: str) -> str | None:
    for line in lines:
        parts = line.split(None, 1)
        if len(parts) == 2 and parts[0] == key:
            return parts[1].strip()
    return None


def _set(lines: list[str], key: str, value: str) -> None:
    for i, line in enumerate(lines):
        parts = line.split(None, 1)
        if parts and parts[0] == key:
            lines[i] = f"{key} {value}"
            return
    lines.append(f"{key} {value}")


def _write(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tmp.replace(path)


def select_satellite_band() -> None:
    """次のLangstone起動を10GHz受信用バンド(受信専用)で開くようにする。"""
    lines = _read(CONF_PATH)
    current = _get(lines, "currentBand")
    if current is not None and current != str(SATELLITE_BAND):
        _write(PREV_BAND_PATH, [current])
    b = f"{SATELLITE_BAND:02d}"
    offset = f"{-LNB_LO_MHZ:f}"
    _set(lines, f"bandFreq{b}", f"{SATELLITE_DISPLAY_MHZ:f}")
    _set(lines, f"bandRxOffSet{b}", offset)
    _set(lines, f"bandTxOffSet{b}", offset)
    _set(lines, f"bandRxHarmonic{b}", "1")
    _set(lines, f"bandTxHarmonic{b}", "1")
    _set(lines, f"bandRxOnly{b}", "1")
    _set(lines, "currentBand", str(SATELLITE_BAND))
    _write(CONF_PATH, lines)


def restore_previous_band() -> None:
    """衛星から開いたままなら、次のLangstone起動を衛星の前のバンドで開くようにする。"""
    prev = _read(PREV_BAND_PATH)
    PREV_BAND_PATH.unlink(missing_ok=True)
    if not prev or not prev[0].strip().isdigit():
        return
    lines = _read(CONF_PATH)
    # Langstone上で別のバンドへ切り替えていた場合は、その選択を尊重して変えない。
    if _get(lines, "currentBand") != str(SATELLITE_BAND):
        return
    _set(lines, "currentBand", prev[0].strip())
    _write(CONF_PATH, lines)
