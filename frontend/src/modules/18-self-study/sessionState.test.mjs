import assert from 'node:assert/strict';
import { validateSession, mayEditSession } from './sessionState.js';
const bank = { version: 1, questions: [{ id: 'a', type: 'choice', options: [{ key: 'A' }] }, { id: 'b', type: 'short' }] };
const value = { version: 1, ids: ['a', 'b'], index: 0, responses: { a: 'A', b: 'viewed' }, selfScores: { b: 0 } };
assert.equal(validateSession(value, bank), value);
for (const patch of [{ ids: [] }, { ids: ['a', 'a'] }, { index: .5 }, { responses: [] }, { responses: { a: 'Z' } }, { selfScores: { b: 8 } }, { version: 2 }, { gradeSnapshot: { rows: 'broken' } }, { finished: 'yes' }]) {
  assert.equal(validateSession({ ...value, ...patch }, bank), null);
}
assert.equal(mayEditSession({ finished: true, reviewing: true }), false);
assert.equal(mayEditSession({ finished: false }), true);
console.log('PASS: storage validation, zero self-score and read-only review boundaries.');
