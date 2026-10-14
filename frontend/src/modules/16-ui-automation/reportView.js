export function buildReportView(run, cases = []) {
  if (!run) return null;
  const summary = run.result_summary || {};
  if (summary.report?.status) return { ...summary.report, legacy: false };
  const ids = [...new Set(run.case_ids || [])];
  const timeline = summary.timeline || [];
  const failed = new Set(timeline.filter(step => step.status === 'failed').map(step => step.case_id));
  if (summary.failure?.case_id) failed.add(summary.failure.case_id);
  const known = new Map((summary.case_results || []).map(row => [row.case_id, row]));
  // A passed step is not evidence that the entire case finished.
  const passed = ids.filter(id => !failed.has(id) && (known.get(id)?.status === 'passed' || run.status === 'passed'));
  const name = id => known.get(id)?.case_name || cases.find(row => row.id === id)?.name || `用例 ${id}`;
  const problems = ids.filter(id => failed.has(id) || known.get(id)?.status === 'failed');
  const confirmedPassed = passed.filter(id => !problems.includes(id));
  const unknown = ids.filter(id => !confirmedPassed.includes(id) && !problems.includes(id));
  const status = ['queued', 'running'].includes(run.status) ? 'running'
    : problems.length ? (confirmedPassed.length ? 'partial' : 'failed')
      : unknown.length ? 'interrupted' : 'passed';
  return {
    status, legacy: true, total: ids.length, passed: confirmedPassed.length, failed: problems.length,
    unknown: unknown.length, interrupted: run.status === 'interrupted' ? unknown.length : 0,
    unknown_items: unknown.map(id => ({ case_id: id, case_name: name(id) })),
    conclusion: status === 'running' ? '执行中，尚未完成的用例不计为通过。'
      : status === 'passed' ? '本次测试全部通过。'
        : `${confirmedPassed.length} 条确认通过，${problems.length} 条失败，${unknown.length} 条结果无法确认。`,
    started_at: run.started_at, finished_at: run.finished_at,
    duration_ms: run.started_at && run.finished_at ? Math.max(0, Date.parse(run.finished_at) - Date.parse(run.started_at)) : 0,
    tested_features: [],
    passed_items: confirmedPassed.map(id => ({ case_id: id, case_name: name(id), feature_name: '' })),
    problem_items: problems.map(id => ({ case_id: id, case_name: name(id), feature_name: '', status: 'failed', reason: known.get(id)?.reason || (summary.failure?.case_id === id ? summary.failure.reason : '执行失败，请查看步骤记录') })),
  };
}
