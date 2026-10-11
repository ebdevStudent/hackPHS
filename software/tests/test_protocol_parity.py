"""Cross-check real portable C and Python bridge cores on the same injected clock."""
import ctypes
import random
import shutil
import subprocess
from pathlib import Path

import pytest

from ball_demo.protocol import BridgeCore, parse


class CCore(ctypes.Structure):
    _fields_ = [('session', ctypes.c_char * 33), ('seq', ctypes.c_uint32), ('last_valid_ms', ctypes.c_uint32),
                ('enabled', ctypes.c_bool), ('has_command', ctypes.c_bool), ('yaw', ctypes.c_int), ('watchdog_fault', ctypes.c_bool),
                ('output_mode', ctypes.c_char_p), ('session_output', ctypes.c_char_p)]


@pytest.fixture(scope='module')
def c_library(tmp_path_factory):
    compiler = shutil.which('clang') or shutil.which('cc')
    assert compiler, 'Portable core parity tests require a host C compiler'
    root = Path(__file__).resolve().parents[2]
    folder = tmp_path_factory.mktemp('portable-c-parity')
    shim = folder / 'size.c'; shim.write_text('#include "core.h"\nsize_t core_size(void) { return sizeof(ball_core); }\n')
    library = folder / 'libball-core.so'
    result = subprocess.run([compiler, '-std=c11', '-Wall', '-Wextra', '-Werror', '-fPIC', '-shared',
                             '-I', str(root/'firmware'), str(root/'firmware/core.c'), str(shim), '-o', str(library)],
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    dll = ctypes.CDLL(str(library))
    dll.core_size.restype = ctypes.c_size_t
    assert dll.core_size() == ctypes.sizeof(CCore)
    dll.ball_init.argtypes = [ctypes.POINTER(CCore)]
    dll.ball_tick.argtypes = [ctypes.POINTER(CCore), ctypes.c_uint32]
    dll.ball_receive.argtypes = [ctypes.POINTER(CCore), ctypes.c_char_p, ctypes.c_size_t,
                                ctypes.c_uint32, ctypes.c_char_p, ctypes.c_size_t]
    dll.ball_receive.restype = ctypes.c_bool
    return dll


def compare(dll, python, native, frame, ms):
    reply = ctypes.create_string_buffer(160)
    encoded = frame.encode('utf-8')
    accepted = dll.ball_receive(ctypes.byref(native), encoded, len(encoded), ms, reply, len(reply))
    got = python.receive(frame, ms / 1000)
    assert got == (reply.value.decode() if accepted else None), (frame, ms, got, reply.value)
    assert (python.enabled, python.yaw, python.seq, python.fault == 'WATCHDOG') == (
        native.enabled, native.yaw, native.seq, native.watchdog_fault), (frame, ms)


@pytest.mark.parametrize('seed', range(12))
def test_seeded_c_python_protocol_and_watchdog_parity(c_library, seed):
    rng = random.Random(20261004 + seed)
    python, native = BridgeCore(), CCore(); c_library.ball_init(ctypes.byref(native))
    session, ms, seq = 'start', 0, 0
    compare(c_library, python, native, f'HELLO 1 {session}\n', ms)
    for index in range(400):
        ms += rng.choice([0, 1, 20, 249, 250, 251, 300])
        action = rng.randrange(8)
        if action == 0:
            session, seq = f's{seed}_{index}', 0
            frame = f'HELLO 1 {session}\n'
        elif action == 1:
            frame = f'CMD 1 {session} {max(1,seq)} 1 100\n'  # stale sequence
        elif action == 2:
            frame = f'CMD 1 {session} {seq+1} 0 5\n'  # disabled nonzero
        elif action == 3:
            frame = f'CMD 1 other {seq+1} 1 200\n'
        elif action == 4:
            frame = rng.choice(['HELLO 1 bad!\n', 'CMD 1 x 2147483648 1 0\n', 'bad\n', 'CMD 2 x 1 1 0\n', 'HELLO 1 é\n'])
        elif action == 5:
            c_library.ball_tick(ctypes.byref(native), ms); python.tick(ms/1000)
            assert (python.enabled, python.yaw, python.fault == 'WATCHDOG') == (native.enabled, native.yaw, native.watchdog_fault)
            continue
        else:
            seq += 1
            enabled = rng.choice([0, 1]); yaw = rng.randint(-1000, 1000) if enabled else 0
            frame = f'CMD 1 {session} {seq} {enabled} {yaw}\n'
        compare(c_library, python, native, frame, ms)


@pytest.mark.parametrize('start_ms', [0, 1, 10, 100, 110, 111, 222, 333, 1001, 9999])
def test_exact_watchdog_boundary_matches_c(c_library, start_ms):
    python, native = BridgeCore(), CCore(); c_library.ball_init(ctypes.byref(native))
    compare(c_library, python, native, 'HELLO 1 boundary\n', start_ms)
    compare(c_library, python, native, 'CMD 1 boundary 1 1 500\n', start_ms)
    python.tick((start_ms+249)/1000); c_library.ball_tick(ctypes.byref(native), start_ms+249)
    assert python.enabled and native.enabled
    python.tick((start_ms+250)/1000); c_library.ball_tick(ctypes.byref(native), start_ms+250)
    assert not python.enabled and not native.enabled
    assert python.yaw == native.yaw == 0 and python.fault == 'WATCHDOG'


@pytest.mark.parametrize('session', ['', 'bad!', 'a/b', 'a.b', 'a' * 33, 'a\t'])
def test_ascii_session_rejection(session):
    with pytest.raises(ValueError): parse(f'HELLO 1 {session}\n')
