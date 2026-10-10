# Hardware — intended aircraft and ground system

Source: Google Doc **Hardware**, read 2026-10-07. [Source snapshot](sources/google-doc-2026-10-07/05-hardware.md). Models below are the current source plan. The user reports all planned parts already ordered; arrival, fit and electrical compatibility require confirmation.

## Navigation equipment clarification — 2026-10-08

The user identifies **Pi 5** and **RealSense D435** for ground processing/scanning. Exact RAM/OS/Python, SDK installation and actual device labels/measurements remain pending. The Specter onboard VTX transmits; use the **RC832 receiver**, rather than the TS832 transmitter from that pair, to feed composite USB capture. The radio is user-reported RadioMaster Pocket ELRS; installed EdgeTX/ELRS and FC firmware/trainer interface remain unverified. D435 is ground survey equipment, not aircraft sensing/control authority. [Arrival worksheet](13-hardware-arrival.md) collects unresolved values; [mapping runbook](23-navigation-software.md) specifies surveyed stationary captures and measured FPV calibration.

## Airborne assembly

| Item | Current plan |
| --- | --- |
| Frame | Apex-2, approximately 95 mm wheelbase |
| AIO | HGLRC Specter F411 FC + ESC + ELRS; integrated analog VTX preferred |
| Motors | Four HGLRC Specter 1202.5 11000KV; source states 9 mm M2 mounting |
| Propellers | 2-inch; BOM lists Gemfan 2015 two-blade |
| Battery | User reports four OVONIC 7.6 V nominal 450 mAh and two OVONIC 7.6 V nominal 1100 mAh 2S XT30 packs; verify delivered chemistry and maximum charge voltage |
| Camera | 14 × 14 mm analog FPV; BOM lists MEIVIFPV |
| Antenna | Compatible 5.8 GHz VTX antenna |
| Cage | Straight carbon/fiberglass rods and printed connector nodes; target 245–250 mm outer diameter |
| Center/gimbal | Adjustable Apex-2 mount; P1A fixed first, P1B removable rings/bearings/pivots |

A standalone VTX is only needed if the chosen integrated configuration cannot supply the required video path. The vendor calls the AIO a 1–2S board; its published voltage range and the pack's chemistry/maximum charged voltage must be checked together before connection. Confirm exact board variant, receiver/VTX features, power/current margins, motor/prop mounting and battery limits from the actual parts before assembly.

The 450 mAh listing is titled as a 7.6 V 2S LiPo pack. The Google Doc hardware tab calls it LiHV, while an OVONIC listing for the matching XT30 model says stop charging at 4.2 V/cell. The 1100 mAh title calls the pack “High Voltage” and OVONIC labels a matching product LiHV, but that product page also says to stop at 4.2 V/cell and contains inconsistent specification fields. Treat each pack's exact charge limit as **unresolved** until its delivered label/manual is checked; do not infer a 4.35 V/cell limit from a title or 7.6 V nominal voltage.

The user reports six batteries in inventory: four 450 mAh and two 1100 mAh. The matching OVONIC 1100 mAh listing describes a 2S 7.6 V, 60C XT30 product for 100–140 mm-class drones and lists 65 g per pack, but its specification table has an inconsistent cell-configuration field and ambiguous dimension labels. The Apex-2 is a 95 mm frame and its seller recommends 200–650 mAh. Treat the 1100 mAh packs as owned evaluation candidates, not approved flight packs. Measure each pack, inspect its label/manual, verify charger and AIO voltage limits, then confirm retention, center of gravity, thrust margin and flight time before considering flight. Do not use the vendor's inconsistent dimensions as CAD datums.

## Ground equipment and signal paths

The source calls for a Raspberry Pi **4 or 5**, ELRS radio, RC832 analog receiver, composite USB capture adapter and suitable power supplies. On 2026-10-10 the user replaced the unavailable Mega 2560 with a **Freenove ESP32-S3 WROOM** as the selected flight-assistance bridge board. Existing deployment files were prepared for **Pi 5**; compatibility/performance on either real Pi model remains to be demonstrated.

**Video:** camera → Specter VTX → 5.8 GHz analog link → RC832 → yellow RCA composite output → Linux-compatible USB capture adapter → Pi V4L2 → local vision.

**Assistance:** Pi → USB serial → Freenove ESP32-S3 WROOM → verified trainer input → transmitter → ELRS → flight controller.

**Monitoring:** Pi → Wi-Fi → Mac/visitor devices. Wi-Fi preview is outside the vision/control loop.

The source capture candidate is VIXLW BR116; the BOM provides a capture-card listing. Confirm the actual adapter chipset, Linux V4L2/UVC support, analog standard, resolution, frame rate, buffering and device path. `/dev/video0` is an example, not an assigned device.

The RC832 requires its own specified 12 V supply; the source BOM lists ALITOVE 12 V 1 A. The TS832+RC832 product is a transmitter/receiver bundle, not itself a USB video capture device.

## Pilot authority and trainer verification

Keep ARM/DISARM, throttle, roll, pitch and physical override with the pilot. Computer assistance is yaw-only. Confirm connector orientation, signal protocol, voltage/polarity, frame/channel encoding, transmitter mixes, watchdog response and takeover before adding output.

The existing Pico scaffold and Arduino Mega sketch are historical artifacts; neither implements the selected ESP32-S3 bridge. Firmware/host integration, trainer output and physical acceptance remain unverified. A listed radio or 3.5 mm cable does not establish trainer compatibility.

Pico wireless audio and `toImplement` remain deferred by user instruction; neither is part of the current flight-control bridge.

## Assembly order

1. Confirm actual equipment and establish bare-quad Betaflight/ELRS/manual operation.
2. Verify live FPV capture. For physical assistance, implement and verify the Pi/ESP32-S3/trainer/radio path with props removed; an incomplete bridge does not block the manual fallback.
3. Build the gimbal cage (P1B; the fixed cage is not built); check every prop, camera view, airflow and battery access at several ring positions.
4. Mount and balance the quad/battery on the gimbal axes, using the CG slots for each pack.
5. Validate low-energy contact and recovery.
6. Pass the flight gate on P1B: ten consecutive undamaged/no-prop-strike contacts, at least three minutes usable caged flight and repeatable recovery. Recommended: first hovers with the rings zip-tied, then free them.
7. Integrate bounded yaw assistance only after complete bridge/override/failsafe verification. Otherwise rehearse the accepted manual-contact/live-tracking route; keep it ready regardless.

## Measurements and acceptance

Weigh bare quad, each battery type, cage, gimbal, mounts and wiring separately. Evaluate the user-reported 450 mAh baseline and 1100 mAh candidates only after label/charger/AIO checks. The source's 450–850 mAh range is a planning range; the 1100 mAh packs are outside it and above the Apex-2 seller's 650 mAh recommendation. Verify fit, mass, CG, thrust margin and retention before flight.

Targets: **all-up mass at most 175 g** (user limit, 2026-10-07, with either pack); at least 2:1 static thrust-to-weight; below 1.5:1 triggers redesign; at least 3 minutes usable caged flight, 4–5 desired; ten controlled low-energy contacts without broken members or prop strikes. Keep indoor VTX power low, optional lights switchable and redundant boards off the aircraft.

[Parts and unresolved source issues](02-bom.md) · [CAD](03-cad.md) · [Arrival worksheet](13-hardware-arrival.md) · [Build/test gates](10-build-and-test.md).


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Google Doc — Hardware tab](https://docs.google.com/document/d/1QrmGZfF8AJm1gQhVAsY_8FbZmaZgIQHXRB_zzldYWVA/edit?tab=t.y9xlzm2dw43q) — Source snapshot captured 2026-10-07.
- [HGLRC Specter AIO specifications](https://www.hglrc.com/products/hglrc-specter-10a-1-2s-elrs-aio-vtx-400mw-f411-flight-control-10a-bl_s-5-in-1-fc) — Manufacturer board, mounting, feature and voltage statements.
- [HGLRC Specter 1202.5 motor](https://www.hglrc.com/collections/12-sereis-motors/products/specter-1202-5-11000kv-brushless-motor) — Manufacturer current, voltage, mounting and prop recommendations.
- [Gemfan 2015-2](https://www.gemfanhobby.com/2015-pc-2-blade.html) — Manufacturer prop diameter and shaft/hub variants.
- [Freenove ESP32-S3 WROOM USB guide](https://docs.freenove.com/projects/fnk0085/en/latest/fnk0085/codes/C/35_USB.html) — Board USB-UART and USB-OTG roles; use USB-UART for the Pi serial connection.
- [OVONIC 7.6 V 450 mAh XT30 listing](https://us.ovonicshop.com/products/2-x-ovonic-7-6v-100c-450mah-2s-lipo-battery-long-size-with-xt30-plug-for-2s-tiny-whoop-micro-fpv-drones-quadcopter) — Vendor description contains 4.2 V/cell charge notice; verify the delivered pack label/manual.
- [OVONIC 2S 1100 mAh 60C XT30 two-pack listing](https://us.ovonicshop.com/products/2-ovonic-rebel-2-0-60c-2s-1100mah-lipo-battery-lihv-7-6v-pack-with-xt30-plug-for-size-100mm-to-140mm-brushless-drones-long-range-drone-fpv) — Product title/specification inconsistencies require checking the delivered label and measuring each pack.
