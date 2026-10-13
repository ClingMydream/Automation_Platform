// File purpose: 工作手记模块共享的日期、标签和剪贴板工具。
// How to change: 只放纯函数；需要 React 组件的逻辑放到同目录的 Panel/Editor 文件里。

export const PROGRESS_LABELS = { in_progress: '进行中', completed: '已完成', blocked: '受阻' };
export const PROGRESS_TONES = { in_progress: 'processing', completed: 'success', blocked: 'warning' };
export const STATUS_LABELS = { draft: '草稿', completed: '已完成' };
export const CATEGORIES = ['测试执行', '缺陷跟进', '自动化开发', '需求评审', '学习成长', '会议沟通', '其他'];
export const WEEKDAYS = ['一', '二', '三', '四', '五', '六', '日'];

const SHANGHAI = 'Asia/Shanghai';

// 工作日期一律按北京时间计算，不能依赖浏览器本地时区，也不能用 toISOString()。
export function shanghaiToday() {
  return new Intl.DateTimeFormat('en-CA', { timeZone: SHANGHAI }).format(new Date());
}

export function parseISO(value) {
  const [year, month, day] = String(value || '').split('-').map(Number);
  return new Date(Date.UTC(year, (month || 1) - 1, day || 1));
}

export function toISO(date) {
  return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, '0')}-${String(date.getUTCDate()).padStart(2, '0')}`;
}

export function addDays(value, offset) {
  const date = parseISO(value);
  date.setUTCDate(date.getUTCDate() + offset);
  return toISO(date);
}

// 周范围固定为周一至周日；周 ID 使用周一日期，避免跨年冲突。
export function weekStartOf(value) {
  const date = parseISO(value);
  const shift = (date.getUTCDay() + 6) % 7;
  return addDays(value, -shift);
}

export function weekEndOf(value) {
  return addDays(weekStartOf(value), 6);
}

export function weekdayIndex(value) {
  return (parseISO(value).getUTCDay() + 6) % 7;
}

export function dateLabel(value) {
  const date = parseISO(value);
  return `${date.getUTCMonth() + 1}月${date.getUTCDate()}日 周${WEEKDAYS[weekdayIndex(value)]}`;
}

export function shortDate(value) {
  const date = parseISO(value);
  return `${String(date.getUTCMonth() + 1).padStart(2, '0')}-${String(date.getUTCDate()).padStart(2, '0')}`;
}

export function monthOf(value) {
  return String(value || '').slice(0, 7);
}

export function shiftMonth(month, offset) {
  const [year, index] = month.split('-').map(Number);
  const date = new Date(Date.UTC(year, index - 1 + offset, 1));
  return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, '0')}`;
}

// 月历网格按 6 周铺满，跨周记录因此不会漏显示。
export function calendarGrid(month) {
  const first = `${month}-01`;
  const gridStart = weekStartOf(first);
  const days = [];
  for (let index = 0; index < 42; index += 1) {
    days.push(addDays(gridStart, index));
  }
  return days;
}

// 时间戳按北京时间显示。
export function formatClock(value) {
  if (!value) return '';
  const normalized = /Z$|[+-]\d{2}:\d{2}$/.test(value) ? value : `${value}Z`;
  return new Intl.DateTimeFormat('zh-CN', {
    timeZone: SHANGHAI, hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(new Date(normalized));
}

export function formatDateTime(value) {
  if (!value) return '';
  const normalized = /Z$|[+-]\d{2}:\d{2}$/.test(value) ? value : `${value}Z`;
  return new Intl.DateTimeFormat('zh-CN', {
    timeZone: SHANGHAI, month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false,
  }).format(new Date(normalized));
}

export function formatDuration(minutes) {
  if (minutes === null || minutes === undefined) return '未记录';
  if (minutes < 60) return `${minutes} 分钟`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours} 小时 ${rest} 分钟` : `${hours} 小时`;
}

export function newId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
  return `id-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
}

// 复制失败时把文本交回给调用方，用可选中文本弹窗兜底（远程 HTTP 环境常见）。
export async function copyText(text) {
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch (error) {
    // 继续走兜底方案
  }
  try {
    const area = document.createElement('textarea');
    area.value = text;
    area.setAttribute('readonly', '');
    area.style.position = 'fixed';
    area.style.opacity = '0';
    document.body.appendChild(area);
    area.select();
    const ok = document.execCommand('copy');
    document.body.removeChild(area);
    return ok;
  } catch (error) {
    return false;
  }
}

export function downloadText(text, filename) {
  const blob = new Blob([text], { type: 'text/markdown;charset=utf-8' });
  saveBlob(blob, filename);
}

// 保存后端返回的 blob，文件名沿用 Content-Disposition 里的中文名。
export function saveBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename || 'download.md';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

// 只做首行摘要，长正文在详情里完整展示，不静默截断来源内容。
export function summaryOf(text, limit = 80) {
  const flat = String(text || '').replace(/\s+/g, ' ').trim();
  return flat.length > limit ? `${flat.slice(0, limit)}…` : flat;
}

// 周报事项编号：与后端 chinese_index 保持一致，超过十项用阿拉伯数字。
export function chineseIndex(index) {
  const digits = '一二三四五六七八九十';
  return index >= 1 && index <= 10 ? digits[index - 1] : String(index);
}
