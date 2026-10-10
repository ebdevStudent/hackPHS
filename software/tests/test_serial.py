import os
import pty
import select
import threading
import time

from ball_demo.bridge import SerialBridge
from ball_demo.protocol import BridgeCore


def test_real_pyserial_pty_partial_and_invalid_replies():
    master, slave = pty.openpty()
    device = os.ttyname(slave)
    core, stop = BridgeCore(), threading.Event()
    def emulator():
        buffer = b''
        while not stop.is_set():
            if not select.select([master], [], [], .02)[0]: continue
            try: buffer += os.read(master, 4096)
            except OSError: break
            while b'\n' in buffer:
                line, buffer = buffer.split(b'\n', 1)
                response = core.receive(line.decode(), time.monotonic())
                if response:
                    os.write(master, b'ACK 2 bad 1 1 4 NONE\n')
                    payload = response.encode()
                    os.write(master, payload[:8])
                    time.sleep(.003)
                    os.write(master, payload[8:])
    thread = threading.Thread(target=emulator, daemon=True)
    thread.start()
    bridge = SerialBridge(device)
    try:
        end = time.monotonic() + 1
        while not bridge.ready and time.monotonic() < end:
            bridge.poll(time.monotonic())
            time.sleep(.01)
        assert bridge.ready
        bridge.send(True, 350, time.monotonic())
        end = time.monotonic() + 1
        while bridge.accepted_yaw != 350 and time.monotonic() < end:
            bridge.poll(time.monotonic())
            time.sleep(.01)
        assert bridge.accepted_yaw == 350 and core.yaw == 350
        bridge.close()
        time.sleep(.04)
        assert core.yaw == 0
    finally:
        stop.set()
        thread.join(1)
        os.close(master)
        os.close(slave)

