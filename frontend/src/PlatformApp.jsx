import React, { useEffect, useMemo, useState, useRef, lazy, Suspense } from 'react';
import {
  App as AntApp,
  Avatar,
  Alert,
  Drawer,
  Button,
  Dropdown,
  Layout,
  Menu,
  Space,
  Typography,
} from 'antd';
import {
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  UserOutlined,
} from '@ant-design/icons';

import { Login } from './modules/00-auth/Login.jsx';
const FileTransferPanel = lazy(() => import('./modules/04-file-transfer/FileTransferPanel.jsx').then(m => ({ default: m.FileTransferPanel })));
const PublicTransferPage = lazy(() => import('./modules/04-file-transfer/PublicTransferPage.jsx').then(m => ({ default: m.PublicTransferPage })));
const ImageToolPanel = lazy(() => import('./modules/05-image-tools/ImageToolPanel.jsx').then(m => ({ default: m.ImageToolPanel })));
const DataGeneratorPanel = lazy(() => import('./modules/05-data-generator/DataGeneratorPanel.jsx').then(m => ({ default: m.DataGeneratorPanel })));
const IntegrationPanel = lazy(() => import('./modules/06-integrations/IntegrationPanel.jsx').then(m => ({ default: m.IntegrationPanel })));
const ApiWorkspacePanel = lazy(() => import('./modules/09-api-workspace/ApiWorkspacePanel.jsx').then(m => ({ default: m.ApiWorkspacePanel })));
const UserPanel = lazy(() => import('./modules/10-user-management/UserPanel.jsx').then(m => ({ default: m.UserPanel })));
const PublicPackageDownload = lazy(() => import('./modules/11-test-packages/PublicPackageDownload.jsx').then(m => ({ default: m.PublicPackageDownload })));
const CommandLibraryPanel = lazy(() => import('./modules/12-command-library/CommandLibraryPanel.jsx').then(m => ({ default: m.CommandLibraryPanel })));
const EffectStudio = lazy(() => import('./modules/13-effects/EffectStudio.jsx').then(m => ({ default: m.EffectStudio })));
const PublicEffectPage = lazy(() => import('./modules/13-effects/EffectStudio.jsx').then(m => ({ default: m.PublicEffectPage })));
const HAPPY_ZHAO_PATH = '/effect/xiaozhao-happy';
const MobilePreviewPage = lazy(() => import('./modules/15-online-preview/MobilePreviewPage.jsx').then(m => ({ default: m.MobilePreviewPage })));
const UiAutomationPage = lazy(() => import('./modules/16-ui-automation/UiAutomationPage.jsx').then(m => ({ default: m.UiAutomationPage })));
const UiAutomationRunViewer = lazy(() => import('./modules/16-ui-automation/UiAutomationRunViewer.jsx').then(m => ({ default: m.UiAutomationRunViewer })));
const CircleStatsPanel = lazy(() => import('./modules/17-circle-stats/CircleStatsPanel.jsx').then(m => ({ default: m.CircleStatsPanel })));
const SelfStudyPanel = lazy(() => import('./modules/18-self-study/SelfStudyPanel.jsx').then(m => ({ default: m.SelfStudyPanel })));
const OaManagementPanel = lazy(() => import('./modules/19-oa-management/OaManagementPanel.jsx').then(m => ({ default: m.OaManagementPanel })));
const WorkJournalPanel = lazy(() => import('./modules/20-work-journal/WorkJournalPanel.jsx').then(m => ({ default: m.WorkJournalPanel })));
const PersonalSpace = lazy(()=>import('./modules/21-personal-space/PersonalSpace.jsx').then(m=>({default:m.PersonalSpace})));
const LearningRoute = lazy(()=>import('./modules/21-personal-space/LearningRoute.jsx').then(m=>({default:m.LearningRoute})));
const PracticePanel = lazy(()=>import('./modules/22-practice-lab/PracticePanel.jsx').then(m=>({default:m.PracticePanel})));
const PracticePublicApp = lazy(()=>import('./modules/22-practice-lab/PracticeApp.jsx').then(m=>({default:m.PracticePublicApp})));
import { apiClient } from './shared/apiClient.js';
import { authorizedKeys, collapseNavigation, groupKey } from './shared/navigation.js';
import { EnvironmentPanel } from './shared/EnvironmentPanel.jsx';
import { TextToolsPanel } from './shared/TextToolsPanel.jsx';
import { AUTH_EXPIRED_EVENT } from './shared/constants.js';
import { reloadWhenDeploymentChanges } from './shared/deploymentVersion.js';
import { BrandMark, WorkspaceIcon } from './shared/WorkspaceIdentity.jsx';
import { WorkspaceHome, WorkspaceSearch, ModuleIntro, useWorkspaceHistory } from './shared/WorkspaceChrome.jsx';
import { Search, ChevronRight } from 'lucide-react';
import 'antd/dist/reset.css';
import { ModuleBoundary, ModuleLoading } from './shared/ModuleBoundary.jsx';


const { Header, Sider, Content } = Layout;
const { Text, Title } = Typography;
const UI_AUTOMATION_PATH = '/emote-ui-automation';
const MOBILE_PREVIEW_PATH = '/emote-mobile-preview';


const MENU_SECTIONS = [
  { key: 'workspace', label: '我的工作', children: [{ key: 'home', label: '今日工作台', icon: <WorkspaceIcon name="home" /> },{key:'personal_tasks',label:'待办与备忘',icon:<WorkspaceIcon name="personal_tasks"/>},{key:'work_journal',label:'工作手记',icon:<WorkspaceIcon name="work_journal"/>}] },
  {
    key: 'testing',
    label: '测试中心',
    children: [
      {key:'practice_lab',label:'实践实验室',icon:<WorkspaceIcon name="practice_lab"/>},
      { key: 'emote_ui_automation', label: 'Emote UI 自动化', icon: <WorkspaceIcon name="emote_ui_automation" /> },
      { key: 'circle_stats', label: '全员圈统计', icon: <WorkspaceIcon name="circle_stats" /> },
      { key: 'api_workspace', label: '接口工作台', icon: <WorkspaceIcon name="api_workspace" /> },
      { key: 'jenkins', label: '持续集成', icon: <WorkspaceIcon name="jenkins" /> },
      { key: 'online_preview', label: '在线预览', icon: <WorkspaceIcon name="online_preview" /> },
      { key: 'test_packages', label: '测试包安装', icon: <WorkspaceIcon name="test_packages" /> },
    ],
  },
  {
    key: 'growth',
    label: '知识空间',
    children: [
      {key:'knowledge',label:'笔记本',icon:<WorkspaceIcon name="knowledge"/>},
      {key:'learning_route',label:'学习路线',icon:<WorkspaceIcon name="learning_route"/>},
      { key: 'self_study', label: '自考题库', icon: <WorkspaceIcon name="self_study" /> },
      { key: 'command_library', label: '命令手册', icon: <WorkspaceIcon name="command_library" /> },
      { key: 'effects', label: '临时效果', icon: <WorkspaceIcon name="effects" /> },
    ],
  },
  {
    key: 'tools',
    label: '效率工具',
    children: [
      { key: 'data_generator', label: '数据生成', icon: <WorkspaceIcon name="data_generator" /> },
      { key: 'files', label: '文件快传', icon: <WorkspaceIcon name="files" /> },
      { key: 'images', label: '图片工具', icon: <WorkspaceIcon name="images" /> },
      { key: 'json_tools', label: 'JSON 工具', icon: <WorkspaceIcon name="json_tools" /> },
      { key: 'codec', label: '转码工具', icon: <WorkspaceIcon name="codec" /> },
    ],
  },
  {
    key: 'settings',
    label: '系统配置',
    children: [
      { key: 'integrations', label: '集成配置', icon: <WorkspaceIcon name="integrations" /> },
      { key: 'users', label: '用户管理', icon: <WorkspaceIcon name="users" />, adminOnly: true },
      { key: 'oa_management', label: '小程序 OA 管理', icon: <WorkspaceIcon name="oa_management" />, adminOnly: true },
    ],
  },
];

const ALL_ITEMS = MENU_SECTIONS.flatMap((section) => section.children);

function menuForUser(user) {
  if (!user) return [];
  const allowed = authorizedKeys(user, ALL_ITEMS);
  return collapseNavigation(MENU_SECTIONS.map(section => ({ ...section, type: 'group', children: section.children.filter(item => allowed.has(item.key)).map(({adminOnly,...item})=>item) })).filter(section=>section.children.length));
}

function BuiltinEffectGate() {
  const [enabled, setEnabled] = useState(null);
  useEffect(() => {
    fetch('/api/effects/builtin', { cache: 'no-store' })
      .then((response) => response.ok ? response.json() : Promise.reject())
      .then((state) => setEnabled(state.enabled === true))
      .catch(() => setEnabled(false));
  }, []);
  if (enabled === null) return null;
  return enabled ? <PublicEffectPage /> : <main className="effect-unavailable">此效果已下线</main>;
}

export default function PlatformApp() {
  const params = new URLSearchParams(window.location.search);
  const uiAutomationRunMatch = window.location.pathname.match(/^\/emote-ui-automation\/run\/([^/]+)$/);
  const isPublicEffect = window.location.pathname === HAPPY_ZHAO_PATH;
  const isMobilePreview = window.location.pathname === MOBILE_PREVIEW_PATH;
  const transferToken = params.get('transferToken');
  const testPackage = params.get('testPackage');
  const [token, setToken] = useState(() => sessionStorage.getItem('token') || localStorage.getItem('token'));
  const [user, setUser] = useState(null);
  const [tab, updateTab] = useState(() => new URLSearchParams(location.search).get('module') || 'home');
  const [mobile, setMobile] = useState(() => window.innerWidth < 768);
  const [navOpen, setNavOpen] = useState(false);
  const [fullNav,setFullNav]=useState(false);
  useEffect(()=>{try{setFullNav(localStorage.getItem('cling:navigation:'+user?.username+':full')==='true');}catch{setFullNav(false);}},[user?.username]);
  function toggleNavigation(){const next=!fullNav;setFullNav(next);try{localStorage.setItem('cling:navigation:'+user.username+':full',String(next));}catch{}}
  const [updateAvailable, setUpdateAvailable] = useState(false);
  const [connection, setConnection] = useState('checking');
  const [profileError, setProfileError] = useState('');
  useEffect(() => {
    if (!isPublicEffect && !transferToken && !testPackage && !isMobilePreview && !uiAutomationRunMatch) {
      document.title = token ? `${ALL_ITEMS.find(item => item.key === tab)?.label || '工作空间'} · Cling` : '登录 · Cling';
    }
  }, [tab, Boolean(token)]);
  const [searchOpen,setSearchOpen] = useState(false);
  const [searchQuery,setSearchQuery] = useState('');
  function openSearch(query='') { setSearchQuery(query);setSearchOpen(true); }
  const workspaceSections = menuForUser(user);
  const workspaceItems = workspaceSections.flatMap(section => section.children.map(item => ({ ...item, sectionLabel: section.label })));
  const recentModules = useWorkspaceHistory(user?.username,groupKey(tab, workspaceItems),workspaceItems);
  useEffect(() => {
    if (!token || !user) return;
    const handle = event => { if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') { event.preventDefault();setSearchQuery('');setSearchOpen(value => !value); } };
    window.addEventListener('keydown',handle);return () => window.removeEventListener('keydown',handle);
  },[token, user?.username]);
  const authGeneration = useRef(0);
  function setTab(key, extra={}) {
    const url = new URL(location.href); for(const name of ['record','lesson','new','run','suite'])url.searchParams.delete(name);for(const [name,value]of Object.entries(extra))if(value!=null)url.searchParams.set(name,String(value));url.searchParams.set('module', key);
    if (url.href !== location.href) history.pushState(null, '', url);
    updateTab(key); setNavOpen(false); window.dispatchEvent(new Event('cling:location'));
    window.scrollTo(0, 0);
  }
  useEffect(() => {
    const pop = () => updateTab(new URLSearchParams(location.search).get('module') || 'home');
    const resize = () => { setMobile(window.innerWidth < 768); if(window.innerWidth >= 768) setNavOpen(false); };
    window.addEventListener('popstate', pop); window.addEventListener('resize', resize);
    return () => { window.removeEventListener('popstate',pop); window.removeEventListener('resize',resize); };
  }, []);
  useEffect(() => {
    let active = true, timer, controller;
    const check = async () => {
      controller = new AbortController(); const timeout = setTimeout(() => controller.abort(), 8000);
      try { const r = await fetch('/api/health', {signal:controller.signal,cache:'no-store'}); const data = await r.json(); if(active) setConnection(r.ok && data.status === 'ok' ? 'online' : 'offline'); }
      catch { if(active) setConnection('offline'); }
      finally { clearTimeout(timeout); if(active) timer=setTimeout(check,30000); }
    }; check(); return () => {active=false;clearTimeout(timer);controller?.abort();};
  }, []);
  const [collapsed, setCollapsed] = useState(false);
  const [integrations, setIntegrations] = useState([]);
  const [integrationError, setIntegrationError] = useState('');
  const [loading, setLoading] = useState(false);
  const [loginNotice, setLoginNotice] = useState('');
  const { message } = AntApp.useApp();
  const client = useMemo(() => apiClient(token), [token]);

  function logout(notice = '') {
    authGeneration.current++;
    try{sessionStorage.removeItem('cling:practice:'+user?.username);sessionStorage.removeItem('cling:practice:session');}catch{}
    localStorage.removeItem('token');
    sessionStorage.removeItem('token');
    setToken('');
    setUser(null);
    setIntegrations([]);
    setIntegrationError('');
    setLoginNotice(notice);
  }

  async function reload() {
    if (!token) return;
    const generation = ++authGeneration.current;
    setLoading(true); setProfileError('');
    try {
      const currentUser = await client.get('/auth/me');
      if(generation !== authGeneration.current) return;
      setUser(currentUser);
      const allowed = new Set(currentUser.is_admin ? ALL_ITEMS.map((item) => item.key) : currentUser.menu_permissions || []);
      let webhookRows = [];
      try {
        webhookRows = allowed.has('integrations') ? await client.get('/v1/integrations/webhooks') : [];
        if (generation !== authGeneration.current) return;
        setIntegrationError('');
      } catch (error) {
        if (generation !== authGeneration.current || error.authExpired) return;
        setIntegrationError(error.message);
      }
      if (generation !== authGeneration.current) return;
      setIntegrations(webhookRows);
      const available = menuForUser(currentUser).flatMap((section) => section.children.map((item) => item.key));
      if (!new URLSearchParams(location.search).has('module') && !available.includes(tab)) setTab(available[0] || 'data_generator');
    } catch (error) {
      if (generation === authGeneration.current && !error.authExpired) setProfileError(error.message);
    } finally {
      if (generation === authGeneration.current) setLoading(false);
    }
  }

  useEffect(() => { reload(); }, [token]);
  useEffect(() => {
    const check = () => { if (document.visibilityState === 'visible') reloadWhenDeploymentChanges(setUpdateAvailable); };
    const timer = window.setInterval(check, 60_000);
    window.addEventListener('focus', check);
    document.addEventListener('visibilitychange', check);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener('focus', check);
      document.removeEventListener('visibilitychange', check);
    };
  }, []);
  useEffect(() => {
    const navigate = (event) => setTab(event.detail);
    window.addEventListener('cling:navigate', navigate);
    return () => window.removeEventListener('cling:navigate', navigate);
  }, []);
  useEffect(() => {
    const handleExpired = () => logout('登录已过期，请重新登录');
    window.addEventListener(AUTH_EXPIRED_EVENT, handleExpired);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, handleExpired);
  }, []);

  if (location.pathname==='/practice-app') return <PracticePublicApp/>;
  if (isPublicEffect) return <BuiltinEffectGate />;
  if (transferToken) return <PublicTransferPage token={transferToken} />;
  if (testPackage === 'latest') return <PublicPackageDownload />;
  if (!token) return <Login notice={loginNotice} onLogin={(value) => { setLoginNotice(''); setToken(value); }} />;
  if (isMobilePreview && (user?.is_admin || user?.menu_permissions?.includes('online_preview'))) return <MobilePreviewPage />;
  if (uiAutomationRunMatch && (user?.is_admin || user?.menu_permissions?.includes('emote_ui_automation'))) {
    return <UiAutomationRunViewer client={client} runId={uiAutomationRunMatch[1]} />;
  }

  const allMenuItems = menuForUser(user);
  const essentialKeys=new Set(['home','personal_tasks','work_journal','knowledge','learning_route','practice_lab',groupKey(tab,workspaceItems)]);
  const menuItems=fullNav?allMenuItems:allMenuItems.map(section=>({...section,children:section.children.filter(item=>essentialKeys.has(item.key))})).filter(section=>section.children.length);
  const allowedKeys = authorizedKeys(user, ALL_ITEMS);
  const allowed = allowedKeys.has(tab);
  const activeItem = workspaceItems.find(item=>item.key===groupKey(tab,workspaceItems)) || ALL_ITEMS.find(item=>item.key===tab) || ALL_ITEMS[0];
  const section = MENU_SECTIONS.find((item) => item.children.some((child) => child.key === tab));
  const userMenu = {
    items: [
      { key: 'identity', label: user?.display_name || user?.username || '当前用户', disabled: true, icon: <UserOutlined /> },
      ...(user?.is_admin ? [{ key: 'users', label: '用户管理 / 新增用户', icon: <UserOutlined /> }] : []),
      { type: 'divider' },
      { key: 'logout', label: '退出登录', icon: <LogoutOutlined />, danger: true },
    ],
    onClick: ({ key }) => {
      if (key === 'users') setTab('users');
      if (key === 'logout') logout();
    },
  };

  return (
    <Layout className="toolbox-layout">
      <a href="#main-content" className="skip-to-content">跳转到主要内容</a>
      {mobile ? <Drawer title="Cling · 功能导航" placement="left" size={280} open={navOpen} onClose={() => setNavOpen(false)} className="platform-nav">
        <button className="atelier-brand" onClick={() => setTab('home')} aria-label="返回工作台"><BrandMark/>{!collapsed && <span><strong>cling<span>✦</span></strong><small>给好工作，留一点空间。</small></span>}</button>
        <Menu mode="inline" className="toolbox-menu" selectedKeys={[groupKey(tab,workspaceItems)]} items={menuItems} onClick={({ key }) => {
          setTab(key);
        }} />
        <div className="sider-footer">
          {(mobile||!collapsed)&&<Button type="text" block onClick={toggleNavigation}>{fullNav?'收起工具导航':'显示全部功能'}</Button>}
          <div className={`sider-status connection-${connection}`}><i />{!collapsed && <span>{connection === 'online' ? '后端可达' : connection === 'checking' ? '正在检查连接' : '后端连接异常'}</span>}</div>
        </div>
      </Drawer> : <Sider className="toolbox-sider" width={236} collapsedWidth={76} collapsed={collapsed} trigger={null}>
        <button className="atelier-brand" onClick={() => setTab('home')} aria-label="返回工作台"><BrandMark/>{!collapsed && <span><strong>cling<span>✦</span></strong><small>给好工作，留一点空间。</small></span>}</button>
        <Menu mode="inline" className="toolbox-menu" selectedKeys={[groupKey(tab,workspaceItems)]} items={menuItems} onClick={({ key }) => {
          setTab(key);
        }} />
        <div className="sider-footer">
          {(mobile||!collapsed)&&<Button type="text" block onClick={toggleNavigation}>{fullNav?'收起工具导航':'显示全部功能'}</Button>}
          <div className={`sider-status connection-${connection}`}><i />{!collapsed && <span>{connection === 'online' ? '后端可达' : connection === 'checking' ? '正在检查连接' : '后端连接异常'}</span>}</div>
        </div>
      </Sider>}

      <Layout>
        <Header className="toolbox-header">
          <div className="header-left">
            <Button type="text" className="collapse-button" icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />} aria-label="展开或收起导航" onClick={() => mobile ? setNavOpen(true) : setCollapsed((value) => !value)} />
            <div className="atelier-breadcrumb"><button onClick={() => setTab('home')}>工作空间</button><ChevronRight size={13}/><span>{tab==='home' ? '工作台' : section?.label}</span>{tab!=='home'&&<><ChevronRight size={13}/><strong>{activeItem.label}</strong></>}</div>
          </div>
          <Space size={12}>
            <button className="atelier-search-trigger" onClick={() => openSearch()} aria-label="搜索平台功能"><Search size={16}/><span>寻找一个工具…</span><kbd>⌘ / Ctrl K</kbd></button>
            <div className={`header-chip connection-${connection}`} title="仅表示平台后端连接；外部服务状态请查看对应模块">{connection === "online" ? "● 后端可达" : connection === "checking" ? "○ 检查连接中" : "● 连接异常"}</div>
            <Dropdown menu={userMenu} placement="bottomRight">
              <Button className="user-button" aria-label="打开账号菜单">
                <Avatar size={28} icon={<UserOutlined />} />
                <span>{user?.display_name || user?.username || '用户'}</span>
              </Button>
            </Dropdown>
          </Space>
        </Header>

        <Content id="main-content" tabIndex={-1} className="toolbox-content" aria-busy={loading}>
          <div className={`content-container atelier-content atelier-content--${tab}`}>
            {user && allowed && tab!=='home' && <ModuleIntro item={activeItem} section={section}/>}
            {updateAvailable && <Alert className="platform-notice" type="info" title="新版本已就绪，请保存当前输入后更新" action={<Button onClick={() => window.location.reload()}>刷新更新</Button>} />}
            {profileError && <Alert className="platform-notice" type="error" title={profileError} action={<Button onClick={reload}>重试</Button>} />}
            {!user ? <ModuleLoading /> : !allowed ? <Alert type="warning" title="此功能不存在或当前账号没有访问权限" action={<Button onClick={() => setTab(menuItems[0]?.children[0]?.key || 'home')}>返回可用功能</Button>} /> : <ModuleBoundary key={`${user.username}:${tab}`}><Suspense fallback={<ModuleLoading />}>
            {['online_preview','jenkins','test_packages'].includes(tab) && <EnvironmentPanel client={client} activeKey={tab} allowedKeys={allowedKeys} onChange={setTab}/>}
            {['json_tools','codec'].includes(tab) && <TextToolsPanel activeKey={tab} allowedKeys={allowedKeys} onChange={setTab}/>}
            {['personal_tasks','knowledge'].includes(tab) && <PersonalSpace key={user.username+':'+tab} client={client} userKey={user.username} initialKind={tab==='knowledge'?'note':'task'}/>}
            {tab==='learning_route' && <LearningRoute key={user.username} client={client} userKey={user.username} onNavigate={setTab} practiceAllowed={allowedKeys.has('practice_lab')}/>}
            {tab==='practice_lab' && <PracticePanel key={user.username} client={client} userKey={user.username} onNavigate={setTab}/>}
            {tab === 'home' && <WorkspaceHome user={user} sections={workspaceSections} recent={recentModules} onNavigate={setTab} onSearch={openSearch} client={client}/>}
            {tab === 'data_generator' && <DataGeneratorPanel client={client} />}
            {tab === 'files' && <FileTransferPanel client={client} />}
            {tab === 'images' && <ImageToolPanel token={token} />}
            {tab === 'command_library' && <CommandLibraryPanel client={client} />}
            {tab === 'effects' && <EffectStudio client={client} isAdmin={user?.is_admin} />}
            {tab === 'emote_ui_automation' && <UiAutomationPage client={client} embedded />}
            {tab === 'circle_stats' && <CircleStatsPanel key={user?.username} client={client} userKey={user?.username} />}
            {tab === 'self_study' && <SelfStudyPanel key={user?.username} userId={user?.username} client={client} />}
            {tab === 'api_workspace' && <ApiWorkspacePanel client={client} />}
            {tab === 'integrations' && <>{integrationError && <Alert type="error" title={`集成配置加载失败：${integrationError}`} action={<Button onClick={reload}>重新加载配置</Button>} />}<IntegrationPanel client={client} integrations={integrations} reload={reload} /></>}
            {tab === 'users' && user?.is_admin && <UserPanel client={client} />}
            {tab === 'oa_management' && user?.is_admin && <OaManagementPanel client={client} />}
            {tab === 'work_journal' && <WorkJournalPanel client={client} />}
            </Suspense></ModuleBoundary>}
          </div>
        </Content>
      </Layout>
      <WorkspaceSearch open={searchOpen} initialQuery={searchQuery} items={workspaceItems} onClose={() => setSearchOpen(false)} onNavigate={setTab}/>
    </Layout>
  );
}
