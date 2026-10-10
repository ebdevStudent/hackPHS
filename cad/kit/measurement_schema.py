"""Every value the arrival measurements may set, with unit, plausible range, design and method.

Names match the Fusion user parameters read by cad/apex2-cage/build_p1a.py and build_p1b.py
(stage6_measurements applies a name only where that design defines it), plus masses_g entries.
Ranges are sanity limits for typing errors, not tolerances.
"""
# name: (unit, low, high, design, how to measure)
PARAMETERS = {
    'motor_diag': ('mm', 85, 105, 'both', 'Centre of one motor shaft to the diagonally opposite shaft; average both diagonals'),
    'prop_dia': ('mm', 45, 56, 'both', 'Tip-to-tip across an installed prop; take the largest of the four'),
    'prop_z': ('mm', 4, 20, 'both', 'Frame top surface to the underside of the prop blades at the hub'),
    'motor_od': ('mm', 12, 20, 'both', 'Motor bell outside diameter'),
    'motor_h': ('mm', 6, 16, 'both', 'Frame top to the top of the motor bell'),
    'frame_t': ('mm', 1.5, 4, 'both', 'Bottom plate thickness at a mounting hole'),
    'arm_w': ('mm', 4, 14, 'both', 'Narrowest arm width'),
    'stack_w': ('mm', 25, 45, 'both', 'Centre plate width across the flats'),
    'stack_h': ('mm', 5, 30, 'both', 'Frame top to the highest point of the AIO stack and its wiring'),
    'frame_hole_pitch': ('mm', 19, 31, 'both', 'Centre-to-centre of the square mounting-hole pattern you will use'),
    'cam_size': ('mm', 10, 22, 'both', 'Camera body width (19 mm with the bracket)'),
    'cam_y': ('mm', 0, 45, 'both', 'Frame centre to camera centre, forward'),
    'cam_z': ('mm', 0, 25, 'both', 'Frame top to camera centre'),
    'cam_tilt': ('deg', 0, 45, 'both', 'Camera uptilt as mounted (angle gauge or phone level on the lens face)'),
    'cam_hfov': ('deg', 90, 175, 'both', 'Horizontal field of view; leave blank unless measured against a grid'),
    'batt450_l': ('mm', 50, 75, 'both', '450 mAh pack length without leads'),
    'batt450_w': ('mm', 12, 25, 'both', '450 mAh pack width'),
    'batt450_h': ('mm', 9, 20, 'both', '450 mAh pack height'),
    'batt1100_l': ('mm', 45, 80, 'both', '1100 mAh pack length without leads'),
    'batt1100_w': ('mm', 18, 40, 'both', '1100 mAh pack width'),
    'batt1100_h': ('mm', 12, 30, 'both', '1100 mAh pack height'),
    'rod_dia': ('mm', 0.8, 1.6, 'both', 'Carbon rod diameter, calipers at three points along one rod; record the largest'),
    'strap_w': ('mm', 8, 20, 'both', 'Battery strap width'),
    'strap_slot_t': ('mm', 1.2, 4, 'both', 'Strap thickness plus 0.5 mm'),
    'rod_bore_clear': ('mm', 0.03, 0.35, 'both', 'Fit strip: per-side clearance of the snuggest socket a rod enters without force'),
    'socket_depth': ('mm', 3, 8, 'both', 'Only if the fit strip shows a deeper socket is needed'),
    'm2_tap': ('mm', 1.5, 1.9, 'both', 'Fit strip: pilot hole that holds an M2 screw without cracking'),
    'antenna_len': ('mm', 15, 80, 'both', 'Exposed VTX antenna element length'),
    'antenna_d': ('mm', 2, 10, 'both', 'Antenna element outside diameter'),
    'frame_column_h': ('mm', 10, 30, 'both', 'Top plate underside above bottom plate top'),
    'bearing_od': ('mm', 4.9, 5.1, 'p1b', 'MR52ZZ outside diameter'),
    'bearing_w': ('mm', 2.3, 2.7, 'p1b', 'MR52ZZ width'),
    'bearing_seat_clear': ('mm', -0.1, 0.5, 'p1b', 'Gimbal coupon: seat allowance (seat - bearing OD) that holds the bearing; coupon prints 0/+0.10/+0.20/+0.30/+0.40'),
    'pin_d': ('mm', 1.9, 2.05, 'p1b', 'Dowel pin diameter'),
    'pin_press_d': ('mm', 1.75, 2.35, 'p1b', 'Gimbal coupon: press hole that holds a pin without cracking; coupon prints 1.85/1.95/2.05/2.15/2.25'),
    'pin_len': ('mm', 8, 20, 'p1b', 'Dowel pin stock length'),
}
MASSES = {
    'bare_aircraft_g': (30, 90, 'Aircraft with AIO, motors, props, camera, antenna, wiring and XT30, without battery or cage'),
    'pack_450_g': (18, 40, 'One 450 mAh pack with leads'),
    'pack_1100_g': (35, 75, 'One 1100 mAh pack with leads'),
    'thrust_total_g': (100, 600, 'Static thrust of all four motors at full throttle (tools/thrust_log.py)'),
}
