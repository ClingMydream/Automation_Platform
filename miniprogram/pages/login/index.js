const { wechatLogin, accountLogin } = require('../../services/platform');
const { setSession, getSession } = require('../../utils/auth');

Page({
  data: { username: '', password: '', loading: false, error: '' },
  onLoad() {
    if (getSession()) wx.switchTab({ url: '/pages/home/index' });
  },
  onInput(event) { this.setData({ [event.currentTarget.dataset.field]: event.detail.value, error: '' }); },
  async accountSignIn() {
    const { username, password } = this.data;
    if (!username.trim() || !password) { this.setData({ error: '请填写账号和密码。' }); return; }
    this.setData({ loading: true, error: '' });
    try { this.finishLogin(await accountLogin(username.trim(), password)); }
    catch (error) { this.setData({ error: error.message || '账号登录失败，请稍后重试。' }); }
    finally { this.setData({ loading: false }); }
  },
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
  finishLogin(data) { setSession({ accessToken: data.access_token, profile: data.user }); wx.switchTab({ url: '/pages/home/index' }); },
});
