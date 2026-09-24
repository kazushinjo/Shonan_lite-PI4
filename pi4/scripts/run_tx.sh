#!/usr/bin/env bash
# shonan_tx起動用ラッパー。conf/ + cwd/ のレイアウトを用意してから実行する
# (Dvbs2Native.ktのレイアウトを踏襲: <runtime-dir>/conf と <runtime-dir>/cwd を
# 兄弟ディレクトリとして置き、aff3ctの相対パス "../conf/mod/..." を cwd/ から
# 解決させる)。
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="${SHONAN_RUNTIME_DIR:-$HERE/runtime}"

mkdir -p "$RUNTIME_DIR/cwd"
if [ ! -d "$RUNTIME_DIR/conf" ]; then
  cp -r "$HERE/conf" "$RUNTIME_DIR/conf"
fi

exec "$HERE/build/shonan_tx" --runtime-dir "$RUNTIME_DIR" "$@"
