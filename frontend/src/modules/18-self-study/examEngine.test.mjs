import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createPaper } from './examEngine.js';
const bank = JSON.parse(readFileSync(new URL('./questionBank.json', import.meta.url)));
bank.questions = bank.questions.filter(q => !q.priority);
const sources = [...new Set(bank.questions.map(q => q.source))];
assert.equal(bank.questions.length, 124);
assert.equal(new Set(bank.questions.map(q => q.id)).size, 124);
for (const source of sources) {
  const all = bank.questions.filter(q => q.source === source);
  assert.equal(all.length, 31);
  for (const q of all) {
    assert.ok(q.prompt && q.answer && q.sourceFile);
    assert.ok(!/[（(][ABCD][）)]/.test(q.prompt), 'answer leaked in prompt');
    if (q.type === 'choice') {
      assert.deepEqual(q.options.map(o => o.key), ['A','B','C','D']);
      assert.ok(q.options.every(o => o.text));
      assert.ok(q.options.some(o => o.key === q.answer));
    }
  }
}
const signatures = new Set();
for (let i = 0; i < 100; i++) {
  const paper = createPaper(bank.questions, sources);
  assert.equal(paper.length, 31);
  assert.equal(paper.filter(q => q.type === 'choice').length, 25);
  assert.equal(paper.filter(q => q.type === 'short').length, 5);
  assert.equal(paper.filter(q => q.type === 'material').length, 1);
  assert.equal(new Set(paper.map(q => q.fingerprint)).size, paper.length);
  signatures.add(paper.map(q => q.id).join(','));
}
assert.ok(signatures.size > 90);
for (const source of sources) {
  const paper = createPaper(bank.questions, [source]);
  assert.equal(paper.length, 31);
  assert.ok(paper.every(q => q.source === source));
}
assert.equal(createPaper(bank.questions, sources, 'choice').length, 25);
assert.equal(createPaper(bank.questions, sources, 'written').length, 6);
assert.deepEqual(createPaper(bank.questions, []), []);
console.log('PASS: 124 entries, 4 sources, 100 randomized papers, types, answer mapping, source filters, deduplication.');
