"""Ball Drone Flight Sim — desktop app (PyWebView + Three.js).

Starts the local FastAPI server on a free port in a background thread and opens the simulator in a native window
(Edge WebView2 on Windows, GPU-accelerated WebGL). F11 toggles fullscreen.
Run:  pythonw desktop.py     (or double-click "Ball Drone.bat" / the desktop shortcut)
"""
import socket, threading, time, urllib.request
from pathlib import Path

import uvicorn
import webview

from server import app, HOST

ROOT = Path(__file__).resolve().parent


def free_port(preferred=8790):
    for port in (preferred, 0):
        with socket.socket() as s:
            try:
                s.bind((HOST, port))
                return s.getsockname()[1]
            except OSError:
                continue


class Api:
    """Exposed to the page as window.pywebview.api."""
    def __init__(self):
        self._window = None          # underscore: not exposed to JavaScript

    def toggle_fullscreen(self):
        self._window.toggle_fullscreen()

    def quit(self):
        self._window.destroy()


def main():
    port = free_port()
    server = uvicorn.Server(uvicorn.Config(app, host=HOST, port=port, log_level="warning"))
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):                                   # wait until the backend answers
        try:
            urllib.request.urlopen(f"http://{HOST}:{port}/api/health", timeout=0.3); break
        except OSError:
            time.sleep(0.1)
    api = Api()
    api._window = webview.create_window("Ball Drone Flight Sim", f"http://{HOST}:{port}/", js_api=api,
                                       width=1600, height=900, min_size=(1100, 650), maximized=True, background_color="#050607")
    webview.start(debug=False)
    server.should_exit = True


if __name__ == "__main__":
    main()
