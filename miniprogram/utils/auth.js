const SESSION_KEY = 'cling_session';

function getSession() {
  return wx.getStorageSync(SESSION_KEY) || null;
}

function setSession(session) {
  wx.setStorageSync(SESSION_KEY, session);
  getApp().globalData.session = session;
}

function clearSession() {
  wx.removeStorageSync(SESSION_KEY);
  getApp().globalData.session = null;
}

function requireSession() {
  if (getSession()) return true;
  wx.reLaunch({ url: '/pages/login/index' });
  return false;
}

module.exports = { getSession, setSession, clearSession, requireSession };
