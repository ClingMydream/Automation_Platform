import React, { lazy, Suspense, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { App as AntApp, ConfigProvider, theme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { Login } from './modules/00-auth/Login.jsx';
import { ModuleBoundary, ModuleLoading } from './shared/ModuleBoundary.jsx';
import { reloadWhenDeploymentChanges } from './shared/deploymentVersion.js';
import 'antd/dist/reset.css';
import './styles/app.css';
import './styles/platform.css';
import './styles/atelier.css';

const PlatformApp = lazy(() => import('./PlatformApp.jsx'));
function hasSavedSession() {
  try { return Boolean(sessionStorage.getItem('token') || localStorage.getItem('token')); }
  catch { return false; }
}
function PlatformEntry() {
  const [ready, setReady] = useState(hasSavedSession);
  const [updateAvailable, setUpdateAvailable] = useState(false);
  const params = new URLSearchParams(location.search);
  const publicRoute = location.pathname !== '/' || params.has('transferToken') || params.get('testPackage') === 'latest';
  useEffect(() => {
    if (ready || publicRoute) return;
    document.title = '登录 · Cling';
    const check = () => { if (document.visibilityState === 'visible') reloadWhenDeploymentChanges(setUpdateAvailable); };
    const timer = setInterval(check, 60000);
    window.addEventListener('focus', check);
    return () => { clearInterval(timer); window.removeEventListener('focus', check); };
  }, [ready, publicRoute]);
  if (!ready && !publicRoute) return <>
    {updateAvailable && <div className="atelier-login-update" role="status"><span>新版本已就绪，保存输入后可以刷新更新。</span><button onClick={() => location.reload()}>刷新更新</button></div>}
    <Login onLogin={() => setReady(true)} />
  </>;
  return <ModuleBoundary><Suspense fallback={<ModuleLoading />}><PlatformApp /></Suspense></ModuleBoundary>;
}

createRoot(document.getElementById('root')).render(
  <ConfigProvider
    locale={zhCN}
    theme={{
      algorithm: theme.defaultAlgorithm,
      token: {
        colorPrimary: '#756092',
        colorInfo: '#756092',
        colorSuccess: '#15803d',
        colorWarning: '#b45309',
        colorError: '#dc2626',
        colorBgLayout: '#f8f7f4',
        colorText: '#302c35',
        colorTextSecondary: '#736d79',
        colorTextPlaceholder: '#7f678d',
        borderRadius: 12,
        colorBorder: '#9f89ad',
        colorBgContainer: '#fffefd',
        fontSize: 15, controlHeight: 40, controlHeightSM: 32,
        fontFamily: 'Inter, "Segoe UI Variable", "Segoe UI", "Microsoft YaHei", system-ui, sans-serif',
      },
      components: {
        Card: { headerBg: 'transparent', paddingLG: 24 },
        Table: { headerBg: '#f6f4f8', rowHoverBg: '#f4f0f7' },
        Menu: { itemBorderRadius: 12, itemHeight: 42 },
        Button: { fontWeight: 650, borderRadius: 10, controlHeight: 40, controlHeightSM: 32 },
      },
    }}
  >
    <AntApp><ModuleBoundary><Suspense fallback={<ModuleLoading />}><PlatformEntry /></Suspense></ModuleBoundary></AntApp>
  </ConfigProvider>,
);
