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


# Opening an Arduino Mega's USB port resets the board; its bootloader ignores the first
# ~1.5 s of input. Repeat HELLO (same session) until READY rather than sending it once.
HELLO_RETRY_S = .5
# A bridge that reset or dropped the session silently ignores CMDs. After this long with
# commands unanswered, start a new session handshake; the board comes back neutral.
RESYNC_S = 1.0


class SerialBridge:
    transport = 'USB SERIAL / internal command state only'
    physical_output = False
    def __init__(self, device, watchdog_ms=250):
        self.serial = serial.Serial(device, 115200, timeout=0, write_timeout=.02)
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
        self.transport = 'USB SERIAL / internal command state only'
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
            if f[0] == 'READY' and f[3] == 'NO_OUTPUT' and not self.ready:
                self.ready = True
                self.last_ack = now
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
