// One explicitly authorized genuine included edit. Never runs automatically.
// The caller supplies a recorded UUID; no retry, publication or account action.
import assert from 'node:assert/strict';
import { mkdir } from 'node:fs/promises';
import { chromium } from '/Users/nirfeinstein/Documents/shelf/node_modules/playwright/index.mjs';
assert.equal(process.argv[2], '--go');
const requestId = process.argv[3];assert.match(requestId || '', /^[\da-f]{8}-[\da-f]{4}-4[\da-f]{3}-[89ab][\da-f]{3}-[\da-f]{12}$/);
const origin = 'https://open-world.gg', folder = 'qa/claude-beta';await mkdir(folder, { recursive: true });
const message = 'Add a small always-visible badge at the upper-right that says Synthetic QA. Keep all gameplay, controls and other text unchanged.';
console.log('PLANNED ' + JSON.stringify({ request_id: requestId, funding: 'included', message, session_id: null, current_version_id: null }));
const browser = await chromium.launch({ headless: true, executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', args: ['--enable-unsafe-swiftshader'] });
let page, posts = 0;
const errors = [];
try {
  const context = await browser.newContext({ viewport: { width: 375, height: 1000 }, isMobile: true, hasTouch: true });
  await context.addInitScript(() => {
    if (window !== top) return;
    localStorage.setItem('openworld.analytics.v1', 'off');Object.defineProperty(navigator, 'doNotTrack', { value: '1' });
    const original = window.fetch;
    window.fetch = async function(input, init) {
      const response = await original.call(this, input, init);
      if (new URL(typeof input === 'string' ? input : input.url, location.href).pathname === '/api/chat' && init?.method === 'POST') {
        const body = await response.clone().json(), safe = {};
        for (const key of ['session_id', 'version_id', 'version_number', 'detail', 'code', 'dispatched', 'included_remaining']) if (key in body) safe[key] = body[key];
        sessionStorage.setItem('ow_qa_response', JSON.stringify({ request_id: JSON.parse(init.body).request_id, status: response.status, body: safe }));
      }
      return response;
    };
  });
  await context.route('**/*', route => {
    const req = route.request(), url = new URL(req.url());
    if (url.origin === origin && !['GET', 'HEAD'].includes(req.method())) {
      if (url.pathname !== '/api/chat' || req.method() !== 'POST') return route.abort();
      const body = req.postDataJSON();assert.equal(++posts, 1);assert.equal(body.request_id, requestId);assert.equal(body.funding, 'included');
      assert.equal(body.message, message);assert.equal(body.session_id, null);assert.equal(body.current_version_id, null);assert.equal(body.api_key, undefined);assert.equal(body.image, undefined);
    }
    return route.continue();
  });
  page = await context.newPage();page.setDefaultTimeout(180000);page.on('pageerror', error => errors.push(error.message));
  await page.goto(origin + '/', { waitUntil: 'domcontentloaded' });
  await page.frameLocator('#ow-game').locator('#overlay').waitFor({ state: 'visible' });
  assert.ok(await page.frameLocator('#ow-game').locator('canvas').count());
  if (await page.locator('#ow-fab').isVisible()) await page.locator('#ow-fab').click();
  await page.locator('#ow-funding').waitFor();assert.equal(await page.locator('#ow-funding').inputValue(), 'included');
  await page.locator('#ow-included-status').filter({ hasText: 'included attempts' }).waitFor();
  // Preseed only the existing client idempotency reference, never identity or
  // a capability. The public actor still comes from its real random guest proof.
  await page.evaluate(async ({ requestId, message }) => {
    const material = JSON.stringify({ message, session_id: localStorage.getItem('ow_session_id'), current_version_id: localStorage.getItem('ow_current_version') });
    const bytes = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(material));
    const hash = [...new Uint8Array(bytes)].map(n => n.toString(16).padStart(2, '0')).join('');
    sessionStorage.setItem('ow_included_request', JSON.stringify({ id: requestId, hash }));
  }, { requestId, message });
  assert.equal(await page.evaluate(() => JSON.parse(sessionStorage.getItem('ow_included_request')).id), requestId);
  await page.locator('#ow-input').fill(message);
  const pending = page.waitForResponse(response => new URL(response.url()).pathname === '/api/chat' && response.request().method() === 'POST');
  const started = Date.now();await page.getByRole('button', { name: 'Send game change', exact: true }).click();
  const response = await pending;
  // The app deliberately navigates immediately on success. Capture the native
  // clone before returning it to the app; CDP body retrieval can lose that race.
  await page.waitForFunction(id => { try { return JSON.parse(sessionStorage.getItem('ow_qa_response'))?.request_id === id; } catch { return false; } }, requestId);
  const captured = await page.evaluate(() => JSON.parse(sessionStorage.getItem('ow_qa_response'))), body = captured.body;
  console.log('RESULT ' + JSON.stringify({ request_id: requestId, http: response.status(), elapsed_ms: Date.now() - started,
    version_id: body.version_id, session_id: body.session_id, version_number: body.version_number,
    detail: body.detail, code: body.code, dispatched: body.dispatched, included_remaining: body.included_remaining }));
  assert.equal(response.status(), 200);assert.ok(body.version_id);assert.ok(body.version_number > 0);
  await page.waitForURL(url => url.pathname === '/v/' + body.version_id);
  if (await page.locator('#ow-panel.ow-open').count()) await page.locator('#ow-panel-close').click();
  const guestVersions = await page.evaluate(async session => {
    const r = await fetch('/api/versions/' + session, { headers: { 'X-OpenWorld-Guest': localStorage.getItem('ow_guest_token') } });
    if (!r.ok) throw Error('Owned QA versions unavailable');return r.json();
  }, body.session_id);
  assert.equal(guestVersions.length, 2);assert.ok(guestVersions.some(version => version.version_number === 0));
  assert.ok(guestVersions.every(version => !version.is_shared && !version.is_published));
  assert.equal((await context.request.get(origin + '/game/version/' + body.version_id)).status(), 404, 'Generated version is private without its guest proof');
  const checkGame = async (screen, width) => {
    const frame = screen.frameLocator('#ow-game'), badge = frame.getByText('Synthetic QA', { exact: true });
    await badge.waitFor();await frame.locator('#overlay').waitFor({ state: 'visible' });assert.ok(await frame.locator('canvas').count());
    const box = await badge.evaluate(el => { const b = el.getBoundingClientRect();return { top: b.top, right: b.right, left: b.left, width: b.width, height: b.height, viewport: innerWidth }; });
    assert.ok(box.top >= 0 && box.top < 100 && box.right <= box.viewport + 1 && box.left >= box.viewport - 300 && box.width <= 250 && box.height <= 80);
    await screen.screenshot({ path: `${folder}/real-anchor-ready-${width}.jpg`, type: 'jpeg', quality: 72 });
    await frame.locator('#overlay').click();await frame.locator('#overlay').waitFor({ state: 'hidden' });
    assert.equal(await frame.locator('#hud').evaluate(node => getComputedStyle(node).display), 'block');
    if (width === 375) await frame.locator('body.playing').waitFor({ state: 'attached' });
    await badge.waitFor();
    if (width === 375) { await frame.locator('#btn-veh-m').click();await frame.locator('#veh-menu.open').waitFor({ state: 'visible' });await badge.waitFor(); }
    await frame.locator('body').evaluate(() => { if (document.fullscreenElement) void document.exitFullscreen();if (document.pointerLockElement) document.exitPointerLock(); });
    assert.equal(await screen.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1), false);
    await screen.screenshot({ path: `${folder}/real-anchor-play-${width}.jpg`, type: 'jpeg', quality: 72 });
    console.log(`${width}: genuine private version, exact upper-right badge, real canvas/Start and retained gameplay controls passed.`);
  };
  await checkGame(page, 375);
  const state = await context.storageState(); // synthetic guest capability stays in memory only
  const desktop = await browser.newContext({ viewport: { width: 1440, height: 1000 }, storageState: state });
  await desktop.addInitScript(() => { if (window !== top) return;Object.defineProperty(navigator, 'doNotTrack', { value: '1' }); });
  await desktop.route('**/*', route => new URL(route.request().url()).origin === origin && !['GET', 'HEAD'].includes(route.request().method()) ? route.abort() : route.continue());
  const wide = await desktop.newPage();wide.setDefaultTimeout(180000);wide.on('pageerror', error => errors.push(error.message));
  await wide.goto(origin + '/v/' + body.version_id, { waitUntil: 'domcontentloaded' });
  if (await wide.locator('#ow-panel.ow-open').count()) await wide.locator('#ow-panel-close').click();
  await checkGame(wide, 1440);
  assert.equal(posts, 1);assert.deepEqual(errors, []);
  console.log('PASS ' + JSON.stringify({ request_id: requestId, version_id: body.version_id, session_id: body.session_id,
    private_versions: guestVersions.length, posts, real_provider_attempts: 1, published: false, errors }));
  await desktop.close();await context.close();
} catch (error) {
  console.log('STOP: no automatic retry; reconcile the recorded request ID. ' + JSON.stringify({ request_id: requestId, posts, error: error.message, page_errors: errors }));
  if (page) await page.screenshot({ path: `${folder}/real-anchor-incomplete.jpg`, type: 'jpeg', quality: 70 }).catch(() => {});
  throw error;
} finally { await browser.close(); }
