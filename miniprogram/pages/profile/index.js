const { getSession, clearSession, requireSession } = require('../../utils/auth');

Page({
  data: { profile: null },
  onShow() {
    if (!requireSession()) return;
    const profile = getSession()?.profile || null;
    this.setData({ profile, avatarText: (profile?.display_name || profile?.username || '我').slice(0, 1) });
  },
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
