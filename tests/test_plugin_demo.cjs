const { test } = require('node:test');
const assert = require('node:assert/strict');
const { catalog, defaults, initialOrder, setEnabled, move, moveToIndex } = require('../assets/plugin-demo.js');

test('catalog contains 30 distinct plugins with safe source links and samples', () => {
  assert.equal(catalog.length, 30);
  assert.equal(new Set(catalog.map(p => p.id)).size, catalog.length);
  for (const p of catalog) {
    assert.match(p.id, /^[a-z_]+$/);
    assert.equal(new URL(p.url).protocol, 'https:');
    assert.ok(p.name && p.description && p.category && p.source && p.sample.length);
  }
});

test('one ordered list of five known plugins is the initial state', () => {
  const a = initialOrder();
  a.reverse();
  a.pop();
  const b = initialOrder();
  assert.deepEqual(b, defaults);
  assert.equal(b.length, 5);
  assert.ok(b.every(id => catalog.some(p => p.id === id)));
});

test('move inserts before or after target without dropping or duplicating plugins', () => {
  const order = ['a', 'b', 'c', 'd'];
  assert.deepEqual(move(order, 'd', 'b'), ['a', 'd', 'b', 'c']);
  assert.deepEqual(move(order, 'a', 'c', true), ['b', 'c', 'a', 'd']);
  assert.deepEqual(move(order, 'd', 'a'), ['d', 'a', 'b', 'c']);
  assert.deepEqual(order, ['a', 'b', 'c', 'd']);
});

test('self-drop and unknown IDs leave ordering intact', () => {
  const order = ['a', 'b'];
  assert.deepEqual(move(order, 'a', 'a'), order);
  assert.deepEqual(move(order, 'missing', 'b'), order);
  assert.deepEqual(move(order, 'a', 'missing'), order);
});

test('moveToIndex inserts at every boundary without duplicates or mutation', () => {
  const order = ['a', 'b', 'c', 'd'];
  assert.deepEqual(moveToIndex(order, 'a', 3), ['b', 'c', 'd', 'a']);
  assert.deepEqual(moveToIndex(order, 'd', 0), ['d', 'a', 'b', 'c']);
  assert.deepEqual(moveToIndex(order, 'b', 1), order);
  assert.deepEqual(moveToIndex(order, 'b', -9), ['b', 'a', 'c', 'd']);
  assert.deepEqual(moveToIndex(order, 'b', 99), ['a', 'c', 'd', 'b']);
  assert.deepEqual(moveToIndex(order, 'missing', 0), order);
  assert.deepEqual(order, ['a', 'b', 'c', 'd']);
});

test('enabling appends at the bottom without duplicates; disabling removes', () => {
  const order = initialOrder();
  const appended = setEnabled(order, 'recipe', true);
  assert.deepEqual(appended, [...order, 'recipe']);
  assert.deepEqual(setEnabled(appended, 'recipe', true), appended);
  assert.deepEqual(setEnabled(appended, 'recipe', false), order);
  assert.deepEqual(setEnabled(order, 'recipe', false), order);
  assert.deepEqual(setEnabled(order, 'missing', true), order);
  assert.deepEqual(order, defaults);
});

test('re-enabling a removed plugin appends; it has no remembered position', () => {
  let order = move(initialOrder(), 'crypto', 'weather');
  order = setEnabled(order, 'crypto', false);
  order = move(order, 'headlines', 'weather');
  order = setEnabled(order, 'recipe', true);
  order = setEnabled(order, 'crypto', true);
  assert.deepEqual(order, ['headlines', 'weather', 'quote', 'ai_pricing', 'recipe', 'crypto']);
});

test('reordering only enabled plugins leaves the library and selection intact', () => {
  const libraryOrder = catalog.map(p => p.id);
  const order = move(initialOrder(), 'crypto', 'weather');
  assert.equal(order[0], 'crypto');
  assert.deepEqual(new Set(order), new Set(defaults));
  assert.deepEqual(catalog.map(p => p.id), libraryOrder);
  assert.deepEqual(move(order, 'weather', 'recipe'), order); // Not enabled.
});

test('empty and single-section lists are safe to reorder', () => {
  assert.deepEqual(move([], 'weather', 'quote'), []);
  assert.deepEqual(move(['weather'], 'weather', 'weather'), ['weather']);
  assert.deepEqual(setEnabled([], 'weather', true), ['weather']);
});

test('repeated selection and moves never duplicate or lose plugins', () => {
  let order = [];
  for (const p of catalog) order = setEnabled(order, p.id, true);
  for (const p of catalog) {
    order = move(order, p.id, order[0]);
    order = setEnabled(order, p.id, false);
    order = setEnabled(order, p.id, true);
    assert.equal(order.length, catalog.length);
    assert.equal(new Set(order).size, catalog.length);
  }
});
