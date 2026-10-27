import React, { lazy, Suspense, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Login } from './modules/00-auth/Login.jsx';
import { reloadWhenDeploymentChanges } from './shared/deploymentVersion.js';
import 'antd/dist/reset.css';
import './styles/theme.css';
import './styles/app.css';
import './styles/platform.css';
import './styles/atelier.css';

const PlatformApp = lazy(() => import('./WorkspaceRoot.jsx'));
const ModuleLoading = () => <div className="module-loading" role="status"><p>正在加载工作空间…</p></div>;
class ModuleBoundary extends React.Component {
  state = { failed: false };
  static getDerivedStateFromError(){return {failed:true};}
  render(){return this.state.failed ? <div className="atelier-entry-error" role="alert"><h1>工作空间暂时无法加载</h1><p>请检查网络后重试。</p><button onClick={()=>this.setState({failed:false})}>重试</button><button onClick={()=>location.reload()}>刷新加载</button></div> : this.props.children;}
}
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

createRoot(document.getElementById('root')).render(<ModuleBoundary><PlatformEntry /></ModuleBoundary>);
