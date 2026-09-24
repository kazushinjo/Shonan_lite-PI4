#!/bin/bash
# Push this local Langstone-V2 working copy to a Raspberry Pi over SSH,
# instead of having install_dfr0550.sh clone from GitHub on the Pi.
#
# Run this from your PC (not on the Pi):
#   ./deploy_to_pi.sh pi@<raspberry-pi-ip-or-hostname>
#
# Then on the Pi:
#   cd Langstone
#   chmod +x install_dfr0550.sh
#   ./install_dfr0550.sh
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <user@pi-host>" >&2
  echo "Example: $0 pi@192.168.1.50" >&2
  exit 1
fi

PI_TARGET="$1"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

rsync -avz --delete \
  --exclude '.git' \
  --exclude '*.conf' \
  --exclude 'GUI_Pluto' \
  --exclude 'HW_Test' \
  --exclude 'Pluto_Test' \
  --exclude 'run' \
  --exclude 'stop' \
  "$SCRIPT_DIR"/ "$PI_TARGET":/home/pi/Langstone/

echo
echo "Done. Now log in and run the installer:"
echo "  ssh $PI_TARGET"
echo "  cd Langstone"
echo "  chmod +x install_dfr0550.sh"
echo "  ./install_dfr0550.sh"
