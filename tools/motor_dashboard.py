#!/usr/bin/env python3
"""Local web dashboard for props-off Betaflight motor testing over USB MSP.

    python3 tools/motor_dashboard.py            # then open http://127.0.0.1:8765
    python3 tools/motor_dashboard.py --max 1400 # raise the slider ceiling

The server owns the FC USB port (close the Betaflight app first). It waits for
the FC to appear and reconnects automatically. Safety model:
  * starts DISABLED; enabling needs the "props removed" attestation
  * dead-man: if the page stops sending heartbeats for 0.5 s, all motors stop
    and the dashboard disables itself (closing the tab = stop)
  * any USB reconnect, FC arming, low battery or error -> stop + disable
  * normal arming is blocked via MSP while connected (same as the bench tool)
Commands are disarmed motor-test values, not RPM. Unplug the battery if a
stop ever fails to take effect.
"""

import argparse
import json
import struct
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from betaflight_motor_bench import DEFAULT_PORT, FC, dshot_percent

HEARTBEAT_TIMEOUT = 0.5
LOW_BATTERY = 6.4        # cut if a battery is present and sags below this
HTML = (Path(__file__).with_name('motor_dashboard.html')).read_text()


class Controller:
    def __init__(self, port, max_value):
        self.port = port
        self.max_value = max_value
        self.lock = threading.Lock()
        self.fc = None
        self.targets = [1000] * 4
        self.enabled = False
        self.heartbeat = 0.0
        self.state = dict(connected=False)
        self.config = {}
        self.events = []
        self.running = True

    def log(self, message):
        self.events.append(dict(t=time.strftime('%H:%M:%S'), msg=message))
        del self.events[:-30]
        print(message, flush=True)

    # --- called from HTTP threads ---
    def disable(self, reason):
        with self.lock:
            if self.enabled:
                self.log(f'Disabled: {reason}')
            self.enabled = False
            self.targets = [1000] * 4

    def enable(self, props_removed):
        with self.lock:
            if not props_removed:
                return 'Confirm that all propellers are removed'
            if not self.state.get('connected'):
                return 'FC not connected'
            if self.state.get('armed'):
                return 'FC is armed'
            self.enabled = True
            self.heartbeat = time.monotonic()
            self.targets = [1000] * 4
            self.log('Enabled (props removed attested)')
            return None

    def set_targets(self, motors):
        with self.lock:
            self.heartbeat = time.monotonic()
            if not self.enabled:
                return
            clean = []
            for value in motors[:4]:
                value = int(value)
                clean.append(1000 if value <= 1000 else min(value, self.max_value))
            self.targets = clean + [1000] * (4 - len(clean))

    def snapshot(self):
        with self.lock:
            return dict(self.state, enabled=self.enabled, targets=self.targets,
                        targets_pct=[dshot_percent(v) for v in self.targets],
                        max_value=self.max_value, config=self.config,
                        events=self.events[-12:], port=self.port)

    # --- worker thread: sole owner of the serial port ---
    def connect(self):
        fc = FC(self.port)
        try:
            fc.request(99, b'\x01\x00')   # block normal arming while dashboard owns FC
            fc.stop()
            status = fc.status()
            try:
                config = fc.config()
            except Exception:
                config = {}
        except Exception:
            fc.ser.close()
            raise
        with self.lock:
            self.fc = fc
            self.config = config
            self.enabled = False
            self.targets = [1000] * 4
            self.state = dict(status, connected=True)
            self.log(f"FC connected: BF {'.'.join(map(str, status['firmware']))}, "
                     f"{status['voltage']:.2f} V")

    def drop(self, reason):
        with self.lock:
            fc, self.fc = self.fc, None
            self.enabled = False
            self.targets = [1000] * 4
            self.state = dict(connected=False)
            self.log(f'FC disconnected: {reason}')
        if fc:
            try:
                fc.stop()
            except Exception:
                pass
            try:
                fc.ser.close()
            except Exception:
                pass

    def run(self):
        tick = 0
        while self.running:
            if self.fc is None:
                try:
                    self.connect()
                except Exception:
                    time.sleep(1.0)
                    continue
            try:
                with self.lock:
                    if self.enabled and time.monotonic() - self.heartbeat > HEARTBEAT_TIMEOUT:
                        self.enabled = False
                        self.targets = [1000] * 4
                        self.log('Disabled: dashboard heartbeat lost')
                    out = list(self.targets) if self.enabled else [1000] * 4
                self.fc.request(214, struct.pack('<8H', *(out + [1000] * 4)))
                if tick % 4 == 0:
                    status = self.fc.status()
                    with self.lock:
                        self.state = dict(status, connected=True)
                    if status['armed']:
                        self.disable('FC reports ARMED')
                    v = status['voltage']
                    if 5.0 < v < LOW_BATTERY and any(t > 1000 for t in out):
                        self.disable(f'battery low ({v:.2f} V)')
                else:
                    commands = self.fc.motors()
                    with self.lock:
                        self.state['motor_commands'] = commands
                tick += 1
                time.sleep(0.05)
            except Exception as exc:
                self.drop(str(exc) or type(exc).__name__)

    def shutdown(self):
        self.running = False
        with self.lock:
            self.enabled = False
            self.targets = [1000] * 4
        if self.fc:
            try:
                self.fc.stop()
                self.fc.ser.close()
            except Exception:
                pass


def make_handler(ctl):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, code, body, ctype='application/json'):
            data = body.encode() if isinstance(body, str) else body
            self.send_response(code)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path in ('/', '/index.html'):
                self.send(200, HTML, 'text/html; charset=utf-8')
            elif self.path == '/api/state':
                self.send(200, json.dumps(ctl.snapshot()))
            else:
                self.send(404, '{}')

        def do_POST(self):
            try:
                length = int(self.headers.get('Content-Length') or 0)
                body = json.loads(self.rfile.read(length) or b'{}')
            except Exception:
                ctl.disable('bad request')
                return self.send(400, json.dumps(dict(error='bad request')))
            error = None
            if self.path == '/api/stop':
                ctl.disable(body.get('reason', 'STOP pressed'))
            elif self.path == '/api/enable':
                error = ctl.enable(body.get('props_removed') is True)
            elif self.path == '/api/set':
                motors = body.get('motors')
                if (not isinstance(motors, list) or len(motors) != 4
                        or not all(isinstance(m, int) and not isinstance(m, bool)
                                   for m in motors)):
                    ctl.disable('bad motor request')
                    return self.send(400, json.dumps(dict(error='bad motors')))
                ctl.set_targets(motors)
            else:
                return self.send(404, '{}')
            self.send(200, json.dumps(dict(ctl.snapshot(), error=error)))

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--port', default=DEFAULT_PORT, help='FC serial device')
    parser.add_argument('--host', default='127.0.0.1',
                        help='bind address (0.0.0.0 exposes motor control to the network!)')
    parser.add_argument('--http-port', type=int, default=8765)
    parser.add_argument('--max', type=int, default=1300,
                        help='slider ceiling, 1001-2000 (default 1300 = ~30%% throttle)')
    args = parser.parse_args()
    if not 1001 <= args.max <= 2000:
        parser.error('--max must be 1001-2000')

    ctl = Controller(args.port, args.max)
    worker = threading.Thread(target=ctl.run, daemon=True)
    worker.start()
    server = ThreadingHTTPServer((args.host, args.http_port), make_handler(ctl))
    print(f'Motor dashboard: http://{args.host}:{args.http_port}  '
          f'(max {args.max} = {dshot_percent(args.max)}%)  waiting for FC on {args.port}',
          flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        ctl.shutdown()
        server.server_close()
        print('Stopped; motors commanded to 1000.', flush=True)


if __name__ == '__main__':
    main()
