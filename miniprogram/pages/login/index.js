const { wechatLogin, devLogin } = require('../../services/platform');
const { setSession, getSession } = require('../../utils/auth');

Page({
  data: { displayName: '体验同事', loading: false, error: '' },
  onLoad() {
    if (getSession()) wx.switchTab({ url: '/pages/home/index' });
  },
  onInput(event) { this.setData({ displayName: event.detail.value, error: '' }); },
  async wechatSignIn() {
    this.setData({ loading: true, error: '' });
    try {
      const loginResult = await wx.login();
      if (!loginResult.code) throw new Error('未获取到微信授权凭据。');
      this.finishLogin(await wechatLogin(loginResult.code));
    } catch (error) {
      this.setData({ error: error.message || '微信授权失败，请稍后重试。' });
    } finally { this.setData({ loading: false }); }
  },
  async devSignIn() {
    this.setData({ loading: true, error: '' });
    try { this.finishLogin(await devLogin(this.data.displayName.trim() || '体验同事')); }
    catch (error) { this.setData({ error: error.message || '体验登录失败，请稍后重试。' }); }
    finally { this.setData({ loading: false }); }
  },
  finishLogin(data) { setSession({ accessToken: data.access_token, profile: data.user }); wx.switchTab({ url: '/pages/home/index' }); },
});
