// File purpose: Shared HTML report exporter for test reports.
// How to change: edit UI text/layout in this file; move reusable logic into shared helpers or the module feature file.

import { escapeHtml } from './html';
import { formatDuration, formatTime } from './formatters';

// 测试报告导出模块。
// 修改建议：如果要调整 HTML 报告样式，优先改这里；不要把导出模板散落在页面组件里。

// Build and download an HTML test report file.
// Shared helper block: exported helpers below are reused by multiple modules.
export function downloadReportHtml(report) {
  if (report?.report_kind === 'batch') {
    downloadBatchReportHtml(report);
    return;
  }
  const detail = report?.report || {};
  const checks = detail.checks || [];
  const events = detail.events || [];
  const html = `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>测试报告 #${report.id}</title>
  <style>
    body { margin: 0; padding: 28px; font-family: "Segoe UI", Arial, sans-serif; color: #17202a; background: #eef2f5; }
    main { max-width: 980px; margin: 0 auto; background: #fff; padding: 24px; border-radius: 8px; }
    h1 { margin-top: 0; }
    table { width: 100%; border-collapse: collapse; margin: 14px 0; }
    th, td { border: 1px solid #d7e2e8; padding: 8px; text-align: left; vertical-align: top; }
    th { background: #f3f7f8; }
    pre { white-space: pre-wrap; background: #142028; color: #e7f3f4; padding: 12px; border-radius: 6px; overflow: auto; }
    .passed { color: #15803d; font-weight: 700; }
    .failed { color: #b91c1c; font-weight: 700; }
    img { max-width: 100%; border: 1px solid #d7e2e8; border-radius: 6px; }
  </style>
</head>
<body>
  <main>
    <h1>测试报告 #${report.id}</h1>
    <p>用例：${escapeHtml(report.case_name)} ｜ 类型：${escapeHtml(report.case_type)} ｜ 状态：<span class="${report.status === 'passed' ? 'passed' : 'failed'}">${escapeHtml(report.status)}</span></p>
    <table>
      <tbody>
        <tr><th>创建时间</th><td>${escapeHtml(formatTime(report.created_at))}</td></tr>
        <tr><th>更新时间</th><td>${escapeHtml(formatTime(report.updated_at))}</td></tr>
        <tr><th>耗时</th><td>${escapeHtml(formatDuration(report.duration_ms))}</td></tr>
        <tr><th>错误信息</th><td>${escapeHtml(report.error || '-')}</td></tr>
      </tbody>
    </table>
    <h2>断言检查</h2>
    ${checks.length ? `<table><thead><tr><th>名称</th><th>结果</th><th>期望</th><th>实际</th></tr></thead><tbody>${checks.map((item) => `<tr><td>${escapeHtml(item.name)}</td><td>${item.passed ? '通过' : '失败'}</td><td>${escapeHtml(item.expected)}</td><td>${escapeHtml(item.actual)}</td></tr>`).join('')}</tbody></table>` : '<p>无断言检查。</p>'}
    <h2>UI 步骤</h2>
    ${events.length ? `<table><thead><tr><th>步骤</th><th>动作</th><th>目标</th><th>值</th><th>耗时</th></tr></thead><tbody>${events.map((item) => `<tr><td>${escapeHtml(item.step)}</td><td>${escapeHtml(item.action)}</td><td>${escapeHtml(item.target || '-')}</td><td>${escapeHtml(item.value || '-')}</td><td>${escapeHtml(formatDuration(item.elapsed_ms))}</td></tr>`).join('')}</tbody></table>` : '<p>无 UI 步骤。</p>'}
    ${detail.response ? `<h2>接口响应</h2><pre>${escapeHtml(JSON.stringify(detail.response, null, 2))}</pre>` : ''}
    ${detail.latest_screenshot ? `<h2>最新截图</h2><img src="${detail.latest_screenshot}" alt="latest screenshot" />` : ''}
    <h2>原始报告 JSON</h2>
    <pre>${escapeHtml(JSON.stringify(detail, null, 2))}</pre>
  </main>
</body>
</html>`;
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = `test-report-${report.id}.html`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}

// Build and download an HTML report for an execution batch.
function downloadBatchReportHtml(report) {
  const detail = report?.report || {};
  const batch = detail.batch || {};
  const stats = detail.stats || {};
  const results = detail.results || [];
  const performance = detail.performance_summary || {};
  const html = `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <title>批次测试报告 ${escapeHtml(batch.batch_no || report.id)}</title>
  <style>
    body { margin: 0; padding: 28px; font-family: "Segoe UI", Arial, sans-serif; color: #17202a; background: #eef2f5; }
    main { max-width: 1080px; margin: 0 auto; background: #fff; padding: 24px; border-radius: 8px; }
    h1 { margin-top: 0; }
    table { width: 100%; border-collapse: collapse; margin: 14px 0; }
    th, td { border: 1px solid #d7e2e8; padding: 8px; text-align: left; vertical-align: top; }
    th { background: #f3f7f8; }
    pre { white-space: pre-wrap; background: #142028; color: #e7f3f4; padding: 12px; border-radius: 6px; overflow: auto; }
    .passed { color: #15803d; font-weight: 700; }
    .failed { color: #b91c1c; font-weight: 700; }
  </style>
</head>
<body>
  <main>
    <h1>批次测试报告 ${escapeHtml(batch.batch_no || `#${report.id}`)}</h1>
    <p>任务：${escapeHtml(report.case_name)} · 状态：<span class="${report.status === 'passed' ? 'passed' : 'failed'}">${escapeHtml(report.status)}</span></p>
    <table>
      <tbody>
        <tr><th>触发方式</th><td>${escapeHtml(batch.trigger_type || '-')}</td></tr>
        <tr><th>环境 ID</th><td>${escapeHtml(batch.environment_id || '-')}</td></tr>
        <tr><th>创建时间</th><td>${escapeHtml(formatTime(report.created_at))}</td></tr>
        <tr><th>更新时间</th><td>${escapeHtml(formatTime(report.updated_at))}</td></tr>
        <tr><th>耗时</th><td>${escapeHtml(formatDuration(report.duration_ms))}</td></tr>
      </tbody>
    </table>
    <h2>执行统计</h2>
    <table><tbody>
      <tr><th>总数</th><td>${escapeHtml(stats.total ?? 0)}</td><th>通过</th><td>${escapeHtml(stats.passed ?? 0)}</td></tr>
      <tr><th>失败</th><td>${escapeHtml(stats.failed ?? 0)}</td><th>跳过</th><td>${escapeHtml(stats.skipped ?? 0)}</td></tr>
    </tbody></table>
    ${performance.total ? `<h2>性能摘要</h2>
    <table><tbody>
      <tr><th>性能结果</th><td>${escapeHtml(performance.total)}</td><th>通过率</th><td>${escapeHtml(`${performance.pass_rate ?? 0}%`)}</td></tr>
      <tr><th>平均响应</th><td>${escapeHtml(`${performance.avg_response_ms ?? 0} ms`)}</td><th>最大 P95</th><td>${escapeHtml(`${performance.max_p95_ms ?? 0} ms`)}</td></tr>
      <tr><th>最大 P99</th><td>${escapeHtml(`${performance.max_p99_ms ?? 0} ms`)}</td><th>最高错误率</th><td>${escapeHtml(`${performance.max_error_rate ?? 0}%`)}</td></tr>
      <tr><th>最大 TPS</th><td>${escapeHtml(performance.max_tps ?? 0)}</td><th>风险</th><td>${escapeHtml(performance.risk_level || '-')}</td></tr>
    </tbody></table>` : ''}
    <h2>结果明细</h2>
    ${results.length ? `<table><thead><tr><th>ID</th><th>类型</th><th>用例</th><th>状态</th><th>耗时</th><th>错误</th></tr></thead><tbody>${results.map((item) => `<tr><td>${escapeHtml(item.id)}</td><td>${escapeHtml(item.result_type)}</td><td>${escapeHtml(item.case_id)}</td><td>${escapeHtml(item.status)}</td><td>${escapeHtml(formatDuration(item.duration_ms))}</td><td>${escapeHtml(item.error || '-')}</td></tr>`).join('')}</tbody></table>` : '<p>暂无结果明细。</p>'}
    <h2>原始报告 JSON</h2>
    <pre>${escapeHtml(JSON.stringify(detail, null, 2))}</pre>
  </main>
</body>
</html>`;
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = `batch-report-${report.id}.html`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}
