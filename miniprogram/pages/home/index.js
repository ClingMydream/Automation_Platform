const { getMe, getHealth } = require('../../services/platform');
const { setSession, requireSession } = require('../../utils/auth');

Page({
  data: { profile: null, loading: true, healthText: '正在检查服务…', healthOk: false },
  onShow() {
    if (!requireSession()) return;
    this.load();
  },
  async load() {
    this.setData({ loading: true });
    const session = getApp().globalData.session;
    this.setData({ profile: session?.profile || null });
    try {
      const profile = await getMe();
      setSession({ ...session, profile });
      this.setData({ profile });
    } catch (_) { /* request helper already handles expired sessions */ }
    try {
      await getHealth();
      this.setData({ healthText: '服务连接正常', healthOk: true });
    } catch (error) {
      this.setData({ healthText: error.message, healthOk: false });
    } finally {
      this.setData({ loading: false });
    }
  },
  openFeature(event) {
    wx.showToast({ title: `${event.currentTarget.dataset.name}将在下一阶段接入`, icon: 'none' });
  },
});
