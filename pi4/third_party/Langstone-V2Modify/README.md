# Langstone-V2 SDR Transceiver by Colin Durbridge G4EML

# Personal fork: Adalm Pluto + DFRobot DFR0550 5" Touchscreen only

This is an experimental project to produce a simple VHF, UHF and Microwave SDR Transceiver operating on SSB CW and FM.

For the complete Japanese operating, installation, touch-panel, troubleshooting, and recovery procedures, see [Langstone-V2取扱説明書.docx](Langstone-V2取扱説明書.docx).

It was inspired by the very successful Portsdown Amateur Television system created by the British Amateur Television Club.

To install the software on a raspberry pi please follow the instructions further down the page. 

**More information can also be found on the UK Microwave group wiki at https://wiki.microwavers.org.uk/Langstone_Project**

This fork has been trimmed down to a single supported configuration:-

- Raspberry Pi 4

- DFRobot DFR0550 5" Touchscreen

- Adalm Pluto SDR Module (optionally with a LimeRFE front-end board)

- USB Audio module. Connected to loudspeaker or headphones and microphone. 
 
- USB Scroll mouse

- Optional GPIO extender using MCP23017 Module.

- PTT via Raspberry Pi GPIO pin 11. This needs a pull up resistor to 3.3V. Grounding this pin will switch to Transmit.

- CW Key is via Raspberry Pi GPIO pin 12. This needs a pull up resistor to 3.3V. Grounding this pin will key the transmitter. 

- Tx Output is via Raspberry Pi GPIO pin 40. This output goes high when the Langstone is transmitting. This can be used to switch antenna relays and amplifiers. (100ms delay included for sequencing)

- 8 Band select Outputs on pins 28, 35, 7, 22, 16, 18, 19, and 21. These can be used to select external filters, amplifiers or Transverters. The state of these outputs is defined using the Band Bits setting. 

- The TX output and first three of the Band Select outputs are also available on the Internal Pluto GPO connector. GPO0 is the Tx Output, GPO1-3 are the Band Select outputs. The main use for these is for when the Pluto is remotely mounted. Care must be taken as these pins are low voltage. They will need to be buffered before use. 

- An external MCP23017 module (cheaply available on Ebay etc.) can optionally be used for additional I/O by connecting to the Raspberry Pi i2c bus (pins 3 and 5 of the GPIO connector).

- When using the MCP23017 module Port B will output the 8 band select bits. Port A bit 0 will be the PTT input, Port A bit 1 will be the Key input and Port A bit 7 will be the Tx Output. 

To build a complete functional transceiver you will need to add suitable filters, preamplifiers and power amplifiers to the Adalm Pluto. 

All control is done using the touchscreen and mouse.

Tuning uses the mouse scrollwheel. The mouse left and right buttons select the tuning step. The centre button is used for the CW key.  Mouse movement is not used.

A mouse is used to provide the tuning input because it effectively hands the task of monitoring the tuning knob to a seperate processor (in the mouse). Rotary encoders can be tricky to handle reliably in linux. 

It is easy to modify a cheap mouse by disconnecting the existing switches and wiring the PCB to larger switches on the Langstone front panel. The scroll wheel can likewise be replaced with a panel mounted tuning knob. 

Microphone input and headphone output uses the USB audio device. (a couple of pounds on Ebay)

The software consists of two parts. The SDR itself uses a python GNURadio Flowgraph (Lang_TRX_Pluto.py) which can be created on a PC running GNUradio companion. This Python program is then manually edited by adding the code from ControlTRX_Pluto.py so it can be controlled by the GUI part of the software (LangstoneGUI_Pluto.c). This is written in C and communicates with GNURadio using a Linux Pipe. However to build and use a Langstone transceiver you do not need to know this!



# Installation Manual

This manual covers installing this fork (Pluto + DFR0550 5" only) from a Mac onto a Raspberry Pi 4, deploying the software over SSH instead of cloning from GitHub on the Pi. Do not connect a keyboard or HDMI display directly to the Raspberry Pi at any point; everything is done over the network.

## 1. Flash Raspberry Pi OS to a Micro-SD card

- Install Raspberry Pi Imager on your Mac from https://www.raspberrypi.com/software/
- Insert a good quality class 10 Micro-SD card (16GB or larger) into your Mac.
- Open Raspberry Pi Imager:
  - **Device**: Raspberry Pi 4
  - **Operating System**: Raspberry Pi OS (Legacy, 32-bit) — Bullseye or Buster Lite. (Buster Lite is the version this fork has been tested against; newer Legacy releases should also work.)
  - **Storage**: select your Micro-SD card
- Click the gear icon (⚙, "Edit Settings") before writing and configure:
  - Set hostname, e.g. `langstone` (so the Pi is reachable at `langstone.local`)
  - Enable SSH, "Use password authentication", username `pi`, and a password of your choice
  - Configure your Wi-Fi SSID/password if you are not using Ethernet
- Write the image, then insert the card into the Pi.

## 2. First boot

- Connect the DFR0550 5" HDMI touchscreen, USB mouse, USB sound card, and the Adalm Pluto (via USB) to the Pi. Connect Ethernet, or rely on the Wi-Fi configured above.
- Power up the Pi and wait a minute or two for the first boot to complete.
- Confirm you can reach it from your Mac:

```sh
ping langstone.local
```

(Replace `langstone.local` with whatever hostname you set, or use the Pi's IP address from your router's DHCP client list if `.local` resolution does not work on your network.)

## 3. Deploy this repo to the Pi over SSH

From this local working copy on your Mac (not on the Pi):

```sh
cd ~/AppDev/Langstone-V2
./deploy_to_pi.sh pi@langstone.local
```

This uses `rsync` over SSH to copy the files to `/home/pi/Langstone` on the Pi (you will be prompted for the Pi's SSH password unless you have set up an SSH key). It does **not** touch `github.com/g4eml/Langstone-V2` or any other remote — it only pushes your local files directly to the Pi.

## 4. Run the installer on the Pi

Log in to the Pi over SSH and run the installer from the copy that was just deployed:

```sh
ssh pi@langstone.local
cd Langstone
chmod +x install_dfr0550.sh
./install_dfr0550.sh
```

The build can take a while (compiling GNU Radio, libiio, LimeSuite, WiringPi, etc. from source), but it does not need any input until the very end, so go and make a cup of coffee and keep an eye on the touchscreen. When it finishes it reboots automatically and starts the Langstone Transceiver using the Adalm Pluto.

Note that sometimes the first boot after install does not start correctly; just recycle the power and try again.

## 5. Updating after making further local changes

Whenever you change files in this local working copy, redeploy and rebuild rather than reinstalling from scratch:

```sh
cd ~/AppDev/Langstone-V2
./deploy_to_pi.sh pi@langstone.local
```

Then, on the Pi:

```sh
cd Langstone
./stop
./update
sudo reboot
```

`./update` only rebuilds from the files already on the Pi — it does not clone from GitHub, so your local modifications are preserved.

## 6. Troubleshooting

If the transceiver does not start up correctly after a reboot, log in over SSH and run the built-in self tests:

```sh
cd ~/Langstone
./Pluto_Test
./HW_Test
./set_sound
```

If those do not reveal the problem, check whether the software is actually running:

```sh
ps -ax | grep Lang
```

You should see `Lang_TRX_Pluto.py` and `GUI_Pluto` in the list. If one or both are missing, kill any stuck instance (`kill -9 <pid>`) and start them manually to see any error output:

```sh
cd ~/Langstone
python Lang_TRX_Pluto.py > /tmp/LangstoneTRX_Pluto.log 2>&1 &
tail -f /tmp/LangstoneTRX_Pluto.log
```

Once the flowgraph is running without errors, start the GUI in the foreground to see its output directly:

```sh
./GUI_Pluto
```

Occasional `aU` characters printed to the SSH session indicate a rare audio overrun in GNU Radio on the Pi; this is harmless if it only happens occasionally.


