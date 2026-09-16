const { login, getMe } = require('../../services/platform');
const { setSession, getSession } = require('../../utils/auth');

Page({
  data: { username: '', password: '', loading: false, error: '' },
  onLoad() {
    if (getSession()) wx.switchTab({ url: '/pages/home/index' });
  },
  onInput(event) {
    this.setData({ [event.currentTarget.dataset.field]: event.detail.value, error: '' });
  },
  async submit() {
    const { username, password } = this.data;
    if (!username || !password) {
      this.setData({ error: '请输入用户名和密码。' });
      return;
    }
    this.setData({ loading: true, error: '' });
    try {
      const token = await login(username.trim(), password);
      const profile = await getMeWithToken(token.access_token);
      setSession({ accessToken: token.access_token, profile });
      wx.switchTab({ url: '/pages/home/index' });
    } catch (error) {
      this.setData({ error: error.message || '登录失败，请稍后重试。' });
    } finally {
      this.setData({ loading: false });
    }
  },
});

function getMeWithToken(token) {
  const { apiBaseUrl } = require('../../config/env');
  return new Promise((resolve, reject) => wx.request({
    url: `${apiBaseUrl}/auth/me`,
    header: { Authorization: `Bearer ${token}` },
    success: ({ statusCode, data }) => statusCode >= 200 && statusCode < 300
      ? resolve(data)
      : reject(new Error(data?.detail || '无法读取账号信息。')),
    fail: () => reject(new Error('网络连接失败，请检查网络和服务地址。')),
  }));
}
