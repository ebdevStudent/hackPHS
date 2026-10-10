"""Six real Chromium sessions, API timing and isolation checks; duration is measured."""
import argparse
import asyncio
import json
import platform
import time
from pathlib import Path

import httpx
from playwright.async_api import async_playwright


async def run(args):
    token = Path(args.token_file).read_text().strip()
    headers = {'Authorization': 'Bearer ' + token}
    failures, samples, console_errors = [], [], []
    started = time.monotonic()
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        contexts, pages = [], []
        for index in range(6):
            context = await browser.new_context(viewport={'width': 390 if index % 2 else 1280, 'height': 844 if index % 2 else 900})
            page = await context.new_page()
            page.on('pageerror', lambda error: console_errors.append(str(error)))
            await page.goto(args.url, wait_until='domcontentloaded')
            await page.wait_for_function("document.querySelector('#connection').textContent === 'Connected'")
            contexts.append(context)
            pages.append(page)
        await pages[0].click('#operator-open')
        await pages[0].fill('#token', token)
        await pages[0].click('#login-form button[type=submit]')
        await pages[0].wait_for_selector('#operator-panel:not(.hidden)')
        async with httpx.AsyncClient(base_url=args.url, timeout=3) as client:
            await client.post('/api/operator/assist', headers=headers, json={'enabled': True})
            await pages[0].screenshot(path=args.output + '-start.png', full_page=True)
            deadline = started + args.seconds
            rounds = 0
            while time.monotonic() < deadline:
                tick = time.monotonic()
                response = await client.get('/api/state')
                latency = (time.monotonic() - tick) * 1000
                s = response.json()
                if abs(s['yaw']) > s['settings']['max_yaw']: failures.append('command bound')
                if s['state'] != 'LOCKED' and s['yaw'] != 0: failures.append('non-neutral non-locked')
                if response.status_code != 200: failures.append('state API')
                samples.append({'t': time.monotonic() - started, 'latency_ms': latency, 'frames': s['frames'], 'state': s['state'], 'yaw': s['yaw']})
                if rounds % 12 == 0:
                    for page in pages:
                        if await page.locator('#connection').inner_text() != 'Connected': failures.append('viewer stale')
                        if await page.evaluate('document.documentElement.scrollWidth > innerWidth'): failures.append('layout overflow')
                        if not await page.locator('#preview').evaluate('(img)=>img.naturalWidth>0'): failures.append('preview absent')
                    before = (await client.get('/api/state')).json()
                    await pages[1].click('#sandbox-tab')
                    await pages[1].select_option('#sandbox-scenario', 'loss')
                    await pages[1].click('#sandbox-play')
                    await pages[1].click('#monitor-tab')
                    after = (await client.get('/api/state')).json()
                    if before['source'] != after['source'] or before['settings'] != after['settings']: failures.append('sandbox changed shared state')
                    if (await client.post('/api/operator/assist', json={'enabled': True})).status_code != 401: failures.append('visitor operator access')
                if rounds % 120 == 60:
                    await client.post('/api/operator/fault', headers=headers, json={'fault': 'disconnect'})
                    await asyncio.sleep(.4)
                    fault = (await client.get('/api/state')).json()
                    if fault['state'] != 'FAULT' or fault['yaw'] != 0: failures.append('disconnect fault')
                    await client.post('/api/operator/fault', headers=headers, json={'fault': 'none'})
                    await asyncio.sleep(.15)
                    if (await client.get('/api/state')).json()['enabled']: failures.append('automatic enable')
                    await client.post('/api/operator/assist', headers=headers, json={'enabled': True})
                rounds += 1
                if rounds % 12 == 0: print(f'{time.monotonic()-started:.0f}s: six sessions; {len(failures)} failures', flush=True)
                await asyncio.sleep(min(5, max(0, deadline - time.monotonic())))
            await client.post('/api/operator/assist', headers=headers, json={'enabled': False})
            final = (await client.get('/api/state')).json()
            await pages[0].screenshot(path=args.output + '-end.png', full_page=True)
        await browser.close()
    elapsed = time.monotonic() - started
    latencies = sorted(s['latency_ms'] for s in samples)
    report = {'environment': platform.platform(), 'python': platform.python_version(), 'duration_s': elapsed,
              'requested_s': args.seconds, 'browser_sessions': 6, 'operator_sessions': 1, 'viewer_sessions': 5,
              'samples': len(samples), 'api_latency_ms_p95': latencies[int(.95 * (len(latencies)-1))],
              'api_latency_ms_max': max(latencies), 'final': final, 'failures': failures,
              'console_errors': console_errors, 'pass': not failures and not console_errors and elapsed >= args.seconds}
    Path(args.output + '.json').write_text(json.dumps(report, indent=2))
    Path(args.output + '-samples.json').write_text(json.dumps(samples))
    print(json.dumps({k: v for k, v in report.items() if k not in ['final', 'failures', 'console_errors']}), flush=True)
    if not report['pass']: raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:8080')
    parser.add_argument('--seconds', type=int, default=1800)
    parser.add_argument('--token-file', default='software/runs/operator-token')
    parser.add_argument('--output', default='evidence/mac-rehearsal')
    asyncio.run(run(parser.parse_args()))
