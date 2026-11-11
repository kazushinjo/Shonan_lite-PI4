"""設定画面の「Pluto 情報」(iPad/Mac版 SettingsView の Pluto 情報欄と同じ内容)。

どれも読み取りのみで、Plutoには何も書き込まない。
- バージョン: IIOコンテキスト属性(iPad版はiiodへPRINTを送って読む。ここではiio_attr -Cで同じ属性を読む)
- セッティング: Pluto Web UIの settings.txt(送信開始時にこのアプリが save.php で書き込む値)
- AD9361: ad9361-phy の現在値17項目(iPad版 PlutoAD9361Reader と同じ項目)
"""
from __future__ import annotations

import re
import subprocess
import urllib.error
import urllib.request
from typing import Optional

# (表示名(日本語), 表示名(英語), 属性の置き場所, 属性名, 書式)
# 置き場所は None ならデバイス属性、(チャンネル名, 出力か) ならチャンネル属性。
AD9361_ENTRIES = [
    ("ENSMモード", "ENSM mode", None, "ensm_mode", "raw"),
    ("キャリブレーション", "Calibration", None, "calib_mode", "raw"),
    ("xo_correction", "xo_correction", None, "xo_correction", "raw"),
    ("RX LO周波数", "RX LO frequency", ("altvoltage0", True), "frequency", "mhz"),
    ("RX LO停止", "RX LO powerdown", ("altvoltage0", True), "powerdown", "raw"),
    ("RXサンプルレート", "RX sample rate", ("voltage0", False), "sampling_frequency", "mhz"),
    ("RX帯域", "RX bandwidth", ("voltage0", False), "rf_bandwidth", "mhz"),
    ("RXポート", "RX port", ("voltage0", False), "rf_port_select", "raw"),
    ("RXゲイン制御", "RX gain control", ("voltage0", False), "gain_control_mode", "raw"),
    ("RXゲイン", "RX gain", ("voltage0", False), "hardwaregain", "raw"),
    ("RX RSSI", "RX RSSI", ("voltage0", False), "rssi", "raw"),
    ("TX LO周波数", "TX LO frequency", ("altvoltage1", True), "frequency", "mhz"),
    ("TX LO停止", "TX LO powerdown", ("altvoltage1", True), "powerdown", "raw"),
    ("TXサンプルレート", "TX sample rate", ("voltage0", True), "sampling_frequency", "mhz"),
    ("TX帯域", "TX bandwidth", ("voltage0", True), "rf_bandwidth", "mhz"),
    ("TXポート", "TX port", ("voltage0", True), "rf_port_select", "raw"),
    ("TX減衰", "TX attenuation", ("voltage0", True), "hardwaregain", "raw"),
]

# バージョン欄に出すコンテキスト属性(iPad版 PlutoVersionChecker と同じ)。
VERSION_ENTRIES = [
    ("ファーム", "Firmware", "fw_version"),
    ("型式", "Model", "hw_model"),
    ("チップ設定", "Chip", "ad9361-phy,model"),
    ("xo_correction", "xo_correction", "ad9361-phy,xo_correction"),
    ("カーネル", "Kernel", "local,kernel"),
    ("シリアル", "Serial", "hw_serial"),
]

_TIMEOUT_SEC = 8


class PlutoInfoError(Exception):
    pass


def _run_iio_attr(args: list[str]) -> str:
    try:
        result = subprocess.run(["iio_attr", *args], capture_output=True, text=True,
                                timeout=_TIMEOUT_SEC)
    except FileNotFoundError as exc:
        raise PlutoInfoError("iio_attrが見つかりません") from exc
    except subprocess.TimeoutExpired as exc:
        raise PlutoInfoError("Plutoから応答がありません(タイムアウト)") from exc
    text = (result.stdout or "") + (result.stderr or "")
    if "Unable to create IIO context" in text:
        raise PlutoInfoError(f"Plutoへ接続できません: {text.strip().splitlines()[-1]}")
    return result.stdout or ""


def parse_context_attrs(text: str) -> dict[str, str]:
    """`iio_attr -C` の出力(「key: value」の行)を辞書にする。"""
    attrs: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("IIO context with") or ": " not in line:
            continue
        key, value = line.split(": ", 1)
        attrs[key.strip()] = value.strip()
    return attrs


_DEV_ATTR_RE = re.compile(r"^dev '[^']*', attr '([^']+)', value :'(.*)'$")
_CHAN_ATTR_RE = re.compile(
    r"^dev '[^']*', channel '([^']+)' \((input|output)\), (?:id '[^']*', )?attr '([^']+)', value '(.*)'$")


def parse_device_attrs(text: str) -> dict[str, str]:
    """`iio_attr -d ad9361-phy` の出力を {属性名: 値} にする。"""
    attrs: dict[str, str] = {}
    for line in text.splitlines():
        m = _DEV_ATTR_RE.match(line.strip())
        if m:
            attrs[m.group(1)] = m.group(2)
    return attrs


def parse_channel_attrs(text: str) -> dict[tuple[str, bool, str], str]:
    """`iio_attr -c ad9361-phy` の出力を {(チャンネル名, 出力か, 属性名): 値} にする。"""
    attrs: dict[tuple[str, bool, str], str] = {}
    for line in text.splitlines():
        m = _CHAN_ATTR_RE.match(line.strip())
        if m:
            attrs[(m.group(1), m.group(2) == "output", m.group(3))] = m.group(4)
    return attrs


def _format_value(value: Optional[str], fmt: str) -> str:
    if value is None or value == "":
        return "-"
    if fmt == "mhz":
        try:
            return f"{float(value) / 1_000_000:.3f} MHz"
        except ValueError:
            return value
    return value


def read_version(pluto_uri: str, english: bool = False) -> list[tuple[str, str]]:
    attrs = parse_context_attrs(_run_iio_attr(["-u", pluto_uri, "-C"]))
    if not attrs:
        raise PlutoInfoError("Plutoのコンテキスト属性を読めませんでした")
    return [(en if english else ja, attrs.get(key, "-")) for ja, en, key in VERSION_ENTRIES]


def read_ad9361(pluto_uri: str, english: bool = False) -> list[tuple[str, str]]:
    dev_attrs = parse_device_attrs(_run_iio_attr(["-u", pluto_uri, "-d", "ad9361-phy"]))
    # ★チャンネル名を付けずに `-c ad9361-phy` とするとチャンネルの一覧しか出ないため
    # (実機で確認)、使うチャンネルごとに読む(入力/出力の両方が出る)。
    chan_attrs: dict[tuple[str, bool, str], str] = {}
    for channel in sorted({target[0] for _ja, _en, target, _a, _f in AD9361_ENTRIES if target}):
        chan_attrs.update(parse_channel_attrs(
            _run_iio_attr(["-u", pluto_uri, "-c", "ad9361-phy", channel])))
    if not dev_attrs and not chan_attrs:
        raise PlutoInfoError("ad9361-phyが見つかりません")
    rows = []
    for ja, en, target, attr, fmt in AD9361_ENTRIES:
        if target is None:
            value = dev_attrs.get(attr)
        else:
            value = chan_attrs.get((target[0], target[1], attr))
        rows.append((en if english else ja, _format_value(value, fmt)))
    return rows


def parse_settings_txt(text: str) -> list[tuple[str, str]]:
    """settings.txt(1行に「キー 値」)を (キー, 値) の並びにする(iPad版と同じ)。"""
    rows = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        key, _, value = line.partition(" ")
        rows.append((key, value))
    return rows


def read_settings_txt(pluto_host: str) -> list[tuple[str, str]]:
    url = f"http://{pluto_host}/settings.txt"
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            text = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise PlutoInfoError("settings.txtがありません(Pluto起動後、まだ送信していません)") from exc
        raise PlutoInfoError(f"HTTPエラー {exc.code}") from exc
    except (urllib.error.URLError, OSError) as exc:
        raise PlutoInfoError(f"Plutoへ接続できません: {exc}") from exc
    return parse_settings_txt(text)
