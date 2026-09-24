# tanzawa_lite-android parameter port

Reference: `kazushinjo/tanzawa_lite-android` commit
`cc167c9c71c18a7efff040d7ffe949df09c919d0`.

The Pi 4 implementation uses the same operational meanings and defaults for:

- band profiles and custom TX/RX frequency;
- symbol rate in Msym/s (converted to Ksym/s for the Pluto RTMP URL);
- DVB-S2 FEC and modulation, with standard MODCOD validation;
- Pluto address, RTMP port 7272, TS port 4003, and status port 4002;
- RX AGC/manual gain (0–73 dB), TX attenuation (-70–0 dB), and RX volume;
- color-bar source, 400 kbps H.264, and 16 kbps AAC;
- localhost/remote software loopback and simultaneous TX/RX testing.

Pi-specific adaptations:

- `pluto_uri` stores the Android `txDestinationIP` as a libiio URI;
- the local `rpi-dvbs2-receiver-gui` watchdog performs DVB-S2 demodulation;
- ffplay provides video/audio rendering and is restarted when volume changes;
- loopback uses MPEG-TS over UDP without starting the SDR receiver.
