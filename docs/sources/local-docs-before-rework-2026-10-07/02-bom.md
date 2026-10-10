# BOM — bill of materials

Source: Google Doc **BOM** tab, read 2026-10-04. [Preserved tab text](../google-doc-2026-10-04/02-bom.md). Current user decisions are recorded in [decisions.md](decisions.md).

Component choices, prices, stock, shipping, and physical compatibility are provisional until checked. The dated source tab preserves the full purchasing list and vendor links.

## Aircraft candidates

| Item | Source direction | Still needs confirmation |
| --- | --- | --- |
| Frame | 85 mm micro quad; Meteor85 named, FlyLens 85 listed as an alternative | Exact purchased frame and dimensions |
| Electronics | F411 AIO with FC, ESC, ELRS, and analog VTX preferred | Exact board, voltage support, mounting, and interfaces |
| Motors | Four 1103 11000KV class brushless motors | Board, prop, battery, and frame compatibility |
| Propellers | 2-inch; Gemfan 2015/2020 candidates | Shaft size, motor fit, measured thrust and efficiency |
| Battery | 2S LiHV XT30; test roughly 450–850 mAh | Pack size/mass, charger, fit, and endurance |
| Camera | 14 × 14 mm analog camera | Purchased camera, mounting, and field of view |
| VTX | Integrated preferred; separate only if needed | Antenna, power, connections, and reliable video |

Ground equipment: ELRS transmitter, UVC-compatible USB 5.8 GHz FPV receiver, Pi 5 processing host and Mac development/simulation machine, provisional RP2040/Pico command bridge, and the exact compatible trainer/serial interface.

Include a compatible charger, batteries, spare props, rods, hubs, connectors, and fasteners in the purchase plan. The source targets arrival by October 7; checkout delivery dates remain unverified here.

## Cage and ground equipment candidates

| Item | Source direction |
| --- | --- |
| Cage rods | 30 straight 1 mm carbon-fiber/fiberglass rods; 1.5 mm reinforcement only where needed |
| Hubs | 12 five-way TPU 95A printed hubs |
| Mounts and damping | TPU/PETG and silicone mounting elements |
| Gimbal | Removable rings, bearings, pivot pins, and center-mount hardware |
| Ground video | UVC-compatible USB FPV receiver |
| Radio and bridge | ELRS transmitter, RP2040/Arduino, and exact compatible trainer/serial cable |
| Battery support | Compatible LiHV charger; four batteries minimum, five or six preferred |
| Spares | Props, rods, hubs, fasteners, heat-shrink, connectors, tape, and zip ties |

The user's Mac runs the simulation. A Raspberry Pi 5 is selected as the tracking/control/demo-server host. Power supply, cooling, storage and actual devices remain to be confirmed. See [software deployment](04-software.md#demo-deployment).

## Purchasing references

The source BOM tab names vendor pages for a FlyLens 85 frame alternative, F411 AIO, EX1103 motors, Gemfan props, Tattu battery, Caddx camera, optional VTX, and rods. It also records missing charger, bridge, cable, bearings, pivots, mounts, and antenna items. See the [complete source BOM](../google-doc-2026-10-04/02-bom.md) for the supplied links and reported costs.

Vendor availability was reported as checked on October 3. That is historical source information, not a current stock check. Confirm the checkout delivery date and compatibility before ordering.


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Pre-rewrite archive index](README.md) — identifies this file as historical context, not current instruction.
- [Maintained document](../../02-bom.md) — current requirements and status.
- This citation note is external to the preserved pre-rewrite text.
