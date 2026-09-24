#!/usr/bin/env bash
# kazushinjo/Langstone-V2Modify の最新版を同梱コピーへ取り込む。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TARGET_DIR="$ROOT/pi4/third_party/Langstone-V2Modify"
UPSTREAM_URL="https://github.com/kazushinjo/Langstone-V2Modify.git"
WORK_DIR="${LANGSTONE_UPDATE_WORKDIR:-/tmp/langstone-v2modify-upstream-update}"

echo "=== 1/2 upstream(${UPSTREAM_URL})を取得 ==="
rm -rf "$WORK_DIR"
git clone --depth 1 "$UPSTREAM_URL" "$WORK_DIR"
rm -rf "$WORK_DIR/.git"

echo "=== 2/2 同梱コピーを更新 ==="
rsync -a --delete "$WORK_DIR/" "$TARGET_DIR/"
rm -rf "$WORK_DIR"

echo "更新完了: $TARGET_DIR"
echo "Shonan統合用の差分を確認し、必要なら再適用してください。"
