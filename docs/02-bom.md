# Bill of materials — ordered plan and contingency

Source: Google Doc **BOM**, read 2026-10-07. [Exact source table and original vendor links](sources/google-doc-2026-10-07/02-bom.md). User clarification on 2026-10-07: **all currently planned parts have already been ordered**.

## Current purchase status and spending rule

Treat planned-part ordering as **user-reported**, not receipt/delivery/compatibility verification. The source's Done?/Ordered? cells remain blank; the table preserves that source state separately from the user's newer report.

The hard cap for **additional purchases is $200 total**. Reserve at least **15% ($30)** for replacements, failed prints, shipping issues and rework; at most **$170** is available before using that reserve. Do not fund optional features until the core build is working. Record each additional purchase and the remaining balance.

## Amazon sourcing instruction

The user says this is the complete parts list and intends to source planned purchases from Amazon. Treat Amazon URLs/ASINs in the supplied list as selected sourcing references, not confirmation of current listing identity, price, stock, order or delivery. The source BOM links the HGLRC Specter AIO to GetFPV and provides no Amazon ASIN. Keep that exact product unresolved until an Amazon listing is confirmed to match the HGLRC Specter AIO F411, ELRS, 1–2S, 10A ESC and 400 mW VTX. The Pi and Pi power supply are reported already owned. On 2026-10-10 the user said the team does not have the source BOM's Arduino Mega and selected a Freenove ESP32-S3 WROOM in its place; this supersedes the bridge row in the source table. The speaker is optional and its audio work remains deferred. The earlier report that planned parts were ordered remains a separate user-reported status; verify receipts and arrivals in the worksheet.

## Source purchasing table

These are source selections and **source estimated prices**, not verified current prices, stock or delivered parts. Quantity can mean a retail pack. Do not multiply prices by quantity or treat their sum as a confirmed purchase total until pack contents and row-cost meaning are checked.

| Category | Part | Source quantity | Item / source link | Source estimated cost | Source Done? | Source Ordered? |
| --- | --- | --- | --- | --- | --- | --- |
| Drone | Frame | 1 | [Apex-2 Frame](https://www.amazon.com/dp/B0B25C6XRD) | 15$ | Blank in source | Blank in source |
| Drone | Flight controller + ESC | 1 | [HGLRC Specter AIO](https://www.getfpv.com/fpv/video-transmitters/hglrc-specter-aio-f411-elrs-fc-10a-1-2s-blheli-s-esc-400mw-vtx.html) | 99$ | Blank in source | Blank in source |
| Drone | Brushless motors | 4 | [HGLRC Specter 1202.5 11000KV](https://www.amazon.com/dp/B0CHN18RXH?th=1) | 64$ | Blank in source | Blank in source |
| Drone | Propellers | 1 | [Gemfan 2015 2-Blades Props](https://www.amazon.com/dp/B0DPB4WM4T) | 10$ | Blank in source | Blank in source |
| Drone | Battery | 2 | [OVONIC 7.6V 100C 450mAh 2S Lipo Battery Long Size](https://www.amazon.com/dp/B0D3F5SQ5T) | 40$ | Blank in source | Blank in source |
| Drone | Battery Strap | Not specified | [Battery Strap](https://www.amazon.com/dp/B01BR2DFV0) | 7$ | Blank in source | Blank in source |
| Drone | FPV camera | 1 | [MEIVIFPV FPV Camera](https://www.amazon.com/dp/B0DZJTMPHS?th=1) | 20$ | Blank in source | Blank in source |
| Drone | VTX antenna | 1 | [E-outstanding FPV Antenna](https://www.amazon.com/dp/B08M39CG7T) | 7$ | Blank in source | Blank in source |
| Drone | Cables | 1 | [BNTECHGO 30 AWG](https://www.amazon.com/dp/B01M70EDCW?th=1) | 10$ | Blank in source | Blank in source |
| Drone | Heatshrink | 1 | [Heat Shrink Tubing](https://www.amazon.com/dp/B0DRKLWLY5) | 5$ | Blank in source | Blank in source |
| Drone | XT30 Connector Male Female | 1 | [10 Pairs XT30 Connector Male Female](https://www.amazon.com/dp/B07CTRH86M) | 9$ | Blank in source | Blank in source |
| Cage | Straight rods | 3 | [Carbon Fiber Rods](https://www.amazon.com/dp/B0BDL6X2ZG?th=1) | 24$ | Blank in source | Blank in source |
| Cage | Gimbal bearings | 1 | [MR52ZZ Bearings](https://www.amazon.com/dp/B07X9T5F81?th=1) | 10$ | Blank in source | Blank in source |
| Cage | Pivot pins | 1 | [Yesallwas100Pcs 2mm X 16mm Dowel Pin](https://www.amazon.com/dp/B07V4HPJWD?th=1) | 8$ | Blank in source | Blank in source |
| Cage | Screws and Washers | 1 | [https://www.amazon.com/dp/B0FJ1XLMJT?lv=shuf&](https://www.amazon.com/dp/B0FJ1XLMJT) | $8 | Blank in source | Blank in source |
| Cage | Epoxy | 1 | [J-B Weld 50112 ClearWeld?](https://www.amazon.com/dp/B009EU5ZM0) | $6 | Blank in source | Blank in source |
| Cage | PETG Filament | 1 | [Creality PETG Filament 1.75mm](https://www.amazon.com/dp/B0DFCG5PZT?th=1) | 22$ | Blank in source | Blank in source |
| Ground | USB FPV receiver | 1 | [AKK TS832+RC832](https://www.amazon.com/dp/B01FXGQ2KC) | 54$ | Blank in source | Blank in source |
| Ground | ELRS radio compatible with the arduino | 1 | [RadioMaster Pocket Crush ELRS](https://www.amazon.com/dp/B0HBZ4VY3S?th=1) | 72$ | Blank in source | Blank in source |
| Ground | Battery charger | 1 | [ToothStor 4-Port 2S LiPo Balance Charger](https://www.amazon.com/dp/B0GS5658RG) | 35$ | Blank in source | Blank in source |
| Ground | USB video capture card | 1 | [Capture Card](https://www.amazon.com/dp/B0CB6BW6X4) | 13$ | Blank in source | Blank in source |
| Ground | Mask | 1 | [Premium Respirator](https://www.amazon.com/dp/B0D9R8H8T7) | 25$ | Blank in source | Blank in source |
| Ground | Raspberry PI | 1 | Have already | Not supplied | Blank in source | Blank in source |
| Ground | Raspberry PI power supply | 1 | Have already | Not supplied | Blank in source | Blank in source |
| Ground | Raspberry Pi microSD card | 1 | 64 gig | Not supplied | Blank in source | Blank in source |
| Ground | Soldering Kit | 1 | [Soldering Iron Kit](https://www.amazon.com/dp/B087767KNW?th=1) | 11$ | Blank in source | Blank in source |
| Ground | Arduino 2560 | 1 | Have already | Not supplied | Blank in source | Blank in source |
| Ground | 3.5mm Mono Male Plug Pigtail Wire | 1 | [3.5mm Mono Male Plug Pigtail Wire](https://www.amazon.com/dp/B0813BQ2XW) | 10$ | Blank in source | Blank in source |
| Drone | Speaker | 1 | CQRobot CQR3020-8O1W-A 8Ω 1W Mini Rectangular Speaker, 30×20×4 mm, 80 mm leads | TBD | Blank in source | Blank in source |
| Ground* | RC832 12 V power supply | 1 | [ALITOVE DC 12V 1A Power Supply](https://www.amazon.com/dp/B07VQHYGRD?th=1) | 7$ | Blank in source | Blank in source |

*The source labels the RC832 power-supply row “Total.” It contains an individual 12 V supply, not a project total; this table places it under ground equipment.*

Blank status cells do not mean “not ordered”: the user has supplied the newer aggregate ordering status above. They do not establish delivery, assembly or testing either.

### User-reported battery inventory

The user reports **six physical packs in inventory**: four OVONIC 450 mAh 2S XT30 packs and two OVONIC 1100 mAh 2S, 7.6 V, 60C XT30 packs. The user identified the 1100 mAh model as “OVONIC 2S 1100mAh Lipo Battery 7.6V 60C Battery with XT30 Plug High Voltage”; the supplied product title says **one package includes two batteries**, matching the two 1100 mAh packs reported. Keep physical-pack counts distinct from retail-package quantities in the source table. The OVONIC listing describes the 1100 mAh model for 100–140 mm-class drones; its specification table also has conflicting configuration and dimension labels, so do not use its dimensions as CAD datums. The Apex-2 seller recommends 200–650 mAh. Treat the 1100 mAh packs as evaluation candidates: verify each label/manual, weigh and measure each pack, confirm charger/AIO voltage limits, and check retention, CG and thrust margin before flight.

## Inventory notes from the source

- The propeller listing reportedly includes three additional spare propellers; confirm pack contents.
- The soldering kit already includes solder and flux.
- Zip ties, double-sided foam tape and electrical tape are reported already owned.
- Raspberry Pi and Pi power supply are reported already owned; the user selected the Freenove ESP32-S3 WROOM bridge board and reports no Arduino Mega 2560. Verify the ESP32 board revision and USB interface in the arrival worksheet.
- Battery-strap quantity is unspecified.
- The optional speaker row remains source information. Pico/audio procurement and integration are deferred with `toImplement`; this rewrite does not activate those tasks.

## Researched part specifications (2026-10-07)

These are published listing, manufacturer or reseller values, gathered for CAD and **not measurements of the delivered parts**. On 2026-10-07 every Amazon page was read in full (bullets, description and detail tables); values marked "Amazon listing" come from there. Items in the last column are genuinely not published on the listing. The machine-readable copy used by the CAD generator is [`cad/apex2-cage/vendor_specs.json`](../cad/apex2-cage/vendor_specs.json).

| Part (Amazon link) | Identified product | Published dimensions / specs | Still to measure |
| --- | --- | --- | --- |
| [Frame B0B25C6XRD](https://www.amazon.com/dp/B0B25C6XRD) | QWinOut APEX-2, 2-inch 95 mm carbon frame (frame only) | 95 mm wheelbase; bottom plate 2.5 mm, upper and side plates 1.5 mm; 20 mm column height; FC 20×20 / 25.5×25.5 / 26.5×26.5 mm; motor 9×9 mm; 14 mm camera width; 18 g; seller recommends 2–6S **200–650 mAh** (Amazon listing) | Centre-plate width (not on the listing), camera-mount position |
| [Motors B0CHN18RXH](https://www.amazon.com/dp/B0CHN18RXH) | HGLRC Specter 1202.5 11000KV | Ø15.84 × 8.9 mm; M1.5 × 4.8 mm shaft; 4 × M2 on Ø9 mm; 4.47 ± 0.3 g with wire; **80 mm wires**, no plug; 9N12P; 1–2S; 88 W max; includes 2 × M2×7 and 4 × M2×5 screws (Amazon listing). The thrust table has no 2-inch props; the nearest is Gemfan 65 mm at 2S, 100 % = 222 g per motor, 9.7 A ([table](https://rcdrone.top/products/specter-1202-5-11000kv-brushless-motor)). That is an upper reference only. | Static thrust with the Gemfan 2015 on 2S |
| [Props B0DPB4WM4T](https://www.amazon.com/dp/B0DPB4WM4T) | Gemfan 2015 2-blade, 16 pcs (8 CW / 8 CCW), sold by MEIVIRC | 2 in × 1.5 in pitch; PC; 0.5 g; 1.5 mm centre hole (Amazon listing) | Hub Ø/height (not on the listing); assembled prop height above frame (~9 mm assumed) |
| [450 mAh B0D3F5SQ5T](https://www.amazon.com/dp/B0D3F5SQ5T) | OVONIC 7.6 V 100C 450 mAh 2S long, XT30, 2 per package | **62.8 × 16.4 × 13.8 mm, 26 g**; LiPo, 2S1P; **stop charging at 4.2 V/cell** (Amazon listing) | Cable length; confirm label |
| [1100 mAh B0D318NL5W](https://www.amazon.com/gp/product/B0D318NL5W) | OVONIC 2S **1100 mAh** 7.6 V 60C XT30, 2 per package (user called it 1150 mAh; the listing says 1100 everywhere) | **56.56 × 23.50 × 18.40 mm, ~48 g**; LiPo 2S1P; cell 3.8–4.2 V; **stop charging at 4.2 V/cell** despite "High Voltage" in the title (Amazon listing). Above the frame seller's 650 mAh recommendation. | Cable length; confirm label |
| [Strap B01BR2DFV0](https://www.amazon.com/dp/B01BR2DFV0) | Apex RC #3060, nylon, 5 pcs | 12.5 × 200 mm (Amazon listing) | Thickness (not on the listing) |
| [Camera B0DZJTMPHS](https://www.amazon.com/dp/B0DZJTMPHS) | MEIVIFPV listing of **Caddx Ant 1200TVL 1.8 mm**, 4:3, NTSC/PAL | 14 × 14 mm body, 19 × 19 mm with bracket, ~2 g, DC 3.7–18 V, CVBS ([GetFPV](https://www.getfpv.com/caddx-ant-1200tvl-1-8mm-fpv-nano-camera-14x14-black.html)); FOV ~160° H / ~120° V / 165–170° D ([Rotorama](https://www.rotorama.com/product/caddx-ant-nano)) | Mounted position, uptilt |
| [Antenna B08M39CG7T](https://www.amazon.com/dp/B08M39CG7T) | E-outstanding 5.8 GHz UFL/IPEX, dual pack | 70 mm long, 2.15 dBi, 50 Ω ([vxb](https://vxb.com/products/dual-pack-seven-centimeter-five-point-eight-gigahe)) | Polarisation, mounted routing (must stay out of prop disks) |
| [Dowel pins B07V4HPJWD](https://www.amazon.com/dp/B07V4HPJWD) | Yesallwas 2 × 16 mm 304 stainless dowel pins, 100 pcs | Ø2 mm +0/−0.02 mm, 16 mm ± 0.5 mm, centerless ground, chamfered ends, 0.4 g each; seller advises a hole ≤ 2 mm for a tight fit (Amazon listing). 304 is not hardened, so it is cuttable. | Press-fit hole size via test coupon |
| [Bearings B07X9T5F81](https://www.amazon.com/dp/B07X9T5F81) | Donepart MR52ZZ, 10 pcs | 2 mm bore × 5 mm OD × 2.5 mm wide, double shielded, chrome steel (Amazon listing) | Precision grade; seat press fit via test coupon |
| [Screw kit B0FJ1XLMJT](https://www.amazon.com/dp/B0FJ1XLMJT) | VGBUY 840 pcs M2 kit, 304 stainless | M2 × 4/6/8/10/12/16/20 mm socket-head cap screws, nuts, washers (Amazon title). ISO standard sizes: head Ø3.8 × 2 mm, nut 4 mm AF × 1.6 mm, washer 5 × 2.2 × 0.3 mm | Per-size counts; actual head/nut sizes |

## Resolve on arrival

| Source issue | Required resolution |
| --- | --- |
| “USB FPV receiver” names AKK TS832+RC832 | RC832 supplies composite video; a separate USB capture adapter feeds the Pi. Identify whether the bundled TS832 is needed with the Specter VTX. |
| Radio listed as Arduino-compatible | Verify trainer protocol, electrical levels, channel encoding and mixes. |
| 3.5 mm mono cable | Check actual trainer connector/pinout before using it. |
| AIO/motor/prop/battery combination | Check exact board variant, limits, mounting and prop hub dimensions. |
| OVONIC pack chemistry/charge limit | The 450 mAh listing title says 7.6 V 2S LiPo; the Hardware source calls it LiHV. The 1100 mAh title says High Voltage and OVONIC's current matching listing labels it LiHV, but both vendor pages include a 4.2 V/cell stop-charge notice. Check each delivered label/manual and verify charger and AIO limits; do not assume 4.35 V/cell. |
| 1100 mAh pack fit/use | User reports two 1100 mAh packs. The Apex-2 seller recommends 200–650 mAh, and OVONIC targets this product at 100–140 mm-class drones. Its listing claims 65 g per pack but contains inconsistent configuration/dimension fields. Measure dimensions/mass and verify retention, CG, thrust and electrical limits before any flight. |
| FC/AIO mounting | HGLRC specifies 25.5 × 25.5 mm M2 mounting; the Apex-2 seller lists several possible FC patterns. Measure the received frame and AIO before finalizing the stack or center mount. |
| Capture listing versus Hardware's VIXLW BR116 candidate | Identify purchased chipset and actual Linux/V4L2 behavior. |
| PETG and reference hub materials | Check printer capability, fit, stiffness and mass using small test pieces. |
| Epoxy listing ends with a question mark | Keep bonding method provisional until checked. |
| Pack quantity/cost and status | Record actual delivered quantities, receipts and functional checks. |

The BOM's **64 GB microSD** remains its stated baseline. Differing storage/audio tasks in `toImplement` are deferred and have not replaced this plan.

Four OVONIC 450 mAh packs and two OVONIC 1100 mAh packs are user-reported. The 1100 mAh units are outside the source's 450–850 mAh test range and the seller's 650 mAh upper recommendation; they need individual fit, mass, charge-limit and electrical checks before flight.

## Additional-purchase ledger

| Date | Need restoring the core | Item / quantity | Total delivered cost | Reserve used | Remaining contingency | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Not yet recorded | — | — | — | — | $200 before any additional spending | — |

Track tax/shipping within the cap. Order receipts, arrival photos and compatibility checks belong with the [hardware worksheet](13-hardware-arrival.md), not in a claim that ordering alone verifies the build.

[Hardware](05-hardware.md) · [Build and test](10-build-and-test.md) · [Arrival worksheet](13-hardware-arrival.md).


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Google Doc — BOM tab](https://docs.google.com/document/d/1QrmGZfF8AJm1gQhVAsY_8FbZmaZgIQHXRB_zzldYWVA/edit?tab=t.mtfkaop9vhud) — Source snapshot captured 2026-10-07.
- [OVONIC 7.6 V 450 mAh XT30 listing](https://us.ovonicshop.com/products/2-x-ovonic-7-6v-100c-450mah-2s-lipo-battery-long-size-with-xt30-plug-for-2s-tiny-whoop-micro-fpv-drones-quadcopter) — Vendor listing reviewed for stated mass, dimensions, and charge-language ambiguity.
- [OVONIC 2S 1100 mAh 60C XT30 two-pack listing](https://us.ovonicshop.com/products/2-ovonic-rebel-2-0-60c-2s-1100mah-lipo-battery-lihv-7-6v-pack-with-xt30-plug-for-size-100mm-to-140mm-brushless-drones-long-range-drone-fpv) — Title and description identify the pack, but configuration/dimension fields conflict; confirm details from delivered labels and measurements.
- [Apex-2 frame listing](https://speedyfpv.com/products/apex-2-2-inch-95mm-carbon-fiber-drone-frame-kit?variant=46334350164182) — Seller recommendation and mounting description; verify delivered frame.
- [HGLRC Specter AIO](https://www.hglrc.com/products/hglrc-specter-10a-1-2s-elrs-aio-vtx-400mw-f411-flight-control-10a-bl_s-5-in-1-fc) — Manufacturer AIO specifications.
- [Gemfan 2015-2](https://www.gemfanhobby.com/2015-pc-2-blade.html) — Manufacturer prop diameter and shaft/hub variants.
