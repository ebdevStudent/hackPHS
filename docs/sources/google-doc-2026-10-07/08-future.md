# Source snapshot — future

Source: https://docs.google.com/document/d/1QrmGZfF8AJm1gQhVAsY_8FbZmaZgIQHXRB_zzldYWVA/edit?tab=t.9zl6mz9qzdr6

Read: 2026-10-07. Tab order: 7; parent: none. 

---

FUTURE FEATURES



Implementation difficulty: 1 = Easy · 2 = Low · 3 = Moderate · 4 = Hard · 5 = Very hard / high integration uncertainty.

Priority guide: P0–P2 = core build · P2.5/P3 = add only after the core is reliable · P4/P5 = future/stretch.



FEATURE MATRIX



| Feature | Value | Difficulty | Priority |
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



BUILD RULE

- Core demo = P0–P2 only.

- Add P2.5/P3 only after the core passes and three clean rehearsals.

- P4/P5 are future work and must not delay the physical demo.







## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Google Doc — future tab](https://docs.google.com/document/d/1QrmGZfF8AJm1gQhVAsY_8FbZmaZgIQHXRB_zzldYWVA/edit?tab=t.9zl6mz9qzdr6) — source revision `ANLCKQnLVBOUgYbF9xiV7-InTsia-NHBAIK6uRHga-e4J5upeOn-tJgL1FVO9wv0_COaZWscwb-pNlIDnIFEctx2nWF87sQFyqftuH4YmVg`, captured 2026-10-07.
- This citation note was appended after the captured text; it is not part of the source tab.
