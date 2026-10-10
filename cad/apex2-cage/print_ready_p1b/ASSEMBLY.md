# P1B assembly — parts and cold-fit checks

The connection path is **aircraft → carrier → fore/aft support arms → arm pivot blocks/pins → inner Y bearings → inner ring → inner X pins → outer X bearings → outer ring → outer Z bearings → pole-hub pins → rod cage**. Forward is +Y in CAD; left/right is X; up/down is Z.

| Printed part | Quantity | Where it goes |
| --- | --- | --- |
| `hub_3way` | 46 | Ordinary cage nodes; flat face outward |
| `hub_3way_mount_A` | 4 | The four designated mount nodes in the cage; retained bosses are unused by P1B |
| `hub_4way` | 10 | Five nodes around each pole |
| `hub_pole_5way_pivot` | 2 | Top/bottom poles; inward metal pins enter the outer Z bearings |
| `inner_ring_quarter` | 4 | Horizontal inner hoop at nominal pose |
| `inner_junction_Y_bearing` | 2 | Inner front/back; receive aircraft-side arm pins |
| `inner_junction_X_pin` | 2 | Inner left/right; metal pins enter outer X bearings |
| `outer_ring_quarter` | 4 | Vertical outer hoop at nominal pose |
| `outer_junction_X_bearing` | 2 | Outer left/right; receive inner X pins |
| `outer_junction_Z_bearing` | 2 | Outer top/bottom; receive pole-hub pins |
| `carrier_plate` | 1 | Under aircraft bottom plate |
| `nut_shield_plate` | 1 | Between relieved foam and battery, under carrier |
| `support_arm_p1b` | 2 | Carrier fore/aft ends; connect to pivot blocks |
| `arm_pivot_block` | 2 | Adjustable end plates on arm flanges; pins point into inner Y bearings |

The sixteen ring-splice screw passages are coaxial with the quarter pilots. Each junction has two screws, one into each adjacent quarter. Quarter ends seat beneath the splice plates and are secured with screws.

## Nonprinted hardware

| Hardware | Quantity | Use |
| --- | --- | --- |
| 1 mm carbon rods, 44.50 mm cuts | 90 | Cage edges |
| 1 mm carbon rods, 37.83 mm cuts | 10 | Pole spokes |
| MR52ZZ (nominal 2 × 5 × 2.5 mm) | 6 | Two bearings per axis |
| 2 mm metal pins cut to 11.00 mm | 6 | Two per axis; do not install uncut 16 mm stock |
| M2 screws into quarter pilots | 16 | Ring splice joints; nominal joined thickness 5 mm (2 mm splice + 3 mm quarter) |
| M2 screws + nuts | 4 | Frame to carrier; nominal frame/carrier thickness 5 mm |
| M2 screws + nuts | 4 | Arms to carrier; nominal stack 6.5 mm |
| M2 screws + nuts | 4 | Pivot blocks to arm flanges; nominal stack 7 mm |
| Foam pad / battery strap | 1 each | Hand-cut relieved pad and actual strap |

Screw-length selection must include actual washers and full nut engagement. M2×6 is the nominal ring-splice candidate; try one joint and confirm grip before the full ring. Frame M2×8 and arm/flange M2×10 are candidates, not verified hardware stacks. Use washers or shorten screws as needed. All frame/arm screws and nuts below the carrier must project **≤2.6 mm beneath its underside**; an unmodified long screw can violate this limit. Check screw heads/washer access and clearance during a full hand rotation. All twenty-eight screws are accounted approximately in the mass estimate; actual nuts/washers and extra masses still need weighing.

## Assembly order

1. Print T3, remove brim/strings without enlarging sockets, and test three arms of a hub with actual carbon rod. Assemble nine hubs and ten 44.50 mm rods into the shared-edge hexagon/pentagon. Qualify pull-out, sag/recovery and drops per the print plan. Keep the extra hub spare.
2. Check T4 against the actual frame, with props removed and battery disconnected. The carrier assumes 25.5 × 25.5 mm accessible holes, ±2 mm lateral frame adjustment and ±3 mm arm adjustment. If the real pattern differs or screws cannot pass without force, record measurements for a CAD revision; do not force or rescale the part.
3. Cold-fit a ring-splice screw into the selected 2.00 mm pilot. It must tighten and hold without stripping or cracking. The T1B result says #5 fits best; sustained grip remains to be confirmed.
4. Print production hub, quarter and G2 plates after their respective test gates. Check bearing seats and pin holders retain the actual hardware without cracking. Press the six measured 11.00 mm pins 6 mm into the two pole hubs, two inner X junctions and two arm pivot blocks. Support the plastic and keep bearing races free. All six bearings must turn freely on their pins.
5. Attach the carrier to the frame and both fore/aft arms with screws and nuts. Fit the foam reliefs and shield described below, and route the actual strap, antenna and leads clear of props and pivots.
6. Assemble the inner hoop around the aircraft, closing the last quarter after inserting both arm pins into the inner Y bearings. Attach pivot blocks loosely through their vertical slots, then balance and tighten.
7. Close the outer hoop around the inner ring with inner X pins in outer X bearings. Assemble the rod cage around the rings, leaving one cap open until the pole pins are seated in the outer Z bearings. Close the cap last.
8. Balance each intended battery separately. Slots allow ±5 mm vertical adjustment; the 1100 pack needs about 3.6 mm estimated additional raise. Check the aircraft hangs level, adjustments hold under load and all three pivots rotate freely through reachable motion. Check battery removal, cable slack and actual camera image.
9. With the system unpowered, inspect every actual prop/airframe/wire clearance throughout motion, including gentle representative deflection. Record pin/bearing retention, joint slip, cracks and masses. Complete thrust and the project contact/flight/recovery gates before demo flight. Initial hovers can use the documented zip-tied-ring fallback.

## Foam and shield

The nominal pad is **15.88 × 62.8 × 3 mm**. Cut a centered notch at each short end, approximately **5.62 mm wide and 8.21 mm deep**, all the way through the 3 mm foam, so the arm nuts/tails clear across ±3 mm arm travel. These are guide dimensions from the modeled envelopes; mark and fit the actual hardware. Leave no foam trapped under a nut or screw tail.

Stack below the carrier: **relieved foam → 0.8 mm printed shield → battery**. At the modeled ≤2.6 mm metal protrusion and 3 mm uncompressed pad, only 0.4 mm nominal vertical reserve remains to the shield. Check the compressed assembly. The shield is a barrier; its presence does not prove that fastener pressure cannot reach a battery.

## Identifying G2 parts on its plate

Use the part footprints and coordinates in `manifest.json` rather than guessing from similar-looking junctions. The individual `parts/` STL files carry the full part names and supplied print orientations. G2 contains two of each junction type, two arm blocks and two pole hubs. Preserve the print axes if printing a replacement part separately.

All dimensions are CAD values with vendor assumptions or user-reported coupon fits. This guide supplies assembly candidates and inspection gates, not physical strength or flight certification.

| G2 placement in manifest order | Part | Center X / Y on bed (mm) |
| --- | --- | --- |
| 1 | `inner_junction_X_pin` | -50.96 / -39.37 |
| 2 | `inner_junction_X_pin` | -29.50 / -39.37 |
| 3 | `inner_junction_Y_bearing` | -9.03 / -39.37 |
| 4 | `inner_junction_Y_bearing` | 10.43 / -39.37 |
| 5 | `outer_junction_Z_bearing` | 36.48 / -39.40 |
| 6 | `outer_junction_Z_bearing` | -45.37 / 15.40 |
| 7 | `outer_junction_X_bearing` | -19.43 / 15.40 |
| 8 | `outer_junction_X_bearing` | -0.19 / 15.40 |
| 9 | `hub_pole_5way_pivot` | 22.50 / 1.45 |
| 10 | `hub_pole_5way_pivot` | 48.63 / 1.45 |
| 11 | `arm_pivot_block` | -40.19 / 54.77 |
| 12 | `arm_pivot_block` | 2.82 / 54.77 |

In the actual first-layer preview, positive Y is toward the top of the image. [G2 first-layer paths](previews/G2_sliced_first_layer.png).
