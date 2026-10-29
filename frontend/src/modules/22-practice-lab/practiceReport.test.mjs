import assert from 'node:assert/strict';
import test from 'node:test';
import {testLabel,reportSummary}from'./practiceReport.js';
test('missing and partial execution evidence is never reported as all passed',()=>{assert.match(reportSummary({status:'passed',suite:'api',result:{}}).title,/无可核对/);assert.match(reportSummary({status:'stopped',suite:'ui',result:{tests:[{status:'passed'}]}}).title,/未完整/);});
test('failures have readable names and keep unknown cases identifiable',()=>{assert.equal(testLabel('test_integer_amount'),'整数金额计算');assert.equal(testLabel('custom_case'),'custom_case');assert.match(reportSummary({status:'failed',suite:'api',result:{tests:[{name:'test_concurrent_inventory_never_negative',status:'failed'}]}}).detail,/并发库存不超卖/);});
