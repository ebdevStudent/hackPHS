"""Motion physics estimates for the Ball Drone (P1A fixed cage and P1B gimbal).

Run:  python motion_physics.py           (numpy only; no Fusion needed)

Every input below is a vendor value, CAD estimate or assumption. Replace them with measured values
(static thrust, weighed masses, hover throttle) and re-run; nothing here is a measured result.
Writes motion_physics.json next to this file and prints the tables used in docs/22-motion-physics.md.
"""
import itertools
import json
import math
from pathlib import Path

import numpy as np

G = 9.81
RHO = 1.20                      # air density, kg/m^3 (indoor, ~20 C)

# ---------------------------------------------------------------- inputs (update after measuring)
INPUTS = {
    'thrust_total_g': {'low': 280, 'plan': 350, 'high': 400},   # vendor_specs.json ESTIMATE, 4 motors, fresh 2S pack
    'sag_thrust_factor': 0.85,          # end of pack (~7.0 V vs ~7.6 V): thrust ~ V^2 -> ~0.85 (assumption)
    'throttle_exponent': (1.3, 2.0),    # thrust ~ throttle^n; measured small-quad curves fall between these (assumption)
    'mass_g': {                         # accounted CAD estimates (generator reports; P1B finalization 2026-10-09, with nut shield)
        'P1A + 450': 117.08, 'P1A + 1100': 139.08, 'P1B + 450': 144.68, 'P1B + 1100': 166.68},
    'cage_mass_g': 24.8,                # 62 hubs (19.5 g) + 100 carbon rods (5.3 g)
    'ring_mass_g': 31.3,                # 8 quarters 14.6 + 8 junctions 10.7 + 16 splice screws 4.8 + 6 bearings 1.2 (estimate)
    'aircraft_inner_g': {'P1B + 450': 88.8, 'P1B + 1100': 110.8},   # everything inside the inner ring
    'cage_outer_r_mm': 123.923,         # cage_outer_dia / 2 (44.50 mm rods -> 247.846 mm)
    'hub_core_r_mm': 2.5,
    'motor_diag_mm': 95.0,
    'prop_dia_mm': 50.8,
    'rod_dia_mm': 1.0,
    'floor_mu': {'smooth hard floor (tile, sealed wood)': 0.3, 'gym floor / matte': 0.45, 'low carpet': 0.6},  # PETG hub, assumption
    'cd_rod': 1.1, 'cd_body': 1.0,
    'hub_frontal_mm2': 40.0,            # one hub seen from any side (estimate)
    'aircraft_frontal_mm2': {'450': 1400.0, '1100': 1600.0},       # frame, stack, camera, motors, battery (estimate)
    'figure_of_merit': (0.40, 0.60),    # tiny 2" props (assumption)
    'drive_efficiency': (0.55, 0.75),   # motor x ESC (assumption)
    'pack': {'450': 0.450, '1100': 1.100},   # Ah, 2S
    'usable_fraction': 0.80,
    'pack_voltage_v': 7.4,
    'bearing_friction_nmm': 0.05,       # each MR52ZZ, light load, ZZ shields (estimate)
    'cg_offset_1100_mm': 3.63,          # if the 1100 mAh pack is fitted without using the CG slots
}


def current_p1b_masses():
    """Match the current native-generator allowances, excluding unweighed extras.

    Allocate each of six cut-pin allowances to its owning body. All nut,
    washer, wire, strap and delivered-hardware masses still require weighing.
    """
    folder = Path(__file__).resolve().parent
    export = json.loads((folder/'exports_p1b/manifest.json').read_text())
    native = json.loads((folder/'review-2026-10-09-finalization/native-inspection.json').read_text())
    vendor = json.loads((folder/'vendor_specs.json').read_text())['masses_g']
    measured = json.loads((folder/'measurements.json').read_text()).get('masses_g', {})
    vendor.update({k: v for k,v in measured.items() if v is not None})
    density = native['parameters']['petg_density']['value']  # native density scenario, not a weighed print
    groups = {'cage': 0., 'rings': 0., 'mount': 0.}
    for row in export['parts']:
        name = row['name']
        if name == 'gimbal_fit_coupon':
            continue
        key = 'cage' if name.startswith('hub_') else 'rings' if ('ring_' in name or '_junction_' in name) else 'mount'
        groups[key] += row['native_volume_mm3']*row['qty']*density/1000
    rods = sum(b['volume_mm3'] for b in native['bodies'] if b['name'].startswith('rods_')) * native['parameters']['rod_density']['value']/1000
    bare = sum(vendor[k] for k in ('frame_g','aio_g','motors_x4_g','props_x4_g','camera_g'))
    cage = groups['cage'] + rods + 2*.26
    rings = groups['rings'] + 16*.2 + 6*.2 + 2*.26
    aircraft = {f'P1B + {pack}': bare+groups['mount']+12*.2+2*.26+vendor[f'pack_{pack}_g'] for pack in ('450','1100')}
    INPUTS['cage_mass_g'] = cage
    INPUTS['ring_mass_g'] = rings
    INPUTS['aircraft_inner_g'] = aircraft
    INPUTS['mass_g'].update({k: cage+rings+v for k,v in aircraft.items()})
    INPUTS['mass_basis'] = 'Current native P1B volumes, PETG/carbon density scenarios and unchanged generator hardware allowances; unweighed extras excluded'


current_p1b_masses()


# ---------------------------------------------------------------- cage contact geometry
def cage_points(outer_r, hub_r):
    """62 hub centres exactly as build_p1a.cage_graph places them (pentagons at +/-Z, pole hubs added)."""
    phi = (1 + 5 ** 0.5) / 2
    ico = []
    for s1 in (-1, 1):
        for s2 in (-1, 1):
            ico += [(0, s1, s2 * phi), (s1, s2 * phi, 0), (s2 * phi, 0, s1)]
    ico = np.array(ico, float)
    verts = []
    for i, j in itertools.combinations(range(12), 2):
        if abs(np.linalg.norm(ico[i] - ico[j]) - 2) < 1e-9:
            for f in (1 / 3, 2 / 3):
                verts.append(ico[i] + (ico[j] - ico[i]) * f)
    verts = np.array(verts)
    a, b = ico[0] / np.linalg.norm(ico[0]), np.array([0, 0, 1.0])
    k = np.cross(a, b); s, c = np.linalg.norm(k), a @ b; k /= s
    verts = verts * c + np.cross(k, verts) * s + np.outer(verts @ k, k) * (1 - c)
    rv = outer_r - hub_r
    verts = verts / np.linalg.norm(verts, axis=1, keepdims=True) * rv
    return np.vstack([verts, [[0, 0, rv], [0, 0, -rv]]])


def hull_faces(pts):
    """Convex-hull faces by brute force (62 points): list of (unit normal, offset, vertex indices)."""
    faces = {}
    for i, j, k in itertools.combinations(range(len(pts)), 3):
        n = np.cross(pts[j] - pts[i], pts[k] - pts[i])
        if np.linalg.norm(n) < 1e-9: continue
        n /= np.linalg.norm(n); d = n @ pts[i]
        if d < 0: n, d = -n, -d
        if np.all(pts @ n <= d + 1e-6):
            key = tuple(np.round(n, 6))
            faces.setdefault(key, (n, d, set()))[2].update((i, j, k))
    return list(faces.values())


def face_metrics(pts, faces, hub_r):
    out = []
    for n, d, idx in faces:
        foot = n * d
        poly = pts[list(idx)]
        u = poly[0] - foot; u /= np.linalg.norm(u); v = np.cross(n, u)
        xy = np.c_[(poly - foot) @ u, (poly - foot) @ v]
        xy = xy[np.argsort(np.arctan2(xy[:, 1], xy[:, 0]))]
        edges = list(zip(xy, np.roll(xy, -1, axis=0)))
        apothem = min(abs((q - p)[0] * -p[1] - (q - p)[1] * -p[0]) / np.linalg.norm(q - p) for p, q in edges)
        circ = max(np.linalg.norm(xy, axis=1))
        H = d + hub_r                                # centre height above the floor when resting on this face
        out.append({'sides': len(idx), 'normal': n, 'H': H, 'apothem': apothem, 'circ': circ, 'idx': idx,
                    'alpha_min': math.degrees(math.atan(apothem / H)), 'alpha_max': math.degrees(math.atan(circ / H))})
    return out


def rolling_resistance(faces):
    """Worst-case (slow, fully inelastic) rolling: lift per step / distance per step, for every face-to-neighbour step."""
    coeffs = []
    for a, b in itertools.permutations(faces, 2):
        shared = a['idx'] & b['idx']
        if len(shared) != 2: continue
        lift = math.hypot(a['H'], a['apothem']) - a['H']
        step = a['apothem'] + b['apothem']
        coeffs.append(lift / step)
    return min(coeffs), max(coeffs), float(np.mean(coeffs))


# ---------------------------------------------------------------- helpers
def start_fraction(beta_deg, tilt_deg):
    """Thrust / total weight needed to start moving the P1B cage on the ground.
    Thrust T at tilt theta through the gimbal centre: F = T sin(theta), N = W - T cos(theta).
    Tipping (or sliding) starts when F/N >= tan(beta)  ->  T/W >= sin(beta) / sin(theta + beta)."""
    b, t = math.radians(beta_deg), math.radians(tilt_deg)
    return math.sin(b) / math.sin(t + b)


def throttle(frac_of_max):
    lo_n, hi_n = INPUTS['throttle_exponent']
    if frac_of_max > 1: return None
    return frac_of_max ** (1 / lo_n) * 100, frac_of_max ** (1 / hi_n) * 100


def fmt_throttle(frac_of_max):
    t = throttle(frac_of_max)
    return 'not possible' if t is None else f'{t[0]:.0f}-{t[1]:.0f} %'


def cage_frontal_cda(pts, with_rings, pack):
    """Wire-frame cage + rings + aircraft, flow along +Y. Returns Cd*A in m^2 (both cage halves count)."""
    edges = [(i, j) for i, j in itertools.combinations(range(60), 2)
             if abs(np.linalg.norm(pts[i] - pts[j]) - min(np.linalg.norm(pts[0] - pts[m]) for m in range(1, 60))) < 1e-6]
    poles = [(60, i) for i in range(60) if pts[i][2] > pts[:60, 2].max() - 1e-6] + [(61, i) for i in range(60) if pts[i][2] < pts[:60, 2].min() + 1e-6]
    flow = np.array([0, 1.0, 0])
    rod = 0.0
    for i, j in edges + poles:
        d = pts[j] - pts[i]; L = np.linalg.norm(d) - 2 * INPUTS['hub_core_r_mm']
        rod += L * INPUTS['rod_dia_mm'] * np.linalg.norm(np.cross(d / np.linalg.norm(d), flow))
    hubs = 62 * INPUTS['hub_frontal_mm2']
    cda = INPUTS['cd_rod'] * rod + INPUTS['cd_body'] * (hubs + INPUTS['aircraft_frontal_mm2'][pack])
    rings = (0, 0)
    if with_rings:
        inner_edge = 2 * 89 * 3                       # inner ring level (XY plane): seen edge-on
        outer_edge, outer_face = 2 * 99 * 3, 2 * math.pi * 96.5 * 5 * 0.7   # outer ring yaws freely; 30 % slots
        rings = (INPUTS['cd_body'] * (inner_edge + outer_edge), INPUTS['cd_body'] * (inner_edge + outer_face))
    return (cda + rings[0]) * 1e-6, (cda + rings[1]) * 1e-6, rod


def steady_speed(force_n, cda, mdot):
    """Solve 0.5 rho CdA v^2 + mdot v = F (body drag + rotor ram drag)."""
    a, b = 0.5 * RHO * cda, mdot
    return (-b + math.sqrt(b * b + 4 * a * force_n)) / (2 * a)


# ---------------------------------------------------------------- main
def main():
    I = INPUTS
    out = {'inputs': I}
    pts = cage_points(I['cage_outer_r_mm'], I['hub_core_r_mm'])
    faces = face_metrics(pts, hull_faces(pts), I['hub_core_r_mm'])
    kinds = {3: 'pole triangle', 5: 'pentagon', 6: 'hexagon'}
    print('== Cage contact geometry (hub centres at r = %.1f mm, hub face 2.5 mm) ==' % (I['cage_outer_r_mm'] - I['hub_core_r_mm']))
    geo = {}
    for sides in sorted({f['sides'] for f in faces}):
        fs = [f for f in faces if f['sides'] == sides]
        g = {'count': len(fs), 'centre_height_mm': float(np.mean([f['H'] for f in fs])),
             'alpha_easiest_deg': min(f['alpha_min'] for f in fs), 'alpha_hardest_deg': max(f['alpha_max'] for f in fs)}
        geo[kinds.get(sides, sides)] = g
        print(f"  {kinds.get(sides, sides):14s} x{g['count']:2d}  centre {g['centre_height_mm']:.1f} mm above floor  "
              f"tip angle {g['alpha_easiest_deg']:.1f} deg (easiest direction) .. {g['alpha_hardest_deg']:.1f} deg (hardest)")
    a_easy = min(f['alpha_min'] for f in faces); a_hard = max(f['alpha_max'] for f in faces)
    hexes = [f for f in faces if f['sides'] == 6]
    a_hex = (min(f['alpha_min'] for f in hexes), max(f['alpha_max'] for f in hexes))
    crr = rolling_resistance(faces)
    print(f'  rolling resistance once moving (slow, fully inelastic steps): C_rr {crr[0]:.3f}-{crr[1]:.3f} (mean {crr[2]:.3f})')
    pole_tris = [f for f in faces if f['sides'] == 3 and f['normal'][2] < 0]
    rest_tilt = math.degrees(math.acos(-pole_tris[0]['normal'][2]))
    print(f'  P1A set down pole-first rests on a pole triangle tilted {rest_tilt:.1f} deg')
    out['geometry'] = {'faces': geo, 'rolling_resistance': crr, 'p1a_pole_rest_tilt_deg': rest_tilt}

    tmax = {k: v / 1000 * G for k, v in I['thrust_total_g'].items()}
    print('\n== Hover and flight (thrust range %d-%d g, planning %d g) ==' % (I['thrust_total_g']['low'], I['thrust_total_g']['high'], I['thrust_total_g']['plan']))
    flight = {}
    disk = 4 * math.pi * (I['prop_dia_mm'] / 2000) ** 2
    for cfg, m_g in I['mass_g'].items():
        m = m_g / 1000; W = m * G
        r = {}
        for case in ('low', 'plan', 'high'):
            T = tmax[case]
            r[case] = {'tw': T / W, 'hover_frac': W / T, 'hover_throttle': throttle(W / T),
                       'hover_throttle_end_of_pack': throttle(W / (T * I['sag_thrust_factor'])),
                       'climb_accel_g': (T - W) / W,
                       'max_level_tilt_deg': math.degrees(math.acos(min(1, W / T))),
                       'max_level_accel_g': math.sqrt(max(0, T * T - W * W)) / W}
        vi = math.sqrt(W / (2 * RHO * disk))
        p_ideal = W * vi
        p_elec = (p_ideal / (I['figure_of_merit'][1] * I['drive_efficiency'][1]), p_ideal / (I['figure_of_merit'][0] * I['drive_efficiency'][0]))
        pack = cfg.split('+ ')[1]
        amps = tuple(p / I['pack_voltage_v'] for p in p_elec)
        minutes = tuple(I['pack'][pack] * I['usable_fraction'] / a * 60 for a in amps[::-1])
        r['hover_power_w'] = p_elec; r['hover_current_a'] = amps; r['hover_minutes'] = minutes; r['induced_velocity_ms'] = vi
        flight[cfg] = r
        p = r['plan']
        print(f"  {cfg:11s} {m_g:6.2f} g  T:W {r['low']['tw']:.2f}-{r['high']['tw']:.2f} (plan {p['tw']:.2f})  "
              f"hover thrust {m_g/4:.1f} g/motor = {p['hover_frac']*100:.0f} % of max  hover throttle ~{p['hover_throttle'][0]:.0f}-{p['hover_throttle'][1]:.0f} % "
              f"(range over thrust estimate {r['high']['hover_throttle'][0]:.0f}-{r['low']['hover_throttle'][1]:.0f} %; end of pack {p['hover_throttle_end_of_pack'][0]:.0f}-{p['hover_throttle_end_of_pack'][1]:.0f} %)")
        print(f"              full-throttle climb {p['climb_accel_g']:.2f} g ({p['climb_accel_g']*G:.1f} m/s^2)  max level-flight tilt {p['max_level_tilt_deg']:.0f} deg  "
              f"max level accel {p['max_level_accel_g']:.2f} g   hover ~{p_elec[0]:.0f}-{p_elec[1]:.0f} W, {amps[0]:.1f}-{amps[1]:.1f} A, ~{minutes[0]:.1f}-{minutes[1]:.1f} min (80 % of pack)")
    out['flight'] = flight

    print('\n== Speed in level flight (body drag + rotor ram drag; upper-bound style estimate) ==')
    speeds = {}
    for cfg, m_g in I['mass_g'].items():
        W = m_g / 1000 * G
        pack = cfg.split('+ ')[1]
        cda_lo, cda_hi, rod_area = cage_frontal_cda(pts, cfg.startswith('P1B'), pack)
        mdot = RHO * disk * flight[cfg]['induced_velocity_ms']
        row = {}
        for tilt in (10, 20, 30):
            F = W * math.tan(math.radians(tilt))
            row[tilt] = (steady_speed(F, cda_hi, mdot), steady_speed(F, cda_lo, mdot))
        speeds[cfg] = {'cda_m2': (cda_lo, cda_hi), 'rod_projected_mm2': rod_area, 'speed_ms_by_tilt': row}
        print(f"  {cfg:11s} CdA {cda_lo*1e4:.1f}-{cda_hi*1e4:.1f} cm^2  " + '  '.join(f'{t} deg: {a:.1f}-{b:.1f} m/s' for t, (a, b) in row.items()))
    out['speed'] = speeds

    print('\n== P1B rolling on the ground (aircraft tilts inside the gimbal; cage stays on the floor) ==')
    print('   Thrust needed to START moving, as % of all-up weight, and throttle at the planning thrust.')
    print('   Must also stay below lift-off (T cos(tilt) < W).')
    rolling = {}
    for cfg in ('P1B + 450', 'P1B + 1100'):
        m_g = I['mass_g'][cfg]; W = m_g / 1000 * G; T = tmax['plan']
        rolling[cfg] = {}
        print(f'  {cfg} ({m_g:.1f} g)')
        for tilt in (15, 20, 30, 45, 60):
            liftoff = 1 / math.cos(math.radians(tilt))
            row = {}
            phi_slick = math.degrees(math.atan(min(I['floor_mu'].values())))
            for label, beta in (('easiest', a_easy), ('hexagon typical', sum(a_hex) / 2), ('any face, any direction', a_hard),
                                ('smooth floor, skid start', min(a_hard, phi_slick))):
                k = start_fraction(beta, tilt)
                row[label] = {'thrust_frac_of_weight': k, 'thrust_g': k * m_g, 'throttle': throttle(k * W / T), 'lifts_off_first': k >= liftoff}
            rolling[cfg][tilt] = row
            cells = []
            for label, v in row.items():
                note = ' (lifts off first)' if v['lifts_off_first'] else ''
                cells.append(f"{label}: {v['thrust_frac_of_weight']*100:.0f} % W = {v['thrust_g']:.0f} g -> {fmt_throttle(v['thrust_g']/I['thrust_total_g']['plan'])}{note}")
            row['liftoff_throttle'] = throttle(liftoff * m_g / I['thrust_total_g']['plan'])
            print(f"    tilt {tilt:2d} deg (lift-off at {liftoff*100:.0f} % W = {liftoff*m_g:.0f} g -> {fmt_throttle(liftoff*m_g/I['thrust_total_g']['plan'])}):  " + ' | '.join(cells))
        keep = {}
        for tilt in (15, 30, 45):
            k = start_fraction(math.degrees(math.atan(crr[2])), tilt)
            keep[tilt] = k
        rolling[cfg]['keep_rolling_frac'] = keep
        print('    keep rolling once moving (mean C_rr): ' + '  '.join(f'tilt {t}: {k*100:.0f} % W = {k*m_g:.0f} g -> {fmt_throttle(k*m_g/I["thrust_total_g"]["plan"])}' for t, k in keep.items()))
    print('   Friction: if tan(tip angle) > floor mu, the cage skids instead of tipping; skid start uses the friction angle:')
    for name, mu in I['floor_mu'].items():
        phi = math.degrees(math.atan(mu))
        print(f'    {name:38s} mu {mu:.2f} (friction angle {phi:.0f} deg): ' +
              ('tips/rolls before skidding for every face' if phi > a_hard else
               'skids first for the steeper tips' if phi > a_easy else 'skids before it tips'))
    out['rolling'] = rolling

    print('\n== P1B gimbal: torques on the aircraft ==')
    arm = I['motor_diag_mm'] / 2 / math.sqrt(2) / 1000
    gimbal = {}
    for cfg in ('P1B + 450', 'P1B + 1100'):
        W = I['mass_g'][cfg] / 1000 * G; T = tmax['plan']
        dT = min(T / 4 - W / 4, W / 4)
        authority = 4 * dT * arm * 1000
        pend = I['aircraft_inner_g'][cfg] / 1000 * G
        fric = 6 * I['bearing_friction_nmm']
        gimbal[cfg] = {'roll_pitch_authority_nmm': authority, 'pendulum_nmm_per_mm_offset': pend, 'bearing_friction_total_nmm': fric}
        print(f'  {cfg}: roll/pitch control authority at hover ~{authority:.0f} N*mm; CG offset costs {pend:.2f} N*mm per mm at 90 deg tilt '
              f'({pend*I["cg_offset_1100_mm"]:.1f} N*mm = {pend*I["cg_offset_1100_mm"]/authority*100:.0f} % if the 1100 pack is not re-balanced); '
              f'all bearing friction ~{fric:.1f} N*mm ({fric/authority*100:.1f} %)')
    out['gimbal'] = gimbal

    print('\n== Contacts ==')
    contacts = {}
    R = I['cage_outer_r_mm'] / 1000
    for cfg in ('P1A + 450', 'P1B + 1100'):
        m = I['mass_g'][cfg] / 1000
        rows = {}
        for v in (0.5, 1.0, 2.0):
            ke = 0.5 * m * v * v
            rows[v] = {'energy_j': ke, 'equivalent_drop_cm': v * v / (2 * G) * 100}
        contacts[cfg] = rows
        print(f'  {cfg}: ' + '  '.join(f'{v} m/s = {r["energy_j"]*1000:.0f} mJ (same as a {r["equivalent_drop_cm"]:.0f} cm drop)' for v, r in rows.items()))
    # Glancing wall hit: friction at the contact acts at radius R. P1A: the whole drone spins. P1B: only the cage/rings do.
    m = I['mass_g']['P1A + 450'] / 1000; mu = 0.3; dv = 1.0 * 1.5     # 1 m/s normal speed, restitution ~0.5
    impulse = mu * m * dv * R
    I_p1a = 2 / 3 * I['cage_mass_g'] / 1000 * R ** 2 + (m - I['cage_mass_g'] / 1000) * 0.035 ** 2 * 1.5
    spin = math.degrees(impulse / I_p1a)
    W = m * G; T = tmax['plan']
    auth = 4 * min(T / 4 - W / 4, W / 4) * arm               # N*m, P1A + 450
    knock = math.degrees((impulse / I_p1a) ** 2 / (2 * auth / I_p1a))
    contacts['glancing_1ms'] = {'angular_impulse_nms': impulse, 'p1a_inertia_kgm2': I_p1a, 'p1a_spin_deg_s': spin,
                                'p1a_authority_nmm': auth * 1000, 'p1a_knock_angle_deg': knock}
    print(f'  Glancing 1 m/s wall hit with friction 0.3: angular impulse {impulse*1000:.1f} mN*m*s. '
          f'P1A (whole drone, I ~{I_p1a*1e4:.1f} kg*cm^2) can be spun up to ~{spin:.0f} deg/s; '
          f'With ~{auth*1000:.0f} N*mm of control torque the FC needs ~{knock:.0f} deg of rotation to stop it. '
          f'P1B passes only bearing friction to the aircraft. Rolling at 1 m/s turns the cage at {1/R:.1f} rad/s ({1/R*60/2/math.pi:.0f} rpm).')
    out['contacts'] = contacts

    print('\n== Impact survivability (assumed material properties; not tested) ==')
    rod_E, rod_sigma, rod_strain = 120e3, 1500.0, 0.0125      # MPa, MPa, - : typical pultruded carbon rod (assumption)
    d, L = I['rod_dia_mm'], 44.5
    Irod, Srod = math.pi * d ** 4 / 64, math.pi * d ** 3 / 32
    EI = rod_E * Irod
    M_break = rod_sigma * Srod
    F_ss, F_ff = 4 * M_break / L, 8 * M_break / L
    U_ss = 0.5 * F_ss * F_ss * L ** 3 / (48 * EI)             # N*mm = mJ
    U_arc = EI * L / (2 * (d / 2 / rod_strain) ** 2)          # uniform curvature to break strain (upper bound)
    P_buckle = math.pi ** 2 * EI / L ** 2
    cap = (3 * U_ss, 9 * U_arc)
    print(f'  1 mm rod: breaks at ~{F_ss:.0f}-{F_ff:.0f} N side load; stores ~{U_ss:.0f}-{U_arc:.0f} mJ to break; buckles springily at ~{P_buckle:.0f} N end load')
    print(f'  cage near a struck hub (3-9 rods): ~{cap[0]/1000:.2f}-{cap[1]/1000:.2f} J before a rod breaks (if hubs/sockets hold)')
    imp = {}
    for v in (0.5, 1.0, 2.0, 3.0, 4.43, 5.0):
        row = {cfg: 0.5 * I['mass_g'][cfg] / 1000 * v * v for cfg in ('P1B + 450', 'P1B + 1100')}
        row['realistic_1100_180g'] = 0.5 * 0.180 * v * v
        row['drop_height_cm'] = v * v / (2 * G) * 100
        row['max_v_for_rod_capacity'] = [math.sqrt(2 * c / 1000 / 0.167) for c in cap]
        imp[v] = row
        print(f"  {v:4.2f} m/s: {row['P1B + 450']*1000:4.0f} / {row['P1B + 1100']*1000:4.0f} / {row['realistic_1100_180g']*1000:4.0f} mJ (450 / 1100 / 180 g)  = drop from {row['drop_height_cm']:.0f} cm")
    # Gimbal ring: aircraft (inside the inner ring) stopped through two Y pivots at deceleration a.
    m_in = I['aircraft_inner_g']['P1B + 1100'] / 1000; R_in = 86.5
    band_w, band_t, slot_w = 5.0, 3.0, 2.6
    S_in_plane = band_t * ((band_w ** 3 - slot_w ** 3) / 12) / (band_w / 2)   # slotted, bending in the ring plane
    S_out_plane = (band_w - slot_w) * band_t ** 2 / 6                        # slotted, bending out of plane
    ring = {}
    for gs in (10, 20, 40):
        F = m_in * gs * G; P = F / 2; M = 0.32 * P * R_in
        ring[gs] = {'pivot_force_n': F, 'in_plane_mpa': M / S_in_plane, 'out_of_plane_mpa': M / S_out_plane}
        print(f'  inner ring at {gs} g stop: {F:.0f} N through the pivots -> ~{M/S_in_plane:.0f} MPa side hit (in plane), ~{M/S_out_plane:.0f} MPa flat landing (out of plane); PETG yield ~50 MPa')
    out['impact'] = {'rod': {'E_mpa': rod_E, 'strength_mpa': rod_sigma, 'break_strain': rod_strain, 'side_break_n': [F_ss, F_ff],
                             'energy_to_break_mj': [U_ss, U_arc], 'buckle_n': P_buckle},
                     'cage_capacity_j': [c / 1000 for c in cap], 'speeds': imp, 'inner_ring': ring}

    def clean(o):
        if isinstance(o, dict): return {str(k): clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)): return [clean(v) for v in o]
        if isinstance(o, (np.floating, np.integer)): return float(o)
        if isinstance(o, np.ndarray): return o.tolist()
        return o
    Path(__file__).with_name('motion_physics.json').write_text(json.dumps(clean(out), indent=1) + '\n')


if __name__ == '__main__':
    main()
