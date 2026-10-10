# Source snapshot — Idea

Source: https://docs.google.com/document/d/1QrmGZfF8AJm1gQhVAsY_8FbZmaZgIQHXRB_zzldYWVA/edit?tab=t.0

Read: 2026-10-07. Tab order: 0; parent: none. 

---

# Ball Drone



The Idea

We are building a small drone inside a lightweight protective cage. Instead of trying to avoid every wall, table, or obstacle, the drone is designed to survive contact and keep going.



What it can do

- Fly normally indoors.

- Bump into walls without breaking its propellers.

- Recover after a hit and keep flying.

- Slide or skim across the floor.

- Use a camera and Raspberry Pi to follow a colored target.



Why is it different:

- Most drones need sensors and software to stay far away from obstacles. 

- Our idea is to make the drone physically tougher, so touching the environment is not automatically a failure. 

- That could make small indoor drones simpler, safer, and more useful in tight spaces.



The hackathon build:

- V1 uses the Apex-2 (~95 mm wheelbase) quad inside the lightest protective cage that can survive repeated low-energy contact. A fixed-cage build is an acceptable P1A fallback; the free-rolling two-ring gimbal is P1B.





The Demo

- Core demo: manual takeoff → deliberate foam/cardboard contact → recover → enable computer assist → yaw-center on a colored target → pilot physical override → re-enable assist → cover the target to show automatic target-loss failsafe → land.



Applications:

- Search & Rescue: Explore damaged or cluttered spaces

- Inspection: Check vents, pipes, and machinery.

- Education: Safer drone demos and robotics experiments.

- Human Interaction: Interactive exhibits, games, and demos.

- Navigation Research: Test contact-based movement strategies.

- Industrial Monitoring: Inspect warehouses and equipment.

- Hard to Reach Areas: Reach small or dangerous spaces



IF WE HAVE EXTRA TIME

Only after the core demo is repeatable: add small pitch-based approach, AprilTag inspection/snapshot, inspection LEDs, telemetry replay, then minimal digital-twin state sync. Do not spend hackathon time on SLAM, wall climbing, toss launch, or two-way audio.









FINAL SUCCESS CRITERIA

- ≥3 min usable caged flight; 4–5 min desired.

- Aim for ≥2:1 static thrust-to-weight; treat <1.5:1 as redesign territory.

- Three complete judge-facing rehearsals in a row.

- Pilot can disable computer control instantly; target loss returns computer commands to neutral.



Drone specs (table below)



## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [Google Doc — Idea tab](https://docs.google.com/document/d/1QrmGZfF8AJm1gQhVAsY_8FbZmaZgIQHXRB_zzldYWVA/edit?tab=t.0) — source revision `ANLCKQnLVBOUgYbF9xiV7-InTsia-NHBAIK6uRHga-e4J5upeOn-tJgL1FVO9wv0_COaZWscwb-pNlIDnIFEctx2nWF87sQFyqftuH4YmVg`, captured 2026-10-07.
- This citation note was appended after the captured text; it is not part of the source tab.
