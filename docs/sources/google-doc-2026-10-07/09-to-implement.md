# Source snapshot — toImplement

Source: https://docs.google.com/document/d/1QrmGZfF8AJm1gQhVAsY_8FbZmaZgIQHXRB_zzldYWVA/edit?tab=t.pr5w6cacjtya

Read: 2026-10-07. Tab order: 8; parent: none. Adoption deferred by the user; reference capture only.

---

Ishaan:

- Get Filament

- 256gb microsd card

- Setup monoprice voxel 3d

- Set up raspberry pi

- Get raspberry pi pico wireless with headers

- Get mic

- Get speaker

- Pico interfaces with mic and speaker on drone, .not flight controllerAudio / Pico WH Purchase Findings — buy/reserve ASAP

- FASTEST / SAFEST PROCUREMENT: use local pickup rather than shipping if possible. Recent Micro Center listings show the Pico WH, I2S mic, MAX98357A amp, and mini speaker in stock at Yonkers; Brooklyn/Flushing are useful backups. Stock is volatile—verify/reserve before leaving.

- 1. Pico: Raspberry Pi Pico WH (NOT plain Pico W)

- • Exact model: Raspberry Pi Pico WH / SC0919 — wireless + pre-soldered headers.

- • Micro Center SKU: 412197.

- • Typical price found: about $5.99–$6.99.

- • Why: same RP2040/Pico W functionality, but headers are already soldered; avoids wasting hackathon time soldering 40 pins.

- • Wireless: 2.4 GHz 802.11n Wi-Fi + Bluetooth; enough raw bandwidth for compressed voice audio.

- 2. Microphone: Adafruit I2S MEMS Microphone Breakout (SPH0645LM4H)

- • Micro Center SKU: 007153; Adafruit product 3421.

- • Price found: $6.95.

- • Weight: ~0.4 g; size ~16.7 × 12.7 × 1.8 mm.

- • Audio range: ~50 Hz–15 kHz; digital I2S output.

- • Supply/logic: 1.6–3.6 V; run it from the Pico’s 3.3 V rail, not 5 V.

- • Recommendation: use this over an analog mic because it avoids analog noise and gives a clean digital path into the Pico.

- 3. Speaker: 28 mm Round Mini Speaker — 8 Ω, 1 W (Amazon 8-pack)

- • Amazon listing: 8Pcs 8 Ohm 1W Speaker, 28 mm round, 2-pin.

- • Price found: $6.99 for 8.

- • Size: 28 mm diameter, about 5.5 mm thick. Per-speaker weight is not reliably listed; weigh one on arrival.

- • Recommendation: electrically a good match for the MAX98357A and a reasonable drone option. Use one speaker only; keep the rest as spares. Verify actual weight and loudness before mounting.

- 4. Speaker amplifier: Adafruit MAX98357A I2S Class-D Mono Amp

- • Micro Center SKU: 007112; Adafruit product 3006.

- • Price found: $5.95; board weight ~1.2 g.

- • I2S digital input; no separate DAC required.

- • At 3.3 V into 8 Ω it can deliver roughly 0.6–0.8 W; at 5 V it can exceed 1 W.

- • Start at 3.3 V for a safe first test with the 1 W speaker. If it is too quiet over prop noise, use 5 V to the amp but cap software volume/gain so the 1 W speaker is not overdriven.

- 5. Recommended audio architecture

- Pico WH handles AUDIO + Wi-Fi only. Do not route microphone/speaker processing through the flight controller.

- • Mic → I2S → Pico WH → Wi-Fi → ground Raspberry Pi / phone.

- • Ground Raspberry Pi / phone → Wi-Fi → Pico WH → I2S → MAX98357A → speaker.

- • The mic + amp can share I2S clock / word-select lines in a full-duplex design while using separate data-in and data-out lines; exact Pico implementation will use PIO/software I2S.

- • Important: RP2040 does not give you a conventional dedicated hardware I2S peripheral; Raspberry Pi’s Pico audio support uses PIO. Budget software time for audio input/full-duplex rather than assuming it is plug-and-play.

- • Audio parts alone (mic + amp + mini speaker) add only ~4.6 g before Pico/wiring/mounting.

- 6. RF / bandwidth warning

- • Pico WH Wi-Fi is 2.4 GHz, the same band used by ELRS. Bandwidth for voice is not the problem; RF coexistence is.

- • Keep the Pico WH antenna physically separated from the ELRS antenna and away from conductive cage parts where possible.

- • Test ELRS link quality / packet loss with Pico Wi-Fi OFF vs. ON while the motors are running.

- • If Wi-Fi causes measurable ELRS degradation, lower Pico transmit activity/power, physically separate antennas further, and keep the physical ELRS radio as the safety-critical control path.

- 7. Purchase / test order

- 1) Reserve/pick up Pico WH, SPH0645 I2S mic, MAX98357A amp, and Mini Oval 8 Ω 1 W speaker.

- 2) Bench-test mic capture on Pico WH before mounting anything.

- 3) Bench-test speaker/amp at 3.3 V and low software volume.

- 4) Get one-way audio working each direction before attempting simultaneous full-duplex.

- 5) Measure audio latency and ELRS coexistence before putting the system on the drone.

- 6) Only mount after weighing the complete audio/Pico harness and confirming the aircraft still meets the thrust/weight target.





- Bring Nitrile Gloves

- Bring Frappuccino



## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Google Doc — toImplement tab](https://docs.google.com/document/d/1QrmGZfF8AJm1gQhVAsY_8FbZmaZgIQHXRB_zzldYWVA/edit?tab=t.pr5w6cacjtya) — source revision `ANLCKQnLVBOUgYbF9xiV7-InTsia-NHBAIK6uRHga-e4J5upeOn-tJgL1FVO9wv0_COaZWscwb-pNlIDnIFEctx2nWF87sQFyqftuH4YmVg`, captured 2026-10-07.
- This citation note was appended after the captured text; it is not part of the source tab.
