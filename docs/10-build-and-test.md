# Build sequence, gates and evidence

**CAD update — 2026-10-08:** Both vendor/provisional Fusion designs were regenerated and reviewed. See [the CAD checks and current estimates](../cad/apex2-cage/README.md) and [the geometric review/evidence](../cad/apex2-cage/review-2026-10-08/README.md). P1B frame-slot travel now clears its foam pad; nominal rigid prop checks pass. Local pivot-region reserves are only 0.32–0.36 mm, and the 1100 mAh P1B accounted estimate leaves 9.75 g for unweighed items. Strap/wire routing, battery service access, printed fits, loaded clearance, strength, actual weight and thrust remain pending. The user requested P1B CAD ahead of the fixed-cage gate; that gate still controls physical P1B adoption.

Baseline: [current source and decisions](README.md#authority-and-history), updated 2026-10-07. All physical checks below remain to be evidenced; existing Mac/container tests are separate.

## Work sequence

| Stage | Work | Gate / evidence |
| --- | --- | --- |
| Inventory | Identify ordered Apex-2/Specter/video/radio/ground parts and delivered quantities | Receipts, actual variants, dimensions, masses and compatibility checks |
| P0 aircraft | Configure Betaflight/ELRS and establish bare-quad manual operation | Stable manual flight, verified ARM/DISARM and radio failsafe |
| P0 video | RC832 composite capture to Pi, live HSV detection and display | Live FPV, bounding box, center/error, actual capture/latency measurements |
| P0 bridge | Pi → Freenove ESP32-S3 WROOM → trainer → radio → ELRS → FC | ESP32 firmware/host integration plus electrical/protocol/channel verification, independent takeover, watchdog and signal-loss tests |
| P1A | Fixed cage: CAD reference only, not built (user decision, 2026-10-08) | — |
| P1B | Two-ring gimbal cage with adjustable aircraft/battery mount (the build) | Clearance, mass, camera/airflow, balance, free ring motion and the flight gate below |
| P2 assistance | Bounded yaw centering | Full physical bridge/override/failsafe gates; no sustained oscillation |
| Judge readiness | Assisted route if verified; otherwise accepted manual-contact/live-tracking route | At least three consecutive complete rehearsals of the chosen route; manual fallback always ready |
| P2.5/P3 | Optional pitch, tags/snapshots, lighting and mission reporting | Core works, three clean rehearsals, budget/time remain, freeze has not begun |

The bridge and physical-assistance gates apply to the assisted route; an incomplete bridge does not block cage/manual/live-vision work. Physical yaw assistance is not required for demo success. If its gate fails, explicitly state that computer steering is unavailable and use manual piloting with live vision.

## P1B flight gate

No fixed cage is built (user decision, 2026-10-08), so the gate applies to the gimbal build. All three must pass before demo use:

1. **Ten consecutive low-energy contacts** with no damage or prop strikes.
2. **At least three minutes usable caged flight**.
3. **Repeatable manual recovery** after contact.

There is no fixed-cage fallback. Recommended: fly the first hovers with the rings zip-tied, then free them, and log gyro data while rolling to catch gimbal-lock twitches ([motion physics §2.3](22-motion-physics.md)). The gimbal must preserve full prop clearance, camera view, airflow, battery access and balance through every reachable position. Retest after each geometry change.

## Repeatable contact protocol

Define a recorded protocol before counting the ten consecutive contacts: exact cage revision, battery/aircraft mass, surface material and edge geometry, approach direction, contact point, approach speed or a reproducible displacement/fixture, and permitted pilot recovery actions. If speed/energy is not measured, state that limit and retain enough footage/setup information to repeat the conditions; do not infer impact energy from a simulator.

With props removed, first check representative section stiffness, joint retention and whether intended contact objects can enter an opening and reach the modeled prop envelope. Powered contact acceptance follows the existing successful bare-aircraft/manual checks.

Inspect after every contact for cracks, layer separation, rod migration, loosened hardware, joint slip, permanent deformation and reduced prop separation. These are damage/failure indicators even if the aircraft remains airborne. A prop strike, damage or corrective repair resets the consecutive sequence. Record recovery outcome for each contact and predefine how repeatability will be demonstrated; no recovery-count threshold has yet been selected.

Keep passive protection claims limited to the tested surfaces/edges. The open rod cage is not verified to intercept every narrow object. See [mechanical review](18-mechanical-review.md) and [mass worksheet](17-mechanical-cad-brief.md#measured-mass-budget).

## Physical assistance gate

Confirm exact ESP32-S3/trainer interface and real waveform/channel behavior before output. Demonstrate yaw direction, endpoints, neutral, clamps, slew limiting, source/USB/radio loss, application failure and independent pilot takeover.

Source override acceptance: **20/20 props-off**, then **5/5 airborne**. Target loss returns computer commands to neutral every check. Airborne assisted work follows successful prior electrical, props-off and manual/mechanical checks.

ACKs in the existing scaffold describe accepted internal state; they are not evidence of transmitter output. Record complete camera-to-physical-command latency, jitter and neutral/override response.

## Mass, endurance and contact records

| Measurement | Record |
| --- | --- |
| Mass | Bare quad, pack, cage, gimbal, mounts, wiring and all-up total separately |
| Thrust margin | Measured configuration and method; target ≥2:1, redesign below 1.5:1 |
| Battery matrix | User reports four 2S 450 mAh packs and two 2S 1100 mAh packs; record each pack's label/charge limit, mass/dimensions, handling, start/end voltage, flight time and hover throttle. The frame seller recommends up to 650 mAh; 1100 mAh packs require explicit electrical, fit/CG/thrust review before flight. |
| Endurance | ≥3 min usable caged flight; 4–5 min desired |
| Clearance | Prop envelopes, reachable gimbal poses, flex, wires, camera and airflow |
| Contact | Ten consecutive contacts; surface/energy description, damage, flex, recovery and prop separation |
| Rehearsal | Route, complete sequence, failures/recovery, footage and consecutive-pass count |

Any failure starts a new consecutive-pass sequence. Source ratings or rendered pictures do not replace measured results.

## Contingency and freeze

All planned parts are reported ordered. Additional spending: **$200 hard cap**, with **at least $30** reserved for replacements, failed prints, shipping issues and rework. Optional spending waits until the core works.

Freeze new hardware/features **48 hours before the first judged demo**. Final **24 hours**: reliability, batteries, screenshots/logs/footage and at least three consecutive complete rehearsals. Allow only fixes restoring already-working core functionality.

Pico audio/`toImplement` are deferred. Simulator geometry matching is not required; keep one industrial map stable.

[Arrival worksheet](13-hardware-arrival.md) · [Runbook](12-demo-runbook.md) · [Recorded software status](11-pre-hardware-status.md).


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Google Doc — Idea tab](https://docs.google.com/document/d/1QrmGZfF8AJm1gQhVAsY_8FbZmaZgIQHXRB_zzldYWVA/edit?tab=t.0) — Current high-level goals.
- [Google Doc — Hardware tab](https://docs.google.com/document/d/1QrmGZfF8AJm1gQhVAsY_8FbZmaZgIQHXRB_zzldYWVA/edit?tab=t.y9xlzm2dw43q) — Source hardware assumptions.
- [Hardware arrival worksheet](13-hardware-arrival.md) — Record measured device-specific results.
- [OVONIC 2S 1100 mAh 60C XT30 two-pack listing](https://us.ovonicshop.com/products/2-ovonic-rebel-2-0-60c-2s-1100mah-lipo-battery-lihv-7-6v-pack-with-xt30-plug-for-size-100mm-to-140mm-brushless-drones-long-range-drone-fpv) — Vendor data has internal inconsistencies; verify actual packs before any testing.
