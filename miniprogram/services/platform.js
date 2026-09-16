const { request } = require('../utils/request');

function login(username, password) {
  return request({ url: '/auth/login', method: 'POST', data: { username, password }, auth: false });
}

function getMe() {
  return request({ url: '/auth/me' });
}

function getHealth() {
  return request({ url: '/health', auth: false });
}

module.exports = { login, getMe, getHealth };
