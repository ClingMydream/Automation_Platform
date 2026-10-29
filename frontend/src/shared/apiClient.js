import { API_BASE, AUTH_EXPIRED_EVENT } from './constants.js';

function errorMessage(data, status) {
  if (typeof data?.detail === 'string') return data.detail;
  if (Array.isArray(data?.detail)) return data.detail.map(item => `${(item.loc || []).filter(x => x !== 'body').join('.') || '输入'}：${item.msg || '格式不正确'}`).join('；');
  if (typeof data?.message === 'string') return data.message;
  return ({ 401: '登录已过期，请重新登录', 403: '没有执行此操作的权限', 404: '请求的资源不存在或已被删除', 429: '操作过于频繁，请稍后重试', 500: '服务器处理失败，请重试', 502: '服务暂不可用，请稍后重试', 503: '服务暂不可用，请稍后重试', 504: '服务响应超时，请稍后重试' })[status] || `请求失败（HTTP ${status}）`;
}

export function apiClient(token) {
  let expiryNotified = false;
  async function request(path, options = {}, download = false) {
    const { timeoutMs = download || options.body instanceof FormData ? 120000 : options.method && options.method !== 'GET' ? 90000 : 20000, signal, notifyAuthExpired = true, ...fetchOptions } = options;
    const controller = new AbortController();
    let timedOut = false;
    const relay = () => controller.abort();
    if (signal?.aborted) controller.abort(); else signal?.addEventListener('abort', relay, { once: true });
    const timer = setTimeout(() => { timedOut = true; controller.abort(); }, timeoutMs);
    let res;
    try {
      const form = options.body instanceof FormData;
      res = await fetch(`${API_BASE}${path}`, { ...fetchOptions, signal: controller.signal,
        headers: { ...(form || download ? {} : { 'Content-Type': 'application/json' }),
          ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(fetchOptions.headers || {}) } });
      if (res.status === 401 && token && notifyAuthExpired) {
        if (!expiryNotified) { expiryNotified = true; window.dispatchEvent(new CustomEvent(AUTH_EXPIRED_EVENT)); }
        const err = new Error('登录已过期，请重新登录'); err.authExpired = true; err.status = 401; throw err;
      }
      if (download && res.ok) return { blob: await res.blob(), filename: filenameFromDisposition(res.headers.get('Content-Disposition')) || 'attachment' };
      if (res.status === 204) return null;
      let data;
      try { data = await res.json(); }
      catch {
        if (controller.signal.aborted) throw new DOMException('Aborted', 'AbortError');
        const error = new Error(res.ok ? '服务器响应格式异常，请重试' : errorMessage(null, res.status));
        error.status = res.status; throw error;
      }
      if (!res.ok) { const error = new Error(errorMessage(data, res.status)); error.status = res.status; error.detail = data?.detail; throw error; }
      return data;
    } catch (cause) {
      let error = cause;
      if (controller.signal.aborted) { error = new Error(timedOut ? '请求超时，未确认操作结果。请先刷新记录核对，再决定是否重试。' : '请求已取消'); error.name = timedOut ? 'TimeoutError' : 'AbortError'; }
      else if (cause instanceof TypeError && !cause.status) error = new Error('网络连接失败，请检查网络后重试');
      error.status = error.status || res?.status || 0;
      error.requestId = res?.headers.get('x-request-id') || undefined;
      if (error.status >= 500 && error.requestId) error.message += `（参考编号：${error.requestId.slice(0, 80)}）`;
      throw error;
    } finally { clearTimeout(timer); signal?.removeEventListener('abort', relay); }
  }
  // Writes are never automatically retried: after a timeout the server may have completed them.
  return {
    get: (path, options) => request(path, options),
    post: (path, body, options) => request(path, { ...options, method: 'POST', body: body instanceof FormData ? body : JSON.stringify(body) }),
    put: (path, body, options) => request(path, { ...options, method: 'PUT', body: JSON.stringify(body) }),
    delete: (path, options) => request(path, { ...options, method: 'DELETE' }),
    download: (path, options) => request(path, options, true),
  };
}

export function filenameFromDisposition(value) {
  if (!value) return '';
  const encoded = value.match(/filename\*=(?:UTF-8|utf-8)''([^;]+)/)?.[1];
  if (encoded) { try { return decodeURIComponent(encoded).replace(/[/\\]/g, '_'); } catch { /* Fall back to plain filename. */ } }
  return (value.match(/filename="?([^";]+)"?/)?.[1] || '').replace(/[/\\]/g, '_');
}
