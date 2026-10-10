# 22 — Motion physics and throttle estimates

**Status (2026-10-08): calculated estimates, not measurements.** Inputs are the CAD mass estimates (with the nut shield), the published/estimated thrust of **280–400 g total (planning 350 g)**, the real cage geometry and stated assumptions. Nothing here has been flown or bench-tested. Only **P1B** is being built (user decision, 2026-10-08). P1A rows are kept for comparison, and they also show roughly how P1B behaves with its rings zip-tied, apart from the extra ring mass. Re-run after the static thrust test and weighing:

```
cd cad/apex2-cage && ../../software/.venv/bin/python motion_physics.py
```

The script ([`motion_physics.py`](../cad/apex2-cage/motion_physics.py)) prints every table below and writes `motion_physics.json`. Rolling dynamics come from [`rolling_physics.py`](../cad/apex2-cage/rolling_physics.py) (about 10 minutes; writes `rolling_physics.json`). Its inputs are at the top of the file.

## Short answer: the throttle it needs right now

"Throttle" means motor output %, which is roughly stick position above idle in Betaflight. Thrust grows faster than linearly with throttle, so each value is a range for an assumed curve (thrust ∝ throttle^1.3 to throttle^2). The **measured hover throttle replaces all of these**.

| Configuration | All-up (est.) | T:W at 350 g | **Hover throttle** | Hover, end of pack | Hover time (est.) |
| --- | --- | --- | --- | --- | --- |
| P1A fixed cage + 450 | 117.1 g | 2.99 | **43–58 %** | 49–63 % | 4.0–8.1 min |
| P1A fixed cage + 1100 | 139.1 g | 2.52 | **49–63 %** | 56–68 % | 7.5–15.4 min |
| P1B gimbal + 450 | 144.9 g | 2.42 | **51–64 %** | 57–70 % | 2.9–5.9 min |
| P1B gimbal + 1100 | 166.9 g | 2.10 | **57–69 %** | 64–75 % | 5.7–11.7 min |

The masses are CAD accounted estimates. Uncounted screws, nuts, strap, leads and antenna likely add 7–14 g, putting P1B + 450 at about 154–160 g and P1B + 1100 at about 176–182 g ([CAD README](../cad/apex2-cage/README.md#p1b-build-the-one-being-built-breakdown-and-realistic-all-up-estimate)). Each 10 g raises hover throttle by roughly 2–3 points and shortens hover time by about 10 %.

**Rolling on the ground (P1B only), with the aircraft tilted 30° inside the gimbal:**

| | P1B + 450 | P1B + 1100 |
| --- | --- | --- |
| Start rolling from any resting face, any direction | **29–45 %** (72 g thrust) | **33–49 %** (82 g) |
| Start on a smooth floor (skids first) | 25–40 % | 28–43 % |
| Keep it rolling once moving | **11–24 %** (20 g) | **12–26 %** (23 g) |
| Above this it lifts off instead | 57–69 % | 63–74 % |

So **rolling needs roughly half the hover throttle**. The simulation in §2.2 shows the clean-rolling band is narrow, about **±3 throttle points** above the start point. Above it, the cage skids and tumbles and keeps speeding up. Below it, it stops within ~15 cm. Ease in slowly. The usable window at 30° tilt is about 30–55 % throttle. Below it the cage stays put; above it the drone leaves the ground.

## 1. Flying

**Hover.** Total thrust must equal weight, so each motor carries ¼ of the all-up mass: 29 g (P1A + 450) to 42 g (P1B + 1100). That is 33–48 % of the planning maximum thrust. Thrust falls with pack voltage (about ×0.85 near the end of a 2S pack), so hover throttle rises 5–7 points through a flight.

**Minimum thrust-to-weight:**

| T:W | Hovering | Rolling (P1B) |
| --- | --- | --- |
| 1.0 : 1 | Theoretical floor: full throttle just holds altitude, with nothing left to steer or climb | More than enough |
| ~1.5 : 1 | Practical minimum: sluggish but controllable. This is the project's **redesign trigger** | Easily |
| 2 : 1 | Project **target**: margin for control, climbs, bump recovery and battery sag (~×0.85 thrust at end of pack) | Easily |

Rolling needs much less, because the floor carries most of the weight. The start condition T/W ≥ sin α / sin(θ + α) (§2.1) gives, from the worst face in any direction:
- 0.58 × weight at 20° tilt;
- 0.49 × weight at 30°;
- 0.43 × weight at 45°;
- an absolute minimum of **sin 23.3° ≈ 0.40 × weight** at 67° tilt.

The near-round pole faces need only about 0.1 × weight, and keeping it rolling takes about 0.10–0.14 × weight. A maximum T:W of only about 0.5–0.6 would roll the cage in theory, but the aircraft still has to hold its tilt. Anything that can hover can roll.

The build's estimated T:W at the 350 g planning thrust is 2.42 (450 mAh) and 2.10 (1100 mAh); at the 280 g low estimate it is 1.93 and 1.68. If the 1100 mAh build is really about 180 g, it drops to about 1.9 and 1.56, close to the 1.5 line. Measure thrust early.

**Performance at the 350 g planning thrust:**

| Configuration | Full-throttle climb | Max tilt holding altitude | Max horizontal acceleration |
| --- | --- | --- | --- |
| P1A + 450 | 1.99 g (19.5 m/s²) | 70° | 2.8 g |
| P1A + 1100 | 1.52 g (14.9 m/s²) | 67° | 2.3 g |
| P1B + 450 | 1.42 g (13.9 m/s²) | 66° | 2.2 g |
| P1B + 1100 | 1.10 g (10.8 m/s²) | 62° | 1.8 g |

Climb acceleration is (T − W)/m. The max tilt holding altitude is cos⁻¹(W/T). At the low thrust estimate (280 g), P1B + 1100 drops to T:W 1.68 and 0.68 g of climb. That is above the 1.5:1 redesign trigger in [05-hardware](05-hardware.md) but below the 2:1 target.

**Speed.** In steady level flight, the horizontal thrust W·tan(tilt) equals drag. Drag here is the cage's wire-frame body drag (rods computed from the real geometry, hubs, rings, aircraft) plus the rotor ram drag ṁ·v.

| Tilt | P1A + 450 | P1B + 1100 |
| --- | --- | --- |
| 10° | ~2.4 m/s | ~2.7 m/s |
| 20° | ~4.4 m/s | ~5.0 m/s |
| 30° | ~6.4 m/s | ~7.1–7.4 m/s |

The drag area is about 76 cm² for P1A and 87–104 cm² for P1B (the outer ring yaws freely). These speeds are **optimistic**: prop thrust also falls with airspeed. Indoors you will rarely hold more than 10–15° of tilt.

**Endurance.** This uses momentum theory: ideal hover power = W·√(W / 2ρA), over four 2-inch prop disks (81 cm²). It assumes a figure of merit of 0.4–0.6, motor and ESC efficiency of 0.55–0.75, 7.4 V, and 80 % of the pack used.

| Configuration | Hover power | Current | Time |
| --- | --- | --- | --- |
| P1A + 450 | 20–40 W | 2.7–5.4 A | 4.0–8.1 min |
| P1B + 450 | 27–55 W | 3.6–7.5 A | **2.9–5.9 min** |
| P1B + 1100 | 33–68 W | 4.5–9.2 A | 5.7–11.7 min |

**Flight time for the P1B build, including realistic mass and rolling.** Hover power scales with mass^1.5. Rolling at about 0.5 × weight of thrust uses about 35 % of hover power, roughly 2.8× the time.

| P1B build | Hovering | Mostly rolling | Mixed flying and rolling |
| --- | --- | --- | --- |
| 450 mAh, CAD 145 g | 2.9–5.9 min | ~8–16 min | ~4–8 min |
| 450 mAh, realistic 154–160 g | **2.6–5.2 min** | ~7–15 min | ~3.5–7 min |
| 1100 mAh, CAD 167 g | 5.7–11.7 min | ~16–33 min | ~8–16 min |
| 1100 mAh, realistic 176–182 g | **5.1–10.5 min** | ~14–29 min | ~7–14 min |

Aggressive flying drains faster than a steady hover. The frame seller recommends packs up to 650 mAh, so check balance and handling with the 1100 mAh pack. Replace these estimates with a timed hover to 3.5 V/cell and the OSD hover throttle.

The **P1B + 450 low end is under the 3-minute gate**, so time real flights. Currents are well within the 10 A-per-motor AIO and both packs' C ratings.

## 2. Rolling on the ground (P1B gimbal)

### 2.1 Starting to roll (statics)

**How it moves.** The cage sits on the floor. The aircraft stays level in the gimbal and tilts by θ like a normal quad. Thrust T acts through the gimbal pivots at the cage centre:
- horizontal push **F = T sin θ**;
- the floor load drops to **N = W − T cos θ**.

The cage rests on hubs, not a smooth sphere. To roll, it must tip its centre over the edge between two hubs. Taking moments about that edge, it starts to tip when **F / N ≥ tan α**, where α is the face's tip angle (half-width of the face ÷ centre height). Solving for thrust:

> **T / W ≥ sin α / sin(θ + α)**   and to stay on the ground   **T / W < 1 / cos θ**

Sliding follows the same formula with the friction angle tan⁻¹ μ in place of α. Whichever angle is smaller wins.

**Tip angles of this cage.** These are computed from the actual 62 hub positions (centres at r = 121.5 mm, 2.5 mm hub face):

| Resting on | Count | Centre height | Tip angle α |
| --- | --- | --- | --- |
| Hexagon | 20 | 113.7 mm | 20.5–23.3° |
| Pentagon | 10 | 116.6 mm | 16.1–19.7° |
| Pole triangle | 10 | 121.2 mm | 4.0–12.1° (nearly round: rolls off with almost no push) |

The tip angle depends on the push direction: the smaller value is toward an edge, the larger toward a corner.

**Thrust to start rolling** (% of all-up weight and grams, from any face in any direction, α = 23.3°):

| Tilt θ | P1B + 450 | P1B + 1100 | Lift-off above |
| --- | --- | --- | --- |
| 20° | 58 % = 84 g → 33–49 % throttle | 58 % = 96 g → 37–52 % | 106 % W |
| 30° | 49 % = 72 g → 29–45 % | 49 % = 82 g → 33–49 % | 115 % W |
| 45° | 43 % = 62 g → 26–42 % | 43 % = 71 g → 29–45 % | 141 % W |

Larger tilts need less thrust and leave a wider window before lift-off. The minimum thrust is W·sin α ≈ 40 % W, at a tilt of 90° − α.

**Keeping it rolling.** Each step over an edge lifts the centre a few millimetres. At slow speed that energy is lost at each hub impact, which acts like a rolling-resistance coefficient of **0.006–0.150 (mean 0.08)**, about a fifth of the start threshold. Once moving, about **10–14 % of weight** of push (tilt 30–45°) keeps it going. Momentum makes it easier still.

**Floor matters.** PETG hubs on a smooth hard floor (μ ≈ 0.3, friction angle 17°) skid before they tip off a hexagon. The start is then a skid: 39 % W at 30° tilt, followed by rolling. On matte or gym floors and carpet (μ ≥ 0.45) it tips and rolls. These μ values are assumptions; measure the slide angle of a hub on your demo floor.

**Rolling speed vs cage spin:** 1 m/s of rolling turns the cage at 8.1 rad/s (77 rpm).

**P1A cannot roll in a controlled way.** The aircraft is fixed to the cage. Tilting it means tipping the whole ball, which turns the thrust with it. P1A moves by flying, or by skidding if pushed along. Set down pole-first, it rests on a pole triangle tilted **12°**, so it takes off from a slight tilt.

### 2.2 Rolling dynamics (simulation)

[`rolling_physics.py`](../cad/apex2-cage/rolling_physics.py) simulates the real 62-hub cage tipping from face to face. The run is stopped and labelled when either of these happens:
- the floor force reaches zero (**hop**);
- friction can no longer hold the pivoting hub (**skid**, μ = 0.45).

How the model works:
- Thrust and weight act at the gimbal centre.
- The aircraft adds mass but no spin inertia.
- Each hub landing is a fully inelastic impact.
- The next tipping edge follows both momentum and push.
- Six push directions are tested per row, starting on a hexagon.

Raw output is in `rolling_physics.json`.

**Result: pure rolling only exists in a narrow throttle band.** P1B + 450, mu 0.45. Outcomes per heading: S = stuck, R = rolls, K = skids, H = hops.

| Tilt | Thrust (k = T/W) | Throttle | Outcome | What happens |
| --- | --- | --- | --- | --- |
| 30° | 0.45 W (65 g) | 27–43 % | SSSSSS | Stays put |
| 30° | 0.50 W (72 g) | 30–45 % | SKKKKK | Rolls ~12 cm, reaching ~0.5 m/s in 0.7 s, then starts skidding |
| 30° | 0.55 W (80 g) | 32–48 % | KKKKKK | Skids after ~7 cm (0.36 s) |
| 30° | ≥0.80 W | ≥43–58 % | KKKKKK | Slides immediately; floor grip is too light to pivot |
| 45° | 0.40 W (58 g) | 25–41 % | SKKSSK | Starts in some directions only |
| 45° | 0.50 W (72 g) | 30–45 % | KKKKKK | Skids after ~7 cm at ~0.5 m/s |
| 20° | 0.55 W (80 g) | 32–48 % | SSKSSK | Starts in some directions only |

P1B + 1100 gives the same fractions of weight. The throttle is about 3 points higher because the drone is heavier.

**Why:**
- Thrust that pushes the cage forward also unloads it (N = W − T cos θ).
- Just above the tipping threshold, the floor is carrying only about half the weight.
- As speed builds, each pivot over an edge unloads the hubs further. The hub skids at about **0.4–0.6 m/s**, before the hop speed of 0.8 m/s is reached.
- On a slick floor (μ 0.3) it slides from the start. On carpet-like grip (μ 0.6) it rolls a little further, ~18 cm, before skidding.

**While it rolls** (k ≈ 0.5, before skidding):
- **Energy:** each hub landing loses about **48 %** of the kinetic energy.
- **Jolts:** the centre jumps about **0.25–0.3 m/s** vertically at every landing, as 2–4 bumps per second. The FPV image will bob.
- **Path:** the path wanders **20–40°** from the push direction within the first few faces, because the faces are not lined up with the push. The pilot steers by changing the tilt direction.
- **Coasting with motors at idle:** from 0.5 m/s it stops after **~15 cm**, 2 faces. From 0.8 m/s it stops after ~23 cm. Below about 0.35 m/s it can't get over the next edge at all.

**Skid/tumble mode** (anything above the band). Once sliding, the net push is T sin θ − μₖ(W − T cos θ). It **keeps accelerating** until air drag balances:

| Tilt | k = 0.5 | k = 0.6 | k = 0.7 |
| --- | --- | --- | --- |
| 20° | slows down | +0.5 m/s² | +1.1 m/s² |
| 30° | +0.5 m/s² | +1.2 m/s² | +2.0 m/s² |
| 45° | +1.2 m/s² | +2.1 m/s² | +3.1 m/s² |

The P1B + 450 numbers are the same as P1B + 1100. The drag-limited speeds of 3–10 m/s will never be reached indoors. The practical point is that **there is no natural speed limit once it skids**, so the pilot controls speed with throttle and tilt, like flying. Expect a fast, bouncing slide-and-tumble rather than a smooth roll.

**Hop onset** (v² / d = g_eff, d ≈ 120 mm):

| Throttle | Hop speed |
| --- | --- |
| Motors off | 1.09 m/s |
| k 0.5 at 30° tilt | 0.82 m/s |
| k 0.75 at 30° tilt | 0.65 m/s |

**Slopes** (P1B + 1100, start from rest, worst face; at least 30 % of weight kept on the floor):

| Thrust | Throttle | Steepest slope it rolls up |
| --- | --- | --- |
| Motors off | — | Stays parked up to **16–23°** |
| 0.50 W | 33–49 % | ~7° (tilt 60°) |
| 0.75 W | 45–60 % | ~25° (tilt 41°) |
| 1.00 W | 57–69 % | ~54° (tilt 26°): mostly flying |

**Steps and door sills** (cage contact radius 120–124 mm; P1B + 1100 at 45° tilt):

| Step | Lean angle | Thrust from rest | Throttle |
| --- | --- | --- | --- |
| 5 mm | 16° | 32 % W | 24–39 % |
| 10 mm | 23° | 42 % W | 29–45 % |
| 20 mm | 33° | 56 % W | 36–52 % |
| 30 mm | 41° | 65 % W | 41–56 % |
| 50 mm | 53° | 81 % W | 48–62 % |

Above about 20 mm, the step usually rides into the cage between hubs and catches a rod. A hop or short flight is easier.

**Turning** (ideal sphere, all horizontal thrust used sideways, 70 % of weight still on the floor):

| Speed | Radius at 30° tilt | Radius at 45° tilt |
| --- | --- | --- |
| 0.3 m/s | ~3 cm | ~2 cm |
| 0.5 m/s | ~7 cm | ~4 cm |
| 1.0 m/s | ~29 cm | ~17 cm |

Turning is set by tilt direction alone; the drone's yaw (camera direction) is independent of the cage.

**Power while rolling** (momentum theory):

| Thrust | Power vs hover | Endurance vs hover |
| --- | --- | --- |
| 0.3 W | ~16 % | ~6× |
| 0.5 W | ~35 % | ~2.8× |
| 0.7 W | ~59 % | ~1.7× |

Ground effect helps further. Rolling is the efficient way to cover ground, so use it to stretch the 450 mAh pack.

### 2.3 What the rolling cage does to the gimbal and the aircraft

The cage was rolled smoothly in 400 random orientations and directions. The torque the rings pass to the aircraft was solved through the three bearing constraints (rings estimated at 16.5 g / 96.5 mm and 14.8 g / 86.5 mm).

| Rolling speed | Cage rate | Typical torque on aircraft | Revolutions whose peak exceeds the ~48 N·mm control authority | Median uncorrected rate kick |
| --- | --- | --- | --- | --- |
| 0.3 m/s | 2.6 rad/s | 0.1 N·mm | 25 % | ~40 °/s |
| 0.5 m/s | 4.3 rad/s | 0.3 N·mm | 34 % | ~110 °/s |
| 1.0 m/s | 8.6 rad/s | 1.3 N·mm | 45 % | ~400 °/s |

- **Most of the time the gimbal isolates the aircraft well.** The torque is under 2 N·mm, against about 48 N·mm of available control.
- **The exception is gimbal lock.** About once in every 3–4 revolutions, the cage carries the middle (X) axis close to 90°. The rings then have to spin up to around 10× the cage rate. At that moment the rings' inertia is about the same as the aircraft's (~1.5 × 10⁻⁴ kg·m²), so the aircraft gets a real twitch.
- **The kick grows with speed squared.** **Roll slowly (≤ 0.5 m/s)** and expect occasional twitches. The worst 10 % of passes are not resolved by this rigid-constraint model; physically they are limited by the ring momentum.
- The same applies when a wall contact sets the cage spinning in flight. **Check this in the rolling test with blackbox gyro logs.**
- **If twitches are a problem:** lighter rings reduce the kick in proportion (ring mass vs stiffness is already a trade-off), or roll more slowly.

## 3. Gimbal torques on the aircraft (P1B)

| | P1B + 450 | P1B + 1100 |
| --- | --- | --- |
| Roll/pitch control torque available at hover | ~48 N·mm | ~55 N·mm |
| CG off the pivot, per mm (at 90° tilt) | 0.87 N·mm/mm | 1.09 N·mm/mm |
| 1100 pack fitted without re-balancing (3.6 mm) | — | 3.9 N·mm = **7 %** of authority |
| All six bearings (estimated friction) | ~0.3 N·mm = 0.6 % | ~0.3 N·mm = 0.5 % |

Control torque = 4 × the thrust change per motor × the 33.6 mm arm. The aircraft can easily overpower the gimbal. Re-balancing with the CG slots is still worthwhile; leaving the CG 1–2 mm below the pivots makes it hang level when the motors are off.

**Gimbal lock caution.** The chain is cage →Z→ outer →X→ inner →Y→ aircraft. When the middle (X) axis turns 90°, the Y and Z axes line up and one rotation direction is lost. A cage rotation in that direction is passed to the aircraft. The rings also swing quickly near that pose. Watch for sudden aircraft twitches during the rolling test.

## 4. Contacts

| Speed | P1A + 450 (117 g) | P1B + 1100 (167 g) | Same energy as dropping from |
| --- | --- | --- | --- |
| 0.5 m/s | 15 mJ | 21 mJ | 1 cm |
| 1.0 m/s | 59 mJ | 83 mJ | 5 cm |
| 2.0 m/s | 234 mJ | 334 mJ | 20 cm |

The T3 cage-section drop test (30 cm) is harsher per gram than a 2 m/s wall hit. "Low-energy contact" for the P1B flight gate should mean about 1 m/s or less.

**Why the gimbal matters.** A hub contact pushes along the line through the cage centre, so a square-on hit adds no spin. A **glancing** hit adds friction at the 124 mm radius:
- **P1A:** at 1 m/s with μ 0.3, the whole drone (estimated 4.2 kg·cm²) can be spun up to about **880°/s**. With about 39 N·mm of control torque, the flight controller needs about **75° of rotation** to stop it.
- **P1B:** the same hit only spins the cage and rings, and the aircraft feels the 0.3 N·mm of bearing friction. The exception is when the spin carries the gimbal near lock (see §2.3).

## 5. Impact survivability (estimates; nothing has been tested)

These numbers come from `motion_physics.py` ("Impact survivability"), using assumed properties for pultruded carbon rod (about 120 GPa stiffness, 1500 MPa strength, 1.25 % strain at break) and PETG (yield about 50 MPa). Treat them as order-of-magnitude.

**Impact energy:**

| Speed | 450 mAh (145 g) | 1100 mAh (167 g) | Realistic 1100 (180 g) | Same as dropping from |
| --- | --- | --- | --- | --- |
| 0.5 m/s | 18 mJ | 21 mJ | 22 mJ | 1 cm |
| **1 m/s** | 72 mJ | 83 mJ | 90 mJ | 5 cm |
| 2 m/s | 0.29 J | 0.33 J | 0.36 J | 20 cm |
| 3 m/s | 0.65 J | 0.75 J | 0.81 J | 46 cm |
| 4.4 m/s | 1.42 J | 1.64 J | 1.77 J | 1 m |
| 5 m/s (20° tilt cruise) | 1.81 J | 2.09 J | 2.25 J | 1.3 m |

**What the cage can absorb:**
- One 1 mm rod breaks at about 13–26 N of side load. It stores about 27–82 mJ before breaking, and buckles springily (elastically) at about 29 N of end load.
- A hit on a hub spreads into about 3–9 rods, so the cage can absorb roughly **0.08–0.74 J before a rod breaks**, provided the hubs and sockets hold.

**Stopping force.** In a drop, the deceleration in g ≈ **drop height ÷ stopping distance**, and the cage flexes about 10–30 mm. For example, a 30 cm drop stopped in 20 mm gives about 15 g. A wall hit at speed v stopped in distance s gives a = v² / 2s.

**The gimbal rings, especially the inner ring in flat landings, are the likely weak point:**
- The aircraft (about 111 g with the 1100 mAh pack) is stopped through the two Y pivots.
- The inner ring stays level with the aircraft, so a **flat landing always bends it out of its plane**, where its slotted 5 × 3 mm band is weakest. The model is a ring moment of about 0.32 × P × R with slotted section properties.

| Deceleration | Force through the pivots | Inner ring, side hit (in plane) | Inner ring, flat landing (out of plane) |
| --- | --- | --- | --- |
| 10 g | 11 N | ~14 MPa | ~42 MPa |
| 20 g | 22 N | ~28 MPa | **~84 MPa** (above yield) |
| 40 g | 43 N | ~56 MPa (yield) | ~167 MPa |

So **flat landings above about 12 g** may permanently bend or crack the inner ring. That corresponds to flat drops of about **25–35 cm onto a hard floor** (12 × a 20–30 mm stop). Side hits stay below yield up to about 36 g, which is about 3.5 m/s with a 20 mm stop.

**Best estimate:**

| Impact | Expected result |
| --- | --- |
| **≤ 1 m/s** (wall bumps, flight-gate contacts) | Should survive repeatedly |
| 1–2 m/s side hits | Usually survives. A rod may pop out of a hub; push it back. |
| 2–3 m/s side hits | Risk of a broken rod, cracked hub socket or splice |
| **Flat drop ≥ 25–35 cm onto a hard floor** | Inner ring may bend or crack |
| Drop ≥ 1 m (falling from hover) | Likely damage |

**Likely failure order:** hub sockets (about 1 mm PETG walls) first in side hits, the inner ring in flat drops, then the rods.

The drone can fly at about 5 m/s at only 20° of tilt, faster than it can survive hitting something. **Keep to about 1–1.5 m/s near walls, and land gently: don't cut throttle above the floor.**

**If the rings prove weak:**
- `ring_t` 3 → 4 mm makes the band about 1.8× stronger out of plane, for about +4–5 g.
- Fewer or shorter lightening slots also help.
- A soft landing pad helps during testing.

**How to find the real limits** (also in the [print and test plan](../cad/apex2-cage/PRINT_AND_TEST_PLAN.md)):
1. **T3 section:** after the 30 cm drops, add a 50 cm drop.
2. **Full cage without the aircraft:** hang a ~110 g dummy weight from the carrier, then drop flat onto a hard floor from 10, 20, 30 and 50 cm. Inspect the rings, junctions and hubs after each drop.
3. **Flight:** 10 contacts at about 1 m/s or less (the gate), then step the speed up slowly and stop at the first damage.

## 6. What changes these numbers

| Measurement | Replaces |
| --- | --- |
| Static thrust at full throttle, fresh and end-of-pack ([print and test plan §5](../cad/apex2-cage/PRINT_AND_TEST_PLAN.md)) | `thrust_total_g`, `sag_thrust_factor` |
| Thrust at 25/50/75 % throttle on the same rig | `throttle_exponent` (the throttle curve) |
| Weighed all-up mass with each pack | `mass_g` |
| Hover throttle from the OSD or blackbox | Check on everything in §1 |
| Hub slide angle on the demo floor | `floor_mu` |
| Flight time to 3.5 V/cell | Endurance estimate |
| Drop and contact tests (§5) | Survivable speed and drop height; the rod and PETG property assumptions |

**Limits of this model:**
- rigid cage, point-like hub contacts, no rod flex;
- rotor thrust independent of airspeed and ground effect (ground effect near the floor will slightly *raise* thrust while rolling);
- simplified drag;
- bearing friction is a guess;
- the gimbal-lock behaviour is not simulated.

## Final CAD mass refresh — 2026-10-09

P1B mass inputs now derive from the current native production volumes and the generator's unchanged PETG/carbon and hardware allowance scenarios. Accounted totals are 144.68 / 166.68 g (450 / 1100 packs), excluding unweighed extras. Cut-pin length is now 11.00 mm with a 1 mm running gap; the 0.26 g per-pin accounting allowance remains approximate. Neither the refreshed calculations nor the matching simulator masses establish actual weight, thrust, flex, impact strength or flight endurance. See the [final print package](../cad/apex2-cage/print_ready_p1b/README.md) and its native evidence.
