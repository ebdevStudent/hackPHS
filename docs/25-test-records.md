# Physical test records: thrust, batteries and contacts

Updated 2026-10-08. Use these procedures and the CSV forms in [`forms/`](forms/) when parts arrive. Results go under `evidence/physical/`, recording date, operator, configuration and the raw log. Nothing here is a result until it is measured.

## Static thrust

Highest-priority measurement: the CAD mass budget currently uses a **350 g planning estimate** (range 280–400 g).

**Setup — `lift` (simplest):**

1. Fasten the bare aircraft upright to a heavy, rigid base (≥ 300 g, e.g. a block with zip ties through the frame).
2. Put the base on a kitchen scale (0.1–1 g resolution). The props blow down past the base, so the reading **drops** as thrust rises.
3. Keep props clear of the scale, the bench and hands. Clamp everything; nothing may tip.

**Setup — `push`:** mount the aircraft inverted on a stand on the scale, so the props push down onto it. The reading **rises**.

**Procedure:**

1. Charged pack, voltage logged; props on; safety glasses; a clear area; the spotter holds the disarm switch.
2. Disarmed: tare reading. Then arm and run 25, 50, 75 and 100 % throttle, about 3 s each. Note the scale reading, and the pack voltage and current from the OSD/Betaflight.
3. Throttle back between steps; let the motors cool 10 s. Repeat for each pack type.

**Logging:**

```sh
software/.venv/bin/python tools/thrust_log.py --manual --setup lift \
  --bare 52.3 --pack450 26.4 --pack1100 48.1 --label specter-gemfan2015-450
# or a load-cell board printing grams per line:  --serial /dev/ttyUSB0
# or analyse a typed CSV (docs/forms/thrust-log.csv): --from-csv log.csv --tare 812.0
```

The tool reports peak thrust and thrust-to-weight for P1A/P1B with each pack, against the 2:1 target and the 1.5:1 redesign line. Enter the peak as `thrust_total_g` in [`cad/kit/measurement-form.csv`](../cad/kit/measurement-form.csv).

## Battery log

Form: [`forms/battery-log.csv`](forms/battery-log.csv). Number each pack (450-1 … 450-4, 1100-1, 1100-2). Before first use, record the **label text and chemistry**. Both OVONIC listings say to stop charging at 4.2 V/cell; do not charge to 4.35 V unless the label says LiHV.

| Column | Meaning |
| --- | --- |
| `cells` | 2 for these packs |
| `configuration` | bare, P1A or P1B |
| `start_v` / `end_v` | Resting pack voltage before takeoff / 1 min after landing |
| `flight_s` | Takeoff to landing |
| `hover_throttle_pct` | From the OSD while hovering |

`tools/gate_check.py` flags any start above 4.22 V/cell and any end below 3.3 V/cell. A flight counts toward the three-minute gate only if it ends at or above 3.3 V/cell.

## Contact record (P1B flight gate)

Form: [`forms/contact-log.csv`](forms/contact-log.csv). Define the setup once and keep it for the whole count:

- cage revision;
- pack;
- contact surface (foam board or cardboard);
- approach direction and the point on the cage;
- approach speed, or a repeatable description such as "drift in at walking pace from 1 m".

After **every** contact, land and inspect for:

- cracks or layer separation;
- rods moved in sockets;
- loose screws;
- bent members;
- reduced prop clearance.

Then fill `prop_strike`, `damage`, `repair` and `recovered` with y or n.

**Rules:**

- A prop strike, any damage or any repair resets the count to zero.
- Changing the cage revision starts a new count.
- **Recovery:** the gate requires "repeatable manual recovery". The proposed rule, pending team confirmation, is that every contact in the counted ten was recovered by the pilot without landing or help.

```sh
software/.venv/bin/python tools/gate_check.py --contacts docs/forms/contact-log.csv --flights docs/forms/battery-log.csv
```

The gate passes only when all three hold: ten consecutive clean contacts, every one of them recovered, and at least one caged flight of three minutes or more. Exit code 0 means passed. Keep footage of the counted run.
