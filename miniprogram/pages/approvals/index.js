const { getRequests } = require('../../services/platform');
const { requireSession } = require('../../utils/auth');
Page({ data: { requests: [], active: 'mine' }, onShow() { if (requireSession()) this.load(); }, async load() { try { this.setData({ requests: await getRequests(this.data.active) }); } catch (_) {} }, setTab(e) { this.setData({ active: e.currentTarget.dataset.tab }); this.load(); }, detail(e) { wx.navigateTo({ url: `/pages/detail/index?id=${e.currentTarget.dataset.id}&scope=${this.data.active}` }); } });
