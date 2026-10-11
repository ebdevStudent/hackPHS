#!/usr/bin/env python3
"""FPV capture streamer for the Raspberry Pi (RC832 -> MS210x USB capture -> here).

    /opt/ball-drone/software/.venv/bin/python fpv_stream.py   # http://<pi>:8090/

Endpoints (CORS-open so the laptop motor dashboard can embed them):
  /stream.mjpg   live MJPEG          /snapshot.jpg   latest frame
  /status        JSON signal report  POST /reset     USB-reset the capture stick
  /              monitor page (fpv_page.html next to this file)

Signal classes: PICTURE, SNOW (RC832 tuned to nothing), FLAT (blank screen / no
video modulation), NO INPUT (all-zero frames: the MS210x stick sometimes latches
this until it is re-enumerated; auto-reset handles it), NO DEVICE.
Only one program can open /dev/video0: stop this before ball_demo uses the camera.
"""

import argparse
import json
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import cv2
import numpy as np

RESET_CMD = ['sudo', '-n', '/usr/local/bin/reset-capture']
PAGE = Path(__file__).with_name('fpv_page.html')


class Grabber:
    def __init__(self, device, width, height, auto_reset):
        self.device, self.width, self.height = device, width, height
        self.auto_reset = auto_reset
        self.cond = threading.Condition()
        self.jpeg = None
        self.seq = 0
        self.status = dict(signal='STARTING')
        self.reset_requested = False
        self.last_reset = 0.0

    def request_reset(self):
        self.reset_requested = True

    def _reset(self, cap, why):
        cap.release()
        self.last_reset = time.monotonic()
        self._set(signal='RESETTING', note=why)
        result = subprocess.run(RESET_CMD, capture_output=True, text=True)
        if result.returncode:
            self._set(signal='RESET FAILED', note=result.stderr.strip())
        time.sleep(3)

    def _set(self, **fields):
        with self.cond:
            self.status = dict(fields, t=time.time())

    def run(self):
        while True:
            cap = cv2.VideoCapture(self.device, cv2.CAP_V4L2)
            if not cap.isOpened():
                self._set(signal='NO DEVICE', note='capture stick not found on /dev/video%d' % self.device)
                time.sleep(1)
                continue
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            cap.set(cv2.CAP_PROP_FPS, 30)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            prev, zero_since, frames, t0 = None, None, 0, time.monotonic()
            while True:
                if self.reset_requested:
                    self.reset_requested = False
                    self._reset(cap, 'manual reset')
                    break
                ok, frame = cap.read()
                if not ok:
                    self._set(signal='NO DEVICE', note='read failed')
                    cap.release()
                    time.sleep(1)
                    break
                frames += 1
                small = cv2.cvtColor(frame[::4, ::4], cv2.COLOR_BGR2GRAY).astype(np.int16)
                mean, std = float(small.mean()), float(small.std())
                change = float(np.abs(small - prev).mean()) if prev is not None else 0.0
                prev = small
                if small.max() == 0:
                    signal = 'NO INPUT'
                    zero_since = zero_since or time.monotonic()
                else:
                    zero_since = None
                    signal = 'SNOW' if change > 15 else 'FLAT' if std < 4 else 'PICTURE'
                ok, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                elapsed = time.monotonic() - t0
                with self.cond:
                    self.jpeg = buf.tobytes()
                    self.seq += 1
                    self.status = dict(signal=signal, mean=round(mean, 1), std=round(std, 1),
                                       change=round(change, 1), fps=round(frames / elapsed, 1)
                                       if elapsed > 0 else 0, size=[frame.shape[1], frame.shape[0]],
                                       t=time.time())
                    self.cond.notify_all()
                if (self.auto_reset and zero_since and time.monotonic() - zero_since > 4
                        and time.monotonic() - self.last_reset > 30):
                    self._reset(cap, 'auto reset: all-zero frames')
                    break


def make_handler(grab):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def head(self, code, ctype, length=None):
            self.send_response(code)
            self.send_header('Content-Type', ctype)
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Cache-Control', 'no-store')
            if length is not None:
                self.send_header('Content-Length', str(length))
            self.end_headers()

        def do_GET(self):
            path = self.path.split('?')[0]
            try:
                if path == '/status':
                    with grab.cond:
                        body = json.dumps(dict(grab.status, seq=grab.seq,
                                               device='/dev/video%d' % grab.device)).encode()
                    self.head(200, 'application/json', len(body))
                    self.wfile.write(body)
                elif path == '/snapshot.jpg':
                    with grab.cond:
                        data = grab.jpeg
                    if data is None:
                        self.head(503, 'text/plain', 0)
                        return
                    self.head(200, 'image/jpeg', len(data))
                    self.wfile.write(data)
                elif path == '/stream.mjpg':
                    self.head(200, 'multipart/x-mixed-replace; boundary=frame')
                    seen = -1
                    while True:
                        with grab.cond:
                            grab.cond.wait_for(lambda: grab.seq != seen, timeout=2)
                            data, seen = grab.jpeg, grab.seq
                        if data is None:
                            continue
                        self.wfile.write(b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: '
                                         + str(len(data)).encode() + b'\r\n\r\n' + data + b'\r\n')
                elif path == '/':
                    try:  # re-read per request so the page can be edited without a restart
                        body = PAGE.read_bytes()
                    except OSError:
                        body = (b'<title>FPV</title><body style="margin:0;background:#000">'
                                b'<img src="/stream.mjpg" style="width:100%">')
                    self.head(200, 'text/html; charset=utf-8', len(body))
                    self.wfile.write(body)
                else:
                    self.head(404, 'text/plain', 0)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def do_POST(self):
            if self.path == '/reset':
                grab.request_reset()
                self.head(200, 'application/json', 2)
                self.wfile.write(b'{}')
            else:
                self.head(404, 'text/plain', 0)

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--device', type=int, default=0)
    parser.add_argument('--width', type=int, default=720)
    parser.add_argument('--height', type=int, default=480, help='480 = NTSC, 576 = PAL')
    parser.add_argument('--port', type=int, default=8090)
    parser.add_argument('--no-auto-reset', action='store_true')
    args = parser.parse_args()
    grab = Grabber(args.device, args.width, args.height, not args.no_auto_reset)
    threading.Thread(target=grab.run, daemon=True).start()
    server = ThreadingHTTPServer(('0.0.0.0', args.port), make_handler(grab))
    server.daemon_threads = True
    print(f'FPV stream on :{args.port}', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
