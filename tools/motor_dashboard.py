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

import urllib.request

import preflight_checks
from betaflight_motor_bench import DEFAULT_PORT, FC, dshot_percent

HEARTBEAT_TIMEOUT = 0.5
LOW_BATTERY = 6.4        # cut if a battery is present and sags below this
HTML_PATH = Path(__file__).with_name('motor_dashboard.html')


class Controller:
    def __init__(self, port, max_value, fpv_url=''):
        self.port = port
        self.fpv_url = fpv_url
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
        self.reconnect_requested = False
        self.connect_error = None
        self.pending_direction = None
        self.radio_arming = False          # False: dashboard blocks arming via MSP
        self.pending_arming_block = None
        self.pending_vtx_pit = None
        self.vtx = {}
        self.preflight_request = None   # (Event, result dict) for the worker

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

    def set_radio_arming(self, allow):
        with self.lock:
            if not self.state.get('connected'):
                return 'FC not connected'
            self.enabled = False
            self.targets = [1000] * 4
            self.radio_arming = allow
            self.pending_arming_block = not allow
            self.log('Radio arming ALLOWED (dashboard sliders off)' if allow
                     else 'Radio arming blocked again')
            return None

    def enable(self, props_removed):
        with self.lock:
            if self.radio_arming:
                return 'Radio arming is allowed - block it again to use the sliders'
            if not props_removed:
                self.log('Enable refused: props-removed box not ticked')
                return 'Tick "All propellers are removed" first'
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
                        events=self.events[-12:], port=self.port,
                        connect_error=self.connect_error,
                        radio_arming=self.radio_arming, fpv_url=self.fpv_url, vtx=self.vtx)

    def request_direction(self, motor, reverse):
        with self.lock:
            if not self.state.get('connected'):
                return 'FC not connected'
            if self.state.get('armed'):
                return 'FC is armed'
            if self.pending_direction:
                return 'Direction change already in progress'
            self.enabled = False
            self.targets = [1000] * 4
            self.pending_direction = (motor, reverse)
            self.log(f"Setting M{motor} direction {'REVERSED' if reverse else 'NORMAL'}…")
            return None

    def request_vtx(self, on):
        with self.lock:
            if not self.state.get('connected'):
                return 'FC not connected (plug in USB)'
            if not on and self.state.get('armed'):
                return 'Refusing to turn video off while armed'
            self.enabled = False            # worker is busy ~5 s confirming; stop motors first
            self.targets = [1000] * 4
            self.pending_vtx_pit = not on
            self.log(f"Video transmitter {'ON' if on else 'OFF (pit mode)'} requested")
            return None

    def read_preflight(self):
        """Worker-side: extra read-only MSP queries for the checklist."""
        fc = self.fc
        data = dict(self.state)
        data.update(config=self.config, vtx=fc.vtx(), mode_ranges=fc.mode_ranges(), failsafe=fc.failsafe(),
                    board_alignment=fc.board_alignment(), level_limit=fc.level_limit())
        return data

    def preflight(self):
        """HTTP-thread side: FC data via the worker, Pi data over HTTP, then the GO/NO-GO list."""
        import threading as _t
        fc_data, checks = None, []
        if self.state.get('connected'):
            done, box = _t.Event(), {}
            with self.lock:
                self.preflight_request = (done, box)
            if done.wait(4) and 'data' in box:
                fc_data = box['data']
            checks += (preflight_checks.fc_checks(fc_data) if fc_data else
                       [preflight_checks.check('Flight controller', 'fail', box.get('error', 'read timed out'))])
        else:
            checks.append(preflight_checks.check('Flight controller', 'fail', 'not connected over USB'))
        pi = {}
        base = self.fpv_url
        for key, url in (('fpv', base + '/status'), ('track', base.rsplit(':', 1)[0] + ':8080/api/state')):
            try:
                with urllib.request.urlopen(url, timeout=1.5) as reply:
                    pi[key] = json.loads(reply.read())
            except Exception as exc:
                pi.setdefault('error', f'unreachable ({type(exc).__name__})')
        checks += preflight_checks.pi_checks(pi)
        return dict(summary=preflight_checks.summary(checks), checks=checks, manual=preflight_checks.MANUAL,
                    t=time.strftime('%H:%M:%S'))

    def request_reconnect(self):
        with self.lock:
            self.enabled = False
            self.targets = [1000] * 4
            self.reconnect_requested = True
            self.connect_error = None
            self.log('Reconnect requested')

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
            try:
                config['mspv2_api'] = list(fc.request_v2(1))
            except Exception as exc:
                config['mspv2_api'] = f'unavailable: {exc}'
        except Exception:
            fc.ser.close()
            raise
        with self.lock:
            self.fc = fc
            self.radio_arming = False
            self.pending_arming_block = None
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
            if self.reconnect_requested:
                self.reconnect_requested = False
                if self.fc is not None:
                    self.drop('reconnect requested')
            if self.fc is None:
                try:
                    self.connect()
                    self.connect_error = None
                except Exception as exc:
                    message = str(exc) or type(exc).__name__
                    if message != self.connect_error:
                        self.connect_error = message
                        if 'ermission' in message:
                            self.log('USB permission denied - see hint in status bar')
                    for _ in range(10):
                        if self.reconnect_requested or not self.running:
                            break
                        time.sleep(0.1)
                    continue
            if self.pending_arming_block is not None:
                block, self.pending_arming_block = self.pending_arming_block, None
                try:
                    self.fc.request(99, bytes([1 if block else 0, 0]))
                except Exception as exc:
                    self.log(f'Arming block change FAILED: {exc}')
            if self.preflight_request is not None:
                (done, box), self.preflight_request = self.preflight_request, None
                try:
                    box['data'] = self.read_preflight()
                except Exception as exc:
                    box['error'] = f'FC read failed: {exc}'
                done.set()
            if self.pending_vtx_pit is not None:
                pit, self.pending_vtx_pit = self.pending_vtx_pit, None
                try:
                    self.fc.stop()
                    v = self.fc.set_vtx_pit(pit)
                    self.vtx = v
                    ok = v['pit'] == pit
                    self.log(f"Video transmitter now {'OFF (pit mode)' if v['pit'] else 'ON'}"
                             + ('' if ok else ' - VTX did not accept the change'))
                except Exception as exc:
                    self.log(f'Video transmitter change FAILED: {exc}')
            if self.pending_direction:
                motor, reverse = self.pending_direction
                try:
                    self.fc.set_direction(motor, reverse)
                    self.log(f"M{motor} direction {'REVERSED' if reverse else 'NORMAL'} saved "
                             '- spin it to check (replug battery if unchanged)')
                except Exception as exc:
                    self.log(f'M{motor} direction change FAILED: {exc}')
                finally:
                    self.pending_direction = None
            try:
                with self.lock:
                    if self.enabled and time.monotonic() - self.heartbeat > HEARTBEAT_TIMEOUT:
                        self.enabled = False
                        self.targets = [1000] * 4
                        self.log('Disabled: dashboard heartbeat lost')
                    out = list(self.targets) if self.enabled else [1000] * 4
                self.fc.request(214, struct.pack('<8H', *(out + [1000] * 4)))
                if tick % 60 == 0:
                    try:
                        self.vtx = self.fc.vtx()
                    except Exception:
                        pass
                if tick % 4 == 0:
                    status = self.fc.status()
                    if self.config.get('dshot_bidir'):
                        try:
                            status['rpm'] = self.fc.motor_rpm()
                        except Exception:
                            status['rpm'] = None
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
            try:
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_GET(self):
            if self.path in ('/', '/index.html'):
                self.send(200, HTML_PATH.read_text(), 'text/html; charset=utf-8')
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
            elif self.path == '/api/reconnect':
                ctl.request_reconnect()
            elif self.path == '/api/radio_arming':
                if not isinstance(body.get('allow'), bool):
                    return self.send(400, json.dumps(dict(error='bad request')))
                error = ctl.set_radio_arming(body['allow'])
            elif self.path == '/api/preflight':
                return self.send(200, json.dumps(ctl.preflight()))
            elif self.path == '/api/vtx':
                if not isinstance(body.get('on'), bool):
                    return self.send(400, json.dumps(dict(error='bad request')))
                error = ctl.request_vtx(body['on'])
            elif self.path == '/api/direction':
                motor, reverse = body.get('motor'), body.get('reverse')
                if (not isinstance(motor, int) or isinstance(motor, bool)
                        or not 1 <= motor <= 4 or not isinstance(reverse, bool)):
                    return self.send(400, json.dumps(dict(error='bad direction request')))
                error = ctl.request_direction(motor, reverse)
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
    parser.add_argument('--fpv-url', default='http://172.16.240.48:8090',
                        help='Pi FPV streamer (tools/pi/fpv_stream.py) for the Camera tab')
    parser.add_argument('--max', type=int, default=1300,
                        help='slider ceiling, 1001-2000 (default 1300 = ~30%% throttle)')
    args = parser.parse_args()
    if not 1001 <= args.max <= 2000:
        parser.error('--max must be 1001-2000')

    ctl = Controller(args.port, args.max, args.fpv_url.rstrip('/'))
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
