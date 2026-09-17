const { apiBaseUrl } = require('../config/env');
const { getSession, clearSession } = require('./auth');

function request({ url, method = 'GET', data, auth = true }) {
  return new Promise((resolve, reject) => {
    const session = getSession();
    wx.request({
      url: `${apiBaseUrl}${url}`,
      method,
      data,
      header: {
        'content-type': 'application/json',
        ...(auth && session?.accessToken ? { Authorization: `Bearer ${session.accessToken}` } : {}),
      },
      success: ({ statusCode, data: body }) => {
        if (statusCode === 401) {
          clearSession();
          wx.reLaunch({ url: '/pages/login/index' });
          reject(new Error('登录已过期，请重新登录'));
          return;
        }
        if (statusCode < 200 || statusCode >= 300) {
          reject(new Error(body?.detail || body?.message || `请求失败（${statusCode}）`));
          return;
        }
        resolve(body);
      },
      fail: () => reject(new Error('网络连接失败，请检查网络和服务地址。')),
    });
  });
}

module.exports = { request };
