"""Exhaustive wire domains and ACK arrival orders, with independent state checks."""
import ctypes
import itertools
import string

import pytest

from ball_demo.protocol import BridgeCore
from test_protocol_parity import CCore, c_library, compare
from test_bridge_edges import adapter, feed, ready


@pytest.mark.parametrize('yaw', range(-1000, 1001))
def test_every_wire_yaw_roundtrips_python_and_compiled_c(c_library, yaw):
    py, native = BridgeCore(), CCore(); c_library.ball_init(ctypes.byref(native))
    compare(c_library, py, native, 'HELLO 1 exhaustive\n', 100)
    compare(c_library, py, native, f'CMD 1 exhaustive 1 1 {yaw}\n', 110)
    assert py.enabled and py.yaw == native.yaw == yaw and py.seq == 1
    compare(c_library, py, native, 'CMD 1 exhaustive 2 0 0\n', 111)
    assert not py.enabled and py.yaw == 0
    compare(c_library, py, native, f'CMD 1 exhaustive 1 1 {yaw}\n', 112)
    assert py.seq == 2 and py.last_valid == .111 and py.yaw == 0


INVALID_SESSION_BYTES = [n for n in range(256) if chr(n) not in string.ascii_letters + string.digits + '_-']
@pytest.mark.parametrize('byte', INVALID_SESSION_BYTES)
def test_every_non_session_byte_is_rejected_without_refresh(c_library, byte):
    py, native = BridgeCore(), CCore(); c_library.ball_init(ctypes.byref(native))
    compare(c_library, py, native, 'HELLO 1 valid\n', 0)
    compare(c_library, py, native, 'CMD 1 valid 1 1 650\n', 1)
    compare(c_library, py, native, 'HELLO 1 pre' + chr(byte) + 'post\n', 100)
    assert py.session == 'valid' and py.seq == 1 and py.last_valid == .001
    compare(c_library, py, native, 'CMD 1 valid 1 1 650\n', 251)
    assert not py.enabled and py.yaw == 0 and py.fault == 'WATCHDOG'


@pytest.mark.parametrize('field,bad', list(itertools.product(
    [3, 4, 5], ['', '+0', '+1', '-0', '00', '01', '1.0', '1e0', 'NaN', 'Infinity',
                 'true', 'false', '\t1', '1\t', '1\x00', '2147483648', '999999999999999999999999999999'])))
def test_invalid_integer_spellings_do_not_change_c_or_python(c_library, field, bad):
    py, native = BridgeCore(), CCore(); c_library.ball_init(ctypes.byref(native))
    compare(c_library, py, native, 'HELLO 1 valid\n', 0)
    fields = ['CMD', '1', 'valid', '1', '1', '42']; fields[field] = bad
    compare(c_library, py, native, ' '.join(fields) + '\n', 1)
    # +1 etc are invalid for every numeric field, but large numbers are only
    # sequence-valid up to 2^31-1 and yaw-valid up to 1000.
    assert py.seq == 0 and py.yaw == 0 and not py.enabled and py.last_valid is None


@pytest.mark.parametrize('order', list(itertools.permutations(range(1, 6))), ids=lambda v: ''.join(map(str,v)))
def test_every_five_ack_arrival_order_preserves_latest_state(adapter, order):
    ready(adapter)
    yaws = {1: -650, 2: 400, 3: -100, 4: 250, 5: 0}
    for seq, yaw in yaws.items(): adapter.send(seq != 5, yaw, 1.05)
    latest = 0
    for offset, seq in enumerate(order):
        now = 1.06 + offset * .01
        reply = feed(adapter, f'ACK 1 {adapter.session} {seq} {int(seq != 5)} {yaws[seq]} NONE\n', now)
        if seq > latest:
            assert len(reply) == 1; latest = seq
            assert adapter.last_ack == now
        else: assert reply == []
        assert adapter.last_acked_seq == latest and adapter.accepted_yaw == yaws[latest]
    assert adapter.accepted_yaw == 0 and adapter.last_acked_seq == 5
    previous = adapter.last_ack
    for seq in order:
        assert feed(adapter, f'ACK 1 {adapter.session} {seq} {int(seq != 5)} {yaws[seq]} NONE\n', 1.2) == []
    assert adapter.last_ack == previous and not adapter.outstanding
