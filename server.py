"""Ball Drone Flight Sim — local backend.

Serves the Three.js flight simulator and an optional live-telemetry channel the physical drone
(or its ground station) can POST to; the simulator shows it in the HUD.

Run:  python server.py            -> http://127.0.0.1:8765 opens in the browser
      python server.py --no-browser
"""
import mimetypes, sys, time, threading, webbrowser
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Windows registries often map .js to text/plain, which browsers refuse for ES modules
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")

ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
HOST, PORT = "127.0.0.1", 8765

app = FastAPI(title="Ball Drone Flight Sim", version="2.0")
_lock = threading.Lock()


@app.middleware("http")
async def no_cache(request, call_next):
    resp = await call_next(request)          # always serve the latest game files (handy while editing / demoing)
    if not request.url.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store"
    return resp

telemetry: dict[str, Any] = {"t": 0.0, "data": None, "source": None}


class TelemetryIn(BaseModel):
    source: str = "ball-drone"
    data: dict


@app.get("/api/health")
def health():
    return {"ok": True, "service": "ball-drone backend 2.0"}


@app.post("/api/telemetry")
def telemetry_in(body: TelemetryIn):
    """The physical drone / ground station posts here, e.g. {"source": "ball-drone", "data": {"battery_v": 15.8, "roll": 1.2}}."""
    telemetry.update(t=time.time(), data=body.data, source=body.source)
    return {"ok": True}


@app.get("/api/telemetry")
def telemetry_out():
    if telemetry["data"] is None:
        return {"age": None}
    return {"age": time.time() - telemetry["t"], "source": telemetry["source"], "data": telemetry["data"]}


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-store"})


app.mount("/", StaticFiles(directory=STATIC), name="static")


def serve(open_browser: bool = True, port: int = PORT):
    import uvicorn
    if open_browser:
        threading.Timer(1.2, lambda: webbrowser.open(f"http://{HOST}:{port}/")).start()
    uvicorn.run(app, host=HOST, port=port, log_level="warning")


if __name__ == "__main__":
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else PORT   # e.g. one server per developer/agent
    print(f"Ball Drone flight sim on http://{HOST}:{port}  (Ctrl+C to stop)")
    serve(open_browser="--no-browser" not in sys.argv, port=port)
