import re
import math

VERSION = 1
MAX_FRAME = 128
SESSION = re.compile(r'^[A-Za-z0-9_-]{1,32}$')


def deadline_reached(now, sent, timeout_ms=250):
    # A one-nanosecond tolerance prevents binary floating-point subtraction
    # moving an exact millisecond deadline beyond the integer-clock C core.
    elapsed = (now - sent) * 1000
    return elapsed >= timeout_ms or math.isclose(elapsed, timeout_ms, rel_tol=0, abs_tol=1e-6)


def parse(line):
    if len(line.encode('ascii', errors='replace')) > MAX_FRAME or not line.isascii():
        raise ValueError('FRAME')
    fields = line.strip('\r\n').split(' ')
    kind = fields[0]
    sizes = {'HELLO': 3, 'READY': 4, 'CMD': 6, 'ACK': 7}
    if kind not in sizes or len(fields) != sizes[kind] or fields[1] != '1':
        raise ValueError('VERSION_OR_FIELDS')
    if not SESSION.fullmatch(fields[2]): raise ValueError('SESSION')
    if kind in ['CMD', 'ACK']:
        if not re.fullmatch(r'[1-9][0-9]*', fields[3]) or not 1 <= int(fields[3]) <= 2147483647: raise ValueError('SEQ')
        if fields[4] not in ['0', '1']: raise ValueError('ENABLE')
        if fields[5] == '-0' or not re.fullmatch(r'-?(0|[1-9][0-9]*)', fields[5]) or not -1000 <= int(fields[5]) <= 1000:
            raise ValueError('YAW')
        if fields[4] == '0' and fields[5] != '0': raise ValueError('DISABLED_NONZERO')
    return fields


class BridgeCore:
    def __init__(self, watchdog_ms=250):
        self.session = None
        self.seq = 0
        self.enabled = False
        self.yaw = 0
        self.last_valid = None
        self.watchdog_ms = watchdog_ms
        self.fault = 'NONE'
    def tick(self, now):
        if self.last_valid is not None and deadline_reached(now, self.last_valid, self.watchdog_ms):
            self.enabled, self.yaw, self.fault = False, 0, 'WATCHDOG'
    def receive(self, line, now):
        self.tick(now)
        try: f = parse(line)
        except ValueError: return None
        if f[0] == 'HELLO':
            self.session, self.seq, self.last_valid = f[2], 0, None
            self.enabled, self.yaw, self.fault = False, 0, 'NONE'
            return f'READY 1 {self.session} NO_OUTPUT\n'
        if f[0] != 'CMD' or self.session != f[2]: return None
        seq = int(f[3])
        if seq <= self.seq:
            return f'ACK 1 {self.session} {seq} {int(self.enabled)} {self.yaw} SEQUENCE\n'
        self.seq, self.enabled, self.yaw = seq, f[4] == '1', int(f[5])
        self.last_valid, self.fault = now, 'NONE'
        return f'ACK 1 {self.session} {seq} {int(self.enabled)} {self.yaw} NONE\n'
