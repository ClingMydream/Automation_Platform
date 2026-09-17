import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createPaper,gradePaper} from './examEngine.js';
const bank=JSON.parse(readFileSync(new URL('./questionBank.json',import.meta.url)));
const sources=[...new Set(bank.questions.map(q=>q.source))];
assert.equal(bank.questions.length,162);
assert.equal(bank.questions.filter(q=>q.priority).length,38);
for(let i=0;i<100;i++){
 const paper=createPaper(bank.questions,sources);
 assert.equal(paper.length,31);
 assert.equal(paper.filter(q=>q.priority).length,23);
 assert.equal(new Set(paper.map(q=>q.fingerprint)).size,31);
 assert.equal(gradePaper(paper).max,100);
 const pure=createPaper(bank.questions,['2026年10月押题']);
 assert.equal(pure.length,31);assert.ok(pure.every(q=>q.priority));
 const old=createPaper(bank.questions,sources.filter(s=>!s.includes('押题')));
 assert.equal(old.length,31);assert.ok(old.every(q=>!q.priority));
}
for(const q of bank.questions.filter(q=>q.priority)){
 assert.ok(q.answer&&q.prompt&&q.note);
 if(q.type==='choice'){assert.equal(q.options.length,4);assert.ok(q.options.some(o=>o.key===q.answer));}
}
console.log('PASS: 162 entries; 100 rounds: 23/31 prediction quota, fallback, no duplicates, 100-point score.');
