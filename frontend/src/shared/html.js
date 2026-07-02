// File purpose: Shared HTML escaping helper used by report export.
// How to change: edit UI text/layout in this file; move reusable logic into shared helpers or the module feature file.

// HTML 转义工具。
// 用途：导出报告、HTML 实体编码等场景，避免用户输入破坏 HTML 结构。

// Escape HTML special characters before report export.
// Shared helper block: exported helpers below are reused by multiple modules.
export function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}
