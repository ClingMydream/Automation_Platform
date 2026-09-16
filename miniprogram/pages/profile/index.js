const { getSession, setSession, clearSession, requireSession } = require('../../utils/auth');
const { updateProfile, uploadAvatar } = require('../../services/platform');

Page({
  data: { profile: null, displayName: '', familyRole: '', editing: false, uploading: false },
  onShow() {
    if (!requireSession()) return;
    const profile = getSession()?.profile || null;
    this.setData({ profile, displayName: profile?.name || '', familyRole: profile?.family_role || '家庭成员', avatarText: (profile?.name || '我').slice(0, 1) });
  },
  input(e) { this.setData({ [e.currentTarget.dataset.field]: e.detail.value }); },
  edit() { this.setData({ editing: true }); },
  async chooseAvatar(e) {
    const avatarPath = e.detail.avatarUrl;
    if (!avatarPath) return;
    this.setData({ uploading: true });
    try {
      const { avatar_url } = await uploadAvatar(avatarPath);
      const session = getSession();
      setSession({ ...session, profile: { ...session.profile, avatar_url } });
      this.onShow();
      wx.showToast({ title: '头像已更新' });
    } catch (error) { wx.showToast({ title: error.message, icon: 'none' }); }
    finally { this.setData({ uploading: false }); }
  },
  async save() { try { const data = await updateProfile(this.data.displayName.trim(), this.data.familyRole.trim() || '家庭成员'); setSession({ accessToken: data.access_token, profile: data.user }); this.setData({ editing: false }); this.onShow(); wx.showToast({ title: '资料已保存' }); } catch (error) { wx.showToast({ title: error.message, icon: 'none' }); } },
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
