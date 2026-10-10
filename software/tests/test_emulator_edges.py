"""Exercise emulator framing and cleanup with deterministic virtual-descriptor IO."""
import sys
from itertools import count
from types import SimpleNamespace

import pytest

from ball_demo import serial_emulator
from ball_demo.protocol import MAX_FRAME
from ball_demo.protocol import BridgeCore


@pytest.mark.parametrize('fault', ['none', 'partial', 'invalid', 'missing_ack', 'delayed_ack', 'disconnect'])
def test_emulator_discards_bad_frame_suffix_and_cleans_descriptors(monkeypatch, fault, capsys):
    chunks = iter([
        b'\xff\n' + b'x' * (MAX_FRAME + 1) + b'\n' + b'bad command\nHELLO 1 test\n',
        b'x' * (MAX_FRAME + 1), b'more-without-a-newline',
        b'CMD 1 test 1 1 200\n',  # still a suffix of the oversized input
        b'CMD 1 test 2 1 300\n',
    ])
    writes, closed, delays = [], [], []
    responses = []
    def tracked_core():
        core = BridgeCore()
        receive = core.receive
        def record(line, now):
            result = receive(line, now); responses.append(result); return result
        core.receive = record
        return core
    monkeypatch.setattr(serial_emulator, 'BridgeCore', tracked_core)
    clock = count()
    def read(fd, size):
        try: return next(chunks)
        except StopIteration: raise KeyboardInterrupt
    monkeypatch.setattr(sys, 'argv', ['emulator', '--fault', fault])
    monkeypatch.setattr(serial_emulator, 'pty', SimpleNamespace(openpty=lambda: (100, 101)))
    monkeypatch.setattr(serial_emulator, 'os', SimpleNamespace(
        ttyname=lambda fd: '/virtual/only', read=read,
        write=lambda fd, data: writes.append(data), close=closed.append))
    readiness = iter([([], [], []), ([100], [], [])])
    monkeypatch.setattr(serial_emulator, 'select', SimpleNamespace(select=lambda *args: next(readiness, ([100], [], []))))
    monkeypatch.setattr(serial_emulator, 'time', SimpleNamespace(monotonic=lambda: next(clock) * .01, sleep=delays.append))
    serial_emulator.main()
    combined = b''.join(writes)
    assert combined.startswith(b'READY 1 test NO_OUTPUT\n')
    assert 'ACK 1 test 1 1 200 NONE\n' not in responses  # no suffix accepted as a fresh frame
    if fault in ('missing_ack', 'disconnect'): assert b'ACK' not in combined
    elif fault == 'invalid': assert combined.endswith(b'ACK 2 invalid 1 1 200 NONE\n')
    else: assert combined.endswith(b'ACK 1 test 2 1 300 NONE\n')
    if fault == 'partial': assert .01 in delays
    if fault == 'delayed_ack': assert .4 in delays
    assert closed == [100, 101]
    assert 'Virtual serial device: /virtual/only' in capsys.readouterr().out
