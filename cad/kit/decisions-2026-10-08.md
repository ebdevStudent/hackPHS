# Open CAD decisions — settlement, 2026-10-08

The CAD README listed three deferred decisions. These recommendations need no change to the generators, because each matches what the current P1B model already assumes. Physical checks remain. The user can still override any of them. Numbers come from the generator parameters via `cage_model.py`, recorded P1B inner ring 84–89 mm and outer ring 94–99 mm.

## 1. Pivot pins: cut to 10.5 mm — **confirmed by the user 2026-10-08**

**Decision:** cut the 2 × 16 mm stainless dowels to **10.5 mm** with the [pin cutting gauge](test-pieces/pin_cut_gauge.stl).

**Why:** the model's pin is press depth 6 mm + pivot gap 0.5 mm + bearing 2.5 mm + 1.5 mm past the bearing = 10.5 mm. At the inner-ring Y pivots that pin ends at radius 88.0 mm, inside the inner ring band (89 mm).

An uncut 16 mm pin would end at **93.5 mm**. That is 4.5 mm into the 5 mm ring gap and only **0.5 mm** from the outer ring (94 mm), which sweeps past as the gimbal turns. Deepening the bosses to take the full pin adds printed mass where P1B has the least margin.

**How to cut** (304 stainless is not hardened; about 2–3 minutes per pin):

1. Drop the pin into the gauge's 10.5 mm hole and mark it at the top face. The gauge is only for measuring; it is plastic and would melt under a cut.
2. Clamp the pin in a small vise or locking pliers with the mark just clear of the jaws.
3. Cut with a rotary tool and reinforced abrasive cut-off wheel, or a fine-tooth (32 TPI) hacksaw or jeweller's saw. Avoid side cutters, which crush and flare the end.
4. File or sand a small chamfer on the cut end, then check each pin is 10.3–10.5 mm with calipers.
5. Make six plus two or three spares. Wear eye protection and the respirator; the pin gets hot.

## 2. Rod joints: dry fit first, bond only joints that fail — **confirmed by the user 2026-10-08**

**Decision:** assemble rods **dry**, using the socket clearance the fit strip selects. Bond a joint with the BOM's J-B Weld ClearWeld epoxy only if it slips or pulls out in the [bend test](README.md#rod-and-hub-bend-test) or during the contact gate.

**Why:** the mechanical brief asks for replaceable modules. A bonded rod and its two hubs become one replacement unit; record which ones in the assembly log. If you choose to bond everything instead, keep the generator's 0.15 mm per-side clearance as glue space. For dry fit, enter the snuggest strip result (usually 0.05–0.10 mm) as `rod_bore_clear` and regenerate.

## 3. Camera uptilt: keep 20° — **confirmed by the user 2026-10-08**

**Decision:** mount the camera at **20°** uptilt, then measure the real angle and enter it as `cam_tilt`.

**Why:**

- The 2026-10-08 P1B regeneration confirmed the 20° lens centreline is clear of both rings at the nominal pose. Another angle needs that check repeated.
- Yaw tracking uses only horizontal error.
- A target at camera height sits 20° below the image centre, well inside the Caddx Ant's roughly 120° vertical view.
- Indoor flight here is slow; the simulator caps tilt at 35°, so the picture stays usable.

If you change the angle, regenerate P1B and confirm the "camera centreline clear" line before printing rings.

## Superseding digital finalization — 2026-10-09

The final P1B running gap is 1.00 mm, so the selected cut-pin stack is **11.00 mm**, not the earlier 10.5 mm. Use the regenerated pin-cut gauge in `../apex2-cage/print_ready_p1b/`. This retains the cut-stock approach; it does not qualify physical retention or loaded clearance. Earlier dated decisions above are retained as history.
