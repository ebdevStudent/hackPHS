"""Pretend to be the physical drone: posts fake telemetry to the game backend once a second.
Replace the fake numbers with real values from the flight controller (e.g. MSP / MAVLink over serial) for the live demo.
Run:  python tools/telemetry_sim.py"""
import json, math, time, urllib.request

URL = "http://127.0.0.1:8765/api/telemetry"
t0 = time.time()
while True:
    t = time.time() - t0
    data = {"battery_v": 16.4 - t * 0.004, "roll_deg": 3 * math.sin(t * 0.7), "pitch_deg": 2 * math.cos(t * 0.5),
            "cage_rpm": abs(40 * math.sin(t * 0.2)), "rssi_dbm": -52 - 4 * math.sin(t * 0.3), "mode": "ANGLE"}
    req = urllib.request.Request(URL, json.dumps({"source": "ball-drone (sim)", "data": data}).encode(), {"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=1)
        print(f"sent {data['battery_v']:.2f} V")
    except OSError as e:
        print("backend not reachable:", e)
    time.sleep(1)
