# pi4/scripts/install.sh Detailed Guide

English translation of [`install_script_guide.md`](install_script_guide.md) (Japanese original).
If the two differ, the Japanese original takes precedence.

`install.sh` is a single script that sets up the whole shonan-pi4 suite (Shonan_Lite itself, GNU Radio for receiving,
Langstone V2Modify and the boot menu) on a fresh Raspberry Pi OS (Debian trixie based). This document explains in
detail what each step does and why it is needed. For primary information on the steps themselves, also see
`docs/qtvirtualkeyboard_ja_build.md` (the Qt Virtual Keyboard build part).

## Assumed Environment

- Raspberry Pi 4 + Raspberry Pi OS 64-bit (equivalent to Debian trixie; assumes apt/systemd)
- Display: DFRobot DFR0550 (5-inch DSI, 800x480), drawn with `linuxfb` (direct drawing to `/dev/fb0`)
- ADALM-Pluto+ (DATV firmware) connected to the same Ethernet network
- Run as a user who can use `sudo`, such as `pi` (the script runs `sudo` in front of individual commands, so the script
  itself does not need to be started as root)

## Requirements (Prerequisites)

For `install.sh` to complete successfully when run as a normal user, all of the following must be in place.

**Required**

1. **Raspberry Pi OS 64-bit (aarch64)** — the script hard-codes `/usr/lib/aarch64-linux-gnu/` as the destination for
   replacing the Qt libraries, so it does not work on the 32-bit (armhf) OS.
2. **`git` installed beforehand** — needed to clone the repository (the pi4 `install.sh` does not install git
   automatically). If it is missing, run `sudo apt-get install -y git` first.
3. **Internet access** — both GitHub (cloning Qt Virtual Keyboard, gr-dvbs2rx and the libraries for Langstone) and the
   Debian apt mirrors must be reachable.
4. **Interactive execution with sudo** — `sudo` is called many times for apt/tee/systemctl, etc., so it assumes a tty
   that can answer password prompts (no problem over SSH as long as there is an interactive tty).
5. **The `patch` command available** — used to apply the dark theme patch in 3/9.

The repository is public, so no GitHub authentication is needed (to clone via SSH, use `install_ssh.sh`).

**Time and resources**

6. The Japanese input build (when `SKIP_JA_KEYBOARD=1` is not specified), the gr-dvbs2rx build and the Langstone
   V2Modify build (including LimeSuite and libiio) each take from a few minutes to tens of minutes, so the network and
   power must not be cut off during them.

**Not required**

- The Pluto+ device does not need to be on the network at the time of running (this only installs software; it is
  needed separately for actual operation).
- A USB camera and audio devices are also not needed at installation time.

## How to Run

```sh
git clone https://github.com/kazushinjo/Shonan_lite-PI4.git
cd Shonan_lite-PI4
./pi4/scripts/install.sh          # clone/pull via HTTPS (default)
./pi4/scripts/install_ssh.sh      # clone/pull via SSH (if your SSH key is registered on GitHub)
```

- `install_ssh.sh` is a thin wrapper that only sets `REPO_URL` to `git@github.com:kazushinjo/Shonan_lite-PI4.git` and
  then calls `install.sh`; all other processing is exactly the same.
- By default the install directory is **the clone the script lives in** (`~/Shonan_lite-PI4` in the example above).
  The services also run `pi4/gui` directly inside this clone.

The behavior can be changed with environment variables.

| Variable | Default | Effect |
| --- | --- | --- |
| `REPO_URL` | `https://github.com/kazushinjo/Shonan_lite-PI4.git` | Where to clone from when the install directory has no source |
| `SHONAN_INSTALL_DIR` | The clone the script lives in | Install directory |
| `QTVK_BUILD_DIR` | `/tmp/qtvirtualkeyboard-src` | Working directory for building Qt Virtual Keyboard |
| `GR_DVBS2RX_BUILD_DIR` | `$HOME/gr-dvbs2rx` | Working directory for building gr-dvbs2rx |
| `LANGSTONE_INSTALL_DIR` | `$HOME/Langstone` | Where Langstone V2Modify is placed |
| `SKIP_JA_KEYBOARD` | `0` | Set to `1` to skip the whole Japanese input build (3/9) |
| `SKIP_GNURADIO_BUILD` | `0` | Set to `1` to skip the whole GNU Radio/gr-dvbs2rx build for RX (4/9) (the receive function will not work) |
| `SKIP_LANGSTONE_BUILD` | `0` | Set to `1` to skip the Langstone V2Modify build (5/9) and the creation of `langstone.service` (Langstone on the Home screen will not work) |

Because `set -euo pipefail` is at the top, the script stops immediately when any command fails (it does not continue in
a half-finished state).

---

## Preparation: Installing Raspberry Pi OS

Raspberry Pi OS must be installed beforehand on the Pi 4 on which `install.sh` will be run (this installation itself is
outside the scope of `install.sh`).

### What you need

- A Raspberry Pi 4
- A microSD card or NVMe SSD (the Pi 4's boot storage)
- A PC for writing (Windows/Mac/Linux) and a microSD card reader, etc.
- Raspberry Pi Imager (the official writing tool, available from https://www.raspberrypi.com/software/)

### Steps

1. Start Raspberry Pi Imager on the PC.
2. Under "Choose Device", select **Raspberry Pi 4**.
3. Under "Choose OS", select **Raspberry Pi OS (64-bit)** (★the 32-bit version does not work; see "Requirements
   (Prerequisites)"). Always choose one whose OS name shows "64-bit" (both 32-bit and 64-bit may appear in the list).
4. Under "Choose Storage", select the microSD/NVMe to write to.
5. Open the gear icon (advanced options) and pre-configure the following so that you can connect via SSH and run
   `install.sh` right after the first boot.
   - Hostname
   - Username and password
   - Wi-Fi (not needed if using wired LAN only)
   - Enable SSH (public-key or password authentication)
6. Run "Write" and wait for it to finish.
7. Attach the microSD/NVMe to the Pi 4 and power it on. The first boot takes a few minutes.
8. Check that you can connect from the PC with `ssh <username>@<hostname>.local` (or the IP address assigned to the
   Pi 4).

The following steps (display settings check to 9/9) are run on the Pi 4, which you can now connect to via SSH.

## Checking the Display Settings (DFRobot DFR0550)

With the default `/boot/firmware/config.txt` of the 2026-09 Raspberry Pi OS (`dtoverlay=vc4-kms-v3d`,
`display_auto_detect=1`, `disable_fw_kms_setup=1`), panel initialization on the KMS side (backlight and touch I2C) times
out on the DFR0550, and neither `/dev/fb0` nor the touch (`raspberrypi-ts`) can be used (confirmed on the device).
Moreover, putting the heavy build load on it in this state made the device reboot and corrupted packages being written
(libcairo2, etc.).

Therefore, it first comments out these three lines and adds `dtparam=i2c_arm=on` if missing, aligning the settings to
use the firmware's legacy DSI display (BCM2708 FB 800x480). **If it changes the settings, it shows "reboot the Pi 4 and
run this script again" and exits**, so run `sudo reboot` and then the same command again (the second time nothing
changes, so it proceeds to 1/9).

## 1/9 Getting the Source

```sh
if [ -d "$INSTALL_DIR/.git" ]; then
  git -C "$INSTALL_DIR" pull --ff-only
elif [ -f "$INSTALL_DIR/pi4/gui/main.py" ]; then
  echo "Using the locally transferred source: $INSTALL_DIR"
else
  git clone "$REPO_URL" "$INSTALL_DIR"
fi
```

- If the install directory is a git clone, it is updated with `git pull --ff-only`. `--ff-only` stops with an error
  when a fast-forward is not possible (e.g. there are local commits), a safety measure to avoid unintentionally
  overwriting or merging local changes.
- If there is no `.git` but `pi4/gui/main.py` exists, it is used as is as source transferred with scp, etc.
- Otherwise it clones fresh from `REPO_URL`.

## 2/9 Runtime Dependency Packages

Installs, with `apt`, the set of Debian packages needed to run the GUI itself (`pi4/gui/main.py`).

| Package | Purpose |
| --- | --- |
| `git`, `curl` | Used for getting the source and HTTP communication |
| `python3-pyqt5` | Qt bindings for the GUI |
| `python3-pyqt5.qtquick` | `QQuickWidget` (used to embed the on-screen keyboard) |
| `python3-pyqt5.sip` | Internal dependency of PyQt5 |
| `python3-pil` | Pillow. Used to composite the callsign/note overlay onto the camera video |
| `ffmpeg` | All video encoding (with the Pi 4's built-in H.264 hardware encoder `h264_v4l2m2m`), multiplexing, overlay compositing and decoding of received video |
| `v4l-utils` | Checking the USB camera's resolution and format (`v4l2-ctl`) |
| `alsa-utils` | Listing audio devices and adjusting volume (`aplay`/`arecord`/`amixer`) |
| `sshpass` | Used to SSH into the Pluto+ with a password to reboot it and write its settings file |
| `fonts-droid-fallback` | Font for drawing Japanese glyphs in the overlay (DroidSansFallbackFull) |
| `fonts-dejavu-core` | Font for drawing alphanumeric glyphs in the overlay (DejaVuSans-Bold) |
| `qtvirtualkeyboard-plugin`, `qml-module-qtquick-virtualkeyboard` | The on-screen keyboard itself (apt version; replaced with the Japanese-capable version in 3/9) |
| `qml-module-qt-labs-folderlistmodel`, `qml-module-qtquick-window2`, `qml-module-qtquick-layouts`, `qml-module-qtquick-controls2`, `qml-module-qtquick2` | Auxiliary modules the on-screen keyboard's QML implementation depends on (if missing, loading the keyboard panel's QML fails) |

★2/9 always runs even with `SKIP_JA_KEYBOARD=1` (the English keyboard itself works with the apt version installed here).

## 3/9 Building Qt Virtual Keyboard with Japanese Input (OpenWnn)

With `SKIP_JA_KEYBOARD=1`, this whole block is skipped; it only shows the message "only the English layout is available"
and proceeds to 4/9.

### Why it must be built from source

The `qtvirtualkeyboard-plugin` distributed via apt by Debian (Raspberry Pi OS) does not include a Japanese input engine
(the engines confirmed on the device were only Hangul, Hunspell (Western languages) and Thai). Even the OSS version of
Qt Virtual Keyboard can include OpenWnn (an open-source kana-kanji conversion engine from Android, Apache license) in
the build, but the Debian package build does not enable it. Therefore the official Qt source is fetched, built
ourselves with `CONFIG+=openwnn`, and the apt version's files are replaced.

### Installing additional development packages for the build

```sh
sudo apt-get install -y \
  qtbase5-dev qtbase5-private-dev qtdeclarative5-dev qtdeclarative5-private-dev \
  qtquickcontrols2-5-dev qt5-qmake build-essential libqt5svg5-dev
```

`libqt5svg5-dev` is especially important. The top-level `.pro` file of Qt Virtual Keyboard declares
`requires(qtHaveModule(svg))`, and if this is not satisfied the whole build silently does nothing **without even an
error message** (`qmake` only prints `Some of the required modules (qtHaveModule(svg)) are not available. Skipped.`, and
the following `make` finishes successfully in an instant). We got stuck on this once on the device, so do not remove
it from the package list.

### Matching the Qt version

```sh
QT_VERSION="$(qmake -query QT_VERSION)"
QT_TAG="v${QT_VERSION}-lts-lgpl"
```

The Qt installed on the Pi 4 (`libQt5Core`, etc.) and the Qt Virtual Keyboard build must be **exactly the same version
at the ABI level**. If the versions differ, it crashes at run time or does not even start. Therefore, instead of a
hard-coded tag, the device's Qt version is obtained dynamically with `qmake -query QT_VERSION`, and the corresponding
`v<version>-lts-lgpl` tag (the naming convention for the LTS/LGPL-license branches of the official Qt repository) is
cloned.

### Applying the dark theme patch

```sh
STYLE_PATCH="$INSTALL_DIR/pi4/docs/patches/qtvirtualkeyboard_style_dark_language_popup.patch"
if [ -f "$STYLE_PATCH" ]; then
  patch -p1 -d "$QTVK_BUILD_DIR" < "$STYLE_PATCH"
fi
```

The language-switching popup that appears when tapping the globe icon on Qt Virtual Keyboard's on-screen keyboard
(by default it lists as many entries as the fallback layouts included in the build, such as British English / American
English / Japanese / Korean / Thai; the list actually shown in the app is narrowed down to three, English GB/US and
Japanese, by `pi4/gui/qml/InputPanelWrapper.qml`; see "Narrowing down the language list" below) is **green text on a
white background** by default, which does not match the dark theme (white text on black) of the whole shonan-pi4 app.
`pi4/docs/patches/qtvirtualkeyboard_style_dark_language_popup.patch` is a diff that rewrites `languageListDelegate`
(text color), `languageListBackground` (background color) and the highlight color of the selected item in Qt Virtual
Keyboard's `src/virtualkeyboard/content/styles/default/style.qml` to the same dark colors as the app. If the `patch`
command is not available or the patch file cannot be found, it is simply skipped and the build continues with the
default colors (not a fatal problem).

★Even when this patch file does not exist in the repository (= e.g. an old commit just cloned locally), it is safely
skipped thanks to the `if [ -f ... ]` guard.

### The build itself

```sh
(
  cd "$QTVK_BUILD_DIR"
  qmake CONFIG+=openwnn CONFIG+=lang-ja_JP CONFIG+=lang-en_GB CONFIG+=lang-en_US \
    qtvirtualkeyboard.pro
  make -j"$(nproc)"
)
```

- `CONFIG+=openwnn`: include the Japanese kana-kanji conversion engine (OpenWnn). By the rule
  `contains(CONFIG, lang-ja.*)|lang-all: CONFIG += openwnn` in `src/config.pri`, specifying `lang-ja_JP` enables it
  implicitly as well, but it is specified explicitly to make the intent clear.
- `CONFIG+=lang-ja_JP CONFIG+=lang-en_GB CONFIG+=lang-en_US`: narrow down the keyboard layouts included in the build
  (if not specified, all languages = `lang-all` are built by default, which takes extra time and resources).
- The subshell `( ... )` keeps the change of the script's current directory by `cd` from leaking outside this step.
- `make -j"$(nproc)"` builds in parallel with as many jobs as there are cores. On the Pi 4 (4 cores), including the
  examples, it takes roughly 10–20 minutes (based on actual measurements on the device).

★Japanese does not become the keyboard's default selected language (it is English right after startup); this is known
behavior, detailed under "pitfalls" in `docs/qtvirtualkeyboard_ja_build.md`. Switch manually with the globe icon.

### Narrowing down the language list

Even with `CONFIG+=lang-ja_JP CONFIG+=lang-en_GB CONFIG+=lang-en_US`, the build still includes fallback layouts for
Korean and Thai, and these two appear unnecessarily in the globe icon's language popup. They cannot be excluded by the
build settings, so the displayed languages are narrowed down at run time with the
`VirtualKeyboardSettings.activeLocales` property of `QtQuick.VirtualKeyboard.Settings`.

`pi4/gui/main.py` loads `pi4/gui/qml/InputPanelWrapper.qml` as the keyboard panel instead of the plain
`InputPanel.qml`. This QML inherits `InputPanel` and sets
`VirtualKeyboardSettings.activeLocales = ["en_GB", "en_US", "ja_JP"]` in `Component.onCompleted`, limiting the language
popup list to three: English GB/US and Japanese.

★This narrowing is not done by `install.sh` but by the code in the repository (`pi4/gui/qml/InputPanelWrapper.qml` and
`pi4/gui/main.py`). Since `install.sh` only does `git clone`/`pull` of the repository, it is reflected as is (no change to
`install.sh` itself is needed).

### Backing up and replacing the apt version's files

```sh
BACKUP_DIR="$HOME/qtvk_backup_$(date +%Y%m%d%H%M%S)"
...
sudo cp -a "$QT5_LIB_DIR"/libQt5VirtualKeyboard.so* "$BACKUP_DIR/" 2>/dev/null || true
...
```

Before replacing, the existing files installed by apt in 2/9 are copied to `~/qtvk_backup_<timestamp>/`. The `|| true`
keeps `set -e` from stopping the whole script in the (normally impossible) case that a source file does not exist.

The following are replaced:

1. `libQt5VirtualKeyboard.so.<version>` — the core shared library itself (the keyboard's layout and style QML are also
   compiled into it as resources)
2. `qml/QtQuick/VirtualKeyboard/libqtquickvirtualkeyboardplugin.so` and `plugins.qmltypes` — the QML module
   `QtQuick.VirtualKeyboard` itself
3. `qml/QtQuick/VirtualKeyboard/Settings/libqtquickvirtualkeyboardsettingsplugin.so` —
   `QtQuick.VirtualKeyboard.Settings` (for settings such as the active locales)
4. `qml/QtQuick/VirtualKeyboard/Styles/libqtquickvirtualkeyboardstylesplugin.so` — `QtQuick.VirtualKeyboard.Styles`
5. `plugins/platforminputcontexts/libqtvirtualkeyboardplugin.so` — the platform input context plugin itself, loaded with
   `QT_IM_MODULE=qtvirtualkeyboard`
6. `plugins/virtualkeyboard/libqtvirtualkeyboard_openwnn.so` — the Japanese input engine itself, the main purpose of
   this step (it does not exist in the apt version, so it is newly placed after `mkdir -p`)

Finally, `sudo ldconfig` updates the shared library cache so that the change takes effect immediately.

### To restore (roll back)

```sh
BK=~/qtvk_backup_<timestamp>   # replace with the actual directory name
sudo cp -a $BK/libQt5VirtualKeyboard.so* /usr/lib/aarch64-linux-gnu/
sudo cp -a $BK/VirtualKeyboard_qml/. /usr/lib/aarch64-linux-gnu/qt5/qml/QtQuick/VirtualKeyboard/
sudo cp -a $BK/libqtvirtualkeyboardplugin.so /usr/lib/aarch64-linux-gnu/qt5/plugins/platforminputcontexts/
sudo cp -a $BK/virtualkeyboard_plugins/. /usr/lib/aarch64-linux-gnu/qt5/plugins/virtualkeyboard/
sudo ldconfig
sudo systemctl restart shonan-gui.service
```

Alternatively, simply `sudo apt-get install --reinstall qtvirtualkeyboard-plugin qml-module-qtquick-virtualkeyboard
libqt5virtualkeyboard5` also returns to the apt version (in this case Japanese input will no longer be available).

## 4/9 Installing GNU Radio + gr-dvbs2rx for Receive (RX)

With `SKIP_GNURADIO_BUILD=1`, this whole block is skipped (the receive function will not work).

```sh
sudo apt-get install -y gnuradio gnuradio-dev cmake pkg-config
git clone https://github.com/igorauad/gr-dvbs2rx.git "$GR_DVBS2RX_BUILD_DIR"   # pull --ff-only if it already exists
git -C "$GR_DVBS2RX_BUILD_DIR" submodule update --init --recursive
git -C "$GR_DVBS2RX_BUILD_DIR" apply "$RX_PATCH"   # only if it exists and is not yet applied
cmake .. -DCMAKE_BUILD_TYPE=Release && make -j"$(nproc)" && sudo make install
```

`pi4/rx/shonan_rx.py` needs `from gnuradio import gr, analog, blocks, iio, dvbs2rx` at run time. `gnuradio` itself
(including `libgnuradio-iio*` with the gr-iio functions) can be installed with Debian's apt, but `dvbs2rx` (the OOT
module for DVB-S2 demodulation, [igorauad/gr-dvbs2rx](https://github.com/igorauad/gr-dvbs2rx)) is not distributed via apt,
so its source is fetched, built and installed. The fixes made for stable reception on the device are applied as
`pi4/docs/patches/gr-dvbs2rx_pi4_bringup.patch` (automatically skipped if already applied). Also see
`pi4/third_party/rpi-dvbs2-receiver-gui/` (imported from kazushinjo/rpi-dvbs2-receiver-gui) as a reference implementation.

★Without this, reception fails at RX start with `ModuleNotFoundError: No module named 'gnuradio'` or
`ImportError: cannot import name 'dvbs2rx'` (found and fixed during a fresh installation on the device).

## 5/9 Building Langstone V2Modify (SDR Transceiver)

With `SKIP_LANGSTONE_BUILD=1`, this whole block is skipped.

- It copies `pi4/third_party/Langstone-V2Modify/` (kazushinjo/Langstone-V2Modify with modifications for integration with
  Shonan_Lite) to `~/Langstone` and runs the bundled installer for Pi 4/DFR0550/ADALM-Pluto, `install_dfr0550.sh`, with
  `SHONAN_INTEGRATION=1`.
- `install_dfr0550.sh` installs the apt packages needed for the build, wiringPi, LimeSuite and libiio 0.25, enables I2C
  and sets up sudoers entries for some commands Langstone uses (`/etc/sudoers.d/langstone`), then builds `GUI_Pluto`.
  With `SHONAN_INTEGRATION=1`, it does not set Langstone to start automatically at login (appending to `.bashrc`);
  starting is handled by the boot menu and `langstone.service`.
- ★`~/Langstone` is overwritten as a whole. Langstone's settings file (`~/Langstone/Langstone_Pluto.conf`) is written by
  Langstone when it exits and is not included in the repository, so it is not overwritten.

## 6/9 Suppressing the Boot Console Output

With a plain Raspberry Pi OS, the kernel boot log and the login prompt appear on the device's LCD when the Pi 4 boots
(confirmed on the device). It does the following three things (a reboot is needed for them to take effect).

- Disables `getty@tty1`.
- Adds `quiet loglevel=3 logo.nologo vt.global_cursor_default=0` to `/boot/firmware/cmdline.txt` (does nothing if
  `quiet` is already there).
- Changes `console=tty1` in `cmdline.txt` to `console=tty3`. With KMS disabled (`linuxfb`), systemd's boot log was
  written directly to the framebuffer and overlapped the Shonan_Lite/Langstone screens (confirmed on the device), so
  nothing is output to the device's LCD (tty1).

## 7/9 Allowing Reboot/Shutdown/App Switching Without a Password

"Power Off" on the Home screen, choosing an app in the boot menu, and switching between Shonan_Lite and Langstone run
`sudo` from systemd services without a TTY. With the standard sudo settings a password is requested, the PAM
conversation fails (`pam_unix: conversation failed`) and the action is not performed — a bug confirmed on the device.
Therefore a rule is written to `/etc/sudoers.d/shonan-pi4-reboot` that lets the running user execute only the following
commands without a password, and it is validated with `visudo -c`.

- `/sbin/reboot`, `/sbin/shutdown`
- `/bin/systemctl start --no-block shonan-gui.service`
- `/bin/systemctl start --no-block langstone.service`
- `/bin/systemctl stop shonan-display-off.service`

## 8/9 Suppressing the Under-Voltage Warning (Lightning Icon)

```sh
if [ -f "$BOOT_CONFIG" ] && ! grep -q '^avoid_warnings=' "$BOOT_CONFIG"; then
  echo "avoid_warnings=1" | sudo tee -a "$BOOT_CONFIG" > /dev/null
fi
```

Adds `avoid_warnings=1` to `/boot/firmware/config.txt` if it is not there (does nothing if it already is; idempotent).
`sudo reboot` is needed for it to take effect. This only suppresses the on-screen lightning icon and log warnings; it does
not solve the actual under-voltage itself (the permanent fix is to use a genuine 27 W USB-C PD power supply and a
good-quality USB cable; `vcgencmd get_throttled` shows whether throttling actually occurs).

## 9/9 Registering the systemd Services

The following four services are created in `/etc/systemd/system/` (`sudo tee` is used because the redirection `>`
itself does not inherit `sudo`'s privileges).

| Service | Contents | Auto start |
| --- | --- | --- |
| `shonan-boot-menu.service` | Full-screen menu at boot for choosing "Shonan_Lite / Langstone" (`pi4/gui/boot_menu.py`). Starts the chosen service with `systemctl start` | Enabled |
| `shonan-gui.service` | Shonan_Lite itself (`pi4/gui/main.py`). Restarted after 3 seconds if it exits abnormally | Disabled (started from the boot menu) |
| `langstone.service` | Langstone V2Modify (`~/Langstone/run_pluto`). Not created with `SKIP_LANGSTONE_BUILD=1` | Disabled (started from the boot menu or by switching) |
| `shonan-display-off.service` | Turns off the DSI display and backlight at shutdown (the DSI LCD keeps showing the last frame after the OS stops) | Enabled |

- `shonan-gui.service` and `shonan-boot-menu.service` run with `QT_QPA_PLATFORM=linuxfb:fb=/dev/fb0:nocursor` (direct
  drawing to `/dev/fb0`). With eglfs (KMS/DRM), panel initialization on the DFR0550 DSI panel could conflict depending on
  the combination with Langstone (legacy framebuffer), and it failed to start due to backlight initialization timeouts,
  garbled colors, `no screens available`, etc. (confirmed on the device).
- `shonan-gui.service`, `langstone.service` and `shonan-boot-menu.service` are mutually exclusive through `Conflicts=`.
  Only one process can use the display, so starting any one of them with `systemctl start` automatically stops the
  others. Apps are switched through this mechanism, without rebooting the Pi 4.
- `ConditionPathExists` checks for the marker file `~/.pi4_boot_mode_langstone`, and the side that should not start does
  nothing and is treated as a successful exit (skipped).
- `langstone.service` embeds the actual value in `Environment=HOME=...` and starts `run_pluto` via `/bin/bash` (because
  the first line of `run_pluto` is not a shebang; confirmed on the device).
- Finally, it runs `daemon-reload`, `stop`s a running `shonan-gui.service`/`langstone.service`, and then `enable`s and
  `restart`s `shonan-boot-menu.service` and `shonan-display-off.service`.

## Display After Completion

It shows the state of `shonan-boot-menu.service` and then the following notes.

1. **Assumption of passwordless sudo/ssh**: the "System Date & Time" setting on the settings screen (`timedatectl`) and
   screenshots of the device's LCD, etc., assume that `sudo` can be run without a password. 7/9 allows only the commands
   above, and no other changes are made to `/etc/sudoers.d/` (`/etc/sudoers.d/langstone` for Langstone is created by
   `install_dfr0550.sh` in 5/9). If needed, the operator decides and configures it individually.
2. **Default language for Japanese input**: the on-screen keyboard starts with the English layout, and can be switched to
   Japanese (romaji input) by tapping the globe icon (it does not switch automatically; known behavior).
3. **avoid_warnings**: if it was newly added in 8/9, `sudo reboot` is needed for it to take effect.

## Related Documents

- `pi4/docs/qtvirtualkeyboard_ja_build.md` — primary information on the 3/9 build steps and details of the pitfalls
  encountered on the device
- `pi4/docs/patches/qtvirtualkeyboard_style_dark_language_popup.patch` — the dark theme patch applied in 3/9 (unified
  diff format, equivalent to `git diff`)
- `pi4/docs/patches/gr-dvbs2rx_pi4_bringup.patch` — the RX stabilization patch applied in 4/9
- `pi4/third_party/Langstone-V2Modify/install_dfr0550.sh` — the Langstone V2Modify installer run in 5/9
- `pi4/docs/shonan_pi4_operation_manual.docx` / `pi4/gui/manual_content.py` — how to operate the GUI itself (how to use
  it after installation)
- `pi4/third_party/rpi-dvbs2-receiver-gui/` — reference implementation of the GNU Radio/gr-dvbs2rx receive flowgraph
  (imported from kazushinjo/rpi-dvbs2-receiver-gui)
