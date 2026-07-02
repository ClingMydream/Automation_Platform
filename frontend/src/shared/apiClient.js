import { API_BASE, AUTH_EXPIRED_EVENT } from './constants';

// 前端 API 客户端。
// 页面模块只调用 get/post/put/delete，不直接拼 fetch，方便以后统一加日志、重试或错误提示。

function authExpiredError() {
  const err = new Error('登录已过期，请重新登录');
  err.authExpired = true;
  return err;
}

function notifyAuthExpired() {
  window.dispatchEvent(new CustomEvent(AUTH_EXPIRED_EVENT));
}

export function apiClient(token) {
  async function request(path, options = {}) {
    const isFormData = options.body instanceof FormData;
    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.headers || {}),
      },
    });
    const data = await res.json().catch(() => ({}));
    if (res.status === 401 && token) {
      notifyAuthExpired();
      throw authExpiredError();
    }
    if (!res.ok) throw new Error(data.detail || '请求失败');
    return data;
  }
  return {
    get: (path) => request(path),
    post: (path, body) => request(path, { method: 'POST', body: body instanceof FormData ? body : JSON.stringify(body) }),
    put: (path, body) => request(path, { method: 'PUT', body: JSON.stringify(body) }),
    delete: (path) => request(path, { method: 'DELETE' }),
  };
}
