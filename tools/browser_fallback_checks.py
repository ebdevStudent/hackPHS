"""Real-browser checks for the manual-fallback screen and the 2026-10-08 operator fixes.

Starts its own server (port 8084, fixed test token), drives Chromium and saves
evidence/browser-fallback-checks.json plus screenshots. No aircraft hardware.
"""
import asyncio
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
URL = 'http://127.0.0.1:8084'
TOKEN = 'fallback-check-only-not-a-deployment-secret'
HEADERS = {'Authorization': 'Bearer ' + TOKEN}
STATUS = 'Manual steering — computer steering unavailable'


async def wait_state(client, predicate, timeout=6):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = (await client.get('/api/state')).json()
        if predicate(state): return state
        await asyncio.sleep(.05)
    raise AssertionError('server state condition not reached')


async def unlock(page):
    await page.click('#operator-open')
    await page.fill('#token', TOKEN)
    await page.click('#login-form button[type=submit]')
    await page.wait_for_selector('#operator-panel:not(.hidden)')


async def main(output):
    data = Path(tempfile.mkdtemp(prefix='ball-fallback-'))
    env = {**os.environ, 'BALL_OPERATOR_TOKEN': TOKEN, 'PYTHONPATH': str(ROOT / 'software')}
    server = subprocess.Popen([sys.executable, '-m', 'ball_demo.cli', 'serve', '--port', '8084', '--data', str(data)],
                              cwd=ROOT / 'software', env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    checks, page_errors, external = [], [], []
    def check(name, passed, **detail):
        checks.append({'name': name, 'pass': bool(passed), **detail})
        print(('PASS ' if passed else 'FAIL ') + name, flush=True)
    try:
        async with httpx.AsyncClient(base_url=URL, timeout=3) as client:
            for _ in range(100):
                try:
                    if (await client.get('/api/health')).json()['ok']: break
                except httpx.HTTPError: pass
                await asyncio.sleep(.1)
            await client.post('/api/operator/source', headers=HEADERS, json={'kind': 'synthetic', 'scenario': 'centered'})
            async with async_playwright() as p:
                browser = await p.chromium.launch()
                context = await browser.new_context(viewport={'width': 1280, 'height': 900})
                async def block_external(route):
                    if not route.request.url.startswith(URL):
                        external.append(route.request.url); await route.abort()
                    else: await route.continue_()
                await context.route('**/*', block_external)
                page = await context.new_page()
                page.on('pageerror', lambda error: page_errors.append(str(error)))

                # Fallback screen
                await page.goto(URL + '/fallback')
                await page.wait_for_function("document.querySelector('#source').textContent === 'SYNTHETIC'")
                await page.wait_for_function("!document.querySelector('#marker').classList.contains('hidden')")
                text = await page.inner_text('#steering')
                warning = await page.inner_text('#source-warning')
                await page.screenshot(path=str(output / 'fallback-screen.png'))
                check('fallback screen shows the required status and indicator', text == STATUS and 'not live FPV' in warning,
                      status=text, warning=warning, error=await page.inner_text('#error'))
                natural = await page.evaluate("document.querySelector('#video').naturalWidth")
                check('fallback screen shows the server video with box', natural == 640, natural_width=natural)

                # Monitor: banner, stale overlay rendering
                await page.goto(URL + '/')
                await page.wait_for_function("document.querySelector('#connection').textContent === 'Connected'")
                check('monitor shows steering status', await page.inner_text('#steering-status') == STATUS)
                stale = await page.evaluate("""() => { const s = JSON.parse(JSON.stringify(currentState)); s.frame_age_ms = null;
                    renderState(s); return !document.querySelector('#video-stale').classList.contains('hidden')
                    && document.querySelector('#error-marker').classList.contains('hidden'); }""")
                check('monitor marks stale video separately from connection', stale)

                # Replay import validation keeps the previous playback
                await page.click('#sandbox-tab')
                await page.wait_for_function('playback !== null && playback.samples.length > 0')
                bad = output / 'bad-replay.json'
                bad.write_text(json.dumps({'samples': [{'t': 'soon', 'state': 'LOCKED', 'yaw': 5}]}))
                before = await page.evaluate('playback.samples.length')
                await page.set_input_files('#replay-file', str(bad))
                await page.wait_for_function("document.querySelector('#sandbox-state').textContent.includes('timestamp')")
                after = await page.evaluate('playback.samples.length')
                check('invalid replay is rejected without replacing playback', before == after and before > 0,
                      message=await page.inner_text('#sandbox-state'))
                await page.click('#monitor-tab')

                # Ordering: a slow enable followed by disable must end disabled
                await unlock(page)
                await wait_state(client, lambda s: s['frames'] > 5)
                async def slow_enable(route):
                    body = route.request.post_data or ''
                    if '"enabled":true' in body.replace(' ', ''): await asyncio.sleep(.6)
                    await route.continue_()
                await page.route('**/api/operator/assist', slow_enable)
                await page.click('#enable')
                await page.click('#disable')
                await asyncio.sleep(1.2)
                state = (await client.get('/api/state')).json()
                check('disable cannot be overtaken by an earlier enable', state['enabled'] is False and state['yaw'] == 0, state=state['state'])
                await page.unroute('**/api/operator/assist', slow_enable)

                # Lock requests neutral before giving up the token
                await page.click('#enable')
                await wait_state(client, lambda s: s['enabled'])
                await page.click('#operator-lock')
                state = await wait_state(client, lambda s: not s['enabled'])
                await page.wait_for_selector('#operator-panel', state='hidden')
                check('lock disables assistance first', state['yaw'] == 0)

                # Colour pick from the live preview (centred synthetic target)
                await unlock(page)
                await client.post('/api/operator/settings', headers=HEADERS, json={'hue_low': 0, 'hue_high': 179})
                await page.click('#pick-toggle')
                box = await page.locator('#preview').bounding_box()
                await page.mouse.click(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
                await page.wait_for_function("document.querySelector('#operator-message').textContent.includes('hue')")
                settings = (await client.get('/api/state')).json()['settings']
                # The synthetic target is BGR (50, 220, 105): OpenCV hue 50.
                check('click-to-pick sets a hue range around the target from the video',
                      settings['hue_low'] <= 50 <= settings['hue_high'] and settings['hue_high'] - settings['hue_low'] <= 40,
                      settings={k: settings[k] for k in ('hue_low', 'hue_high', 'saturation_min', 'value_min')})
                await page.screenshot(path=str(output / 'fallback-monitor.png'), full_page=True)

                # Lease: an enabled operator page that disappears stops assistance
                await page.click('#enable')
                await wait_state(client, lambda s: s['state'] == 'LOCKED')
                await page.close()
                state = await wait_state(client, lambda s: s['fault'] == 'operator connection lost', timeout=5)
                check('closing the operator page lapses the lease to neutral', not state['enabled'] and state['yaw'] == 0)
                await browser.close()
    finally:
        server.terminate()
        server.wait(timeout=10)
    check('no page errors', not page_errors, errors=page_errors)
    check('no external requests', not external, requests=external)
    result = {'environment': platform.platform(), 'browser': 'Playwright Chromium', 'checks': checks,
              'pass': all(c['pass'] for c in checks),
              'scope': 'Synthetic source and mock bridge on a local server; not live FPV, Pi or radio behaviour.'}
    (output / 'browser-fallback-checks.json').write_text(json.dumps(result, indent=2))
    print(output / 'browser-fallback-checks.json')
    return 0 if result['pass'] else 1


if __name__ == '__main__':
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'evidence' / 'fallback-2026-10-08'
    target.mkdir(parents=True, exist_ok=True)
    raise SystemExit(asyncio.run(main(target)))
