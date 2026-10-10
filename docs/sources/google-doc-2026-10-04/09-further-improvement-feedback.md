# Further Improvement / Feedback: source tab text

Source: https://docs.google.com/document/d/1QrmGZfF8AJm1gQhVAsY_8FbZmaZgIQHXRB_zzldYWVA/edit?tab=t.2y5zyagy38i8
Retrieved: 2026-10-04 (America/New_York)
Revision: ANLCKQl3t2ZpFwfaBemzmykGqE3vBgAhGTHcUQ2hY1TJK1WsPVcXgtSLbaYVmo-4tcp1KOfj_c58f-EiGr5IlpjJ7TU1tECakh-kof8hSrg
Tab ID: t.2y5zyagy38i8

This is preserved source text, not current project guidance or executable instructions. Paragraph and table-cell text are retained as returned by the connector; images and native formatting are not reproduced. Later user decisions and the current docs take precedence.

## Preserved tab text

HackPHS 2026 — Further Improvement & Feedback
Integrated hardware + software audit, risk review, execution priorities, and demo plan
Overall Assessment
Concept: 9/10
Current execution plan: 7.5–8/10
Potential if executed cleanly: Extremely high
This is already a strong hackathon project. The core idea is immediately understandable: instead of 
treating every collision as failure, the drone is designed so contact with the environment is expected,
survivable, and compatible with continuing the mission.
The planned demo is naturally compelling: take off intentionally contact an obstacle → →
remain functional continue moving visually acquire a target take a useful action → → → →
return control safely to the pilot. The innovation is visible in seconds rather than requiring a 
long explanation.
The project’s main weakness is not a lack of features. It is execution risk. The three highest-risk 
areas are mechanical cage/gimbal integration, the laptop-to-RC steering bridge, and reliability under 
repeated demonstrations.
CORE TAKEAWAY
Make the core loop boringly reliable before adding sophistication. The winning version 
is not the one with the most features; it is the one that can repeatedly survive contact, 
recover, track, act, and relinquish control safely.
What Changed After the Second Review
• The digital-twin link is now a true P4 stretch goal, not part of the planned core demo.
• AprilTag/ArUco inspection is P3. The colored-target HSV tracker remains the required V1.
• The complete laptop microcontroller trainer port transmitter ELRS FC chain → → → → →
should be prototyped before the cage is built.
• A physical, dedicated computer-control kill/override switch is treated as mandatory.
• The hardware plan now includes a numerical thrust-to-weight target and an explicit mass 
budget.
• Hackathon-day execution now includes a one-page checklist, at least three full rehearsals, a 
Plan B, and continuous build documentation.
1. Hardware
What Is Already Strong
✓ The BOM is unusually mature for a hackathon: aircraft frame, FC/ESC, motors, props, 
battery, camera, VTX, cage materials, ground station, and backups are already identified.
✓ The general build logic is sound: establish a known-good bare quad, then add the 
cage/gimbal and retest.
✓ The safety philosophy is correct: the pilot keeps ARM/DISARM and emergency authority 
while autonomous commands stay limited.
✓ The electronics architecture is sensible. The highest uncertainty is the mechanical 
structure surrounding the quad, not ordinary Betaflight flight.
Primary Hardware Risk: The Cage Is the Real Engineering Project
The critical questions are: Is the cage light enough? Is it rigid enough? Does the gimbal rotate 
freely? Is the quad’s center of mass close to the gimbal-axis intersection? Can any cage or ring 
geometry enter a propeller disk? Can the aircraft still recover aggressively enough after contact?
1. Cage Geometry
The current BOM of 12 five-way hubs and 30 rods maps neatly to an icosahedral cage. For a 
hackathon, this simplification is attractive because it is dramatically easier to manufacture, repair, 
and carry spares for than a more complicated soccer-ball-like shell.
The tradeoff is that an icosahedron will transition over edges and vertices rather than roll like a 
perfect sphere. That is acceptable. Favor buildability and reliability over geometric perfection. 
Rounded/flexible TPU hub exteriors can soften those transitions.
2. Keep Thicker Rod Stock Available
A ~220–230 mm cage made entirely from 1 mm rods may be too flexible under impact. Buy some 
1.5 mm carbon rod as backup even if the first prototype uses 1 mm.
• 1.0 mm everywhere — lowest mass.
• 1.5 mm everywhere — much greater rigidity.
• Mixed 1.0/1.5 mm — reinforce only high-load members if that gives the best tradeoff.
A modest increase in rod diameter can produce a large stiffness improvement for a relatively small 
mass penalty. This is cheap mechanical insurance.
3. Make the Center Mount Adjustable
Give the quad mount several millimeters of X/Y adjustment, and ideally allow the battery position to 
shift as well.
If the aircraft center of gravity is displaced from the intersection of the gimbal axes, gravity 
continuously torques the inner aircraft and the mechanism starts behaving like a pendulum instead 
of a freely rotating protective shell. A slotted or adjustable mount lets you correct real-world balance 
errors after assembly.
4. Verify Prop Clearance Through the Entire Gimbal Range
Do not only verify that the props clear the cage while everything is centered. Verify that no propeller 
can contact a cage member, ring, pivot, wire, or mount in any physically reachable gimbal 
orientation.
Test the full mechanical envelope with the props removed before powered testing. In CAD, 
deliberately rotate the inner assembly to its limits and inspect every propeller disk.
5. Establish a Mass and Thrust-to-Weight Budget Before Building the Cage
Do not treat weight as a vague concern. Weigh the bare quad with battery first, estimate the 
cage/gimbal/mount mass, and maintain a running all-up-weight budget as parts are added.
Planning target: aim for at least ~2:1 static thrust-to-weight with the complete cage 
installed. If the finished system falls much below ~1.5:1, expect noticeably weaker 
acceleration and recovery authority, especially after impacts.
Use those values as practical design targets rather than absolute guarantees: real performance also 
depends on the actual propeller, battery sag, airflow obstruction from the cage, tune, and motor/ESC
limits. The important point is to measure rather than guess.
• Record bare-quad mass with battery.
• Estimate cage + hubs + rings + bearings + mount + wiring.
• Weigh the cage immediately after the first prototype is assembled.
• Compare estimated/bench static thrust to full all-up weight.
• If the margin is poor, remove cage mass before adding more electronics.
6. Complete the BOM Before the Hackathon
The detailed hardware plan mentions several parts that are easy to overlook in the main BOM. Make
sure the team physically possesses the complete supporting system before build day.
• Gimbal rings and ring material.
• Bearings and pivot hardware.
• Center-mount hardware and fasteners.
• RP2040/Arduino and the exact required trainer/serial cabling.
• VTX antenna if not bundled.
• Compatible battery charger.
• Spare props, rods, printed hubs, connectors, heat-shrink, zip ties, tape, and small fasteners.
7. Batteries Are Mission-Critical
One 450 mAh battery will bottleneck the entire project. Treat four batteries as a practical minimum; 
five or six is better if budget and charging setup permit.
If the budget gets tight, cut a lower-value accessory before cutting batteries. More flight 
packs directly buy testing time, tuning time, repeated rehearsals, and a safer demo 
margin.
8. Camera Placement Must Account for the Moving Cage
The cage and gimbal move relative to the camera. A camera can technically point outward while still 
having rods or a ring repeatedly sweep through the image.
Design around an approximate camera field-of-view cone, not just the camera centerline. Protect the
central region used by the tracker, and avoid printing cage components in the same color as the 
tracking target.
9. Use the Simplest Viable Airborne Electronics Stack
If an AIO board already integrates FC, ESC, ELRS, and analog VTX, do not add a redundant 
standalone VTX. Every unnecessary board, wire, connector, and antenna is extra mass and another 
failure point.
Cheap Hardware Additions With High Demo Value
• Multiple batteries — highest-value reliability purchase.
• 1.5 mm backup rod stock — cheap insurance if the first cage is too flexible.
• RGB / WS2812 status LEDs — make MANUAL, AUTO, TARGET LOCK, and TARGET LOST 
visible from across the room.
• Small buzzer — useful for crash recovery, low-battery warnings, and debugging.
• FPV DVR — useful for replay, debugging, submission footage, and demo highlights.
• Betaflight OSD / voltage telemetry — makes battery state visible to the pilot and can be shown 
on the laptop feed.
• Replaceable TPU bumpers/skids — protect high-contact areas and make the cage look 
intentionally engineered for impact.
• Quick-access battery opening / quick-release center mount — saves time during repeated 
testing.
• Spare-parts kit — props, rods, hubs, tape, heat-shrink, zip ties, thread locker, connectors, and 
fasteners.
Forward Inspection Lights
Add one or two tiny forward-facing white LEDs near the FPV camera as a low-cost 
inspection feature. They would improve visibility inside dim rooms, vents, machinery, 
debris, or other confined spaces and make the industrial-inspection / search-and-rescue 
use case much more believable.
Keep the lights lightweight and modest in power so they do not meaningfully reduce 
flight time or add heat. Ideally make them transmitter- or software-switchable rather than 
permanently on, and position them so the cage does not cast distracting shadows 
directly across the camera view.
Optional Two-Way Audio: Onboard Microphone + Speaker
Add a tiny onboard microphone and speaker as a P3 stretch feature, especially for 
search-and-rescue or remote inspection. The microphone would let the operator hear 
what is near the drone, while the speaker could play prompts, alerts, or let the operator 
speak to someone near the vehicle.
Keep this lightweight and non-core. Propeller/motor noise will make microphone audio 
challenging, so use physical isolation and simple filtering if needed. Use a very small 
amplified speaker, and verify the actual audio transport path rather than assuming the 
existing analog FPV/VTX setup carries audio. If necessary, handle audio through a 
separate lightweight link or microcontroller/audio module.
Do not let two-way audio delay flight, RC-bridge, cage, tracker, or failsafe work. It is 
valuable because it strengthens the search-and-rescue story, but it should only be added
once the core system is stable.
Recommended Status-Light Language
• Blue — MANUAL.
• Green — AUTO / target locked.
• Red — target lost / failsafe / autonomy disengaged.
This has disproportionate demo value because a judge can understand state transitions without 
staring at the laptop.
Modular Sensor / Payload Port (I²C)
A modular sensor port is a good idea, but do not think of the design in 
terms of every motor or camera wire consuming general-purpose 
microcontroller pins. The four brushless motors are driven through the 
integrated ESC, and the analog camera mainly needs power, ground, and 
one video signal. The real issue is whether the flight controller exposes 
convenient buses for general-purpose sensors.
The current F411 AIO is primarily a flight controller, not a generic sensor 
computer. Its documented pads are well suited to flight, ELRS, video, 
LEDs/buzzer, and UART devices, but it does not expose a convenient 
dedicated I²C header. Avoid making the hackathon depend on obscure 
F411 pin remapping.
Recommended Physical Port
Design a tiny standardized payload connector into the airframe now, even if
only one or two payloads are used during the hackathon.
• GND
• +5 V
• SDA
• SCL
• Optional fifth pin: configurable GPIO / interrupt / UART line
A keyed 4- or 5-pin connector plus a small standardized mounting pattern 
makes the vehicle genuinely extensible without committing to a heavy 
payload stack.
I²C Daisy-Chaining vs. Expansion Boards
Multiple I²C sensors normally share the same SDA and SCL lines as long as
they have unique addresses. Do not add an I²C multiplexer merely because 
there are several sensors.
• Direct I²C daisy-chain — preferred when sensor addresses do not 
conflict.
• I²C multiplexer — only if two devices have the same fixed address or 
buses genuinely need isolation.
• GPIO expander — useful only if more ordinary digital inputs/outputs are
actually needed; it does not replace an I²C master.
For this aircraft, a full breakout-board/multiplexer stack is probably more 
annoying than useful. The silicon is light; the real weight comes from large 
breakout PCBs, connectors, cables, and mounting hardware.
Best Long-Term Architecture: Tiny Dedicated Payload MCU
If modular sensing becomes a real feature, keep flight and payload 
responsibilities separate:
FLIGHT SYSTEM: F411 / Betaflight motors, ELRS, stabilization, →
FPV, failsafes
PAYLOAD SYSTEM: tiny MCU I²C sensors, lights, →
microphone/speaker support, mission-specific payload logic
A small payload MCU can act as the I²C master and talk to multiple sensors
without forcing Betaflight to become the sensor host. Keep wires short and
use one compact board rather than stacking commercial modules.
The harder question is not sensor pin count—it is how payload data gets 
back to the laptop. Solve that only when a specific sensor actually needs 
live telemetry; do not build a large custom telemetry path prematurely.
Payload-Port Design Rule
Build the connector and mounting provision cheaply now; add the 
sensor-controller electronics only when the mission requires them.
This lets you describe the drone as a mission-configurable platform while 
keeping the hackathon aircraft light. Future payloads could include a small 
ToF rangefinder, temperature/environmental sensing, microphone/speaker,
or other low-mass modules.
Flight-Time / Endurance Optimization
For the finished caged aircraft, plan around roughly 4–5 minutes of real 
usable flight at first. A reliable ~5-minute result is a good design target, and
~6 minutes is a plausible optimization goal if the cage stays light and the 
battery/prop combination is chosen well. Do not design the judging demo 
around using the entire pack; the airborne sequence should ideally take 
only about 60–120 seconds.
1. Treat Mass as the Biggest Endurance Lever
Every gram added to the cage, gimbal, wiring, sensor boards, connectors, 
lights, speaker, or mounts increases the thrust required just to hover. Keep
a live mass budget and remove unnecessary structure before chasing 
electronic efficiency.
• Use minimal/hollow TPU hubs rather than chunky printed nodes.
• Use the lightest gimbal-ring design that remains adequately stiff.
• Prefer carbon where it gives better stiffness per gram.
• Keep wires short and connectors small.
• Avoid redundant PCBs and large breakout boards.
• Individually justify every accessory by grams as well as dollars.
A 5 g reduction is meaningful on an aircraft in this size class; a 15–20 g 
reduction can completely change endurance and recovery authority.
2. Do Not Assume 450 mAh Is the Best Battery
Test a few high-energy-density 2S packs rather than locking the design to 
450 mAh. A well-chosen 550 mAh or ~650–680 mAh pack can provide 
substantially more stored energy for only a modest mass increase.
Select batteries by energy per gram (Wh/g), not capacity label or extreme 
C-rating alone. You still need adequate discharge capability for impact 
recovery, but this is an inspection drone, not a racing quad.
A practical test set is:
• 450 mAh 2S — baseline.
• ~550 mAh 2S — likely strong middle-ground candidate.
• ~650–680 mAh 2S — test whether the added energy outweighs the extra 
mass.
As an illustration, moving from 450 mAh to 680 mAh increases nominal 
stored energy by about 51%. If the larger pack adds only a few grams to a 
~100 g aircraft, hover-power demand may rise far less than battery energy, 
so endurance can increase substantially. Measure the actual finished 
aircraft rather than assuming the biggest pack wins.
3. Protect Propeller Airflow
The cage should not obstruct propeller inflow/outflow any more than 
necessary. Rods, hubs, gimbal rings, and mounts placed immediately 
above or below the prop disks can force the motors to use more power for 
the same lift.
• Keep the prop disks visually and aerodynamically clear.
• Avoid placing a gimbal ring directly through the strongest prop wash if 
geometry allows.
• Check for wiring or camera mounts protruding into the prop wash.
Cleaner airflow improves both endurance and control quality.
4. Test Propellers for Efficiency, Not Maximum Aggression
The mission values efficient hover and moderate maneuvering more than 
extreme acceleration. Test a few compatible 2-inch prop options—
especially light, moderate/low-pitch two-blade designs—and compare real 
energy use.
Do not change the motors preemptively. The current 1103 11000KV class is
reasonable for the project; first optimize mass, battery, propeller choice, 
and tune.
5. Tune the Finished Caged Aircraft for Smoothness
The cage and gimbal can introduce vibration and mechanical resonance. A 
tune that feels fine on the bare quad may waste power or oscillate after the 
cage is installed.
• Check for visible high-frequency oscillation.
• Revisit filtering / tune after the cage goes on.
• Favor stable, smooth indoor flight over an ultra-responsive racing feel.
A calm aircraft helps endurance and also makes the OpenCV tracker much 
easier to use.
6. Reduce Non-Propulsion Power Waste
• Run the VTX at the minimum power that is reliable indoors.
• Make inspection lights switchable rather than permanently on.
• Keep status LEDs at sensible brightness.
• Keep the speaker off except when needed.
• Poll sensors only as fast as the mission requires.
These loads are much smaller than motor power, but the principle is to 
avoid wasting energy—especially once lights/audio/payload electronics are
added.
7. Keep Inspection Lighting Efficient
Use small efficient white LEDs rather than several watts of lighting. The 
analog FPV camera does not need a floodlight for short-range inspection. 
Switch the lights on only when entering a dark inspection area, then turn 
them back off.
8. Avoid Turning Sensor Modularity Into a Weight Problem
A sensor IC may weigh almost nothing, but MCU boards, Qwiic-style 
cables, mux boards, JST connectors, headers, and mounting plates add up 
quickly. Prefer one tiny payload MCU, directly attached sensors, short 
wiring, and no multiplexer unless an address conflict makes one 
necessary.
9. Measure Endurance Instead of Guessing
Once the aircraft flies, run a controlled endurance matrix. Five short 
controlled tests will tell you more than hours of estimation.
• Test A — 450 mAh + current props.
• Test B — ~550 mAh + current props.
• Test C — ~650–680 mAh + current props.
• Test D — best battery + alternate efficiency-oriented prop.
• Test E — same setup with inspection lights OFF vs. ON.
For each run, keep the flight profile and voltage cutoff consistent, and 
record all-up mass, flight time, starting/ending voltage, hover throttle, and
—if practical—mAh returned on recharge.
Likely Optimized Direction
1103 11000KV motors + efficient 2-inch props + high-energy-density 2S 
~550–680 mAh pack + very light carbon cage + minimal TPU + low VTX 
power + switchable inspection lights + minimal payload electronics + 
smooth conservative tune
Design around ~5 minutes reliably and treat ~6 minutes as a realistic 
optimization target rather than a requirement. Going substantially beyond 
that would likely require a more fundamental propulsion/airframe redesign.
Revised Hardware / Integration Order
Important change: prototype the entire RC-control chain before investing substantial 
time in the cage. If computer steering cannot reach the FC safely and predictably, the 
autonomous portion of the demo is blocked regardless of how good the cage is.
1. Configure the bare quad and verify stable manual flight.
2. Prototype laptop microcontroller trainer port transmitter ELRS FC with → → → → →
props removed.
3. Verify the dedicated physical computer-control kill/override switch repeatedly.
4. Weigh the bare quad with battery and establish the mass/thrust budget.
5. Test the cage structurally before mounting the quad.
6. Test gimbal freedom and friction with no props.
7. Balance the center of mass using the adjustable mount.
8. Verify the full prop-clearance envelope.
9. Add camera/VTX and verify that the moving cage does not ruin the central video view.
10. Begin with low-power contact tests against a portable foam-board/cardboard obstacle.
11. Only then attempt repeated full demonstration runs.
2. Software
What Is Already Strong
The fundamental software architecture is correct. Betaflight retains responsibility for stabilization, 
motor output, and flight behavior. The laptop performs high-level vision and sends only small 
steering corrections. The pilot retains ARM/DISARM and emergency takeover.
That separation is exactly what you want: do not turn a hackathon vision feature into a custom flight￾controller project.
Primary Software Risk: Laptop RC Control Path →
The highest-risk software/integration path is laptop serial RP2040/Arduino transmitter → → →
trainer input ELRS Betaflight. OpenCV color detection is comparatively easy; trainer → →
protocols, transmitter configuration, mixing, electrical interface, update rate, failsafe 
behavior, and latency can consume hours.
Prototype this chain before building the cage. Do it with props removed, then verify that 
the physical override works every single time.
Safety Architecture for the RC Bridge
• The physical transmitter remains master.
• ARM/DISARM never comes from the laptop.
• Use a dedicated, obvious physical switch on the transmitter to enable/disable computer 
assistance.
• The microcontroller outputs neutral when it has no valid command.
• Add a watchdog: if serial updates stop, commands immediately return to neutral.
• Pilot input must be able to remove computer authority instantly.
• Test the kill/override path repeatedly, not just once.
Fallback if the RC Bridge Is Not Ready
Do not let one integration failure kill the entire software story. Keep a deliberate fallback path.
• Best fallback: yaw-only autonomous centering if pitch/forward control is unstable.
• Lower-risk fallback: run the full vision/HUD pipeline while the pilot manually steers toward the 
target.
• The system can still demonstrate target detection, tracking error, command suggestions, target￾loss logic, and manual takeover even if closed-loop steering is not demo-safe.
Use Yaw + Pitch for V1 Autonomous Steering
For a forward-facing camera, define computer steering explicitly as yaw + pitch rather than vague 
left/right + forward/back.
• Horizontal image error yaw correction. →
• Target too small / too far away small forward pitch correction. →
• Desired apparent target size reached stop forward correction. →
Leave roll and throttle manual. If pitch-based following causes too much altitude drift or instability, 
fall back to yaw-only target centering rather than giving the laptop throttle control.
Make the Colored-Target Tracker Robust, Not Fancy
The colored-target HSV tracker is the required V1. Do not skip it in favor of AprilTags or neural￾network detection. It is the simplest path to a working closed loop and gives you a reliable baseline 
before adding semantics.
Recommended pipeline:
1. FPV frame.
2. Convert to HSV.
3. Threshold the target color.
4. Morphological open/close to suppress noise.
5. Reject blobs outside a minimum/maximum area.
6. Choose the largest valid contour.
7. Calculate target-center error.
8. Low-pass / smooth the error.
9. Apply a center deadband.
10. Convert error into yaw/pitch command.
11. Clamp command magnitude.
12. Apply slew/rate limiting before sending the command.
Target Lock and Loss Logic
Do not enter AUTO based on one successful frame. Require several consecutive valid detections 
before declaring TARGET LOCK. Likewise, use a short loss debounce/timeout so individual bad 
frames do not cause flicker, but cancel autonomy quickly if the target is genuinely lost.
The system should feel deliberate: SEARCHING TARGET LOCK AUTO ALIGN TARGET → → →
LOST MANUAL. →
Latency and Jitter
The loop includes analog video transmission, USB capture, OpenCV processing, serial 
communication, the microcontroller, the transmitter, ELRS, and Betaflight. Expect latency. Keep 
gains conservative, smooth errors, clamp outputs, and use rate limits. A slightly slow drone that 
turns smoothly toward a target will look much better than a fast controller that oscillates.
3. P3 Software Upgrade: AprilTag / ArUco Inspection 
Targets
Do this only after the HSV colored-target V1 is smooth and reliable.
AprilTag/ArUco is an excellent next step because it adds target identity and known geometry. It also 
adds another library, calibration/pose-estimation work, and another failure mode, so it belongs at P3 
rather than in the core.
• Tag 01 — machine / valve / inspection point A.
• Tag 02 — inspection point B.
• Tag 03 — inspection point C.
Once stable, this turns the same controller from “follow a colored object” into a more believable 
inspection workflow: identify a tagged asset, align, capture an image, record the ID/time, and mark 
the inspection point complete.
Example P3 Inspection Workflow
1. Camera detects Tag 02.
2. HUD displays INSPECTION POINT 02.
3. Drone performs small yaw/pitch corrections.
4. Once centered and sufficiently close, capture an FPV still.
5. Save the tag ID and timestamp.
6. Mark the inspection point complete.
7. Mission progress changes from 2/3 3/3. →
4. Judge-Facing HUD and Telemetry
A lot of the project’s cleverness is invisible unless the laptop explains it. The FPV interface should be
judge-facing, not developer-facing: clean, high-contrast, large enough to read from several feet 
away, and focused on the state of the robot rather than raw debugging noise.
HUD Elements Worth Showing
• Large MANUAL / AUTO state.
• SEARCHING / TARGET LOCK / TARGET LOST.
• Bounding box / marker outline and target crosshair.
• Horizontal error.
• Pitch/yaw command.
• Safety clamp / override indicator.
• Battery / voltage if available.
• Target count / mission progress.
• FPS only if it does not clutter the interface.
If a developer view with masks/thresholds is useful for tuning, keep it as a separate toggle. The 
default demo view should tell the software story in two or three seconds.
Telemetry and Replay
Log the run even if the format is only CSV. Useful fields include timestamps, mode changes, 
detections, target IDs, image errors, steering commands, target loss, override events, and 
collision/contact events if available.
A compact post-run summary can be effective:
MISSION COMPLETE — 3 targets inspected • 2 physical contacts • target-lock history 
recorded • 1 pilot takeover
5. Simulation
Keep It as a Strong Parallel Deliverable / Plan B
The simulation is valuable because it communicates the use case and gives you a presentable 
fallback if the physical drone has problems. But it must not become the main engineering project or 
consume time needed to make the real system reliable.
Build one polished industrial environment first. Do not build the rescue map until the core physical 
demo and first simulation environment are already working.
P4 Only: Digital-Twin Synchronization
The real-drone simulation WebSocket link is genuinely impressive, but it is P4. ↔
Only attempt it after the physical drone, RC bridge, colored-target tracker, HUD, 
failsafe, and presentation are working and polished.
A state-sync link can easily consume half a day for very little benefit if anything underneath it is still 
fragile. Do not let it displace higher-value testing or rehearsal.
If you reach P4, keep the integration tiny:
• Physical target captured virtual inspection point turns green. →
• Real MANUAL/AUTO state mirrored in the simulation. →
• Real mission complete simulation displays MISSION COMPLETE. →
That is enough to create a digital-twin story. Do not build a large telemetry architecture just to say 
the systems are connected.
Useful Simulation Polish
• Rich HUD with battery, timer, mode, targets, score, contacts, and override state.
• FPV/chase-camera toggle.
• Mini-map only if it is quick to implement.
• Failsafe-demo key that simulates target loss and shows autonomy cancellation.
• Virtual target detection if useful for a fallback presentation.
• Replay / telemetry playback only after the core build is complete.
Features to De-Prioritize
• Full SLAM or obstacle mapping.
• LiDAR altitude-hold integration.
• Optical-flow navigation unless it is already working.
• Neural-network object detection before the basic tracker is polished.
• Autonomous wall climbing.
• Autonomous toss launch.
• Randomized targets and multiple maps.
• Elaborate particles, sound design, or visual effects before functionality is complete.
• A large FastAPI backend built only to make the architecture look complicated.
6. Recommended Final Demo
Core Demo — Must Be Possible Without AprilTags or a Digital Twin
Step 1 — Launch
Pilot takes off manually. Laptop clearly displays MANUAL. Physical status LEDs are blue.
Step 2 — Deliberate Contact
Pilot intentionally contacts a prepared foam/cardboard obstacle. The cage absorbs/redirects the 
interaction and the drone remains functional.
Step 3 — Recover
Drone returns to normal flight. This is the core mechanical proof: the audience just watched contact 
that did not end the mission.
Step 4 — Enable Computer Assistance
Pilot flips the dedicated computer-control switch. Laptop changes to AUTO — SEARCHING. LEDs 
change state.
Step 5 — Colored Target Lock
The HSV tracker detects the high-contrast target. HUD shows the target box/crosshair, state, and 
error.
Step 6 — Autonomous Alignment
The drone performs small yaw corrections—and pitch only if that portion is stable—while the HUD 
shows the error decreasing.
Step 7 — Demonstrate the Failsafe
Remove or cover the target. HUD changes to TARGET LOST. Computer commands immediately 
neutralize and the pilot has full control.
Step 8 — Demonstrate the Physical Override
Independently flip the dedicated transmitter switch to disable computer control. This visibly proves 
that the pilot can revoke autonomy at any moment.
Step 9 — Finish With Evidence
Show a clean mission/telemetry summary or recorded FPV clip. The core story is: survive 
contact continue mission track act fail safely. → → → →
P3 Upgraded Demo
If AprilTags are working, replace the colored-target step with an identified inspection point, 
automatically capture the target image, and increment mission progress. This is an upgrade to the 
core demo—not a dependency.
P4 Upgraded Demo
If digital-twin synchronization is working, mirror only the key mission state in the simulation. Treat it 
as the final flourish, not as required infrastructure.
7. Development Priority
P0 — Must Work / De-Risk First
• Bare quad flies reliably.
• Laptop microcontroller trainer transmitter ELRS FC chain works with props → → → → →
removed.
• Dedicated physical computer-control kill/override switch works every time.
• Batteries/charging/spares do not bottleneck testing.
• Pilot ARM/DISARM authority is unquestionable.
• Bare mass is measured and full-system mass/thrust budget is acceptable.
P1 — Core Mechanical Product
• Cage survives repeated low-energy impacts.
• Gimbal moves freely.
• Center of mass is balanced.
• Prop clearance is guaranteed.
• FPV is stable and usable.
P2 — Core Autonomous Demo
• Colored HSV target tracking works smoothly.
• Yaw/pitch commands are conservative and stable; yaw-only is an acceptable fallback.
• Target-loss behavior returns control safely.
• HUD is clean, judge-facing, and readable from several feet away.
• Status LEDs mirror system state.
• Full demo has been rehearsed end-to-end.
P3 — High-Value Upgrade
• AprilTag/ArUco inspection mission.
• Automatic inspection snapshot/report.
• Telemetry logging / replay if useful.
P4 — Only After Core Is Working and Polished
• Real drone simulation state synchronization / digital twin. ↔
• Additional simulation integration.
• Blackbox collision analytics.
P5 — Probably Do Not Touch During the Hackathon
• Full SLAM / mapping.
• LiDAR or optical-flow autonomy unless already operational.
• Neural-network object detection.
• Wall climbing / toss launch.
• Multiple polished simulation maps.
8. Hackathon-Day Execution
One-Page Table Checklist
The full planning document is useful before the event; on hackathon day, use a one-page 
operational checklist taped to the table. It should be glanceable in under a minute.
□ Bare quad flies.
□ All batteries charged / charging plan ready.
□ RC bridge passes props-off test.
□ Physical computer-control kill switch verified.
□ Cage secure; no cracked hubs/rods.
□ Gimbal moves freely and CG is acceptable.
□ Full prop clearance rechecked.
□ FPV feed stable.
□ HSV tracker locks target.
□ Target-loss timeout returns to manual.
□ HUD readable from judging distance.
□ Spare props/rods/hubs/tools accessible.
□ Demo obstacle/target ready.
□ Demo sequence rehearsed.
□ Backup simulation opens and runs.
□ Latest build photos/video saved.
Rehearse the Full Demo at Least Three Times
Component tests are not enough. Run the exact judge-facing sequence at least three times end-to￾end, including deliberate contact, target acquisition, autonomy, target loss, physical override, 
recovery, and the final presentation screen.
A feature should not be added to the live judging sequence until the team can perform the entire 
sequence repeatedly without babysitting it.
Plan B
The physical drone should remain the main project, but the presentation must survive a last-minute 
hardware failure.
• If the cage breaks: show recorded physical contact footage + working bare-quad/vision demo + 
simulation.
• If the RC bridge fails: show live vision/HUD with manual steering and explain the closed-loop 
control path honestly.
• If flight is not permitted or safe: use recorded flight/contact footage and run the 
software/simulation live.
• Keep the simulation polished enough to explain the application, but do not divert core build time 
into making it the primary project.
Document as You Go
Take photos, short videos, screenshots, and concise notes during the build—not only at the end. 
Capture the bare quad, cage assembly, gimbal tests, first contact tests, tracker/HUD, and successful
rehearsals.
Good process documentation gives you strong submission material and lets you show evidence of 
working intermediate milestones even if the final live demo has a hiccup.
9. Where to Spend Extra Money
If approximately another $100 is available, spend it on reliability rather than flashy sensors:
• ~$40–50 — additional batteries.
• ~$10–20 — spare mechanical components / props / hubs / bearings.
• ~$10 — alternate rod thicknesses.
• ~$5 — status LEDs.
• ~$5 — buzzer.
• Remaining budget — connectors, cabling, fasteners, tape, heat-shrink, charger needs, or 
unforeseen replacements.
Final Judgment
The project does not need another giant feature. Its strongest idea is the conceptual inversion: 
instead of spending all engineering effort preventing contact, design the robot so contact does not 
end the mission.
The difference between an okay version and an excellent version is not 6 features versus 14 
features. It is whether the following sequence works cleanly and repeatedly:
CONTACT / COLLISION RECOVER TRACK TAKE A USEFUL ACTION → → → →
GRACEFULLY RELINQUISH CONTROL REPEAT →
If that sequence becomes boringly reliable, this is an exceptionally strong hackathon project. 
Prototype the RC bridge first, protect the weight/thrust margin, buy enough batteries, keep HSV as 
the V1, make the override physical and obvious, rehearse the complete demo, and treat AprilTags 
and the digital twin as upgrades rather than dependencies.


## Sources and verification references — 2026-10-07

<!-- audit-source-footer -->
- [HackPHS 2026 Google Doc](https://docs.google.com/document/d/1QrmGZfF8AJm1gQhVAsY_8FbZmaZgIQHXRB_zzldYWVA/edit) — historical captured revision `ANLCKQl3t2ZpFwfaBemzmykGqE3vBgAhGTHcUQ2hY1TJK1WsPVcXgtSLbaYVmo-4tcp1KOfj_c58f-EiGr5IlpjJ7TU1tECakh-kof8hSrg` (2026-10-04).
- This citation note was appended after the historical text; consult the maintained docs for current decisions.
