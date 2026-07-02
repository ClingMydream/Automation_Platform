import { escapeHtml } from './html';
import { formatDuration, formatTime } from './formatters';

// 测试报告导出模块。
// 修改建议：如果要调整 HTML 报告样式，优先改这里；不要把导出模板散落在页面组件里。

// Build and download an HTML test report file.
export function downloadReportHtml(report) {
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
