#!/usr/bin/env bash
# install_drf0550.shのSSH clone版。GitHubへSSH鍵を登録済みの環境向け
# (git@github.com:... でclone/pullする以外はinstall_drf0550.shと完全に同じ)。
# 既にローカルにcloneした状態のrepo内から実行した場合は、install_drf0550.sh
# 側のソース取得ステップ(1/9)がclone自体をスキップするため、この
# REPO_URLはネットワーク経由の新規clone/pullが必要な場合のみ使用される。
#
# 使い方:
#   ./pi4/scripts/install_drf0550-ssh.sh
#   SKIP_JA_KEYBOARD=1 ./pi4/scripts/install_drf0550-ssh.sh
#   SKIP_GNURADIO_BUILD=1 ./pi4/scripts/install_drf0550-ssh.sh
#   SKIP_LANGSTONE_BUILD=1 ./pi4/scripts/install_drf0550-ssh.sh
set -euo pipefail

export REPO_URL="git@github.com:kazushinjo/Shonan_lite-PI4.git"
exec "$(dirname "$(readlink -f "$0")")/install_drf0550.sh" "$@"
