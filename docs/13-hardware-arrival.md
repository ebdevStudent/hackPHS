# Hardware arrival and integration worksheet

Updated 2026-10-10 (ESP32-S3 replaces Mega as the selected bridge board). Planned parts are user-reported ordered. Record actual delivery, identities, dimensions and test outcomes here; ordering alone does not verify compatibility.

## Inventory and measurement

| Item | Source plan | Actual model / revision / measured details | Evidence/date |
| --- | --- | --- | --- |
| Frame | Apex-2, ~95 mm wheelbase | Pending | Pending |
| AIO | HGLRC Specter F411/ESC/ELRS/VTX | Pending exact variant/power limits | Pending |
| Motors | 4 × Specter 1202.5 11000KV | Pending mount/current/shaft | Pending |
| Props | Gemfan 2015, 2-inch | Pending diameter/hub/pack quantity | Pending |
| Battery/charger | User reports 4 × OVONIC 450 mAh and 2 × OVONIC 1100 mAh 2S, 7.6 V, 60C XT30 in inventory (six physical packs total; one 1100 mAh package includes two batteries; [B0D318NL5W](https://www.amazon.com/gp/product/B0D318NL5W); user called it 1150 mAh, listing title says 1100 mAh — check the label); ToothStor charger | In inventory per user; each pack's exact label/chemistry/maximum charge voltage, connector/polarity, charger mode, mass and dimensions still need verification | Pending |
| Camera/antenna | MEIVIFPV listing = Caddx Ant 1200TVL 1.8 mm (14 × 14 mm, 19 × 19 bracket, ~160° H FOV); E-outstanding 70 mm UFL antenna | Pending mounted position/uptilt, antenna routing | Pending |
| Cage parts | 1 × 400 mm rods, PETG hubs, MR52ZZ, Yesallwas 2 × 16 mm stainless pins, VGBUY M2 kit (4–20 mm) | Pending rod/pin diameters, bearing OD/ID/width, screw counts, fit-strip result | Pending |
| Pi/power/cooling/storage | User reports Pi 5; BOM says 64 GB | Raspberry Pi 5 Model B Rev 1.0; aarch64; Raspberry Pi OS/Debian Trixie; Python 3.13; 4045 MB detected. Cooling, power and storage remain unverified | SSH preflight 2026-10-08; [report](../evidence/physical/pi-preflight-2026-10-08.txt) |
| Receiver/power | RC832 receiving the Specter onboard VTX, source 12 V supply | User clarified RC832 receiver use; actual supply/output still pending | User report 2026-10-08 |
| USB capture | User-reported MacroSilicon MS210x (`534d:0021`) | Pi has `/dev/video0` capture and `/dev/video1` metadata nodes. The user's 2026-10-10 `v4l2-ctl` output identifies `/dev/video0` as `uvcvideo` Video Capture at 720x576 YUYV/25 fps (also offers other formats); `/dev/video1` is metadata only. The earlier 30-frame OpenCV read was uniformly black (mean/std 0.0); a live RC832 picture, actual signal, buffering and latency remain unverified | User-pasted Pi outputs, 2026-10-10; prior [Pi capture report](../evidence/physical/pi-preflight-2026-10-08.txt) |
| Flight bridge | User-selected Freenove ESP32-S3 WROOM; user says Mega 2560 is unavailable | Exact board revision/USB port, serial enumeration and firmware integration pending | Pending |
| Transmitter | RadioMaster Pocket ELRS | User linked Pocket ELRS; exact variant/firmware/trainer support pending | User report 2026-10-08 |
| Trainer cable | 3.5 mm mono pigtail candidate | Pending connector/pinout/suitability | Pending |

Pico/audio and the `toImplement` task list remain deferred. The existing Pico scaffold and Mega sketch are historical; neither is evidence of an ESP32-S3 implementation.

## Mechanical measurements before the full cage batch

**Tools (2026-10-08):**

- Measure with [`cad/kit/measurement-form.csv`](../cad/kit/measurement-form.csv): every field with its method, unit and vendor value. Check it with `cad/kit/apply_measurements.py`, which rejects unknown names, wrong units and implausible values, then write it into `measurements.json`.
- Static thrust: [`tools/thrust_log.py`](../tools/thrust_log.py).
- Batteries and contacts: [`docs/25-test-records.md`](25-test-records.md) and `tools/gate_check.py`.
- Rod/hub joints: the [bend-test pieces](../cad/kit/README.md#rod-and-hub-bend-test).

| Measurement | Actual value / evidence |
| --- | --- |
| Maximum outside span and minimum internal cage envelope | Pending |
| Four motor-center coordinates, full prop disks, body/wire/antenna envelopes | Pending |
| Rod/hub/socket retention and loaded/residual deflection | Pending |
| Bare mass, pack mass, available thrust and added-structure allowance | Pending; use [mass worksheet](17-mechanical-cad-brief.md#measured-mass-budget) |
| Each 450 mAh pack | Record label/manual, cell count, nominal and maximum charge voltage, dimensions and mass; confirm charger and AIO compatibility before charging/connecting | Pending |
| Each 1100 mAh pack | Record exact label/manual and measured dimensions/mass; OVONIC listing calls it 2S LiHV but its table has an inconsistent configuration field, ambiguous dimension labels, and a 4.2 V/cell stop-charge notice. Frame seller recommends up to 650 mAh. Flight-unverified until electrical, fit, CG and thrust checks pass | Pending |
| Intended contact objects and opening/probe checks | Pending |
| Repeatable contact setup and per-contact inspection | Pending; use [contact protocol](10-build-and-test.md#repeatable-contact-protocol) |
| For future P1B: 3D CG and axis offsets for each pack | Pending; preserve X/Y adjustment and measure vertical offset |

## Trainer interface — settle before physical output

| Question | Actual verified value and evidence |
| --- | --- |
| Connector orientation, ground/signal pins | Pending |
| Permitted voltage, polarity and ground reference | Pending |
| Protocol: PPM, serial or other actual interface | Pending |
| Frame timing, channels and center/min/max encoding | Pending |
| Yaw channel/sign and transmitter mixes | Pending |
| Pilot authority, override and ARM/DISARM | Pending |
| Power, isolation/level shifting, cable strain relief | Pending |
| Instrument and measured waveform | Pending |
| Communication-loss/watchdog/failsafe action | Pending |
| Complete camera-to-output and takeover latency/jitter | Pending |

A product label or successful USB ASCII ACK cannot fill these rows.

## Navigation and mapping inventory

This worksheet retains the earlier navigation inventory. Current decision: **D435 room mapping will not be done for this project/demo**; its code remains untouched but is not a planned workflow. The active direction is portable FPV/AprilTag interaction in a controlled, unmapped space; see the [portable missions plan](27-portable-visual-missions-plan.md). The user identifies **Pi 5, D435, Freenove ESP32-S3 WROOM, RadioMaster Pocket ELRS** and the video path **Specter onboard VTX → RC832 receiver → composite USB capture → Pi**. Device measurements and live FPV calibration remain unverified.

| Detail needed | Actual value / evidence |
| --- | --- |
| Pi model/RAM, OS/architecture, Python, cooling/power and free storage | **Pi 5**; user says standard OS. Exact release/64-bit architecture/Python/RAM/power/storage remain pending |
| Intel depth-camera model/serial, RGB/depth/IMU capabilities, SDK/runtime compatibility | **RealSense D435**, per user; room mapping is not being done for this project/demo. No further compatibility work is in current scope |
| FC firmware version/build/target, configured modes and available interfaces | Pending |
| Actual FPV camera/capture format, resolution, distortion, latency and buffering | User linked Caddx Ant/MEIVIFPV camera and USB composite capture listing B0CB6BW6X4; actual chipset/format/resolution/distortion/delay remain pending |
| Transmitter/receiver firmware and trainer interface; alternative transport if selected | Pending |
| First desired milestone | Portable FPV/AprilTag interaction in a controlled, unmapped space; physical control authority remains MANUAL/yaw-only as separately verified |
| Small test-zone dimensions, allowed flight volume, surfaces, lighting and pilot access | Small corner of hacking area selected; dimensions and permitted volume still need survey |
| Permission/practicality for printed markers; intended distances, angles and coverage | Pending |
| Fixed external-camera placement/line of sight if that localization route is selected | Pending |
| Raw RGB/depth recording, intrinsics/extrinsics, scanner poses and map units/axes | Outside current project/demo scope; D435 mapping will not be done |
| Moving-person and landing-pad AprilTag family/IDs/sizes; FPV calibration for relative pose | Needed later for physical validation; no fixed room-map survey is required by the portable plan |
| FPV calibration/camera-to-aircraft transform and recording for replay | Pending |
| Exposure/host time provenance, pose error/age, full response latency and jitter | Pending |

Collect these questions together. A small capture/survey experiment should precede a whole-area scan. This worksheet does not change current pilot authority or require additional purchases.

## Ordered checks

1. Inventory and inspect ordered equipment; record receipt/arrival status, dimensions and mass.
2. Establish bare-aircraft manual Betaflight/ELRS operation and radio failsafes.
3. Install the software on the actual Pi in synthetic/mock/MANUAL mode. Measure throughput, deadlines, thermals and power.
4. Verify actual shared-network/hotspot/visitor behavior and RF coexistence.
5. Connect RC832 composite capture. Check live content, color/format/FPS, latency and frozen/disconnected-receiver handling.
6. Verify the manual fallback display: live FPV, target box, center/error and unavailable-steering status.
7. For the assisted route, implement/verify ESP32-S3 output only after the trainer rows are complete. Keep propellers removed for electrical/channel/override/loss checks.
8. For the assisted route, complete 20/20 props-off override checks before the airborne stage; then 5/5 airborne.
9. Build/test the gimbal cage (P1B; no fixed cage is built). Before demo use, require ten consecutive low-energy contacts without damage/prop strikes, ≥3 min usable flight and repeatable recovery.
10. Select the verified demo route and complete three consecutive full rehearsals. Keep the manual fallback ready; zip-tied rings are the only cage fallback.

Bridge/assisted steps 7–8 do not block the accepted manual-contact/live-tracking route. The manual route still requires ordinary aircraft/manual radio authority and live capture.

## Results log

| Check | Configuration | Measured outcome | Evidence | Date/operator |
| --- | --- | --- | --- | --- |
| Pi platform/install/service | Raspberry Pi 5 Model B Rev 1.0; aarch64; Trixie; Python 3.13 | Preflight passed; app installed; service enabled/active; `/api/health` healthy in MANUAL with `physical_output:false`; root and fallback HTTP 200 | [report](../evidence/physical/pi-preflight-2026-10-08.txt) | 2026-10-08 / SSH check |
| Pi capture read/live RC832 | OpenCV/V4L2 camera index 0 as `ball-demo` | 30 frames read at 640x480, all uniformly black. App reports FAULT/stale frame, disabled, yaw 0. Adapter access works; live RC832 image is still missing/unverified | [report](../evidence/physical/pi-preflight-2026-10-08.txt) | 2026-10-08 / SSH check |
| Delivered parts/fit/mass | Pending | Pending | Pending | Pending |
| Pi capture/performance/thermal | Pending | Pending | Pending | Pending |
| Live tracking/fallback screen | Pending | Pending | Pending | Pending |
| Trainer waveform/channel direction | Pending | Pending | Pending | Pending |
| Loss/watchdog/override | Pending | Pending | Pending | Pending |
| Caged endurance/contact/recovery | Pending | Pending | Pending | Pending |
| Gimbal clearance/motion | Pending | Pending | Pending | Pending |
| Consecutive complete rehearsals | Pending | Pending | Pending | Pending |

Keep raw measurements, clips and configuration alongside results. Use the [contingency ledger](02-bom.md#additional-purchase-ledger) for extra purchases. Follow the [freeze rule](12-demo-runbook.md#freeze-and-final-preparation); neither pending hardware nor optional features justify presenting synthetic evidence as physical.

[Hardware](05-hardware.md) · [CAD](03-cad.md) · [Build/test](10-build-and-test.md).


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [OVONIC 7.6 V 450 mAh XT30 listing](https://us.ovonicshop.com/products/2-x-ovonic-7-6v-100c-450mah-2s-lipo-battery-long-size-with-xt30-plug-for-2s-tiny-whoop-micro-fpv-drones-quadcopter) — Listing dimensions, mass and charge notice; delivered pack still governs.
- [OVONIC 2S 1100 mAh 60C XT30 two-pack listing](https://us.ovonicshop.com/products/2-ovonic-rebel-2-0-60c-2s-1100mah-lipo-battery-lihv-7-6v-pack-with-xt30-plug-for-size-100mm-to-140mm-brushless-drones-long-range-drone-fpv) — Includes a 4.2 V/cell notice but contains inconsistent fields; check the physical labels and measurements.
- [HGLRC Specter AIO](https://www.hglrc.com/products/hglrc-specter-10a-1-2s-elrs-aio-vtx-400mw-f411-flight-control-10a-bl_s-5-in-1-fc) — Manufacturer board specifications; confirm actual variant and operating limits.
- [Apex-2 frame seller specification](https://speedyfpv.com/products/apex-2-2-inch-95mm-carbon-fiber-drone-frame-kit?variant=46334350164182) — Seller recommendations and stated mounting patterns; verify delivered parts.
