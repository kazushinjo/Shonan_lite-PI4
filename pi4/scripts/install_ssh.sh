#!/usr/bin/env bash
# install.shのSSH clone版。GitHubへSSH鍵を登録済みの環境向け
# (git@github.com:... でclone/pullする以外はinstall.shと完全に同じ)。
#
# 使い方:
#   ./pi4/scripts/install_ssh.sh
#   SKIP_JA_KEYBOARD=1 ./pi4/scripts/install_ssh.sh
#   SKIP_GNURADIO_BUILD=1 ./pi4/scripts/install_ssh.sh
set -euo pipefail

export REPO_URL="git@github.com:kazushinjo/Shonan_lite-PI4.git"
exec "$(dirname "$(readlink -f "$0")")/install.sh" "$@"
