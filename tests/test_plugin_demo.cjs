const { test } = require('node:test');
const assert = require('node:assert/strict');
const { catalog, defaults, initialState, move } = require('../assets/plugin-demo.js');

test('catalog contains 30 distinct plugins with safe source links and samples', () => {
  assert.equal(catalog.length, 30);
  assert.equal(new Set(catalog.map(p => p.id)).size, catalog.length);
  for (const p of catalog) {
    assert.match(p.id, /^[a-z_]+$/);
    assert.equal(new URL(p.url).protocol, 'https:');
    assert.ok(p.name && p.description && p.category && p.source && p.sample.length);
  }
});

test('defaults are five known plugins; resetting creates independent state', () => {
  const a = initialState();
  a.order.reverse();
  a.enabled.clear();
  const b = initialState();
  assert.deepEqual([...b.enabled], defaults);
  assert.equal(b.enabled.size, 5);
  assert.ok(defaults.every(id => b.order.includes(id)));
  assert.equal(b.order[0], 'weather');
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

test('moving a filtered target preserves hidden plugins and enabled state', () => {
  const state = initialState();
  const before = [...state.enabled];
  state.order = move(state.order, 'crypto', 'weather');
  assert.equal(state.order[0], 'crypto');
  assert.equal(new Set(state.order).size, catalog.length);
  assert.deepEqual([...state.enabled], before);
});
