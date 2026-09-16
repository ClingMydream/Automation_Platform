const { getSession } = require('./utils/auth');

App({
  globalData: {
    session: getSession(),
  },
  onLaunch() {
    const updateManager = wx.getUpdateManager();
    updateManager.onUpdateReady(() => {
      wx.showModal({
        title: '发现新版本',
        content: '新版本已经准备好，重启后即可使用。',
        success: ({ confirm }) => confirm && updateManager.applyUpdate(),
      });
    });
  },
});
