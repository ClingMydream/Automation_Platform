// File purpose: Shared API request wrapper. It adds auth headers and normalizes backend errors.
// How to change: edit UI text/layout in this file; move reusable logic into shared helpers or the module feature file.

import { API_BASE, AUTH_EXPIRED_EVENT } from './constants';

// 前端 API 客户端：页面模块只调用 get/post/put/delete，不直接拼 fetch。
// 这样后续统一加日志、重试、鉴权过期处理时，只需要改这一个文件。
function authExpiredError() {
  const err = new Error('登录已过期，请重新登录');
  err.authExpired = true;
  return err;
}

// 广播登录过期事件，让主应用回到登录页并提示用户。
function notifyAuthExpired() {
  window.dispatchEvent(new CustomEvent(AUTH_EXPIRED_EVENT));
}

// Create a shared API client that attaches tokens and handles expired sessions.
export function apiClient(token) {
  // Send one HTTP request, parse the response, and normalize API errors.
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
    download: async (path) => {
      const res = await fetch(`${API_BASE}${path}`, {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
      });
      if (res.status === 401 && token) {
        notifyAuthExpired();
        throw authExpiredError();
      }
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || '下载失败');
      }
      return {
        blob: await res.blob(),
        filename: filenameFromDisposition(res.headers.get('Content-Disposition')) || 'attachment',
      };
    },
  };
}

// Parse backend file names from Content-Disposition when downloading evidence attachments.
function filenameFromDisposition(value) {
  if (!value) return '';
  const utf8Match = value.match(/filename\*=UTF-8''([^;]+)/i);
  if (utf8Match) return decodeURIComponent(utf8Match[1]);
  const plainMatch = value.match(/filename="?([^";]+)"?/i);
  return plainMatch ? plainMatch[1] : '';
}
