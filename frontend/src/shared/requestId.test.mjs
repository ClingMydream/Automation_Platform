import assert from 'node:assert/strict';
import test from 'node:test';
import {requestId} from './requestId.js';
test('HTTP preview creates a valid idempotency UUID without randomUUID', () => {
  const fallback={getRandomValues: bytes=>globalThis.crypto.getRandomValues(bytes)};
  const ids=Array.from({length:100},()=>requestId(fallback));
  assert.equal(new Set(ids).size,100);
  assert.ok(ids.every(id=>/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/.test(id)));
});
