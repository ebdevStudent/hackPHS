#!/usr/bin/env python3
"""Optional direct-USB bench helper for the known Betaflight 4.4.2 FC.

No browser automation and no installation step. Uses existing pyserial.
Importing this module does not open USB or move a motor. See the dated handoff.
Output readbacks are commands, not measured RPM or proof of physical rotation.
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


def report(**fields):
    print(json.dumps(fields), flush=True)


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

    def status(self):
        version = list(self.request(3))
        api = list(self.request(1))
        analog = self.request(110)
        if not analog:
            raise RuntimeError('Missing voltage reply')
        volts = (struct.unpack_from('<H', analog, 7)[0] / 100
                 if len(analog) >= 9 else analog[0] / 10)
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
                    rc=rc, armed=armed, motor_commands=self.motors())

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


def gate(state):
    if state['firmware'] != [4, 4, 2] or state['api'] != [0, 1, 45]:
        raise RuntimeError('Pulse helper is restricted to the inspected BF 4.4.2 / API 1.45')
    # Conservative diagnostic stop threshold; not a cell-balance or battery-health check.
    if not 6.8 <= state['voltage'] <= 8.4:
        raise RuntimeError('Battery voltage outside 6.8–8.4 V diagnostic range')
    if state['armed'] or state['rc'][4] >= 1800:
        raise RuntimeError('FC must be disarmed and AUX1/SA off')
    if state['motor_commands'] != [1000] * 4:
        raise RuntimeError('Motor commands are not all stopped')


def pulse(fc, seconds, value):
    gate(fc.status())
    desired = [value, 1000, 1000, 1000]
    payload = struct.pack('<8H', *(desired + [1000] * 4))
    timer = threading.Timer(seconds + 0.15, fc.stop)
    start = time.monotonic()
    timer.start()
    try:
        fc.request(214, payload)
        report(event='pulse_started', seconds=seconds, motor_commands=desired)
        while time.monotonic() - start < seconds:
            commands = fc.motors()
            analog = fc.request(110)
            if len(analog) < 9:
                raise RuntimeError('Missing full voltage reply during pulse')
            voltage = struct.unpack_from('<H', analog, 7)[0] / 100
            report(elapsed=round(time.monotonic() - start, 3),
                   motor_commands=commands, voltage=voltage)
            if commands != desired:
                raise RuntimeError('Motor command changed during pulse')
            if not 6.8 <= voltage <= 8.4:
                raise RuntimeError('Voltage crossed diagnostic stop threshold')
            time.sleep(min(0.2, max(0, seconds - (time.monotonic() - start))))
    finally:
        fc.stop()
        timer.cancel()
        timer.join()
    commands = fc.motors()
    report(event='pulse_finished', motor_commands=commands)
    if commands != [1000] * 4:
        raise RuntimeError('Stop readback failed; disconnect battery')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', default=DEFAULT_PORT)
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('status', help='Read-only firmware, voltage, RC and command readbacks')
    sub.add_parser('stop', help='Block normal arming and send all outputs to stop')
    p = sub.add_parser('pulse', help='PHYSICAL ACTION: Motor 1 only; not an aircraft ARM')
    p.add_argument('--value', type=int, default=1020)
    p.add_argument('--seconds', type=float, nargs='+', required=True)
    p.add_argument('--props-removed', action='store_true', required=True,
                   help='Explicitly attest that all propellers are removed')
    args = parser.parse_args()
    if args.action == 'pulse':
        if not 1001 <= args.value <= 1040:
            parser.error('This diagnostic helper limits Motor 1 to 1001–1040')
        if len(args.seconds) > 2 or any(not 0 < n <= 10 for n in args.seconds):
            parser.error('One or two finite durations in (0, 10] seconds only')

    fc = FC(args.port)
    mutating = args.action != 'status'

    def interrupted(signum, frame):
        raise KeyboardInterrupt(f'Signal {signum}')

    old_signals = {s: signal.signal(s, interrupted)
                   for s in (signal.SIGINT, signal.SIGTERM)}
    try:
        state = fc.status()
        report(**state)
        if args.action == 'status':
            return 0
        if args.action == 'pulse':
            gate(state)
        # Blocks normal arming. Second byte 0 retains runaway prevention.
        # Do not silently clear this temporary block when exiting.
        fc.request(99, b'\x01\x00')
        fc.stop()
        if args.action == 'pulse':
            for seconds in args.seconds:
                pulse(fc, seconds, args.value)
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
