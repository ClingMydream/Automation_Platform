const { getTemplates, getRequests } = require('../../services/platform');
const { requireSession } = require('../../utils/auth');
const { getFallbackTemplates } = require('../../utils/oa-templates');

Page({
  data: { profile: null, templates: getFallbackTemplates(), pendingCount: 0 },
  onShow() {
    if (!requireSession()) return;
    this.load();
  },
  async load() {
    const session = getApp().globalData.session;
    this.setData({ profile: session?.profile || null });
    try {
      const templates = await getTemplates();
      if (Array.isArray(templates) && templates.length) this.setData({ templates });
    } catch (_) {
      // Keep the locally packaged household application entries visible.
    }
    try {
      const requests = await getRequests('mine');
      this.setData({ pendingCount: requests.filter((item) => item.status === 'pending').length });
    } catch (_) {}
  },
  apply(event) { wx.navigateTo({ url: `/pages/apply/index?key=${event.currentTarget.dataset.key}` }); },
  openApprovals() { wx.switchTab({ url: '/pages/approvals/index' }); },
});
