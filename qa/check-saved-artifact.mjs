// Render genuine recovered model output, not a provider/game double. This is
// local artifact/sandbox QA, not a reopened production private URL/auth test.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { writeFile } from 'node:fs/promises';
import { chromium } from '/Users/nirfeinstein/Documents/shelf/node_modules/playwright/index.mjs';
const child = spawn('app/venv/bin/python', ['qa/render-saved-game.py', '.runtime/claude-anchor-artifact/generated.html'], { stdio: ['ignore', 'pipe', 'pipe'] });
let output = '', browser;
child.stdout.on('data', value => { output += value; });child.stderr.on('data', value => { output += value; });
const wait = async predicate => { const until = Date.now() + 30000;while (!predicate()) { assert.equal(child.exitCode, null, output.slice(-1000));if (Date.now() > until) throw Error('Artifact renderer did not start');await new Promise(resolve => setTimeout(resolve, 100)); } };
try {
  await wait(() => output.includes('ARTIFACT_RENDER '));
  const base = JSON.parse(output.split('\n').find(line => line.startsWith('ARTIFACT_RENDER ')).slice(16)).base;
  browser = await chromium.launch({ headless: true, executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', args: ['--enable-unsafe-swiftshader'] });
  for (const width of [375, 1440]) {
    const context = await browser.newContext({ viewport: { width, height: 1000 }, ...(width === 375 ? { isMobile: true, hasTouch: true } : {}) });
    const errors = [], writes = [], unexpectedHosts = [];
    await context.addInitScript(() => { if (window !== top) return;localStorage.setItem('openworld.analytics.v1', 'off');Object.defineProperty(navigator, 'doNotTrack', { value: '1' }); });
    await context.route('**/*', route => {
      const request = route.request(), url = new URL(request.url());
      if (!['GET', 'HEAD'].includes(request.method())) { writes.push(url.pathname);return route.abort(); }
      if (url.origin !== base && !['cdn.jsdelivr.net', 'unpkg.com'].includes(url.hostname)) { unexpectedHosts.push(url.hostname);return route.abort(); }
      return route.continue();
    });
    const page = await context.newPage();page.setDefaultTimeout(90000);page.on('pageerror', error => errors.push(error.message));
    await page.goto(base + '/', { waitUntil: 'domcontentloaded' });
    if (await page.locator('#ow-panel.ow-open').count()) await page.locator('#ow-panel-close').click();
    const frame = page.frameLocator('#ow-game');await frame.locator('#overlay').waitFor({ state: 'visible' });
    const badge = frame.getByText('Synthetic QA', { exact: true });await badge.waitFor();assert.ok(await frame.locator('canvas').count());
    const geometry = await badge.evaluate(node => { const b = node.getBoundingClientRect();return { top: b.top, left: b.left, right: b.right, width: b.width, height: b.height, viewport: innerWidth }; });
    assert.ok(geometry.top >= 0 && geometry.top < 100 && geometry.right <= geometry.viewport + 1 && geometry.left >= geometry.viewport - 300 && geometry.width <= 250 && geometry.height <= 80);
    assert.equal(await frame.locator('body').evaluate(() => { try { parent.localStorage.getItem('ow_token');return 'readable'; } catch { return 'blocked'; } }), 'blocked');
    await page.screenshot({ path: `qa/claude-beta/actual-artifact-ready-${width}.jpg`, type: 'jpeg', quality: 74 });
    if (width === 375) await frame.locator('#overlay').tap();else await frame.locator('#overlay').click();
    await frame.locator('#overlay').waitFor({ state: 'hidden' });
    assert.equal(await frame.locator('#hud').evaluate(node => getComputedStyle(node).display), 'block');
    if (width === 375) await frame.locator('body.playing').waitFor({ state: 'attached' });
    await badge.waitFor();
    if (width === 375) { await frame.locator('#btn-veh-m').tap();await frame.locator('#veh-menu.open').waitFor({ state: 'visible' });await badge.waitFor(); }
    await frame.locator('body').evaluate(() => { if (document.fullscreenElement) void document.exitFullscreen();if (document.pointerLockElement) document.exitPointerLock(); });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false);
    await page.screenshot({ path: `qa/claude-beta/actual-artifact-play-${width}.jpg`, type: 'jpeg', quality: 74 });
    assert.deepEqual(errors, []);assert.deepEqual(writes, []);assert.deepEqual(unexpectedHosts, []);
    console.log(`${width}: actual saved model/parser artifact shows the small upper-right badge before and after Start, live canvas/gameplay and ${width === 375 ? 'mobile vehicle menu' : 'desktop HUD'}; opaque storage isolation, no overflow/page errors, no writes/model/account/mail. Local rendering, not reopened private production URL.`);
    await context.close();
  }
} finally {
  await browser?.close();child.kill('SIGTERM');
  await new Promise(resolve => { if (child.exitCode !== null) resolve();else child.once('exit', resolve); });
  await writeFile('qa/claude-beta-artifact-server.log', output);
}
