# future — priorities and later features

Source: Google Doc **future** tab, read 2026-10-04. [Preserved tab text](../google-doc-2026-10-04/08-future.md). Current user decisions are recorded in [decisions.md](decisions.md).

## Scope rule

P0–P2 are the core build. Add P2.5/P3 only after the core passes and three complete rehearsals. P4/P5 must not delay the physical demo.

The table below preserves source priorities and difficulty estimates; they are planning judgments rather than verified implementation effort. Existing simulation source already contains two maps, so the multiple-map row concerns additional work.

## Feature matrix

| Feature | Value | Source difficulty | Source priority |
| --- | --- | --- | --- |
| Battery endurance matrix | Finds the best real Wh/g + handling combination | 1/5 | P0 |
| 4-state RGB indicator | Makes MANUAL / SEARCH / LOCK / FAULT obvious to judges | 1/5 | P2 |
| Forward inspection LEDs | Strengthens the inspection use case in dark spaces | 1/5 | P3 |
| Fixed-cage fallback + removable gimbal | Protects the core demo if gimbal integration fails | 2/5 | P1A |
| Yaw-only visual autonomy | Lowest-risk closed-loop target behavior | 2/5 | P2 |
| Quick-release battery / adjustable center mount | Faster testing and easier CG tuning | 2/5 | P1 |
| CSV telemetry + post-run summary | Provides evidence, debugging, and demo polish | 2/5 | P3 |
| Small pitch-based target approach | Adds forward motion after yaw lock | 3/5 | P2.5 |
| AprilTag/ArUco inspection + auto snapshot | Adds target identity and a useful inspection action | 3/5 | P3 |
| Minimal digital-twin state sync | Mirrors only key mission states in the simulation | 4/5 | P4 |
| Modular payload MCU / sensor port | Enables future mission-specific sensors | 4/5 | P4/P5 |
| Two-way audio | Search-and-rescue communication concept | 4/5 | P5 |
| Blackbox collision analytics | Quantifies contact events for engineering evidence | 3/5 | P4 |
| Autonomous landing | Adds end-of-mission autonomy after core flight is stable | 4/5 | P5 |
| Optical flow / LiDAR / mapping | Adds indoor positioning, ranging, or environment mapping | 5/5 | P5 |
| Wall climbing / toss recovery | High-risk contact-mobility experiments | 5/5 | P5 |
| Multiple simulation maps | Expands presentation breadth after one map is polished | 2/5 | P5 |


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Pre-rewrite archive index](README.md) — identifies this file as historical context, not current instruction.
- [Maintained document](../../08-future.md) — current requirements and status.
- This citation note is external to the preserved pre-rewrite text.
