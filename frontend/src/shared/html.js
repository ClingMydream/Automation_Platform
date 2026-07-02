// HTML 转义工具。
// 用途：导出报告、HTML 实体编码等场景，避免用户输入破坏 HTML 结构。

// Escape HTML special characters before report export.
export function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}
