// File purpose: Shared display formatters for time, duration, size, and status.
// How to change: edit UI text/layout in this file; move reusable logic into shared helpers or the module feature file.

// 通用显示格式化函数。
// 修改建议：这里只处理“如何显示”，不要在这里写接口请求或页面状态逻辑。

// Format backend timestamps for local display.
// Shared helper block: exported helpers below are reused by multiple modules.
export function formatTime(value) {
  if (!value) return '-';
  return new Date(value).toLocaleString('zh-CN', { hour12: false });
}

// Format millisecond duration as milliseconds or seconds.
export function formatDuration(ms) {
  if (ms === null || ms === undefined) return '-';
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

// Format byte counts as B, KB, MB, or GB.
export function formatBytes(value) {
  if (!value && value !== 0) return '-';
  const units = ['B', 'KB', 'MB', 'GB'];
  let size = value;
  let index = 0;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  return `${size.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

// Map run status to an Ant Design tag color.
export function statusColor(status) {
  return {
    queued: 'default',
    running: 'processing',
    passed: 'success',
    failed: 'error',
  }[status] || 'default';
}
