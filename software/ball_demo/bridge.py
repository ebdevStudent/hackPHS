import time
import uuid

import serial

from .protocol import BridgeCore, MAX_FRAME, parse, deadline_reached


class MockBridge:
    transport = 'MOCK / no physical output'
    ready = True
    def __init__(self, watchdog_ms=250):
        self.core = BridgeCore(watchdog_ms)
        self.session = uuid.uuid4().hex
        self.core.receive(f'HELLO 1 {self.session}\n', time.monotonic())
        self.seq, self.last_ack, self.fault = 0, time.monotonic(), 'none'
        self.accepted_yaw = 0
        self.pending = []
    def send(self, enabled, yaw, now):
        self.seq += 1
        self.core.tick(now)
        if self.fault == 'disconnect': return
        response = self.core.receive(f'CMD 1 {self.session} {self.seq} {int(enabled)} {yaw}\n', now)
        if self.fault == 'missing_ack': return
        delay = .4 if self.fault == 'delayed_ack' else 0
        if response: self.pending.append((now + delay, now, response))
    def poll(self, now):
        self.core.tick(now)
        acknowledgements = []
        while self.pending and self.pending[0][0] <= now:
            _, sent_at, line = self.pending.pop(0)
            f = parse(line)
            if f[6] == 'NONE' and not deadline_reached(now, sent_at):
                self.last_ack, self.accepted_yaw = now, int(f[5])
                acknowledgements.append({'seq': int(f[3]), 'yaw': int(f[5]), 'fault': f[6]})
        return acknowledgements
    def close(self):
        self.send(False, 0, time.monotonic())


# Must match Serial.begin() in the ESP32-S3 bridge sketch. At 9600 one worst-case CMD or ACK
# (~55-60 ms on the wire) is longer than the 50 ms control period.
DEFAULT_BAUD = 115200
# Opening the board's USB-UART port can reset it (ESP32-S3 auto-reset via DTR/RTS) and input is
# ignored while it boots. Repeat HELLO (same session) until READY rather than sending it once.
HELLO_RETRY_S = .5
# A bridge that reset or dropped the session silently ignores CMDs. After this long with
# commands unanswered, start a new session handshake; the board comes back neutral.
RESYNC_S = 1.0
NO_OUTPUT_TRANSPORT = 'USB SERIAL / internal command state only'
# The ESP32-S3 sketch reports PPM_YAW only while its GPIO 5 arming jumper is fitted. Output is
# reported by the firmware, not physically verified (radio trainer mapping, override, failsafe).
TRAINER_TRANSPORT = 'ESP32-S3 USB SERIAL / PPM trainer yaw (CH4) reported, not physically verified'


class SerialBridge:
    transport = NO_OUTPUT_TRANSPORT
    physical_output = False
    def __init__(self, device, watchdog_ms=250, baud=DEFAULT_BAUD, trainer_output=False):
        """trainer_output: operator opt-in to accept a bridge whose READY reports PPM_YAW.
        Without it such a bridge is never treated as ready, so no CMD is sent to it."""
        # DTR/RTS drive the board's EN/BOOT auto-reset. Construct without a port, deassert both, then
        # open (same order as firmware/esp32/tools/esp_term.py) so opening does not reset the ESP32-S3.
        self.serial = serial.Serial(None, baud, timeout=0, write_timeout=.02)
        self.serial.dtr = False
        self.serial.rts = False
        self.serial.port = device
        self.serial.open()
        self.accepted_modes = ('NO_OUTPUT', 'PPM_YAW') if trainer_output else ('NO_OUTPUT',)
        self.session, self.seq, self.buffer = uuid.uuid4().hex, 0, bytearray()
        self.discarding = False
        self.ready = False
        self.physical_output = False
        self.last_acked_seq = 0
        self.last_ack, self.accepted_yaw = time.monotonic(), 0
        self.fault = 'none'
        self.outstanding = {}
        self.last_hello = self.handshake_started = time.monotonic()
        self.serial.write(f'HELLO 1 {self.session}\n'.encode())
    def resync(self, now):
        self.session, self.ready, self.outstanding = uuid.uuid4().hex, False, {}
        self.physical_output = False
        self.transport = NO_OUTPUT_TRANSPORT
        self.last_hello = self.handshake_started = now
        self.serial.write(f'HELLO 1 {self.session}\n'.encode())
    def send(self, enabled, yaw, now):
        if not self.ready: return
        self.seq += 1
        self.serial.write(f'CMD 1 {self.session} {self.seq} {int(enabled)} {yaw}\n'.encode())
        self.outstanding[self.seq] = (enabled, yaw, now)
        self.outstanding = {k: v for k, v in self.outstanding.items() if now - v[2] < 1}
    def poll(self, now):
        if not self.ready and now - self.last_hello >= HELLO_RETRY_S:
            self.last_hello = now
            self.serial.write(f'HELLO 1 {self.session}\n'.encode())
        responses = self.read(now)
        # Checked after reading so an ACK already waiting in the buffer still counts.
        if self.ready and self.outstanding and now - self.last_ack >= RESYNC_S:
            self.resync(now)
        return responses
    def read(self, now):
        self.buffer.extend(self.serial.read(min(self.serial.in_waiting, 4096)))
        responses = []
        if self.discarding:
            if b'\n' not in self.buffer:
                self.buffer.clear()
                return responses
            _, _, remaining = self.buffer.partition(b'\n')
            self.buffer = bytearray(remaining)
            self.discarding = False
        while b'\n' in self.buffer:
            line, _, remaining = self.buffer.partition(b'\n')
            self.buffer = bytearray(remaining)
            if len(line) > MAX_FRAME: continue
            try: f = parse(line.decode('ascii'))
            except (UnicodeDecodeError, ValueError): continue
            if f[2] != self.session: continue
            # The output mode is fixed per session: only the first accepted READY sets it.
            if f[0] == 'READY' and f[3] in self.accepted_modes and not self.ready:
                self.ready = True
                self.last_ack = now
                self.physical_output = f[3] == 'PPM_YAW'
                self.transport = TRAINER_TRANSPORT if self.physical_output else NO_OUTPUT_TRANSPORT
            if f[0] == 'ACK' and f[6] == 'NONE':
                seq = int(f[3])
                expected = self.outstanding.pop(seq, None)
                if (expected and seq > self.last_acked_seq and
                    (f[4] == '1', int(f[5])) == expected[:2] and not deadline_reached(now, expected[2])):
                    self.last_acked_seq = seq
                    self.last_ack, self.accepted_yaw = now, int(f[5])
                    responses.append({'seq': seq, 'yaw': int(f[5]), 'fault': f[6]})
        if len(self.buffer) > MAX_FRAME:
            self.buffer.clear()
            self.discarding = True
        return responses
    def close(self):
        try: self.send(False, 0, time.monotonic())
        finally: self.serial.close()
