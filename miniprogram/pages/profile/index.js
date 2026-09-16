const { getSession, setSession, clearSession, requireSession } = require('../../utils/auth');
const { updateProfile } = require('../../services/platform');

Page({
  data: { profile: null, displayName: '', editing: false },
  onShow() {
    if (!requireSession()) return;
    const profile = getSession()?.profile || null;
    this.setData({ profile, displayName: profile?.name || '', avatarText: (profile?.name || '我').slice(0, 1) });
  },
  input(e) { this.setData({ displayName: e.detail.value }); },
  edit() { this.setData({ editing: true }); },
  async save() { try { const data = await updateProfile(this.data.displayName.trim()); setSession({ accessToken: data.access_token, profile: data.user }); this.setData({ editing: false }); this.onShow(); wx.showToast({ title: '已保存' }); } catch (error) { wx.showToast({ title: error.message, icon: 'none' }); } },
  logout() {
    wx.showModal({
      title: '退出登录', content: '退出后需要重新输入平台账号。',
      success: ({ confirm }) => {
        if (!confirm) return;
        clearSession();
        wx.reLaunch({ url: '/pages/login/index' });
      },
    });
  },
});
