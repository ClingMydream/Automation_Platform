import React, { useEffect, useMemo, useState, useRef, lazy, Suspense } from 'react';
import { createRoot } from 'react-dom/client';
import {
  App as AntApp,
  Avatar,
  Alert,
  Drawer,
  Button,
  ConfigProvider,
  Dropdown,
  Layout,
  Menu,
  Space,
  Typography,
  theme,
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
const JsonToolsPanel = lazy(() => import('./modules/06-json-tools/JsonToolsPanel.jsx').then(m => ({ default: m.JsonToolsPanel })));
const CodecPanel = lazy(() => import('./modules/07-codec-tools/CodecPanel.jsx').then(m => ({ default: m.CodecPanel })));
const MasteryLearningPanel = lazy(() => import('./modules/08-learning/MasteryLearningPanel.jsx').then(m => ({ default: m.MasteryLearningPanel })));
const ApiWorkspacePanel = lazy(() => import('./modules/09-api-workspace/ApiWorkspacePanel.jsx').then(m => ({ default: m.ApiWorkspacePanel })));
const RestfulBookerPanel = lazy(() => import('./modules/09-api-workspace/RestfulBookerPanel.jsx').then(m => ({ default: m.RestfulBookerPanel })));
const UserPanel = lazy(() => import('./modules/10-user-management/UserPanel.jsx').then(m => ({ default: m.UserPanel })));
const TestPackagePanel = lazy(() => import('./modules/11-test-packages/TestPackagePanel.jsx').then(m => ({ default: m.TestPackagePanel })));
const PublicPackageDownload = lazy(() => import('./modules/11-test-packages/PublicPackageDownload.jsx').then(m => ({ default: m.PublicPackageDownload })));
const CommandLibraryPanel = lazy(() => import('./modules/12-command-library/CommandLibraryPanel.jsx').then(m => ({ default: m.CommandLibraryPanel })));
const EffectStudio = lazy(() => import('./modules/13-effects/EffectStudio.jsx').then(m => ({ default: m.EffectStudio })));
const PublicEffectPage = lazy(() => import('./modules/13-effects/EffectStudio.jsx').then(m => ({ default: m.PublicEffectPage })));
const HAPPY_ZHAO_PATH = '/effect/xiaozhao-happy';
const JenkinsPanel = lazy(() => import('./modules/14-jenkins/JenkinsPanel.jsx').then(m => ({ default: m.JenkinsPanel })));
const OnlinePreviewPanel = lazy(() => import('./modules/15-online-preview/OnlinePreviewPanel.jsx').then(m => ({ default: m.OnlinePreviewPanel })));
const MobilePreviewPage = lazy(() => import('./modules/15-online-preview/MobilePreviewPage.jsx').then(m => ({ default: m.MobilePreviewPage })));
const UiAutomationPage = lazy(() => import('./modules/16-ui-automation/UiAutomationPage.jsx').then(m => ({ default: m.UiAutomationPage })));
const UiAutomationRunViewer = lazy(() => import('./modules/16-ui-automation/UiAutomationRunViewer.jsx').then(m => ({ default: m.UiAutomationRunViewer })));
const CircleStatsPanel = lazy(() => import('./modules/17-circle-stats/CircleStatsPanel.jsx').then(m => ({ default: m.CircleStatsPanel })));
const SelfStudyPanel = lazy(() => import('./modules/18-self-study/SelfStudyPanel.jsx').then(m => ({ default: m.SelfStudyPanel })));
const OaManagementPanel = lazy(() => import('./modules/19-oa-management/OaManagementPanel.jsx').then(m => ({ default: m.OaManagementPanel })));
const FamilyOaWebPage = lazy(() => import('./modules/19-oa-management/FamilyOaWebPage.jsx').then(m => ({ default: m.FamilyOaWebPage })));
import { apiClient } from './shared/apiClient.js';
import { AUTH_EXPIRED_EVENT } from './shared/constants.js';
import { CuteIcon } from './shared/CuteIcon.jsx';
import 'antd/dist/reset.css';
import './styles/app.css';
import './styles/platform.css';
import { ModuleBoundary, ModuleLoading } from './shared/ModuleBoundary.jsx';


const { Header, Sider, Content } = Layout;
const { Text, Title } = Typography;
const HOTEL_PROJECT_PATH = '/hotel-project';
const UI_AUTOMATION_PATH = '/emote-ui-automation';
const MOBILE_PREVIEW_PATH = '/emote-mobile-preview';
const FAMILY_OA_PATH = '/family-oa';

function currentBundlePath() {
  return document.querySelector('script[type="module"][src]')?.getAttribute('src') || '';
}

async function reloadWhenDeploymentChanges(onAvailable) {
  try {
    const response = await fetch(`/?version_check=${Date.now()}`, { cache: 'no-store' });
    if (!response.ok) return;
    const html = await response.text();
    const nextBundle = html.match(/<script[^>]+type=["']module["'][^>]+src=["']([^"']+)["']/)?.[1] || '';
    if (nextBundle && currentBundlePath() && nextBundle !== currentBundlePath()) onAvailable(true);
  } catch {
    // A temporary network failure must not interrupt the page the user is using.
  }
}

const MENU_SECTIONS = [
  {
    key: 'testing',
    label: '测试中心',
    children: [
      { key: 'emote_ui_automation', label: 'Emote UI 自动化', icon: <CuteIcon emoji="🎬" tone="violet" /> },
      { key: 'circle_stats', label: '全员圈统计', icon: <CuteIcon emoji="🫧" tone="cyan" /> },
    ],
  },
  {
    key: 'growth',
    label: '个人成长',
    children: [
      { key: 'learning', label: '学习空间', icon: <CuteIcon emoji="📚" tone="violet" /> },
      { key: 'self_study', label: '自考题库', icon: <CuteIcon emoji="🌱" tone="mint" /> },
      { key: 'command_library', label: '命令手册', icon: <CuteIcon emoji="⌨️" tone="blue" /> },
      { key: 'restful_booker', label: '酒店练习项目', icon: <CuteIcon emoji="🏨" tone="peach" /> },
      { key: 'api_workspace', label: '接口工作台', icon: <CuteIcon emoji="🧪" tone="cyan" /> },
      { key: 'effects', label: '临时效果', icon: <CuteIcon emoji="🎀" tone="rose" /> },
      { key: 'online_preview', label: '在线预览', icon: <CuteIcon emoji="📱" tone="mint" /> },
    ],
  },
  {
    key: 'tools',
    label: '效率工具',
    children: [
      { key: 'jenkins', label: '持续集成', icon: <CuteIcon emoji="🧱" tone="blue" /> },
      { key: 'data_generator', label: '数据生成', icon: <CuteIcon emoji="🧪" tone="blue" /> },
      { key: 'files', label: '文件快传', icon: <CuteIcon emoji="📤" tone="mint" /> },
      { key: 'test_packages', label: '测试包安装', icon: <CuteIcon emoji="📦" tone="blue" /> },
      { key: 'images', label: '图片工具', icon: <CuteIcon emoji="🖼️" tone="peach" /> },
      { key: 'json_tools', label: 'JSON 工具', icon: <CuteIcon emoji="🧩" tone="violet" /> },
      { key: 'codec', label: '转码工具', icon: <CuteIcon emoji="🔄" tone="yellow" /> },
      { key: 'family_oa_web', label: '莓好审批网页版', icon: <CuteIcon emoji="💗" tone="rose" /> },
    ],
  },
  {
    key: 'settings',
    label: '系统配置',
    children: [
      { key: 'integrations', label: '集成配置', icon: <CuteIcon emoji="🔌" tone="rose" /> },
      { key: 'users', label: '用户管理', icon: <CuteIcon emoji="👥" tone="cyan" />, adminOnly: true },
      { key: 'oa_management', label: '小程序 OA 管理', icon: <CuteIcon emoji="🌸" tone="rose" />, adminOnly: true },
    ],
  },
];

const ALL_ITEMS = MENU_SECTIONS.flatMap((section) => section.children);

function menuForUser(user) {
  if (!user) return [];
  const allowed = new Set(user.is_admin ? ALL_ITEMS.map((item) => item.key) : user.menu_permissions || []);
  return MENU_SECTIONS
    .map((section) => ({ ...section, type: 'group', children: section.children.filter((item) => allowed.has(item.key) && (!item.adminOnly || user.is_admin)) }))
    .filter((section) => section.children.length > 0);
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

function ToolboxApp() {
  const params = new URLSearchParams(window.location.search);
  const isHotelProject = window.location.pathname === HOTEL_PROJECT_PATH;
  const uiAutomationRunMatch = window.location.pathname.match(/^\/emote-ui-automation\/run\/([^/]+)$/);
  const isPublicEffect = window.location.pathname === HAPPY_ZHAO_PATH;
  const isMobilePreview = window.location.pathname === MOBILE_PREVIEW_PATH;
  const isFamilyOa = window.location.pathname === FAMILY_OA_PATH;
  const transferToken = params.get('transferToken');
  const testPackage = params.get('testPackage');
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [user, setUser] = useState(null);
  const [tab, updateTab] = useState(() => new URLSearchParams(location.search).get('module') || 'data_generator');
  const [mobile, setMobile] = useState(() => window.innerWidth < 768);
  const [navOpen, setNavOpen] = useState(false);
  const [updateAvailable, setUpdateAvailable] = useState(false);
  const [connection, setConnection] = useState('checking');
  const [profileError, setProfileError] = useState('');
  const authGeneration = useRef(0);
  function setTab(key) {
    const url = new URL(location.href); url.searchParams.set('module', key);
    if (url.href !== location.href) history.pushState(null, '', url);
    updateTab(key); setNavOpen(false);
  }
  useEffect(() => {
    const pop = () => updateTab(new URLSearchParams(location.search).get('module') || 'data_generator');
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
  const [loading, setLoading] = useState(false);
  const [loginNotice, setLoginNotice] = useState('');
  const { message } = AntApp.useApp();
  const client = useMemo(() => apiClient(token), [token]);

  function logout(notice = '') {
    authGeneration.current++;
    localStorage.removeItem('token');
    setToken('');
    setUser(null);
    setIntegrations([]);
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
      const webhookRows = allowed.has('integrations') ? await client.get('/v1/integrations/webhooks') : [];
      setIntegrations(webhookRows);
      const available = menuForUser(currentUser).flatMap((section) => section.children.map((item) => item.key));
      if (!new URLSearchParams(location.search).has('module') && !available.includes(tab)) setTab(available[0] || 'data_generator');
    } catch (error) {
      if (generation === authGeneration.current && !error.authExpired) setProfileError(error.message);
    } finally {
      setLoading(false);
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

  if (isPublicEffect) return <BuiltinEffectGate />;
  if (transferToken) return <PublicTransferPage token={transferToken} />;
  if (testPackage === 'latest') return <PublicPackageDownload />;
  if (isFamilyOa) return <FamilyOaWebPage />;
  if (!token) return <Login notice={loginNotice} onLogin={(value) => { setLoginNotice(''); setToken(value); }} />;
  if (isHotelProject && (user?.is_admin || user?.menu_permissions?.includes('restful_booker'))) {
    return <main className="hotel-project-window">
      <header className="hotel-project-window__header">
        <div><Text>cling · 独立练习窗口</Text><Title level={3}>🏨 酒店练习项目</Title></div>
        <Button onClick={() => window.close()}>关闭此窗口</Button>
      </header>
      <RestfulBookerPanel client={client} />
    </main>;
  }
  if (isMobilePreview && (user?.is_admin || user?.menu_permissions?.includes('online_preview'))) return <MobilePreviewPage />;
  if (uiAutomationRunMatch && (user?.is_admin || user?.menu_permissions?.includes('emote_ui_automation'))) {
    return <UiAutomationRunViewer client={client} runId={uiAutomationRunMatch[1]} />;
  }

  const menuItems = menuForUser(user);
  const allowed = menuItems.flatMap(section => section.children.map(item => item.key)).includes(tab);
  const activeItem = ALL_ITEMS.find((item) => item.key === tab) || ALL_ITEMS[0];
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
      {mobile ? <Drawer title="Cling · 功能导航" placement="left" width={280} open={navOpen} onClose={() => setNavOpen(false)} className="platform-nav">
        <div className="toolbox-brand">
          <div className="brand-symbol cute-brand">✦</div>
          {!collapsed && <div><strong>Cling 自动化平台</strong><span>测试、学习与效率工具</span></div>}
        </div>
        <Menu mode="inline" className="toolbox-menu" selectedKeys={[tab]} items={menuItems} onClick={({ key }) => {
          if (false && key === 'restful_booker') {
            window.open(HOTEL_PROJECT_PATH, 'cling-hotel-practice', 'noopener,noreferrer');
            return;
          }
          setTab(key);
        }} />
        <div className="sider-footer">
          <div className="sider-status"><i />{!collapsed && <span>{connection === 'online' ? '后端可达' : connection === 'checking' ? '正在检查连接' : '后端连接异常'}</span>}</div>
        </div>
      </Drawer> : <Sider className="toolbox-sider" width={224} collapsedWidth={68} collapsed={collapsed} trigger={null}>
        <div className="toolbox-brand">
          <div className="brand-symbol cute-brand">✦</div>
          {!collapsed && <div><strong>Cling 自动化平台</strong><span>测试、学习与效率工具</span></div>}
        </div>
        <Menu mode="inline" className="toolbox-menu" selectedKeys={[tab]} items={menuItems} onClick={({ key }) => {
          if (false && key === 'restful_booker') {
            window.open(HOTEL_PROJECT_PATH, 'cling-hotel-practice', 'noopener,noreferrer');
            return;
          }
          setTab(key);
        }} />
        <div className="sider-footer">
          <div className="sider-status"><i />{!collapsed && <span>{connection === 'online' ? '后端可达' : connection === 'checking' ? '正在检查连接' : '后端连接异常'}</span>}</div>
        </div>
      </Sider>}

      <Layout>
        <Header className="toolbox-header">
          <div className="header-left">
            <Button type="text" className="collapse-button" icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />} aria-label="展开或收起导航" onClick={() => mobile ? setNavOpen(true) : setCollapsed((value) => !value)} />
            <div className="page-title">
              <Text>{section?.label || '效率工具'}</Text>
              <Title level={3}>{activeItem.label}</Title>
            </div>
          </div>
          <Space size={12}>
            <div className={`header-chip connection-${connection}`} title="仅表示平台后端连接；外部服务状态请查看对应模块">{connection === "online" ? "● 后端可达" : connection === "checking" ? "○ 检查连接中" : "● 连接异常"}</div>
            <Dropdown menu={userMenu} placement="bottomRight">
              <Button className="user-button">
                <Avatar size={28} icon={<UserOutlined />} />
                <span>{user?.display_name || user?.username || '用户'}</span>
              </Button>
            </Dropdown>
          </Space>
        </Header>

        <Content className="toolbox-content" aria-busy={loading}>
          <div className="content-container">
            {updateAvailable && <Alert className="platform-notice" type="info" title="新版本已就绪，请保存当前输入后更新" action={<Button onClick={() => window.location.reload()}>刷新更新</Button>} />}
            {profileError && <Alert className="platform-notice" type="error" title={profileError} action={<Button onClick={reload}>重试</Button>} />}
            {!user ? <ModuleLoading /> : !allowed ? <Alert type="warning" title="此功能不存在或当前账号没有访问权限" action={<Button onClick={() => setTab(menuItems[0]?.children[0]?.key || 'data_generator')}>返回可用功能</Button>} /> : <ModuleBoundary key={`${user.id}:${tab}`}><Suspense fallback={<ModuleLoading />}>
            {tab === 'restful_booker' && <RestfulBookerPanel client={client} />}
            {tab === 'data_generator' && <DataGeneratorPanel client={client} />}
            {tab === 'files' && <FileTransferPanel client={client} />}
            {tab === 'test_packages' && <TestPackagePanel client={client} />}
            {tab === 'images' && <ImageToolPanel token={token} />}
            {tab === 'json_tools' && <JsonToolsPanel />}
            {tab === 'codec' && <CodecPanel />}
            {tab === 'family_oa_web' && <FamilyOaWebPage embedded />}
            {tab === 'learning' && <MasteryLearningPanel client={client} isAdmin={user?.is_admin} />}
            {tab === 'command_library' && <CommandLibraryPanel client={client} />}
            {tab === 'effects' && <EffectStudio client={client} isAdmin={user?.is_admin} />}
            {tab === 'jenkins' && <JenkinsPanel client={client} />}
            {tab === 'online_preview' && <OnlinePreviewPanel client={client} />}
            {tab === 'emote_ui_automation' && <UiAutomationPage client={client} embedded />}
            {tab === 'circle_stats' && <CircleStatsPanel client={client} userId={user?.id} />}
            {tab === 'self_study' && <SelfStudyPanel key={user?.id} userId={user?.id} />}
            {tab === 'api_workspace' && <ApiWorkspacePanel client={client} />}
            {tab === 'integrations' && <IntegrationPanel client={client} integrations={integrations} reload={reload} />}
            {tab === 'users' && user?.is_admin && <UserPanel client={client} />}
            {tab === 'oa_management' && user?.is_admin && <OaManagementPanel client={client} />}
            </Suspense></ModuleBoundary>}
          </div>
        </Content>
      </Layout>
    </Layout>
  );
}

createRoot(document.getElementById('root')).render(
  <ConfigProvider
    theme={{
      algorithm: theme.defaultAlgorithm,
      token: {
        colorPrimary: '#6d5bd0',
        colorInfo: '#6d5bd0',
        colorSuccess: '#15803d',
        colorWarning: '#b45309',
        colorError: '#dc2626',
        colorBgLayout: '#f7f5fb',
        colorText: '#182230',
        colorTextSecondary: '#667085',
        borderRadius: 12,
        controlHeight: 40, controlHeightSM: 32,
        fontFamily: 'Inter, "Segoe UI", "Microsoft YaHei", system-ui, sans-serif',
      },
      components: {
        Card: { headerBg: 'transparent', paddingLG: 24 },
        Table: { headerBg: '#faf9fd', rowHoverBg: '#f7f4ff' },
        Menu: { itemBorderRadius: 12, itemHeight: 42 },
        Button: { fontWeight: 650, borderRadius: 10, controlHeight: 40, controlHeightSM: 32 },
      },
    }}
  >
    <AntApp><ModuleBoundary><Suspense fallback={<ModuleLoading />}><ToolboxApp /></Suspense></ModuleBoundary></AntApp>
  </ConfigProvider>,
);
