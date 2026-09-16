const { getTemplates, getRequests } = require('../../services/platform');
const { requireSession } = require('../../utils/auth');

Page({
  data: { profile: null, templates: [], pendingCount: 0 },
  onShow() {
    if (!requireSession()) return;
    this.load();
  },
  async load() {
    const session = getApp().globalData.session;
    this.setData({ profile: session?.profile || null });
    try { const [templates, requests] = await Promise.all([getTemplates(), getRequests('mine')]); this.setData({ templates, pendingCount: requests.filter((item) => item.status === 'pending').length }); } catch (_) {}
  },
  apply(event) { wx.navigateTo({ url: `/pages/apply/index?key=${event.currentTarget.dataset.key}` }); },
  openApprovals() { wx.switchTab({ url: '/pages/approvals/index' }); },
});
