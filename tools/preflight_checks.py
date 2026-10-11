"""GO / NO-GO preflight checklist from FC (MSP) and Pi readbacks. Pure functions; no I/O."""

BOX_ARM, BOX_ANGLE = 0, 1
MANUAL = [
    'Props on the right motors: M1/M4 CW props, M2/M3 CCW props (leading edge leads)',
    'Nose = M2/M4 side; FC arrow points there; 3D model in Betaflight tilts the same way as the drone',
    'Failsafe tested props-off: armed, radio off -> motors stop',
    'Cage/gimbal clear of all four prop disks through full rotation',
    'Pilot-only first hover: USB unplugged, ESP32 trainer off (SD up), clear area',
]


def check(name, status, detail):
    return {'name': name, 'status': status, 'detail': detail}


def fc_checks(fc):
    """fc: dict from the dashboard worker (see motor_dashboard.Controller.read_preflight)."""
    out = []
    fw = fc.get('firmware')
    out.append(check('Betaflight firmware', 'ok' if fw == [4, 4, 2] else 'warn', f"{'.'.join(map(str, fw or []))}"))
    v = fc.get('voltage') or 0
    if v < 5:
        out.append(check('Battery', 'fail', f'{v:.2f} V: battery not connected (USB only)'))
    elif v < 7.0:
        out.append(check('Battery', 'fail', f'{v:.2f} V: too low to fly, charge it'))
    elif v < 7.9:
        out.append(check('Battery', 'warn', f'{v:.2f} V: usable, but charge to 8.4 V before flight tests'))
    else:
        out.append(check('Battery', 'ok', f'{v:.2f} V'))
    blocked = [f for f in fc.get('arming_blocked', []) if f != 'MSP']
    link_lost = {'RXLOSS', 'FAILSAFE', 'BADRX'} & set(blocked)
    out.append(check('Radio link (ELRS)', 'fail' if link_lost else 'ok',
                     'no signal: Pocket on? same model?' if link_lost else 'receiving the Pocket'))
    ranges = fc.get('mode_ranges', [])
    arm = [r for r in ranges if r[0] == BOX_ARM]
    out.append(check('ARM switch', 'ok' if arm else 'fail',
                     f"AUX{arm[0][1] + 1} {arm[0][2]}-{arm[0][3]} (SA)" if arm else 'no ARM range configured'))
    angle = [r for r in ranges if r[0] == BOX_ANGLE]
    full = any(r[2] <= 900 and r[3] >= 2100 for r in angle)
    out.append(check('ANGLE (self-level) mode', 'ok' if full else 'warn' if angle else 'fail',
                     'always on' if full else f'on a switch: {angle}' if angle else
                     'PARKED: enable once mounted: CLI aux 1 1 0 900 2100 0 0, save'))
    limit = fc.get('level_limit')
    if limit is not None:
        out.append(check('Max tilt (Angle)', 'ok' if limit <= 45 else 'warn', f'{limit} deg'))
    align = fc.get('board_alignment')
    if align is not None:
        out.append(check('Board alignment', 'manual', f'roll/pitch/yaw {align}: confirm the 3D model matches the drone'))
    rc = fc.get('rc') or []
    if len(rc) > 4 and not link_lost:
        out.append(check('Throttle at minimum', 'ok' if rc[3] < 1050 else 'warn', f'{rc[3]} (needs < 1050 to arm)'))
        out.append(check('ARM switch off', 'ok' if rc[4] < 1800 else 'warn', f'AUX1 {rc[4]}'))
    other = [f for f in blocked if f not in ('RXLOSS', 'FAILSAFE', 'BADRX', 'THROTTLE', 'ARMSWITCH')]
    out.append(check('Other arming blockers', 'ok' if not other else 'warn',
                     ', '.join(other) + (' (ANGLE = board tilted >25 deg)' if 'ANGLE' in other else '')
                     if other else 'none'))
    fs = fc.get('failsafe')
    if fs:
        out.append(check('Failsafe', 'ok' if fs['procedure'] == 'DROP' and fs['delay_s'] <= 2 else 'warn',
                         f"{fs['procedure']} after {fs['delay_s']:.1f} s of signal loss"))
    vtx = fc.get('vtx')
    if vtx:
        out.append(check('Video transmitter', 'warn' if vtx['pit'] else 'ok',
                         f"{vtx['freq']} MHz" + (' - PIT MODE (video off)' if vtx['pit'] else '')))
    cfg = fc.get('config') or {}
    if cfg:
        out.append(check('Motor protocol', 'ok' if cfg.get('motor_protocol') == 'DSHOT300' else 'warn',
                         f"{cfg.get('motor_protocol')}, idle {cfg.get('dshot_idle_value', 0) / 100:.1f} %"))
    return out


def pi_checks(pi):
    """pi: {'fpv': status dict or None, 'track': /api/state dict or None, 'error': str}."""
    fpv, track = pi.get('fpv'), pi.get('track')
    if track and track.get('source', {}).get('kind') == 'camera':
        bridge = track.get('bridge', '')
        return [check('Pi', 'ok', f"TRACK mode ({track['settings']['target_mode']}), {track['state']}"),
                check('Pi bridge', 'ok' if 'MOCK' not in bridge else 'warn', bridge),
                check('Pi video', 'fail' if track.get('fault') else 'ok', track.get('fault') or 'live camera')]
    if fpv:
        sig = fpv.get('signal')
        return [check('Pi', 'ok', 'FPV mode (viewer)'),
                check('Pi video', 'ok' if sig == 'PICTURE' else 'warn', f"{sig}" + (f" - {fpv['note']}" if fpv.get('note') else ''))]
    return [check('Pi', 'warn', pi.get('error') or 'unreachable (not needed for a pilot-only hover)')]


def summary(checks):
    statuses = {c['status'] for c in checks}
    return 'NO-GO' if 'fail' in statuses else 'CHECK' if 'warn' in statuses else 'GO'
