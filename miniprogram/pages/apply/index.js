const { getTemplates, createRequest } = require('../../services/platform');
const { getFallbackTemplates } = require('../../utils/oa-templates');

Page({
  data: { template: null, values: {}, loading: false, focusedKey: '' },
  async onLoad(q) {
    let list = getFallbackTemplates();
    try {
      const remoteTemplates = await getTemplates();
      if (Array.isArray(remoteTemplates) && remoteTemplates.length) list = remoteTemplates;
    } catch (_) {
      // The form still opens so a temporary network issue never hides entries.
    }
    this.setData({ template: list.find((item) => item.key === q.key) || null });
  },
  focus(e) { this.setData({ focusedKey: e.currentTarget.dataset.key }); },
  blur() { this.setData({ focusedKey: '' }); },
  input(e) { this.setData({ [`values.${e.currentTarget.dataset.key}`]: e.detail.value }); },
  pick(e) { const f = this.data.template.fields.find((item) => item.key === e.currentTarget.dataset.key); this.setData({ [`values.${f.key}`]: f.options[e.detail.value] }); },
  date(e) { this.setData({ [`values.${e.currentTarget.dataset.key}`]: e.detail.value }); },
  async submit() {
    this.setData({ loading: true });
    try {
      await createRequest(this.data.template.key, this.data.values);
      wx.showToast({ title: '已提交', icon: 'success' });
      setTimeout(() => wx.navigateBack(), 500);
    } catch (e) { wx.showToast({ title: e.message, icon: 'none' }); } finally { this.setData({ loading: false }); }
  },
});
