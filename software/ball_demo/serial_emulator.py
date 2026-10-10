"""A Mac/Linux PTY peer for the actual pyserial adapter. Never touches hardware."""
import argparse
import os
import pty
import select
import time

from .protocol import BridgeCore, MAX_FRAME


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fault', choices=['none', 'missing_ack', 'delayed_ack', 'partial', 'invalid', 'disconnect'], default='none')
    args = parser.parse_args()
    master, slave = pty.openpty()
    print('Virtual serial device: ' + os.ttyname(slave), flush=True)
    print('Run ball-demo serve --serial <path> in another terminal. USB/trainer output is simulated.', flush=True)
    core, buffer, discarding = BridgeCore(), b'', False
    try:
        while True:
            core.tick(time.monotonic())
            if not select.select([master], [], [], .01)[0]: continue
            buffer += os.read(master, 4096)
            if discarding:
                if b'\n' not in buffer:
                    buffer = b''
                    continue
                _, buffer = buffer.split(b'\n', 1)
                discarding = False
            while b'\n' in buffer:
                line, buffer = buffer.split(b'\n', 1)
                if len(line) >= MAX_FRAME: continue
                try: response = core.receive(line.decode('ascii'), time.monotonic())
                except UnicodeDecodeError: continue
                if not response: continue
                if response.startswith('ACK'):
                    if args.fault == 'missing_ack': continue
                    if args.fault == 'disconnect': return
                    if args.fault == 'delayed_ack': time.sleep(.4)
                    if args.fault == 'invalid': response = 'ACK 2 invalid 1 1 200 NONE\n'
                payload = response.encode()
                if args.fault == 'partial':
                    os.write(master, payload[:6]); time.sleep(.01); os.write(master, payload[6:])
                else: os.write(master, payload)
            if len(buffer) > MAX_FRAME:
                buffer, discarding = b'', True
    except KeyboardInterrupt: pass
    finally:
        os.close(master); os.close(slave)


if __name__ == '__main__': main()
