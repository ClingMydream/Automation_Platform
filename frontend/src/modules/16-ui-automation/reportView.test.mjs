import assert from 'node:assert/strict';
import { buildReportView } from './reportView.js';
const run = { status: 'failed', case_ids: [1, 2], result_summary: { timeline: [
  { case_id: 1, status: 'passed' }, { case_id: 1, status: 'failed' }, { case_id: 2, status: 'passed' },
] } };
const view = buildReportView(run);
assert.equal(view.passed, 0);
assert.equal(view.failed, 1);
assert.equal(view.unknown, 1);
assert.equal(view.problem_items[0].case_id, 1);
assert.equal(buildReportView({ ...run, status: 'passed', result_summary: {} }).passed, 2);
assert.equal(buildReportView({ ...run, result_summary: { report: { status: 'partial', passed: 3 } } }).passed, 3);
assert.equal(buildReportView({ ...run, result_summary: { case_results: [{ case_id: 2, status: 'passed' }], timeline: run.result_summary.timeline } }).passed, 1);
console.log('PASS: failed steps never count as case passes; incomplete legacy evidence stays unknown.');
