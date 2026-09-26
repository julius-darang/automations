/* Optional real-browser checks. See README for the isolated Playwright install. */
const assert = require('node:assert/strict');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {});
  const url = pathToFileURL(path.resolve(__dirname, '../index.html')).href;
  const defaults = ['weather', 'quote', 'headlines', 'ai_pricing', 'crypto'];
  const requests = [];
  const errors = [];
  const observe = page => {
    page.on('request', r => requests.push(r.url()));
    page.on('pageerror', e => errors.push(e.message));
  };
  const selected = page => page.locator('.demo-email-section').evaluateAll(nodes => nodes.map(n => n.dataset.plugin));
  const library = page => page.locator('.plugin-row').evaluateAll(nodes => nodes.map(n => n.dataset.id));
  const checked = page => page.locator('.plugin-row:has(input:checked)').evaluateAll(nodes => nodes.map(n => n.dataset.id));
  const reset = page => page.locator('#demo-reset').click();
  const handle = (page, id) => page.locator(`[data-plugin="${id}"] .drag-handle`);
  const toggle = (page, id) => page.locator(`[data-id="${id}"] input`);

  // Put the preview at a known visible position, then reveal the source handle.
  async function sourcePoint(page, id) {
    await page.evaluate(id => {
      const preview = document.querySelector('#demo-sections');
      const handle = preview.querySelector(`[data-plugin="${id}"] .drag-handle`);
      preview.scrollTop += handle.getBoundingClientRect().top - preview.getBoundingClientRect().top - 24;
      window.scrollBy(0, preview.getBoundingClientRect().top - 80);
    }, id);
    const rect = await handle(page, id).boundingBox();
    return { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2 };
  }
  async function startDrag(page, id) {
    const point = await sourcePoint(page, id);
    await page.mouse.move(point.x, point.y);
    await page.mouse.down();
    return point;
  }
  async function targetPoint(page, id, after) {
    return page.evaluate(({ id, after }) => {
      const preview = document.querySelector('#demo-sections');
      const target = preview.querySelector(`[data-plugin="${id}"]`);
      const bounds = preview.getBoundingClientRect();
      const rect = target.getBoundingClientRect();
      const y = after ? rect.bottom - 6 : rect.top + 6;
      const middle = (Math.max(0, bounds.top) + Math.min(innerHeight, bounds.bottom)) / 2;
      preview.scrollTop += y - middle;
      const updated = target.getBoundingClientRect();
      return { x: bounds.left + bounds.width / 2, y: after ? updated.bottom - 6 : updated.top + 6 };
    }, { id, after });
  }
  async function aim(page, id, after) {
    const point = await targetPoint(page, id, after);
    await page.mouse.move(point.x, point.y, { steps: 10 });
  }
  async function assertDragClean(page) {
    assert.equal(await page.locator('.demo-drag-label, .is-picked, .drop-before, .drop-after, .is-dragging').count(), 0);
  }
  try {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, reducedMotion: 'reduce' });
    const page = await context.newPage();
    observe(page);
    await page.goto(url);
    const originalLibrary = await library(page);
    assert.equal(originalLibrary.length, 30);
    assert.equal(await page.locator('#plugin-list button').count(), 0, 'Library must only select, never reorder');
    assert.equal(await page.locator('.reorder-buttons, [data-action="up"], [data-action="down"]').count(), 0);
    assert.deepEqual(await selected(page), defaults);
    assert.equal(await page.locator('[data-plugin="ai_pricing"] h5').count(), 3);
    assert.equal(await page.locator('[data-plugin="ai_pricing"] .drag-handle').count(), 1);

    // Selection is the ordered preview, not a hidden catalog-order slot.
    await toggle(page, 'weather').uncheck();
    await toggle(page, 'recipe').check();
    await toggle(page, 'weather').check();
    assert.deepEqual(await selected(page), ['quote', 'headlines', 'ai_pricing', 'crypto', 'recipe', 'weather']);
    assert.equal(await page.locator(':focus').getAttribute('aria-label'), 'Enable Weather in demo');
    assert.deepEqual(await library(page), originalLibrary);
    await reset(page);

    // Only the preview handle reorders, with keyboard focus retained.
    await handle(page, 'weather').focus();
    await page.keyboard.press('ArrowUp');
    assert.deepEqual(await selected(page), defaults);
    await page.keyboard.press('ArrowDown');
    assert.deepEqual(await selected(page), ['quote', 'weather', 'headlines', 'ai_pricing', 'crypto']);
    assert.equal(await page.locator(':focus').getAttribute('aria-label'), 'Reorder Weather');
    await page.keyboard.press('ArrowUp');
    assert.deepEqual(await selected(page), defaults);
    assert.deepEqual(await library(page), originalLibrary);

    // An in-progress drag is visual feedback only; commit order on drop.
    await startDrag(page, 'weather');
    await aim(page, 'quote', true);
    assert.deepEqual(await selected(page), defaults);
    assert.equal(await page.locator('.demo-drag-label').textContent(), 'Weather');
    assert.equal(await page.locator('.drop-before, .drop-after').count(), 1);
    await page.mouse.up();
    assert.deepEqual(await selected(page), ['quote', 'weather', 'headlines', 'ai_pricing', 'crypto']);
    assert.equal(await page.locator(':focus').getAttribute('aria-label'), 'Reorder Weather');
    assert.deepEqual(await library(page), originalLibrary);
    assert.deepEqual(new Set(await checked(page)), new Set(defaults));
    await assertDragClean(page);

    // Long composite content moves as a whole, then last-to-first insertion.
    await startDrag(page, 'ai_pricing');
    await aim(page, 'weather', false);
    await page.mouse.up();
    assert.deepEqual(await selected(page), ['quote', 'ai_pricing', 'weather', 'headlines', 'crypto']);
    assert.equal(await page.locator('[data-plugin="ai_pricing"] h5').count(), 3);
    await startDrag(page, 'crypto');
    await aim(page, 'quote', false);
    await page.mouse.up();
    assert.equal((await selected(page))[0], 'crypto');
    await toggle(page, 'crypto').uncheck();
    await toggle(page, 'crypto').check();
    assert.equal((await selected(page)).at(-1), 'crypto');

    // Escape, outside drop, cancellation, lost capture, and window blur roll back.
    for (const reason of ['escape', 'outside', 'cancel', 'lost-capture', 'blur']) {
      await reset(page);
      await startDrag(page, 'weather');
      await aim(page, 'quote', true);
      if (reason === 'escape') await page.keyboard.press('Escape');
      if (reason === 'outside') await page.mouse.move(10, 10, { steps: 5 });
      if (reason === 'cancel') await handle(page, 'weather').dispatchEvent('pointercancel', { pointerId: 1 });
      if (reason === 'lost-capture') await handle(page, 'weather').evaluate(node => node.releasePointerCapture(1));
      if (reason === 'blur') await page.evaluate(() => window.dispatchEvent(new Event('blur')));
      await page.mouse.up();
      assert.deepEqual(await selected(page), defaults, reason);
      await assertDragClean(page);
    }

    // Hold still near an edge: RAF scrolling must continue without pointer moves.
    for (const direction of ['bottom', 'top']) {
      if (direction === 'bottom') await reset(page);
      await startDrag(page, 'weather');
      const edge = await page.locator('#demo-sections').evaluate((node, direction) => {
        const r = node.getBoundingClientRect();
        return { x: r.left + r.width / 2, y: direction === 'bottom' ? Math.min(innerHeight, r.bottom) - 3 : Math.max(0, r.top) + 3 };
      }, direction);
      await page.mouse.move(edge.x, edge.y, { steps: 8 });
      await page.waitForFunction(direction => {
        const node = document.querySelector('#demo-sections');
        return direction === 'bottom' ? node.scrollTop >= node.scrollHeight - node.clientHeight - 2 : node.scrollTop <= 1;
      }, direction, { timeout: 8000 });
      await page.mouse.up();
      assert.equal(direction === 'bottom' ? (await selected(page)).at(-1) : (await selected(page))[0], 'weather');
      await assertDragClean(page);
    }
    assert.deepEqual(await selected(page), defaults);

    // Selection changes and reset/clear during a drag cannot resurrect stale IDs.
    for (const action of ['disable', 'clear', 'reset']) {
      await reset(page);
      await startDrag(page, 'weather');
      await aim(page, 'quote', true);
      await page.evaluate(action => {
        if (action === 'disable') {
          const input = document.querySelector('[data-id="weather"] input');
          input.checked = false;
          input.dispatchEvent(new Event('change', { bubbles: true }));
        } else document.querySelector(`#demo-${action}`).click();
      }, action);
      await page.mouse.up();
      assert.deepEqual(await selected(page), action === 'disable' ? defaults.slice(1) : action === 'clear' ? [] : defaults);
      await assertDragClean(page);
    }

    // Search filters the library only, and enables append despite catalog position.
    await page.locator('#plugin-search').fill('semantic');
    assert.equal((await library(page)).length, 1);
    assert.deepEqual(await selected(page), defaults);
    await toggle(page, 'semantic_scholar').check();
    assert.equal((await selected(page)).at(-1), 'semantic_scholar');
    await handle(page, 'weather').focus();
    await page.keyboard.press('ArrowDown');
    assert.equal((await selected(page))[1], 'weather');
    await startDrag(page, 'weather');
    await aim(page, 'quote', false);
    await page.mouse.up();
    assert.deepEqual(await selected(page), [...defaults, 'semantic_scholar']);
    assert.equal((await library(page)).length, 1);
    assert.equal(await toggle(page, 'semantic_scholar').isChecked(), true);
    await page.locator('#plugin-search').fill('');
    await page.locator('#plugin-category').selectOption('Markets');
    assert.equal((await library(page)).length, 3);
    await page.locator('#plugin-search').fill('zzzz');
    assert.ok(await page.locator('#no-plugins').isVisible());
    await page.locator('#demo-clear').click();
    assert.deepEqual(await selected(page), []);
    assert.equal(await page.locator('#demo-sections .demo-empty').count(), 1);
    await reset(page);
    assert.deepEqual(await selected(page), defaults);
    assert.deepEqual(await library(page), originalLibrary);

    // Clicking sample content doesn't start a drag; source links retain normal clicks.
    await page.locator('[data-plugin="weather"] dt').first().click();
    assert.equal(await page.locator('.is-dragging').count(), 0);
    await page.locator('[data-plugin="weather"] .demo-source a').evaluate(node => {
      node.addEventListener('click', event => {
        window.normalSourceClick = !event.defaultPrevented;
        event.preventDefault(); // Test only: don't actually visit the provider.
      }, { once: true });
    });
    await page.locator('[data-plugin="weather"] .demo-source a').click();
    assert.equal(await page.evaluate(() => window.normalSourceClick), true);
    for (const checkbox of await page.locator('.plugin-row input').all()) await checkbox.check();
    assert.equal((await selected(page)).length, 30);
    assert.equal(new Set(await selected(page)).size, 30);
    assert.equal(await page.locator('#demo-sections .drag-handle').count(), 30);
    await page.reload();
    assert.deepEqual(await selected(page), defaults);
    await page.locator('#plugin-builder').screenshot({ path: '/tmp/email-brief-builder-desktop.png' });

    const mobile = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, reducedMotion: 'reduce' });
    const phone = await mobile.newPage();
    observe(phone);
    await phone.goto(url);
    assert.ok(await phone.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
    await toggle(phone, 'recipe').tap();
    assert.equal((await selected(phone)).at(-1), 'recipe');
    await phone.locator('#demo-reset').tap();
    const session = await mobile.newCDPSession(phone);
    const from = await sourcePoint(phone, 'weather');
    await session.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [from] });
    const to = await targetPoint(phone, 'quote', true);
    for (let step = 1; step <= 8; step++) {
      const point = { x: from.x + (to.x - from.x) * step / 8, y: from.y + (to.y - from.y) * step / 8 };
      await session.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [point] });
    }
    assert.deepEqual(await selected(phone), defaults);
    await session.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
    assert.deepEqual(await selected(phone), ['quote', 'weather', 'headlines', 'ai_pricing', 'crypto']);
    assert.deepEqual(await library(phone), originalLibrary);
    await assertDragClean(phone);
    const beforeCancel = await selected(phone);
    const cancelFrom = await sourcePoint(phone, 'weather');
    await session.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: [cancelFrom] });
    const cancelTo = await targetPoint(phone, 'quote', false);
    await session.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: [cancelTo] });
    assert.equal(await phone.locator('.demo-drag-label').count(), 1);
    await session.send('Input.dispatchTouchEvent', { type: 'touchCancel', touchPoints: [] });
    assert.deepEqual(await selected(phone), beforeCancel);
    await assertDragClean(phone);
    await phone.locator('#plugin-builder').screenshot({ path: '/tmp/email-brief-builder-mobile.png' });
    await mobile.close();

    const noJS = await browser.newContext({ javaScriptEnabled: false });
    const fallback = await noJS.newPage();
    observe(fallback);
    await fallback.goto(url);
    assert.ok(await fallback.locator('noscript').isVisible());
    assert.ok(await fallback.locator('#setup').isVisible());
    assert.ok(await fallback.locator('.catalog-summary').isVisible());
    assert.equal(await fallback.locator('#demo-interactive').isVisible(), false);
    await noJS.close();
    assert.ok(requests.every(r => r.startsWith('file:')), requests.join('\n'));
    assert.deepEqual(errors, []);
    console.log('PASS: preview-only ordering, fixed library, append/re-enable, keyboard, drag commit/cancel, edge scrolling, selection during drag, filters, touch, no-JS, and no external requests.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
