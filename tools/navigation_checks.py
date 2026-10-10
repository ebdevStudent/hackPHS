"""Hardware-free real-browser navigation smoke; preserves fresh evidence directories."""
import argparse
import asyncio
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
from playwright.async_api import async_playwright

from ball_demo.navigation_fixtures import example_recording
from ball_demo.navigation_replay import replay, simulation

ROOT = Path(__file__).resolve().parents[1]


async def main(output):
    output.mkdir(parents=True, exist_ok=False)
    runtime = ROOT / 'software/runs/navigation-browser-check'
    runtime.mkdir(parents=True, exist_ok=True)
    recording = example_recording()
    (runtime / 'session.json').write_text(recording.model_dump_json())
    (runtime / 'bundle.json').write_text(recording.bundle.model_dump_json())
    (runtime / 'demo.json').write_text(json.dumps(simulation(recording)))
    token, url = 'navigation-local-test-token', 'http://127.0.0.1:8093'
    env = {**os.environ, 'BALL_OPERATOR_TOKEN': token, 'PYTHONPATH': str(ROOT / 'software')}
    process = subprocess.Popen([sys.executable, '-m', 'ball_demo.cli', 'serve', '--port', '8093', '--data', str(runtime / 'runs'), '--nav-replay', str(runtime / 'session.json')], cwd=ROOT / 'software', env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    checks, errors, mutations = [], [], []
    report = {'environment': platform.platform(), 'python': sys.version, 'scope': 'Mac Chromium and synthetic/mock navigation only; no Pi/D435/radio/aircraft test', 'started_utc': datetime.now(timezone.utc).isoformat()}
    try:
        async with httpx.AsyncClient(base_url=url, timeout=5) as client:
            for i in range(100):
                if process.poll() is not None: raise RuntimeError('Navigation test backend exited')
                try:
                    if (await client.get('/api/health')).status_code == 200: break
                except httpx.RequestError: pass
                await asyncio.sleep(.05)
            else: raise RuntimeError('Backend did not become ready')
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch()
                context = await browser.new_context(viewport={'width': 1280, 'height': 900})
                await context.route('**/*', lambda route: route.continue_() if route.request.url.startswith(url) else route.abort())
                page = await context.new_page()
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.on('request', lambda request: mutations.append(request.url) if request.method == 'POST' else None)
                await page.goto(url, wait_until='domcontentloaded')
                await page.wait_for_function("document.querySelector('#connection').textContent==='Connected'")
                assert 'Pilot' in await page.locator('#nav-authority').inner_text() or 'pilot' in await page.locator('#nav-authority').inner_text()
                assert 'computer steering unavailable' in await page.locator('#steering-status').inner_text()
                checks.append('manual fallback and pilot authority visible')
                assert (await client.post('/api/operator/navigation', json={'action': 'resume'})).status_code == 401
                checks.append('unauthorized navigation mutation denied')
                before = (await client.get('/api/state')).json()
                posts = len(mutations)
                await page.set_input_files('#nav-replay-file', str(runtime / 'demo.json'))
                await page.wait_for_function("document.querySelector('#nav-label').textContent.includes('LOCAL REPLAY')")
                await page.click('#nav-replay-play')
                await page.wait_for_function("document.querySelector('#nav-status').textContent==='advisory route'")
                await page.screenshot(path=str(output / 'route.png'), full_page=True)
                await page.wait_for_function("document.querySelector('#nav-status').textContent==='goal reached'")
                after = (await client.get('/api/state')).json()
                assert before['source'] == after['source'] and before['settings'] == after['settings']
                assert not after['enabled'] and after['yaw'] == 0 and len(mutations) == posts
                checks.append('local estimated-vision waypoint playback reaches goal without shared mutations')
                await page.screenshot(path=str(output / 'desktop.png'), full_page=True)
                await page.set_viewport_size({'width': 390, 'height': 844})
                assert await page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
                assert await page.evaluate("Math.abs(document.querySelector('#nav-map').clientWidth / document.querySelector('#nav-map').clientHeight - 640/260) < .03")
                await page.screenshot(path=str(output / 'phone.png'), full_page=True)
                checks.append('desktop/phone navigation layout without horizontal overflow')
                await page.set_viewport_size({'width': 1280, 'height': 900})
                await page.click('#nav-live')
                await page.click('#operator-open'); await page.fill('#token', token)
                await page.click('#login-form button[type=submit]')
                await page.wait_for_selector('#operator-panel:not(.hidden)')
                await page.set_input_files('#nav-bundle-file', str(runtime / 'bundle.json'))
                await page.wait_for_function("document.querySelector('#operator-message').textContent.includes('bundle loaded')")
                await page.fill('#nav-goal', '2.2 1.5 1.3'); await page.click('#nav-goal-apply')
                await page.wait_for_function("document.querySelector('#operator-message').textContent.includes('Goal set')")
                await page.click('#nav-disable')
                await page.wait_for_function("document.querySelector('#operator-message').textContent.includes('Guidance stopped')")
                after = (await client.get('/api/state')).json()
                assert not after['enabled'] and after['yaw'] == 0 and not after['navigation']['guidance_enabled']
                checks.append('authorized bundle/goal/stop preserve MANUAL yaw and suppress guidance')
                assert not errors
                await context.close(); await browser.close()
        report.update(checks=checks, browser_errors=errors, passed=True)
    except Exception as error:
        report.update(checks=checks, browser_errors=errors, passed=False, error=f'{type(error).__name__}: {error}')
        raise
    finally:
        if process.poll() is None:
            process.terminate()
            try: process.wait(timeout=5)
            except subprocess.TimeoutExpired: process.kill(); process.wait(timeout=2)
        report['finished_utc'] = datetime.now(timezone.utc).isoformat()
        files = [*ROOT.joinpath('software/ball_demo').rglob('*.py'), *ROOT.joinpath('software/ball_demo/static').glob('*'), Path(__file__)]
        report['source_hashes'] = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in files if path.is_file()}
        (output / 'report.json').write_text(json.dumps(report, indent=2))
        (output / 'SHA256SUMS.json').write_text(json.dumps({path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in output.iterdir() if path.is_file() and path.name != 'SHA256SUMS.json'}, indent=2))
        print(output / 'report.json')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    asyncio.run(main(parser.parse_args().output.resolve()))
