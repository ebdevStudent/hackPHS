import asyncio
import atexit
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

import httpx
import cv2
from ball_demo.config import Settings
from ball_demo.sources import synthetic
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
URL = 'http://127.0.0.1:8081'
TOKEN = 'browser-check-only-not-a-deployment-secret'


async def main():
    output = ROOT / 'evidence'
    clip = ROOT / 'software/runs/browser-fixture.avi'
    clip.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(clip), cv2.VideoWriter_fourcc(*'MJPG'), 20, (640, 480))
    for i in range(40): writer.write(synthetic(i, Settings())[0])
    writer.release()
    env = {**os.environ, 'BALL_OPERATOR_TOKEN': TOKEN}
    def launch():
        return subprocess.Popen([sys.executable, '-m', 'ball_demo.cli', 'serve', '--port', '8081', '--data', str(ROOT / 'software/runs/browser')], cwd=ROOT / 'software', env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    process = launch()
    atexit.register(lambda: process.terminate() if process.poll() is None else None)
    checks, errors, requests = [], [], []
    async with httpx.AsyncClient(base_url=URL, timeout=3) as client:
        for _ in range(100):
            try:
                if (await client.get('/api/health')).status_code == 200: break
            except httpx.RequestError: pass
            await asyncio.sleep(.1)
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            context = await browser.new_context(viewport={'width': 1280, 'height': 900}, record_video_dir=str(output / 'raw/walkthrough'), record_video_size={'width': 1280, 'height': 900})
            # Deny all external traffic while permitting the local demonstration.
            await context.route('**/*', lambda route: route.continue_() if route.request.url.startswith(URL) else route.abort())
            page = await context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('request', lambda request: requests.append(request.url))
            await page.goto(URL, wait_until='domcontentloaded')
            await page.wait_for_function("document.querySelector('#connection').textContent==='Connected'")
            await page.wait_for_function("document.querySelector('#preview').naturalWidth===640")
            assert await page.locator('#source-label').inner_text() == 'SYNTHETIC'
            checks.append('offline local assets and synthetic preview')
            assert (await client.post('/api/operator/assist', json={'enabled': True})).status_code == 401
            await page.click('#operator-open'); await page.fill('#token', 'incorrect'); await page.click('#login-form button[type=submit]')
            await page.wait_for_function("document.querySelector('#login-error').textContent.includes('token')")
            await page.fill('#token', TOKEN); await page.click('#login-form button[type=submit]')
            await page.wait_for_selector('#operator-panel:not(.hidden)')
            await page.click('#enable')
            await page.locator('.workspace').scroll_into_view_if_needed()
            await page.wait_for_function("document.querySelector('#state').textContent==='LOCKED'")
            checks.append('operator token and stable acquisition')
            await page.wait_for_timeout(2500)
            await page.screenshot(path=str(output / 'dashboard-desktop.png'), full_page=True)
            auth = {'Authorization': 'Bearer ' + TOKEN}
            await page.click('#sandbox-tab')
            before = (await client.get('/api/state')).json()
            await page.select_option('#sandbox-scenario', 'loss'); await page.click('#sandbox-play'); await page.wait_for_timeout(400)
            after = (await client.get('/api/state')).json()
            assert before['source'] == after['source'] and before['settings'] == after['settings'] and after['enabled']
            checks.append('sandbox source/settings/bridge isolation')
            await page.set_input_files('#replay-file', str(output / 'demonstration-replay.json'))
            await page.wait_for_timeout(200)
            assert (await client.get('/api/state')).json()['enabled']
            await page.click('#sandbox-play')
            await page.wait_for_timeout(300)
            await page.click('#sandbox-play')
            await page.locator('.timeline summary').click()
            assert await page.locator('#playback-events li').count() > 0
            checks.append('local replay event timeline remains isolated')
            await page.click('#monitor-tab')
            await page.select_option('#source-kind', 'recorded')
            await page.fill('#source-path', str(clip))
            await page.click('#source-apply')
            await page.wait_for_function("document.querySelector('#source-label').textContent==='RECORDED'")
            await page.wait_for_timeout(250)
            await page.click('#enable')
            await page.locator('.workspace').scroll_into_view_if_needed()
            await page.wait_for_function("document.querySelector('#state').textContent==='LOCKED'")
            await page.wait_for_function("document.querySelector('#state').textContent==='MANUAL'")
            assert (await client.get('/api/state')).json()['yaw'] == 0
            checks.append('recorded badge and normal EOF disable')
            await page.select_option('#source-kind', 'synthetic')
            await page.select_option('#operator-scenario', 'loss'); await page.click('#source-apply'); await page.wait_for_timeout(350); await page.click('#enable')
            await page.wait_for_function("document.querySelector('#state').textContent==='LOCKED'")
            await page.wait_for_function("document.querySelector('#state').textContent==='SEARCHING'")
            assert (await client.get('/api/state')).json()['yaw'] == 0
            await page.wait_for_timeout(1200)
            await page.locator('.workspace').scroll_into_view_if_needed()
            checks.append('target loss visible and neutral')
            await page.select_option('#operator-scenario', 'freeze'); await page.click('#source-apply'); await page.wait_for_timeout(350); await page.click('#enable')
            await page.wait_for_function("document.querySelector('#state').textContent==='FAULT'")
            assert 'stale frame' in await page.locator('#fault-box').inner_text()
            await page.locator('.workspace').scroll_into_view_if_needed()
            await page.screenshot(path=str(output / 'dashboard-fault.png'), full_page=True)
            await page.wait_for_timeout(1500)
            checks.append('frozen input visible fault')
            await page.click('#reset'); await page.wait_for_timeout(350); await page.click('#enable')
            await page.get_by_text('Bridge fault demonstration', exact=True).click()
            await page.select_option('#bridge-fault', 'disconnect'); await page.click('#fault-apply')
            await page.wait_for_function("document.querySelector('#state').textContent==='FAULT'")
            assert 'acknowledgement' in await page.locator('#fault-box').inner_text()
            await page.locator('.workspace').scroll_into_view_if_needed()
            await page.wait_for_timeout(1500)
            await page.select_option('#bridge-fault', 'none'); await page.click('#fault-apply')
            await page.wait_for_function("document.querySelector('#state').textContent==='MANUAL'")
            assert (await client.get('/api/state')).json()['yaw'] == 0
            checks.append('bridge disconnect and recovery stays disabled')
            process.terminate(); await asyncio.to_thread(process.wait, 10)
            await page.wait_for_function("document.querySelector('#connection').textContent!=='Connected'")
            await page.wait_for_timeout(1700)
            process = launch()
            await page.wait_for_function("document.querySelector('#connection').textContent==='Connected'", timeout=15000)
            await page.wait_for_function("document.querySelector('#state').textContent==='MANUAL'", timeout=15000)
            assert not (await client.get('/api/state')).json()['enabled']
            checks.append('stream disconnect and browser reconnection stays disabled')
            checks.append('server restart new MANUAL session')
            await page.set_viewport_size({'width': 390, 'height': 844})
            await page.click('#operator-lock')
            assert not await page.evaluate('document.documentElement.scrollWidth > innerWidth')
            await page.screenshot(path=str(output / 'dashboard-phone.png'), full_page=True)
            checks.append('phone layout no horizontal overflow')
            video = page.video
            await context.close()
            await video.save_as(str(output / 'walkthrough.webm'))
            await browser.close()
    process.terminate(); await asyncio.to_thread(process.wait, 10)
    assert not errors, errors
    assert all(url.startswith(URL) for url in requests)
    report = {'environment': platform.platform(), 'checks': checks, 'page_errors': errors, 'external_requests': [], 'pass': True,
              'offline_scope': 'Browser external requests blocked; localhost remains accessible. Mac networking was not changed.'}
    (output / 'browser-checks.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__': asyncio.run(main())
