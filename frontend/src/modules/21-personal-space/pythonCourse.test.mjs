import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read=name=>JSON.parse(readFileSync(new URL(name,import.meta.url),'utf8'));
const catalog=read('./pythonCourseCatalog.json');
test('complete source-linked course has unique stable identities and compatible first lesson',()=>{
 assert.equal(catalog.length,124);
 assert.equal(new Set(catalog.map(u=>u.id)).size,124);
 assert.equal(new Set(catalog.map(u=>u.url)).size,124);
 assert.equal(new Set(catalog.map(u=>u.group)).size,18);
 assert.equal(catalog[2].id,'geekbang-python-01');
 assert.equal(catalog[2].title,'01｜配置 Python 开发环境');
 for(const [i,u]of catalog.entries()){
  assert.equal(u.order,i+1);
  assert.match(u.url,/^https:\/\/time.geekbang.org\/course\/detail\/100310001-\d+$/);
  assert.ok(('learning-unit:'+u.id).length<=40);
 }
});
test('every catalog item has loadable editorial content, code and separate answers',()=>{
 for(const meta of catalog){
  const unit=read('./python-units/'+meta.id+'.json');
  assert.equal(unit.id,meta.id);
  assert.equal(unit.url,meta.url);
  assert.equal(unit.codeChecked,true);
  for(const heading of ['```python','## 自己动手','## 参考答案（练习时先自己回答）','## 与测试工作的联系'])assert.ok(unit.body.includes(heading),meta.id+heading);
  assert.ok(unit.body.includes(meta.url));
  assert.ok(['video','article','assessment'].includes(unit.sourceKind));
  if(unit.sourceKind==='video')assert.ok(unit.captionCues>0);
 }
});
