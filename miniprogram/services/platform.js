const { request } = require('../utils/request');

function wechatLogin(code) { return request({ url: '/oa/auth/wechat-login', method: 'POST', data: { code }, auth: false }); }
function devLogin(displayName) { return request({ url: '/oa/auth/dev-login', method: 'POST', data: { display_name: displayName }, auth: false }); }
function getTemplates() { return request({ url: '/oa/templates' }); }
function getRequests(scope = 'mine') { return request({ url: `/oa/requests?scope=${scope}` }); }
function createRequest(templateKey, formData) { return request({ url: '/oa/requests', method: 'POST', data: { template_key: templateKey, form_data: formData } }); }
function decideRequest(id, action, comment) { return request({ url: `/oa/requests/${id}/decision`, method: 'POST', data: { action, comment } }); }
function updateProfile(displayName) { return request({ url: '/oa/profile', method: 'PUT', data: { display_name: displayName } }); }

module.exports = { wechatLogin, devLogin, getTemplates, getRequests, createRequest, decideRequest, updateProfile };
