"""Smoke test for Wasim's free-flight simulator (no missions or targets in the current game).

Starts the simulator server if port 8765 is free, drives Chromium, and records
evidence/simulation-smoke.json plus one screenshot per map. Checks per map: it loads, the drone climbs
and flies forward, motor power toggles off/on, the camera cycles, pause/resume works and frame rate is
sampled from the HUD. Also checks: posted telemetry is shown as text (no HTML injection), a level that
fails to load returns to the previous working level, no page errors and no requests leave localhost.
Illustrative game only: none of this validates the physical aircraft.
"""
import asyncio
import json
import platform
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
SIM = ROOT if (ROOT / 'server.py').exists() else ROOT / 'simulation'
URL = 'http://127.0.0.1:8765'
LEVELS = ['industrial', 'rescue', 'lab']


def reachable():
    try:
        return json.load(urllib.request.urlopen(URL + '/api/health', timeout=1)).get('ok') is True
    except OSError:
        return False


def commit():
    try:
        return subprocess.run(['git', '-C', str(SIM), 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


async def drone(page):
    return await page.evaluate('({pos: __game.drone.pos.toArray(), armed: __game.drone.armed, state: __game.G.state, '
                               'level: __game.G.id, cam: __game.G.cam, time: __game.G.time})')


async def hold(page, key, ms):
    await page.keyboard.down(key); await page.wait_for_timeout(ms); await page.keyboard.up(key)


async def main(gpu=False):
    server = None
    if not reachable():
        server = subprocess.Popen([sys.executable, 'server.py', '--no-browser'], cwd=SIM, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            if reachable(): break
            time.sleep(.1)
    checks, errors, external, sessions = [], [], [], []
    def check(name, ok, **detail):
        checks.append({'name': name, 'pass': bool(ok), **detail}); print(('PASS ' if ok else 'FAIL ') + name, flush=True)
    try:
        async with async_playwright() as p:
            args = ['--use-angle=metal', '--enable-gpu'] if gpu else ['--enable-unsafe-swiftshader']
            browser = await p.chromium.launch(args=args)
            page = await browser.new_page(viewport={'width': 1280, 'height': 800})
            page.on('pageerror', lambda error: errors.append(str(error)))
            async def route(r):
                if r.request.url.startswith(URL): await r.continue_()
                else: external.append(r.request.url); await r.abort()
            await page.route('**/*', route)
            await page.goto(URL, wait_until='domcontentloaded')
            await page.wait_for_function('!!window.__game', timeout=30000)
            for name in LEVELS:
                await page.evaluate('(n) => window.__game.start(n)', name)
                await page.wait_for_function('(n) => __game.G.state === "play" && __game.G.id === n', arg=name, timeout=180000)
                start = await drone(page)
                # Fixed-step flight through the game's own test API, independent of render speed.
                await page.evaluate('() => { __game.fly(["Space"], 1.0); __game.fly(["KeyW"], 1.0); }')
                moved = await drone(page)
                distance = sum((a - b) ** 2 for a, b in zip(moved['pos'], start['pos'])) ** .5
                check(f'{name}: drone climbs and flies', distance > .3 and moved['pos'][1] > start['pos'][1] - .05, metres=round(distance, 2))
                await page.keyboard.press('p'); await page.wait_for_timeout(200)
                off = (await drone(page))['armed']
                await page.keyboard.press('p'); await page.wait_for_timeout(200)
                check(f'{name}: motor power toggles', off is False and (await drone(page))['armed'] is True)
                cams = []
                for _ in range(3):
                    await page.keyboard.press('c'); await page.wait_for_timeout(150); cams.append((await drone(page))['cam'])
                check(f'{name}: camera cycles chase/FPV/orbit', sorted(cams) == ['chase', 'fpv', 'orbit'], cameras=cams)
                await page.wait_for_timeout(1500)
                fps = int(await page.inner_text('#s-fps') or 0)
                await page.screenshot(path=str(ROOT / 'evidence' / f'simulation-{name}.png'))
                sessions.append({'level': name, 'fps_hud': fps, 'moved_m': round(distance, 2), 'time_s': round(moved['time'], 2)})
            await page.keyboard.press('Escape')
            paused = (await drone(page))['state']
            await page.keyboard.press('Escape')
            check('pause and resume', paused == 'paused' and (await drone(page))['state'] == 'play')

            # Telemetry is untrusted: markup must render as text.
            payload = {'source': '<img src=x onerror=window.__pwned=1>', 'data': {'note': '<b id="injected">x</b>', 'battery_v': 7.6}}
            urllib.request.urlopen(urllib.request.Request(URL + '/api/telemetry', json.dumps(payload).encode(), {'Content-Type': 'application/json'}), timeout=2)
            await page.wait_for_function('!document.querySelector("#link").classList.contains("hidden")', timeout=5000)
            injected = await page.evaluate('!!document.querySelector("#link-body img, #injected") || !!window.__pwned')
            shown = await page.inner_text('#link-body')
            check('telemetry is displayed as text', not injected and '<b id="injected">' in shown)

            # A level whose module cannot load returns to the working level. Modules are cached per page,
            # so use a fresh page that never fetched rescue.js. Close the first page so two software-WebGL
            # contexts do not compete (an industrial load alone takes ~30 s without a GPU).
            await page.close()
            failing = await browser.new_page(viewport={'width': 960, 'height': 600})
            failing.on('pageerror', lambda error: errors.append(str(error)))
            async def block_rescue(r):
                if 'levels/rescue.js' in r.request.url: await r.abort()
                elif r.request.url.startswith(URL): await r.continue_()
                else: external.append(r.request.url); await r.abort()
            await failing.route('**/*', block_rescue)
            await failing.goto(URL, wait_until='domcontentloaded')
            await failing.wait_for_function('!!window.__game', timeout=30000)
            await failing.evaluate('() => window.__game.start("industrial")')
            await failing.wait_for_function('__game.G.state === "play" && __game.G.id === "industrial"', timeout=180000)
            await failing.evaluate('() => window.__game.start("rescue")')
            await failing.wait_for_timeout(800)
            await failing.wait_for_function('__game.G.state === "play" && __game.G.id === "industrial" && !__game.G.loading', timeout=180000)
            restored = await failing.evaluate('() => { const y0 = __game.drone.pos.y; __game.fly(["Space"], .5); '
                                              'return {colliders: __game.colliders.list.length, level: !!__game.G.level, climbed: __game.drone.pos.y - y0}; }')
            check('failed level load returns to the previous level', restored['colliders'] > 0 and restored['level'] and restored['climbed'] > .05,
                  attempted='rescue', **restored)
            await failing.close()
            await browser.close()
    finally:
        if server: server.terminate(); server.wait(timeout=10)
    check('no page errors', not errors, errors=errors[:5])
    check('no requests leave localhost', not external, requests=external[:5])
    result = {'environment': platform.platform(), 'browser': 'Playwright Chromium' + (' (GPU)' if gpu else ', software WebGL'),
              'simulation_commit': commit(), 'sessions': sessions, 'checks': checks, 'pass': all(c['pass'] for c in checks),
              'scope': 'Short free-flight smoke of the illustrative simulator; not a physical model validation.'}
    (ROOT / 'evidence').mkdir(exist_ok=True)
    (ROOT / 'evidence' / 'simulation-smoke.json').write_text(json.dumps(result, indent=2))
    print(json.dumps({k: result[k] for k in ('sessions', 'pass')}, indent=2))
    return 0 if result['pass'] else 1


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main('--gpu' in sys.argv)))
