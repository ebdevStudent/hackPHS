"""Rolling dynamics of the P1B gimbal cage on the ground (estimates, not measurements).

Run:  python rolling_physics.py          (numpy only; inputs come from motion_physics.INPUTS)

Model
- The real 62-hub cage (hub centres at r = 121.5 mm, 2.5 mm hub faces) is a rigid convex polyhedron on a flat floor.
- The aircraft stays level inside the gimbal. Its thrust and all weight act at the cage centre.
  The aircraft contributes mass but no rotational inertia (gimbal-decoupled).
- Rolling = pivot about a floor edge between two hubs until the next face lands. Each landing is a perfectly inelastic
  hub impact: angular momentum about the next pivot edge is conserved, and the rest of the energy is lost.
- Each run checks hop (floor reaction pulls) and slip (friction demand > mu).
- Body drag from motion_physics. Rotor thrust is constant (no ground effect, no airspeed effect).
- Gimbal: the cage rolls smoothly. Each ring's angular momentum change is solved through the bearing constraints;
  the reaction on the aircraft is the torque the flight controller must cancel.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import motion_physics as M   # noqa: E402

G, RHO, IN = M.G, M.RHO, M.INPUTS
RH = IN['hub_core_r_mm'] / 1000
PTS = M.cage_points(IN['cage_outer_r_mm'], IN['hub_core_r_mm']) / 1000
FACES = M.face_metrics(PTS * 1000, M.hull_faces(PTS * 1000), IN['hub_core_r_mm'])
R_V = float(np.linalg.norm(PTS[0]))
Z = np.array([0, 0, 1.0])
MU_DEFAULT = 0.45
I_AIRCRAFT = 1.5e-4    # kg m^2, aircraft inside the inner ring about a horizontal axis (estimate: ~110 g within ~45 mm)


def rot(v, e, a):
    c, s = math.cos(a), math.sin(a)
    if v.ndim == 1:
        return v * c + np.cross(e, v) * s + e * (v @ e) * (1 - c)
    return v * c + np.cross(e, v) * s + np.outer(v @ e, e) * (1 - c)


def align(a, b):
    """Rotation matrix taking unit vector a to unit vector b."""
    v = np.cross(a, b); s = np.linalg.norm(v); c = a @ b
    if s < 1e-12:
        return np.eye(3) if c > 0 else np.diag([1.0, -1.0, -1.0])
    k = v / s; K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + s * K + (1 - c) * K @ K


def mass_props(cfg, ring_share=0.5):
    m = IN['mass_g'][cfg] / 1000
    Ic = 2 / 3 * IN['cage_mass_g'] / 1000 * R_V ** 2 + ring_share * 2 / 3 * IN['ring_mass_g'] / 1000 * 0.0915 ** 2
    return m, Ic


def cda(cfg):
    lo, hi, _ = M.cage_frontal_cda(PTS * 1000, True, cfg.split('+ ')[1])
    return (lo + hi) / 2


def thrust_g_to_throttle(t_g):
    return M.throttle(t_g / IN['thrust_total_g']['plan'])


def pick_edge(X, c, w):
    """Floor edge the horizontal direction w leaves the contact polygon through. Returns (i, j, axis e)."""
    idx = np.where(X[:, 2] < RH + 1e-7)[0]
    q = X[idx, :2] - c[:2]
    order = idx[np.argsort(np.arctan2(q[:, 1], q[:, 0]))]
    w = w[:2] / np.linalg.norm(w[:2])
    best, best_dot = None, -9
    for a, b in zip(order, np.roll(order, -1)):
        pa, pb = X[a, :2] - c[:2], X[b, :2] - c[:2]
        d = pb - pa
        n_out = np.array([d[1], -d[0]]); n_out /= np.linalg.norm(n_out)
        if n_out @ pa < 0: n_out = -n_out
        den = w[0] * -d[1] - w[1] * -d[0]
        if abs(den) > 1e-12:
            t = (pa[0] * -d[1] - pa[1] * -d[0]) / den
            s = (w[0] * pa[1] - w[1] * pa[0]) / den
            if t > 0 and -1e-9 <= s <= 1 + 1e-9:
                return a, b, np.cross(Z, np.r_[n_out, 0])
        if n_out @ w > best_dot:
            best, best_dot = (a, b, np.cross(Z, np.r_[n_out, 0])), n_out @ w
    return best


def start_pose(sides=6):
    """Rest on the face of the requested kind nearest the equator (P1B cage can rest any way up)."""
    f = min((f for f in FACES if f['sides'] == sides), key=lambda f: abs(f['normal'][2]))
    R = align(f['normal'], -Z)
    X = PTS @ R.T
    c = np.array([0, 0, RH - X[:, 2].min()])
    return X + c, c


def simulate(cfg, k, tilt_deg, heading_deg=0.0, v0=0.0, sides=6, steps=60, t_max=12.0, mu=MU_DEFAULT,
             ring_share=0.5, slope_deg=0.0, dt=2e-4):
    """Roll from rest (or with initial speed v0) under thrust k*W tilted tilt_deg toward heading.
    slope_deg > 0: uphill along the heading (gravity and thrust are expressed in the ramp frame)."""
    m, Ic = mass_props(cfg, ring_share); W = m * G; T = k * W
    h = math.radians(heading_deg); u = np.array([math.cos(h), math.sin(h), 0.0])
    th, s = math.radians(tilt_deg), math.radians(slope_deg)
    F0 = u * (T * math.sin(th + s) - W * math.sin(s)) + Z * (T * math.cos(th + s) - W * math.cos(s))
    kd = 0.5 * RHO * cda(cfg)
    X, c = start_pose(sides)
    i, j, e = pick_edge(X, c, u)
    r0 = c - X[i]
    rp = r0 - e * (r0 @ e)
    phid = v0 / math.sqrt(rp @ rp) if v0 else 0.0
    t, log = 0.0, {'status': 'running', 'steps': [], 'max_slip_ratio': 0.0, 'hop': None, 'skid': None}
    start_xy = c[:2].copy()

    def accel(r, v, Ie):
        F = F0 - kd * np.linalg.norm(v) * v
        return (e @ np.cross(r, F)) / Ie, F

    for n in range(steps):
        p = X[i].copy(); r0 = c - p; q = X - p
        A, B = q[:, 2], np.cross(e, q)[:, 2]
        land = np.full(len(X), np.inf)
        up = A > 1e-9
        land[up] = np.arctan2(A[up], -B[up])
        land[i] = land[j] = np.inf
        phi_land = land.min()
        rp = r0 - e * (r0 @ e); Ie = Ic + m * (rp @ rp)
        if phid <= 0:
            if accel(r0, np.zeros(3), Ie)[0] <= 0:
                log['status'] = 'stuck'; break
        phi, t0, z_top = 0.0, t, c[2]
        while True:
            r = rot(r0, e, phi); v = phid * np.cross(e, r)
            a, F = accel(r, v, Ie)
            ac = a * np.cross(e, r) + phid ** 2 * np.cross(e, np.cross(e, r))
            Rf = m * ac - F
            if Rf[2] <= 0:
                log['hop'] = {'t_s': t, 'speed_ms': float(np.linalg.norm(v[:2])), 'distance_m': float(np.linalg.norm((p + r)[:2] - start_xy))}
                log['status'] = 'hops'; break
            slip = float(np.linalg.norm(Rf[:2]) / Rf[2])
            log['max_slip_ratio'] = max(log['max_slip_ratio'], slip)
            if slip > mu:
                log['skid'] = {'t_s': t, 'speed_ms': float(np.linalg.norm(v[:2])), 'distance_m': float(np.linalg.norm((p + r)[:2] - start_xy))}
                log['status'] = 'skids'; break
            z_top = max(z_top, p[2] + r[2])
            # RK4 on (phi, phid)
            def f(ph, pd):
                rr = rot(r0, e, ph); return pd, accel(rr, pd * np.cross(e, rr), Ie)[0]
            step = dt if phid * dt < phi_land - phi else max((phi_land - phi) / max(phid, 1e-9), 1e-7)
            k1 = f(phi, phid); k2 = f(phi + step / 2 * k1[0], phid + step / 2 * k1[1])
            k3 = f(phi + step / 2 * k2[0], phid + step / 2 * k2[1]); k4 = f(phi + step * k3[0], phid + step * k3[1])
            phi += step / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
            phid += step / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
            t += step
            if phid <= 0 and phi > 1e-6:
                log['status'] = 'rocks back (stuck)'; break
            if phi >= phi_land - 1e-12 or t > t_max:
                break
        if log['status'] != 'running' or t > t_max:
            break
        # landing on the next face
        X = p + rot(X - p, e, phi_land); r = rot(r0, e, phi_land); c = p + r
        v = phid * np.cross(e, r); w_vec = phid * e
        X[:, 2] = np.where(np.abs(X[:, 2] - RH) < 1e-7, RH, X[:, 2])
        ke0 = 0.5 * m * v @ v + 0.5 * Ic * w_vec @ w_vec
        vh = v.copy(); vh[2] = 0
        hv = (vh / np.linalg.norm(vh) if np.linalg.norm(vh) > 1e-6 else 0) + u   # momentum and push both steer the next tip
        i, j, e = pick_edge(X, c, hv)
        rn = c - X[i]; rpn = rn - e * (rn @ e); Ien = Ic + m * (rpn @ rpn)
        phid = (e @ (Ic * w_vec + m * np.cross(rn, v))) / Ien
        vn = max(phid, 0) * np.cross(e, rn)
        ke1 = 0.5 * Ien * max(phid, 0) ** 2
        log['steps'].append({'t_s': t, 'dt_s': t - t0, 'speed_before_ms': float(np.linalg.norm(v[:2])),
                             'speed_after_ms': float(np.linalg.norm(vn[:2])), 'energy_lost_frac': 1 - ke1 / ke0 if ke0 > 0 else 0,
                             'vertical_jolt_ms': float(vn[2] - v[2]), 'centre_rise_mm': (z_top - min(c[2], z_top)) * 1000,
                             'x_m': float(c[0] - start_xy[0]), 'y_m': float(c[1] - start_xy[1])})
        if phid <= 0:
            phid = 0.0
    st = log['steps']
    log['distance_m'] = float(np.linalg.norm(c[:2] - start_xy))
    log['time_s'] = t
    if st:
        late = st[len(st) // 2:]
        dist = math.hypot(late[-1]['x_m'] - (st[len(st) // 2 - 1]['x_m'] if len(st) > 1 else 0),
                          late[-1]['y_m'] - (st[len(st) // 2 - 1]['y_m'] if len(st) > 1 else 0))
        dur = late[-1]['t_s'] - (st[len(st) // 2 - 1]['t_s'] if len(st) > 1 else 0)
        log['avg_speed_late_ms'] = dist / dur if dur > 0 else 0
        log['heading_drift_deg'] = math.degrees(math.atan2(st[-1]['y_m'], st[-1]['x_m'])) - heading_deg
        log['mean_energy_lost_frac'] = float(np.mean([s['energy_lost_frac'] for s in st]))
        log['mean_jolt_ms'] = float(np.mean([abs(s['vertical_jolt_ms']) for s in st]))
        log['mean_step_mm'] = log['distance_m'] / len(st) * 1000
    return log


def hop_speed(cfg, k, tilt_deg):
    """Speed at which the cage leaves the floor going over a hub edge: v^2 / d > g_eff."""
    m, _ = mass_props(cfg); W = m * G
    geff = (W - k * W * math.cos(math.radians(tilt_deg))) / m
    d = np.mean([math.hypot(f['H'], f['apothem']) for f in FACES if f['sides'] == 6]) / 1000
    return math.sqrt(max(geff, 0) * d)


# ---------------------------------------------------------------- gimbal ring dynamics while rolling
def euler_zxy(Mx):
    """Mx = Rz(psi) Rx(phi) Ry(gamma); returns psi, phi, gamma."""
    phi = np.arcsin(np.clip(Mx[..., 2, 1], -1, 1))
    gamma = np.arctan2(-Mx[..., 2, 0], Mx[..., 2, 2])
    psi = np.arctan2(-Mx[..., 0, 1], Mx[..., 1, 1])
    return psi, phi, gamma


def Rx(a):
    c, s = np.cos(a), np.sin(a); o, l = np.zeros_like(a), np.ones_like(a)
    return np.stack([np.stack([l, o, o], -1), np.stack([o, c, -s], -1), np.stack([o, s, c], -1)], -2)


def Rz(a):
    c, s = np.cos(a), np.sin(a); o, l = np.zeros_like(a), np.ones_like(a)
    return np.stack([np.stack([c, -s, o], -1), np.stack([s, c, o], -1), np.stack([o, o, l], -1)], -2)


def gimbal_rolling(speed=1.0, cases=400, seed=1, dt=2e-4):
    rng = np.random.default_rng(seed)
    m_o, R_o, m_i, R_i = 0.0165, 0.0965, 0.0148, 0.0865
    Io_b = m_o * R_o ** 2 * np.diag([0.5, 1.0, 0.5])      # outer ring in its XZ plane
    Ii_b = m_i * R_i ** 2 * np.diag([0.5, 0.5, 1.0])      # inner ring in its XY plane
    r_roll = np.mean([f['H'] for f in FACES]) / 1000
    w = speed / r_roll
    n = int(round(2 * math.pi / w / dt))
    tt = np.arange(n) * dt
    peaks, rates, near80, near85, closest, medians, kicks = [], [], [], [], [], [], []
    for _ in range(cases):
        qv = rng.normal(size=4); qv /= np.linalg.norm(qv)
        a_, b_, c_, d_ = qv
        R0 = np.array([[a_*a_+b_*b_-c_*c_-d_*d_, 2*(b_*c_-a_*d_), 2*(b_*d_+a_*c_)],
                       [2*(b_*c_+a_*d_), a_*a_-b_*b_+c_*c_-d_*d_, 2*(c_*d_-a_*b_)],
                       [2*(b_*d_-a_*c_), 2*(c_*d_+a_*b_), a_*a_-b_*b_-c_*c_+d_*d_]])
        h = rng.uniform(0, 2 * math.pi)
        axis = np.cross(Z, [math.cos(h), math.sin(h), 0])
        K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
        ang = w * tt
        Rroll = np.eye(3) + np.sin(ang)[:, None, None] * K + (1 - np.cos(ang))[:, None, None] * (K @ K)
        Rc = Rroll @ R0
        psi, phi, gam = euler_zxy(np.transpose(Rc, (0, 2, 1)))
        psi, gam = np.unwrap(psi), np.unwrap(gam)
        Rout = Rc @ Rz(psi); Rin = Rout @ Rx(phi)
        wc = np.broadcast_to(w * axis, (n, 3))
        psid, phid = np.gradient(psi, dt), np.gradient(phi, dt)
        gamd = np.gradient(gam, dt)
        wo = wc + psid[:, None] * Rc[:, :, 2]
        wi = wo + phid[:, None] * Rout[:, :, 0]
        ao, ai = np.gradient(wo, dt, axis=0), np.gradient(wi, dt, axis=0)
        Iow = Rout @ Io_b @ np.transpose(Rout, (0, 2, 1)); Iiw = Rin @ Ii_b @ np.transpose(Rin, (0, 2, 1))
        dLo = np.einsum('nij,nj->ni', Iow, ao) + np.cross(wo, np.einsum('nij,nj->ni', Iow, wo))
        dLi = np.einsum('nij,nj->ni', Iiw, ai) + np.cross(wi, np.einsum('nij,nj->ni', Iiw, wi))
        B1 = Rc[:, :, :2]                          # cage -> outer: free about cage Z
        B2 = Rout[:, :, 1:]                        # outer -> inner: free about outer X
        B3 = Rin[:, :, [0, 2]]                     # inner -> aircraft: free about inner Y
        A = np.zeros((n, 6, 6))
        A[:, :3, 0:2], A[:, :3, 2:4] = B1, -B2
        A[:, 3:, 2:4], A[:, 3:, 4:6] = B2, -B3
        sol = np.einsum('nij,nj->ni', np.linalg.pinv(A), np.concatenate([dLo, dLi], 1))
        tau_a = np.einsum('nij,nj->ni', B3, sol[:, 4:6])
        mag = np.linalg.norm(tau_a, axis=1)[5:-5] * 1000
        win = int(0.04 / dt)
        cum = np.cumsum(tau_a[5:-5] * dt, axis=0)
        jw = np.linalg.norm(cum[win:] - cum[:-win], axis=1).max() if len(cum) > win else np.linalg.norm(cum[-1])
        kicks.append(math.degrees(jw / I_AIRCRAFT))
        peaks.append(mag.max()); closest.append(90 - np.degrees(np.abs(phi)).max()); medians.append(np.median(mag))
        rates.append(max(np.abs(psid[5:-5]).max(), np.abs(gamd[5:-5]).max()) / w)
        near80.append(np.mean(np.abs(phi) > math.radians(80))); near85.append(np.mean(np.abs(phi) > math.radians(85)))
    pk = np.array(peaks)
    return {'speed_ms': speed, 'cage_rate_rad_s': w, 'cases': cases,
            'aircraft_torque_typical_nmm': float(np.median(medians)),
            'aircraft_torque_peak_nmm': {'median': float(np.median(pk)), 'p25': float(np.percentile(pk, 25)), 'p75': float(np.percentile(pk, 75))},
            'fraction_runs_peak_over': {str(a): float(np.mean(pk > a)) for a in (25, 48, 100, 500)},
            'aircraft_rate_kick_deg_s_40ms': {'median': float(np.median(kicks)), 'p75': float(np.percentile(kicks, 75)),
                                              'p90': float(np.percentile(kicks, 90)), 'fraction_over_100': float(np.mean(np.array(kicks) > 100))},
            'ring_rate_over_cage_rate': {'median': float(np.median(rates)), 'p90': float(np.percentile(rates, 90)), 'max': float(np.max(rates))},
            'time_fraction_middle_axis_beyond_80deg': float(np.mean(near80)),
            'time_fraction_beyond_85deg': float(np.mean(near85)),
            'closest_approach_to_lock_deg': {'median': float(np.median(closest)), 'p10': float(np.percentile(closest, 10))}}


# ---------------------------------------------------------------- main
def fmt(t):
    return 'n/a' if t is None else f'{t[0]:.0f}-{t[1]:.0f} %'


def main():
    out = {}
    tilts = (20, 30, 45)
    print('== Rolling from rest on a hexagon (P1B), straight-line push; floor mu 0.45; 6 headings per row ==')
    print('   k = thrust / all-up weight. Outcomes per heading: R = keeps rolling, S = stuck, H = hops (floor reaction reaches zero), K = skids (friction demand > mu).')
    runs = {}
    headings = (0, 17, 34, 51, 68, 85)

    def row_for(cfg, k, tilt, mu=MU_DEFAULT):
        m_g = IN['mass_g'][cfg]
        res = [simulate(cfg, k, tilt, hd, mu=mu) for hd in headings]
        code = {'running': 'R', 'stuck': 'S', 'rocks back (stuck)': 'S', 'hops': 'H', 'skids': 'K'}
        outcome = ''.join(code[r['status']] for r in res)
        rolled = [r for r in res if r['status'] == 'running' and r['steps']]
        ev = [r['hop'] or r['skid'] for r in res if r['hop'] or r['skid']]
        row = {'k': k, 'tilt': tilt, 'mu': mu, 'thrust_g': k * m_g, 'throttle': thrust_g_to_throttle(k * m_g), 'outcomes': outcome}
        if rolled:
            row.update(speed_ms=[min(r['avg_speed_late_ms'] for r in rolled), max(r['avg_speed_late_ms'] for r in rolled)],
                       energy_lost_per_step=float(np.mean([r['mean_energy_lost_frac'] for r in rolled])),
                       jolt_ms=float(np.mean([r['mean_jolt_ms'] for r in rolled])),
                       drift_deg=float(np.mean([abs(r['heading_drift_deg']) for r in rolled])),
                       step_mm=float(np.mean([r['mean_step_mm'] for r in rolled])),
                       steps_per_s=float(np.mean([len(r['steps']) / r['time_s'] for r in rolled])))
        if ev:
            row.update(event_after_s=float(np.mean([e['t_s'] for e in ev])), event_speed_ms=float(np.mean([e['speed_ms'] for e in ev])),
                       event_distance_m=float(np.mean([e['distance_m'] for e in ev])))
        return row

    def describe(row):
        d = f"{row['outcomes']}"
        if 'speed_ms' in row:
            d += f"  rolls {row['speed_ms'][0]:.2f}-{row['speed_ms'][1]:.2f} m/s, {row['steps_per_s']:.1f} faces/s, step {row['step_mm']:.0f} mm, loss {row['energy_lost_per_step']*100:.0f} %/step, jolt {row['jolt_ms']*100:.0f} cm/s, wander {row['drift_deg']:.0f} deg"
        if 'event_after_s' in row:
            d += f"  | H/K after {row['event_after_s']:.2f} s, {row['event_distance_m']*100:.0f} cm, at {row['event_speed_ms']:.2f} m/s"
        return d

    for cfg in ('P1B + 450', 'P1B + 1100'):
        m_g = IN['mass_g'][cfg]; runs[cfg] = {}
        print(f'  {cfg} ({m_g:.1f} g)')
        for tilt in tilts:
            lift = 1 / math.cos(math.radians(tilt))
            for k in [x for x in (0.4, 0.45, 0.5, 0.55, 0.6, 0.7, 0.8, 0.9, 1.0) if x < lift * 0.97]:
                row = row_for(cfg, k, tilt)
                runs[cfg][f'tilt{tilt}_k{k}'] = row
                print(f"    tilt {tilt:2d}  k {k:.2f} ({k*m_g:4.0f} g, throttle {fmt(row['throttle'])}): {describe(row)}")
    print('  Floor friction sensitivity (P1B + 450, tilt 30):')
    for mu in (0.3, 0.6):
        for k in (0.5, 0.55, 0.6, 0.7):
            row = row_for('P1B + 450', k, 30, mu)
            runs['P1B + 450'][f'mu{mu}_tilt30_k{k}'] = row
            print(f"    mu {mu}  k {k:.2f}: {describe(row)}")
    out['runs'] = runs

    print('\n== Skid/tumble regime: net push once sliding = T sin(tilt) - mu_k (W - T cos(tilt)); mu_k = 0.8 x mu ==')
    skid = {}
    for cfg in ('P1B + 450', 'P1B + 1100'):
        m = IN['mass_g'][cfg] / 1000; W = m * G; kd = 0.5 * RHO * cda(cfg); skid[cfg] = {}
        for tilt in (20, 30, 45):
            th = math.radians(tilt); cells = []
            for k in (0.5, 0.6, 0.7, 0.8):
                if k * math.cos(th) >= 0.97: continue
                net = k * W * math.sin(th) - 0.8 * MU_DEFAULT * (W - k * W * math.cos(th))
                vt = math.sqrt(net / kd) if net > 0 else 0
                skid[cfg][f'{tilt}_{k}'] = {'net_n': net, 'accel_ms2': net / m, 'drag_limited_speed_ms': vt}
                cells.append(f"k {k}: {'decelerates' if net <= 0 else f'+{net/m:.1f} m/s^2, drag-limited {vt:.1f} m/s'}")
            print(f'  {cfg} tilt {tilt}: ' + ' | '.join(cells))
    out['skid_regime'] = skid

    print('\n== Hop (bounce) onset speed: v^2/d = g_eff, d = centre-to-pivot distance ==')
    hop = {}
    for cfg in ('P1B + 450', 'P1B + 1100'):
        hop[cfg] = {f'{k}@{t}': hop_speed(cfg, k, t) for t in (0, 30, 45) for k in (0.0, 0.5, 0.75) if k * math.cos(math.radians(t)) < 1}
        print(f'  {cfg}: ' + '  '.join(f'k {k} tilt {t}: {v:.2f} m/s' for (kt, v) in hop[cfg].items() for k, t in [kt.split('@')]))
    out['hop_speed_ms'] = hop

    print('\n== Coasting with motors at idle (k = 0) from a push ==')
    coast = {}
    for v0 in (0.3, 0.5, 0.8):
        res = [simulate('P1B + 450', 0.0, 0, hd, v0=v0) for hd in (0, 30, 60)]
        coast[v0] = {'distance_m': float(np.mean([r['distance_m'] for r in res])), 'steps': float(np.mean([len(r['steps']) for r in res])),
                     'time_s': float(np.mean([r['time_s'] for r in res])), 'hopped': any(r['hop'] for r in res)}
        print(f"  start {v0} m/s: stops after ~{coast[v0]['distance_m']*100:.0f} cm, {coast[v0]['steps']:.1f} faces, {coast[v0]['time_s']:.2f} s" + (' (hops)' if coast[v0]['hopped'] else ''))
    out['coast'] = coast

    print('\n== Slopes (start from rest, worst face/direction, P1B + 1100) ==')
    alpha = max(f['alpha_max'] for f in FACES if f['sides'] in (5, 6))
    a_r = math.radians(alpha)
    slopes = {}
    print(f'  With motors off it stays parked on slopes up to ~{min(f["alpha_min"] for f in FACES if f["sides"] in (5,6)):.0f}-{alpha:.0f} deg (by face and direction).')
    for k in (0.5, 0.75, 1.0):
        best = (0, None)
        for tilt in range(0, 86):
            th = math.radians(tilt)
            lo, hi = 0.0, math.radians(60)
            for _ in range(40):
                s = (lo + hi) / 2
                Ft = k * math.sin(th + s) - math.sin(s); N = math.cos(s) - k * math.cos(th + s)
                (lo, hi) = (s, hi) if N > 0.3 and Ft / N >= math.tan(a_r) else (lo, s)
            if lo > best[0]: best = (lo, tilt)
        slopes[k] = {'max_slope_deg': math.degrees(best[0]), 'at_tilt_deg': best[1], 'throttle': thrust_g_to_throttle(k * IN['mass_g']['P1B + 1100'])}
        print(f"  thrust {k:.2f} W (throttle {fmt(slopes[k]['throttle'])}): rolls up slopes to ~{slopes[k]['max_slope_deg']:.0f} deg (tilt {best[1]} deg, keeping >= 30 % of weight on the floor)")
    out['slopes'] = slopes

    print('\n== Steps and door sills (sphere approximation, contact radius 120-124 mm) ==')
    steps = {}
    for hmm in (5, 10, 20, 30, 50):
        row = {}
        for Rr in (0.120, 0.124):
            hgt = hmm / 1000
            beta = math.degrees(math.acos((Rr - hgt) / Rr))
            row[Rr] = {'beta_deg': beta, 'k_at_45': M.start_fraction(beta, 45), 'k_best': math.sin(math.radians(beta))}
        steps[hmm] = row
        b = row[0.124]
        print(f"  {hmm:2d} mm step: lean angle {b['beta_deg']:.0f} deg; thrust needed from rest {b['k_at_45']*100:.0f} % W at 45 deg tilt "
              f"(min {b['k_best']*100:.0f} % W at {90-b['beta_deg']:.0f} deg tilt) -> throttle {fmt(thrust_g_to_throttle(b['k_at_45']*IN['mass_g']['P1B + 1100']))} (1100, 45 deg)")
    out['steps'] = steps

    print('\n== Turning while rolling (P1B + 450, all horizontal thrust used sideways, k cos(tilt) kept at 0.7 W) ==')
    m, Ic = mass_props('P1B + 450'); m_eff = m + Ic / R_V ** 2
    turns = {}
    for tilt in (30, 45):
        k = 0.7 / math.cos(math.radians(tilt))
        Fh = k * m * G * math.sin(math.radians(tilt))
        turns[tilt] = {v: m_eff * v * v / Fh for v in (0.3, 0.5, 1.0)}
        print(f'  tilt {tilt}: ' + '  '.join(f'{v} m/s -> radius {r*100:.0f} cm' for v, r in turns[tilt].items()))
    out['turning'] = {'effective_mass_kg': m_eff, 'radius_m': turns}

    print('\n== Rolling power vs hover (momentum theory, same efficiencies) ==')
    power = {}
    for k in (0.3, 0.5, 0.7):
        power[k] = k ** 1.5
        print(f'  thrust {k} W: ~{k**1.5*100:.0f} % of hover power -> ~{1/k**1.5:.1f}x hover endurance (ground effect would help further)')
    out['power_fraction'] = power

    print('\n== Gimbal rings while the cage rolls (random cage orientation and direction, smooth rolling) ==')
    gim = {}
    for v in (0.3, 0.5, 1.0):
        g = gimbal_rolling(v)
        gim[v] = g
        tq = g['aircraft_torque_peak_nmm']
        fr = g['fraction_runs_peak_over']
        print(f"  {v} m/s (cage {g['cage_rate_rad_s']:.1f} rad/s): torque on aircraft typical {g['aircraft_torque_typical_nmm']:.1f} N*mm; per-revolution peak median {tq['median']:.0f} (IQR {tq['p25']:.0f}-{tq['p75']:.0f}); "
              f"revolutions exceeding 25/48/100/500 N*mm: {fr['25']*100:.0f}/{fr['48']*100:.0f}/{fr['100']*100:.0f}/{fr['500']*100:.0f} %; "
              f"uncorrected rate kick per revolution (40 ms) median {g['aircraft_rate_kick_deg_s_40ms']['median']:.0f} deg/s, 75th {g['aircraft_rate_kick_deg_s_40ms']['p75']:.0f}, 90th {g['aircraft_rate_kick_deg_s_40ms']['p90']:.0f}; "
              f"ring rate up to {g['ring_rate_over_cage_rate']['median']:.1f}x cage rate (90th pct {g['ring_rate_over_cage_rate']['p90']:.1f}x); "
              f"middle axis beyond 80 deg {g['time_fraction_middle_axis_beyond_80deg']*100:.0f} % of the time")
    out['gimbal'] = gim

    def clean(o):
        if isinstance(o, dict): return {str(k): clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)): return [clean(v) for v in o]
        if isinstance(o, (np.floating, np.integer)): return float(o)
        return o
    (HERE / 'rolling_physics.json').write_text(json.dumps(clean(out), indent=1) + '\n')


if __name__ == '__main__':
    main()
