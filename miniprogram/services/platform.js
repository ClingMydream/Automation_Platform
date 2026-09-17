const { request } = require('../utils/request');

function wechatLogin(code) { return request({ url: '/oa/auth/wechat-login', method: 'POST', data: { code }, auth: false }); }
function accountLogin(username, password) { return request({ url: '/oa/auth/account-login', method: 'POST', data: { username, password }, auth: false }); }
function devLogin(displayName) { return request({ url: '/oa/auth/dev-login', method: 'POST', data: { display_name: displayName }, auth: false }); }
function getTemplates() { return request({ url: '/oa/templates' }); }
function getRequests(scope = 'mine') { return request({ url: `/oa/requests?scope=${scope}` }); }
function createRequest(templateKey, formData) { return request({ url: '/oa/requests', method: 'POST', data: { template_key: templateKey, form_data: formData } }); }
function decideRequest(id, action, comment) { return request({ url: `/oa/requests/${id}/decision`, method: 'POST', data: { action, comment } }); }
function updateProfile(displayName, familyRole) { return request({ url: '/oa/profile', method: 'PUT', data: { display_name: displayName, family_role: familyRole } }); }
function uploadAvatar(filePath) {
  const { apiBaseUrl } = require('../config/env');
  const { getSession } = require('../utils/auth');
  return new Promise((resolve, reject) => wx.uploadFile({
    url: `${apiBaseUrl}/oa/profile/avatar`, filePath, name: 'file', header: { Authorization: `Bearer ${getSession()?.accessToken || ''}` },
    success: ({ statusCode, data }) => { let body = {}; try { body = JSON.parse(data); } catch (_) {} if (statusCode >= 200 && statusCode < 300) resolve(body); else reject(new Error(body.detail || '头像上传失败')); },
    fail: () => reject(new Error('头像上传失败，请检查网络后重试。')),
  }));
}

module.exports = { wechatLogin, accountLogin, devLogin, getTemplates, getRequests, createRequest, decideRequest, updateProfile, uploadAvatar };
