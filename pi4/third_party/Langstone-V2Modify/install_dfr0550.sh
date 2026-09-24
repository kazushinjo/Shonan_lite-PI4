#!/bin/bash
# Langstone-V2 installer for Raspberry Pi OS (Bullseye/Bookworm/Trixie).
# This installer deploys the local /home/pi/Langstone copy and is safe to rerun.
set -Eeuo pipefail

PI_HOME=/home/pi
LANGSTONE_DIR="$PI_HOME/Langstone"
LIMESUITE_COMMIT=9c983d872e75214403b7778122e68d920d583add
LIBIIO_COMMIT=b6028fdeef888ab45f7c1dd6e4ed9480ae4b55e3
JOBS="${JOBS:-$(nproc)}"

# Raspberry Pi OS Bookworm/Trixie keeps boot files under /boot/firmware.
# Fall back to the legacy paths for older images.
BOOT_CONFIG=/boot/firmware/config.txt
BOOT_CMDLINE=/boot/firmware/cmdline.txt
[ -f "$BOOT_CONFIG" ] || BOOT_CONFIG=/boot/config.txt
[ -f "$BOOT_CMDLINE" ] || BOOT_CMDLINE=/boot/cmdline.txt

trap 'echo "ERROR: installer failed at line $LINENO" >&2' ERR

if [ "$(id -un)" != pi ]; then
  echo "ERROR: run this installer as the pi user" >&2
  exit 1
fi

echo "#########################################"
echo "## Installing Langstone-V2 Transceiver ##"
echo "#########################################"

echo "#################################"
echo "##  Update the Package Manager ##"
echo "#################################"

# Do not replace the OS repositories with the obsolete Buster repository.
# That broke apt signature verification on modern Raspberry Pi OS releases.
sudo dpkg --configure -a
sudo apt-get -y update

echo "#################################"
echo "##       Install Packages      ##"
echo "#################################"

# gr-iio and raspi-gpio are not available on current Raspberry Pi OS.
# gnuradio-dev provides the packaged IIO integration; raspi-gpio is optional
# at runtime and is handled by run_pluto when present.
sudo DEBIAN_FRONTEND=noninteractive apt-get -y install \
  git wget unzip cmake make gcc g++ pkg-config \
  libxml2 libxml2-dev bison flex libcdk5-dev \
  libaio-dev libusb-1.0-0-dev libserialport-dev libavahi-client-dev \
  gnuradio gnuradio-dev sshpass libi2c-dev doxygen swig \
  libfreetype-dev

echo "#################################"
echo "##     Install Wiring Pi       ##"
echo "#################################"

cd "$PI_HOME"
if [ ! -d WiringPi/.git ]; then
  git clone https://github.com/WiringPi/WiringPi.git WiringPi
fi
git -C WiringPi pull --ff-only
cd WiringPi
./build debian
WIRING_DEB=$(find debian-template -maxdepth 1 -type f -name "wiringpi_*_$(dpkg --print-architecture).deb" -print -quit)
if [ -z "$WIRING_DEB" ]; then
  echo "ERROR: no WiringPi package was produced for $(dpkg --print-architecture)" >&2
  exit 1
fi
sudo apt-get install -y "./$WIRING_DEB"
cd "$PI_HOME"

# Install LimeSuite 22.09 as at 27 Feb 23
# Commit 9c983d872e75214403b7778122e68d920d583add
echo
echo "#######################################"
echo "##### Installing LimeSuite 22.09 #####"
echo "######################################"
if [ ! -d LimeSuite/src ]; then
  wget "https://github.com/myriadrf/LimeSuite/archive/$LIMESUITE_COMMIT.zip" -O /tmp/LimeSuite.zip
  rm -rf "/tmp/LimeSuite-$LIMESUITE_COMMIT"
  unzip -q /tmp/LimeSuite.zip -d /tmp
  rm -rf LimeSuite
  cp -a "/tmp/LimeSuite-$LIMESUITE_COMMIT" LimeSuite
fi

# GCC 14 no longer provides uint8_t transitively through iostream.
MCU_FILE="$PI_HOME/LimeSuite/src/lms7002m_mcu/MCU_File.cpp"
if ! grep -q '#include <cstdint>' "$MCU_FILE"; then
  sed -i '4i#include <cstdint>' "$MCU_FILE"
fi

# Compile LimeSuite
cd LimeSuite
mkdir -p dirbuild
cd dirbuild
cmake ..
make -j"$JOBS"
sudo make install
sudo ldconfig
cd "$PI_HOME"

# Install udev rules for LimeSuite
cd LimeSuite/udev-rules
chmod +x install.sh
sudo /home/pi/LimeSuite/udev-rules/install.sh
cd /home/pi/	

# Record the LimeSuite Version	
echo "9c983d8" >/home/pi/LimeSuite/commit_tag.txt



echo "#################################"
echo "##        Install LibIIO       ##"
echo "#################################"

# Install libiio 0.25
if [ ! -d libiio/.git ]; then
  git clone https://github.com/analogdevicesinc/libiio.git libiio
fi
git -C libiio fetch --depth 1 origin "$LIBIIO_COMMIT"
git -C libiio reset --hard "$LIBIIO_COMMIT"
cmake -S libiio -B libiio/build
cmake --build libiio/build --parallel "$JOBS"
sudo cmake --install libiio/build
sudo ldconfig

cd ~
# Set auto login to command line.

sudo raspi-config nonint do_boot_behaviour B2

# Enable i2c support

sudo raspi-config nonint do_i2c 0

# The GUI starts from the local tty, where sudo cannot ask for a password.
# Allow only the privileged helpers used by run_pluto to run unattended.
sudo tee /etc/sudoers.d/langstone >/dev/null <<'EOF'
pi ALL=(root) NOPASSWD: /usr/bin/amixer, /usr/bin/cp, /usr/bin/raspi-gpio, /usr/bin/tee, /usr/bin/reboot, /sbin/reboot, /bin/systemctl stop shonan-display-off.service
EOF
sudo chmod 440 /etc/sudoers.d/langstone
sudo visudo -cf /etc/sudoers.d/langstone

# Use the Langstone files already copied to this Pi over SSH (e.g. via
# deploy_to_pi.sh run from your PC: rsync -avz . pi@<pi>:/home/pi/Langstone/)
# instead of cloning from GitHub.

echo "###################################"
echo "##     Installing Langstone-V2   ##"
echo "###################################"

if [ ! -d "$LANGSTONE_DIR" ]; then
  echo "ERROR: /home/pi/Langstone not found." >&2
  echo "Copy the Langstone files to this Pi over SSH first" >&2
  echo "(e.g. run deploy_to_pi.sh from your PC), then re-run" >&2
  echo "this script from inside /home/pi/Langstone." >&2
  exit 1
fi

cd "$LANGSTONE_DIR"
chmod +x build
chmod +x run_pluto
chmod +x stop_pluto
chmod +x update
chmod +x set_pluto
chmod +x set_sound

./build


#make Langstone autostart on boot

if [ "${SHONAN_INTEGRATION:-0}" != "1" ] && ! grep -q '/home/pi/Langstone/run' "$PI_HOME/.bashrc"; then
  echo if test -z \"\$SSH_CLIENT\" >> ~/.bashrc 
  echo then >> ~/.bashrc
  echo /home/pi/Langstone/run >> ~/.bashrc
  echo fi >> ~/.bashrc
fi

# Configure the boot parameters. DFR0550 is an 800x480 Raspberry Pi DSI
# display. The known-good Langstone image uses the legacy framebuffer stack:
# firmware display auto-detection creates both the DSI framebuffer and the
# raspberrypi-ts touchscreen. Do not force the KMS DSI overlay here.

if ! grep -q '^disable_splash=1' "$BOOT_CONFIG"; then
  echo 'disable_splash=1' | sudo tee -a "$BOOT_CONFIG" >/dev/null
fi
if ! grep -q 'vt.global_cursor_default=0' "$BOOT_CMDLINE"; then
  sudo sed -i '1s,$, vt.global_cursor_default=0,' "$BOOT_CMDLINE"
fi
# Remove stale HDMI/KMS settings from earlier installer revisions.
sudo sed -i '/^hdmi_force_hotplug=1$/d;/^hdmi_group=2$/d;/^hdmi_mode=87$/d;/^hdmi_cvt=800 480 60 6 0 0 0$/d' "$BOOT_CONFIG"
sudo sed -i 's/ video=HDMI-A-1:800x480@60D//g' "$BOOT_CMDLINE"
# ★Shonan_Lite-RasPI5のLangstone-V3インストーラ(installPluto.sh)を参考に、
# KMS overlayは削除ではなくコメントアウトのみとし、disable_fw_kms_setupや
# display_auto_detectの追加操作は行わない(Pi5側はこれらを一切触っていない)。
# Pi4のDFR0550ではKMS有効時にfirmwareのディスプレイ自動検出と競合し
# バックライト初期化タイムアウトや画面の色化けを実機で確認しているため、
# Shonan_Lite側(eglfs)との相性を再検証する目的の変更。
sudo sed -i '/^dtoverlay=vc4-kms-v3d$/s/^/#/' "$BOOT_CONFIG"

cd "$LANGSTONE_DIR"
ln -sf "$LANGSTONE_DIR/run_pluto" "$LANGSTONE_DIR/run"
ln -sf "$LANGSTONE_DIR/stop_pluto" "$LANGSTONE_DIR/stop"

echo "#################################"
echo "##       Reboot and Start      ##"
echo "#################################"

# Shonan統合時は後続のsystemd登録を続けるため、ここでは再起動しない。
if [ "${SHONAN_INTEGRATION:-0}" != "1" ]; then
  sudo reboot
fi
