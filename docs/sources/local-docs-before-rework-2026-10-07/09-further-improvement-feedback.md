# Further Improvement / Feedback

Source: Google Doc **Further Improvement / Feedback** tab, read 2026-10-04. [Preserved tab text](../google-doc-2026-10-04/09-further-improvement-feedback.md). Current user decisions are recorded in [decisions.md](decisions.md).

The full review is preserved in its own [source file](../google-doc-2026-10-04/09-further-improvement-feedback.md). Its ratings, estimated performance, and recommendations are source opinions. The current baseline follows the explicit V1/final rules and later user decisions.

## Current recommendations from the review

1. **Hardware:** prototype the full computer-to-radio control path before committing to cage integration. Keep the fixed-cage fallback, adjustable center mount, low mass, and full prop-clearance checks.
2. **Endurance:** compare real battery/mass/handling combinations, rod thicknesses, hub volume, propellers, final-aircraft tuning, lighting, and VTX power. Use measurements rather than source estimates as acceptance evidence.
3. **Software:** retain pilot ARM/DISARM and physical override, neutral outputs and watchdogs, clamping, and slew limits. V1 is yaw-only; review passages recommending yaw plus pitch are later-stage suggestions.
4. **Inspection upgrades:** add tag identity, snapshots, and mission reports after the colored-target core is reliable.
5. **HUD and evidence:** make state, target lock/loss, commands, and override clear. Log events and retain footage; keep development views separate from the default demo interface.
6. **Simulation:** use it for presentation and fallback. The user has assigned simulation to the Mac and tracking/control and the demo server to Raspberry Pi 5. Minimal real-to-virtual state sync remains P4.
7. **Demo readiness:** rehearse the complete contact/recover/track/override/loss sequence repeatedly; preserve a fallback if flight, the cage, or the control bridge is unavailable.
8. **Execution:** maintain a concise event-day checklist and capture evidence as work proceeds.
9. **Budget priorities:** favor batteries, spares, connectors, mounting hardware, and reliability over new sensors. The review's cost suggestions are not confirmed prices.

## Where the guidance is maintained

Use [Hardware](05-hardware.md), [CAD](03-cad.md), [Software](04-software.md), [Simulation](06-simulation.md), [future](08-future.md), and [build and test](10-build-and-test.md) for the current working requirements. Record new evidence and scope changes in [decisions.md](decisions.md).


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Pre-rewrite archive index](README.md) — identifies this file as historical context, not current instruction.
- [Maintained document](../../09-further-improvement-feedback.md) — current requirements and status.
- This citation note is external to the preserved pre-rewrite text.
