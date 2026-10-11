#!/usr/bin/env python3
"""Direct-USB bench helper for the known Betaflight 4.4.2 FC.

No browser automation and no installation step. Uses existing pyserial.
Importing this module does not open USB or move a motor. See the dated handoff.
Output readbacks are commands, not measured RPM or proof of physical rotation.

Motor test values map to DShot throttle as Betaflight 4.4 does it:
    1000 = DShot stop; 1001..2000 -> DShot 48..2047 (0..100 %).
So 1020 is only ~2 % throttle, far below the armed idle (dshot_idle_value
1000 = 10 %, i.e. motor-test value ~1100). Small BLHeli_S motors without a
prop commonly lose sync and restart at ~2 %. Use `pulse --value 1100` to test
at the same throttle the motor actually sees when armed at idle.

Subcommands:
  status    read-only firmware, voltage, RC and motor command readbacks
  config    read-only motor protocol / idle / pole settings
  stop      block normal arming and send all outputs to stop
  direction store one ESC's spin direction (normal/reversed) via DShot cmds
  esc-info  read-only ESC firmware + settings via BLHeli 4-way passthrough
            (needs battery; the FC must be power-cycled or re-plugged after)
  pulse     PHYSICAL ACTION: spin one motor, props removed
"""

import argparse
import json
import signal
import struct
import sys
import threading
import time

import serial


DEFAULT_PORT = '/dev/serial/by-id/usb-Betaflight_Betaflight_STM32F411_0x8000000-if00'
STOP = struct.pack('<8H', *([1000] * 8))
MAX_PULSE_VALUE = 1150   # ~15 % DShot throttle; props-off diagnostic ceiling
ARMING_DISABLE_NAMES = [   # Betaflight 4.4 runtime_config.h order
    'NOGYRO', 'FAILSAFE', 'RXLOSS', 'BADRX', 'BOXFAILSAFE', 'RUNAWAY', 'CRASH',
    'THROTTLE', 'ANGLE', 'BOOTGRACE', 'NOPREARM', 'LOAD', 'CALIB', 'CLI', 'CMS',
    'BST', 'MSP', 'PARALYZE', 'GPS', 'RESCUE_SW', 'RPMFILTER', 'REBOOT_REQD',
    'DSHOT_BBANG', 'NO_ACC_CAL', 'MOTOR_PROTO', 'ARMSWITCH']
MOTOR_PROTOCOLS = ['PWM', 'ONESHOT125', 'ONESHOT42', 'MULTISHOT', 'BRUSHED',
                   'DSHOT150', 'DSHOT300', 'DSHOT600', 'PROSHOT1000', 'DISABLED']


def report(**fields):
    print(json.dumps(fields), flush=True)


def dshot_percent(value):
    """Betaflight 4.4 dshotConvertFromExternal, expressed as throttle %."""
    if value <= 1000:
        return 0.0
    dshot = 48 + (min(value, 2000) - 1001) * (2047 - 48) / (2000 - 1001)
    return round((dshot - 48) / (2047 - 48) * 100, 1)


class FC:
    def __init__(self, port):
        self.ser = serial.Serial(port, 115200, timeout=0.02,
                                 write_timeout=0.1, exclusive=True)
        self.buf = bytearray()
        self.write_lock = threading.Lock()
        self.ser.reset_input_buffer()

    def write(self, command, payload=b''):
        body = bytes([len(payload), command]) + payload
        checksum = 0
        for value in body:
            checksum ^= value
        frame = b'$M<' + body + bytes([checksum])
        with self.write_lock:
            if self.ser.write(frame) != len(frame):
                raise IOError('Incomplete serial write')

    def request(self, command, payload=b'', timeout=0.4):
        self.write(command, payload)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.buf.extend(self.ser.read(self.ser.in_waiting or 1))
            while True:
                pos = self.buf.find(b'$M')
                if pos < 0:
                    if len(self.buf) > 2:
                        del self.buf[:-2]
                    break
                if pos:
                    del self.buf[:pos]
                if len(self.buf) < 6:
                    break
                if self.buf[2] not in (ord('>'), ord('!')):
                    del self.buf[0]
                    continue
                length = self.buf[3] + 6
                if len(self.buf) < length:
                    break
                frame = bytes(self.buf[:length])
                del self.buf[:length]
                checksum = 0
                for value in frame[3:-1]:
                    checksum ^= value
                if checksum != frame[-1] or frame[4] != command:
                    continue
                if frame[2] == ord('!'):
                    raise RuntimeError(f'MSP {command} rejected')
                return frame[5:-1]
        raise TimeoutError(f'MSP {command} reply timeout')

    def motors(self):
        data = self.request(104)
        if len(data) < 8 or len(data) % 2:
            raise RuntimeError('Invalid motor reply')
        return list(struct.unpack('<' + 'H' * (len(data) // 2), data))[:4]

    def voltage(self):
        analog = self.request(110)
        if len(analog) < 9:
            raise RuntimeError('Missing full voltage reply')
        return struct.unpack_from('<H', analog, 7)[0] / 100

    def status(self):
        version = list(self.request(3))
        api = list(self.request(1))
        volts = self.voltage()
        data = self.request(105)
        if len(data) < 10 or len(data) % 2:
            raise RuntimeError('Missing RC channels')
        rc = list(struct.unpack('<' + 'H' * (len(data) // 2), data))
        status = self.request(101)
        ids = list(self.request(119))
        if len(status) < 10 or 0 not in ids:
            raise RuntimeError('Cannot determine ARM status')
        flags = struct.unpack_from('<I', status, 6)[0]
        armed = bool(flags & (1 << ids.index(0)))
        return dict(firmware=version, api=api, voltage=volts,
                    rc=rc[:8], armed=armed, motor_commands=self.motors(),
                    arming_blocked=self.arming_blocked())

    def arming_blocked(self):
        """Names of active Betaflight arming-disable flags (MSP_STATUS_EX)."""
        d = self.request(150)
        i = 16 + d[15]
        flags = struct.unpack_from('<I', d, i + 1)[0]
        return [name for bit, name in enumerate(ARMING_DISABLE_NAMES) if flags >> bit & 1]

    def config(self):
        mc = self.request(131)
        minthrottle, maxthrottle, mincommand = struct.unpack_from('<3H', mc, 0)
        out = dict(minthrottle=minthrottle, maxthrottle=maxthrottle,
                   mincommand=mincommand)
        if len(mc) >= 10:
            out.update(motor_count=mc[6], motor_poles=mc[7],
                       dshot_bidir=bool(mc[8]), esc_sensor=bool(mc[9]))
        ac = self.request(90)
        protocol = ac[3]
        out.update(motor_protocol=(MOTOR_PROTOCOLS[protocol]
                                   if protocol < len(MOTOR_PROTOCOLS) else protocol),
                   motor_pwm_rate=struct.unpack_from('<H', ac, 4)[0],
                   dshot_idle_value=struct.unpack_from('<H', ac, 6)[0])
        out['idle_equivalent_test_value'] = round(
            1001 + out['dshot_idle_value'] / 10000 * 999)
        return out

    def request_v2(self, command, payload=b'', timeout=1.5):
        """MSPv2 request; returns the reply payload."""
        body = struct.pack('<BHH', 0, command, len(payload)) + payload
        with self.write_lock:
            self.ser.write(b'$X<' + body + bytes([crc8_dvb_s2(body)]))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.buf.extend(self.ser.read(self.ser.in_waiting or 1))
            while True:
                pos = self.buf.find(b'$X')
                if pos < 0:
                    if len(self.buf) > 2:
                        del self.buf[:-2]
                    break
                if pos:
                    del self.buf[:pos]
                if len(self.buf) < 9:
                    break
                if self.buf[2] not in (ord('>'), ord('!')):
                    del self.buf[0]
                    continue
                size = struct.unpack_from('<H', self.buf, 6)[0]
                total = 8 + size + 1
                if len(self.buf) < total:
                    break
                frame = bytes(self.buf[:total])
                del self.buf[:total]
                if crc8_dvb_s2(frame[3:-1]) != frame[-1]:
                    continue
                if struct.unpack_from('<H', frame, 4)[0] != command:
                    continue
                if frame[2] == ord('!'):
                    raise RuntimeError(f'MSPv2 0x{command:04X} rejected')
                return frame[8:-1]
        raise TimeoutError(f'MSPv2 0x{command:04X} reply timeout')

    def vtx(self):
        """Video transmitter state from MSP_VTX_CONFIG."""
        d = self.request(88)
        return dict(type=d[0], band=d[1], channel=d[2], power=d[3], pit=bool(d[4]),
                    freq=struct.unpack_from('<H', d, 5)[0], ready=bool(d[7]))

    def set_vtx_pit(self, pit):
        """Pit mode on/off (runtime only, not saved). Keeps band/channel/power."""
        v = self.vtx()
        chan = (v['band'] - 1) * 8 + (v['channel'] - 1) if v['band'] else v['freq']
        self.request(89, struct.pack('<HBB', chan, v['power'], 1 if pit else 0))
        deadline = time.monotonic() + 8   # SmartAudio applies asynchronously (~3-5 s)
        while time.monotonic() < deadline:
            time.sleep(0.5)
            v = self.vtx()
            if v['pit'] == pit:
                break
        return v

    def motor_rpm(self):
        """Real RPM per motor from MSP_MOTOR_TELEMETRY (needs bidirectional DShot on)."""
        d = self.request(139)
        count = d[0] if d else 0
        return [struct.unpack_from('<I', d, 1 + 13 * i)[0] for i in range(min(count, 4))
                if len(d) >= 1 + 13 * (i + 1)]

    def mode_ranges(self):
        """[(permanent_box_id, aux_index, start_us, end_us)] for configured (non-empty) ranges."""
        d = self.request(34)
        out = []
        for i in range(0, len(d) - 3, 4):
            box, aux, start, end = d[i:i + 4]
            if end > start:
                out.append((box, aux, 900 + 25 * start, 900 + 25 * end))
        return out

    def failsafe(self):
        d = self.request(75)
        return dict(delay_s=d[0] / 10, off_delay_s=d[1] / 10, throttle=struct.unpack_from('<H', d, 2)[0],
                    procedure=['DROP', 'LAND', 'GPS_RESCUE'][d[7]] if len(d) > 7 and d[7] < 3 else d[7:8])

    def board_alignment(self):
        return list(struct.unpack_from('<3h', self.request(38), 0))

    def level_limit(self):
        d = self.request(94)
        return d[18] if len(d) > 18 else None

    def set_direction(self, motor, reverse):
        """Store spin direction in one ESC via DShot commands (motors must be stopped).

        Sends DSHOT_CMD_SPIN_DIRECTION_1 (7, normal) or _2 (8, reversed), then
        DSHOT_CMD_SAVE_SETTINGS (12), as a blocking MSP2_SEND_DSHOT_COMMAND; Betaflight
        repeats each 10x. Physical direction also depends on wire order, so
        "normal" is not a fixed CW/CCW - check by eye afterwards.
        """
        if not 1 <= motor <= 4:
            raise ValueError('motor must be 1-4')
        self.stop()
        time.sleep(0.5)            # let the motor spin down; ESCs ignore commands while running
        if self.motors() != [1000] * 4:
            raise RuntimeError('Motors not stopped; direction not changed')
        self.request_v2(0x3003, bytes([1, motor - 1, 2, 8 if reverse else 7, 12]))

    def stop(self):
        errors = []
        for _ in range(3):
            try:
                self.write(214, STOP)
            except Exception as exc:
                errors.append(str(exc))
            time.sleep(0.025)
        if errors:
            report(stop_write_errors=errors,
                   action='If the motor is moving, disconnect the battery immediately')


def crc8_dvb_s2(data):
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ 0xD5) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


# --- BLHeli 4-way interface (read-only use) --------------------------------

def crc16_xmodem(data):
    crc = 0
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) if crc & 0x8000 else crc << 1
            crc &= 0xFFFF
    return crc


class FourWay:
    TEST_ALIVE, GET_PROTOCOL, GET_NAME, GET_IF_VERSION, EXIT = 0x30, 0x31, 0x32, 0x33, 0x34
    INIT_FLASH, READ = 0x37, 0x3A

    def __init__(self, ser):
        self.ser = ser

    def cmd(self, command, address=0, params=b'\x00', timeout=1.0):
        frame = bytes([0x2F, command, address >> 8, address & 0xFF,
                       len(params) & 0xFF]) + params
        crc = crc16_xmodem(frame)
        self.ser.reset_input_buffer()
        self.ser.write(frame + bytes([crc >> 8, crc & 0xFF]))
        buf = bytearray()
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            buf.extend(self.ser.read(self.ser.in_waiting or 1))
            start = buf.find(0x2E)
            if start < 0:
                buf.clear()
                continue
            del buf[:start]
            if len(buf) < 5:
                continue
            n = buf[4] or 256
            total = 5 + n + 3
            if len(buf) < total:
                continue
            resp = bytes(buf[:total])
            if crc16_xmodem(resp[:-2]) != (resp[-2] << 8 | resp[-1]):
                raise RuntimeError(f'4-way CRC error on cmd 0x{command:02X}')
            if resp[1] != command:
                raise RuntimeError(f'4-way reply for 0x{resp[1]:02X}, wanted 0x{command:02X}')
            ack = resp[5 + n]
            if ack != 0:
                raise RuntimeError(f'4-way cmd 0x{command:02X} NACK {ack}')
            return resp[5:5 + n]
        raise TimeoutError(f'4-way cmd 0x{command:02X} timeout')


BLHELI_S_FIELDS = [
    'main_revision', 'sub_revision', 'layout_revision', 'p_gain', 'i_gain',
    'governor_mode', 'low_voltage_limit', 'motor_gain', 'motor_idle',
    'startup_power', 'pwm_frequency', 'motor_direction', 'input_pwm_polarity',
    'mode_lo', 'mode_hi', 'programming_by_tx', 'rearm_at_start',
    'governor_setup_target', 'startup_rpm', 'startup_accel', 'volt_comp',
    'commutation_timing', 'damping_force', 'governor_range', 'startup_method',
    'ppm_min_throttle', 'ppm_max_throttle', 'beep_strength', 'beacon_strength',
    'beacon_delay', 'throttle_rate', 'demag_compensation', 'bec_voltage_high',
    'ppm_center_throttle', 'spoolup_time', 'temperature_protection',
    'low_rpm_power_protection', 'pwm_input', 'pwm_dither', 'brake_on_stop',
    'led_control',
]


def esc_info(fc, escs):
    count = fc.request(245, timeout=1.0)   # MSP_SET_PASSTHROUGH -> 4-way mode
    report(event='passthrough', esc_count=count[0] if count else None)
    fw = FourWay(fc.ser)
    results = []
    try:
        report(protocol=list(fw.cmd(FourWay.GET_PROTOCOL)),
               interface=fw.cmd(FourWay.GET_NAME).decode(errors='replace'))
        for esc in escs:
            try:
                info = fw.cmd(FourWay.INIT_FLASH, params=bytes([esc - 1]))
                sig = info[1] << 8 | info[0] if len(info) >= 2 else None
                mode = info[3] if len(info) >= 4 else None
                if mode not in (1, 2):   # SiLabs BLB / Atmel BLB: BLHeli_S layout
                    results.append(dict(esc=esc, signature=hex(sig or 0),
                                        interface_mode=mode,
                                        note='non-BLHeli_S layout; raw read skipped'))
                    continue
                raw = fw.cmd(FourWay.READ, address=0x1A00, params=b'\x70')
                fields = dict(zip(BLHELI_S_FIELDS, raw))
                text = lambda a, b: raw[a:b].decode('ascii', 'replace').strip('\x00\xff #')
                results.append(dict(
                    esc=esc, signature=hex(sig), interface_mode=mode,
                    layout=text(0x40, 0x50), mcu=text(0x50, 0x60),
                    name=text(0x60, 0x70),
                    firmware=f"{fields['main_revision']}.{fields['sub_revision']}",
                    settings=fields, raw=raw.hex()))
            except Exception as exc:
                results.append(dict(esc=esc, error=str(exc)))
    finally:
        try:
            fw.cmd(FourWay.EXIT)
        except Exception:
            pass
    for item in results:
        report(**item)
    report(note='4-way exited; unplug/replug FC USB (or power-cycle) before more MSP use')


# --- Pulse ------------------------------------------------------------------

def gate(state):
    if state['firmware'] != [4, 4, 2] or state['api'] != [0, 1, 45]:
        raise RuntimeError('Pulse helper is restricted to the inspected BF 4.4.2 / API 1.45')
    # Conservative diagnostic stop threshold; not a cell-balance or battery-health check.
    if not 6.8 <= state['voltage'] <= 8.45:
        raise RuntimeError(f"Battery voltage {state['voltage']} V outside 6.8–8.45 V "
                           '(is the battery plugged in?)')
    if state['armed'] or state['rc'][4] >= 1800:
        raise RuntimeError('FC must be disarmed and AUX1/SA off')
    if state['motor_commands'] != [1000] * 4:
        raise RuntimeError('Motor commands are not all stopped')


def pulse(fc, motor, seconds, value):
    gate(fc.status())
    desired = [1000] * 4
    desired[motor - 1] = value
    payload = struct.pack('<8H', *(desired + [1000] * 4))
    timer = threading.Timer(seconds + 0.15, fc.stop)
    start = time.monotonic()
    timer.start()
    min_v = 99.0
    try:
        fc.request(214, payload)
        report(event='pulse_started', motor=motor, value=value,
               dshot_throttle_pct=dshot_percent(value), seconds=seconds)
        while time.monotonic() - start < seconds:
            commands = fc.motors()
            voltage = fc.voltage()
            min_v = min(min_v, voltage)
            report(elapsed=round(time.monotonic() - start, 3),
                   motor_commands=commands, voltage=voltage)
            if commands != desired:
                raise RuntimeError('Motor command changed during pulse')
            if not 6.6 <= voltage <= 8.45:
                raise RuntimeError('Voltage crossed diagnostic stop threshold')
            time.sleep(min(0.2, max(0, seconds - (time.monotonic() - start))))
    finally:
        fc.stop()
        timer.cancel()
        timer.join()
    commands = fc.motors()
    report(event='pulse_finished', motor_commands=commands, min_voltage=min_v)
    if commands != [1000] * 4:
        raise RuntimeError('Stop readback failed; disconnect battery')


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--port', default=DEFAULT_PORT)
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('status', help='Read-only firmware, voltage, RC and command readbacks')
    sub.add_parser('config', help='Read-only motor protocol / idle settings')
    sub.add_parser('stop', help='Block normal arming and send all outputs to stop')
    d = sub.add_parser('direction', help='Store one ESC spin direction (normal/reversed)')
    d.add_argument('--motor', type=int, required=True, choices=[1, 2, 3, 4])
    d.add_argument('setting', choices=['normal', 'reversed'])
    e = sub.add_parser('esc-info', help='Read-only ESC firmware/settings via 4-way passthrough')
    e.add_argument('--escs', type=int, nargs='+', default=[1, 2, 3, 4])
    p = sub.add_parser('pulse', help='PHYSICAL ACTION: one motor; not an aircraft ARM')
    p.add_argument('--motor', type=int, default=1, choices=[1, 2, 3, 4])
    p.add_argument('--value', type=int, default=1100)
    p.add_argument('--seconds', type=float, nargs='+', required=True)
    p.add_argument('--props-removed', action='store_true', required=True,
                   help='Explicitly attest that all propellers are removed')
    args = parser.parse_args()
    if args.action == 'pulse':
        if not 1001 <= args.value <= MAX_PULSE_VALUE:
            parser.error(f'Props-off diagnostic limit is 1001–{MAX_PULSE_VALUE}')
        if len(args.seconds) > 3 or any(not 0 < n <= 10 for n in args.seconds):
            parser.error('Up to three finite durations in (0, 10] seconds only')

    fc = FC(args.port)
    mutating = args.action in ('stop', 'pulse', 'direction')

    def interrupted(signum, frame):
        raise KeyboardInterrupt(f'Signal {signum}')

    old_signals = {s: signal.signal(s, interrupted)
                   for s in (signal.SIGINT, signal.SIGTERM)}
    try:
        state = fc.status()
        report(**state)
        if args.action == 'status':
            return 0
        if args.action == 'direction':
            if state['armed']:
                raise RuntimeError('FC is armed')
            fc.request(99, b'\x01\x00')
            fc.set_direction(args.motor, args.setting == 'reversed')
            report(event='direction_saved', motor=args.motor, setting=args.setting,
                   note='spin it to check; replug battery if it did not change')
            return 0
        if args.action == 'config':
            report(**fc.config())
            return 0
        if args.action == 'esc-info':
            if state['voltage'] < 5.0:
                raise RuntimeError('ESCs need battery power for passthrough; plug in the battery')
            if state['armed']:
                raise RuntimeError('FC is armed')
            esc_info(fc, args.escs)
            return 0
        if args.action == 'pulse':
            gate(state)
        # Blocks normal arming. Second byte 0 retains runaway prevention.
        # Do not silently clear this temporary block when exiting.
        fc.request(99, b'\x01\x00')
        fc.stop()
        if args.action == 'pulse':
            for i, seconds in enumerate(args.seconds):
                if i:
                    time.sleep(1.5)
                pulse(fc, args.motor, seconds, args.value)
        return 0
    finally:
        try:
            if mutating:
                fc.stop()
                try:
                    commands = fc.motors()
                    report(event='final_stop', motor_commands=commands)
                    if commands != [1000] * 4:
                        raise RuntimeError('Stop unconfirmed; disconnect battery')
                except Exception:
                    print('STOP UNCONFIRMED: disconnect battery if motor is moving',
                          file=sys.stderr, flush=True)
                    raise
        finally:
            fc.ser.close()
            for sig, handler in old_signals.items():
                signal.signal(sig, handler)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (Exception, KeyboardInterrupt) as exc:
        print(f'Bench helper stopped: {exc}', file=sys.stderr, flush=True)
        sys.exit(1)
