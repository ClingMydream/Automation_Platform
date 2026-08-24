import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  App as AntApp,
  Avatar,
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
import { FileTransferPanel } from './modules/04-file-transfer/FileTransferPanel.jsx';
import { PublicTransferPage } from './modules/04-file-transfer/PublicTransferPage.jsx';
import { ImageToolPanel } from './modules/05-image-tools/ImageToolPanel.jsx';
import { DataGeneratorPanel } from './modules/05-data-generator/DataGeneratorPanel.jsx';
import { IntegrationPanel } from './modules/06-integrations/IntegrationPanel.jsx';
import { JsonToolsPanel } from './modules/06-json-tools/JsonToolsPanel.jsx';
import { CodecPanel } from './modules/07-codec-tools/CodecPanel.jsx';
import { LearningPanel } from './modules/08-learning/LearningPanel.jsx';
import { ApiWorkspacePanel } from './modules/09-api-workspace/ApiWorkspacePanel.jsx';
import { RestfulBookerPanel } from './modules/09-api-workspace/RestfulBookerPanel.jsx';
import { UserPanel } from './modules/10-user-management/UserPanel.jsx';
import { TestPackagePanel } from './modules/11-test-packages/TestPackagePanel.jsx';
import { PublicPackageDownload } from './modules/11-test-packages/PublicPackageDownload.jsx';
import { CommandLibraryPanel } from './modules/12-command-library/CommandLibraryPanel.jsx';
import { EffectStudio, PublicEffectPage, HAPPY_ZHAO_PATH } from './modules/13-effects/EffectStudio.jsx';
import { JenkinsPanel } from './modules/14-jenkins/JenkinsPanel.jsx';
import { apiClient } from './shared/apiClient.js';
import { AUTH_EXPIRED_EVENT } from './shared/constants.js';
import { CuteIcon } from './shared/CuteIcon.jsx';
import 'antd/dist/reset.css';
import './styles/app.css';


const { Header, Sider, Content } = Layout;
const { Text, Title } = Typography;
const HOTEL_PROJECT_PATH = '/hotel-project';

const MENU_SECTIONS = [
  {
    key: 'growth',
    label: '个人成长',
    children: [
      { key: 'learning', label: '学习空间', icon: <CuteIcon emoji="📚" tone="violet" /> },
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
    ],
  },
  {
    key: 'settings',
    label: '系统配置',
    children: [
      { key: 'integrations', label: '集成配置', icon: <CuteIcon emoji="🔌" tone="rose" /> },
      { key: 'users', label: '用户管理', icon: <CuteIcon emoji="👥" tone="cyan" />, adminOnly: true },
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

function ToolboxApp() {
  const params = new URLSearchParams(window.location.search);
  const isHotelProject = window.location.pathname === HOTEL_PROJECT_PATH;
  const isPublicEffect = window.location.pathname === HAPPY_ZHAO_PATH;
  const transferToken = params.get('transferToken');
  const testPackage = params.get('testPackage');
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [user, setUser] = useState(null);
  const [tab, setTab] = useState('data_generator');
  const [collapsed, setCollapsed] = useState(false);
  const [integrations, setIntegrations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loginNotice, setLoginNotice] = useState('');
  const { message } = AntApp.useApp();
  const client = useMemo(() => apiClient(token), [token]);

  function logout(notice = '') {
    localStorage.removeItem('token');
    setToken('');
    setUser(null);
    setIntegrations([]);
    setLoginNotice(notice);
  }

  async function reload() {
    if (!token) return;
    setLoading(true);
    try {
      const currentUser = await client.get('/auth/me');
      setUser(currentUser);
      const allowed = new Set(currentUser.is_admin ? ALL_ITEMS.map((item) => item.key) : currentUser.menu_permissions || []);
      const webhookRows = allowed.has('integrations') ? await client.get('/v1/integrations/webhooks') : [];
      setIntegrations(webhookRows);
      const available = menuForUser(currentUser).flatMap((section) => section.children.map((item) => item.key));
      if (!available.includes(tab)) setTab(available[0] || 'data_generator');
    } catch (error) {
      if (!error.authExpired) message.error(error.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { reload(); }, [token]);
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

  if (isPublicEffect) return <PublicEffectPage />;
  if (transferToken) return <PublicTransferPage token={transferToken} />;
  if (testPackage === 'latest') return <PublicPackageDownload />;
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

  const menuItems = menuForUser(user);
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
      <Sider className="toolbox-sider" width={224} collapsedWidth={68} collapsed={collapsed} trigger={null}>
        <div className="toolbox-brand">
          <div className="brand-symbol cute-brand">✦</div>
          {!collapsed && <div><strong>cling</strong><span>cling 的私人空间</span></div>}
        </div>
        <Menu mode="inline" className="toolbox-menu" selectedKeys={[tab]} items={menuItems} onClick={({ key }) => {
          if (key === 'restful_booker') {
            window.open(HOTEL_PROJECT_PATH, 'cling-hotel-practice', 'noopener,noreferrer');
            return;
          }
          if (key === 'online_preview') {
            window.open('/emote-preview/', 'cling-emote-preview', 'noopener,noreferrer');
            return;
          }
          setTab(key);
        }} />
        <div className="sider-footer">
          <div className="sider-status"><i />{!collapsed && <span>服务运行正常</span>}</div>
        </div>
      </Sider>

      <Layout>
        <Header className="toolbox-header">
          <div className="header-left">
            <Button type="text" className="collapse-button" icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />} onClick={() => setCollapsed((value) => !value)} />
            <div className="page-title">
              <Text>{section?.label || '效率工具'}</Text>
              <Title level={3}>{activeItem.label}</Title>
            </div>
          </div>
          <Space size={12}>
            <div className="header-chip"><i /> API 已连接</div>
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
            {tab === 'data_generator' && <DataGeneratorPanel client={client} />}
            {tab === 'files' && <FileTransferPanel client={client} />}
            {tab === 'test_packages' && <TestPackagePanel client={client} />}
            {tab === 'images' && <ImageToolPanel token={token} />}
            {tab === 'json_tools' && <JsonToolsPanel />}
            {tab === 'codec' && <CodecPanel />}
            {tab === 'learning' && <LearningPanel client={client} />}
            {tab === 'command_library' && <CommandLibraryPanel client={client} />}
            {tab === 'effects' && <EffectStudio />}
            {tab === 'jenkins' && <JenkinsPanel />}
            {tab === 'api_workspace' && <ApiWorkspacePanel client={client} />}
            {tab === 'integrations' && <IntegrationPanel client={client} integrations={integrations} reload={reload} />}
            {tab === 'users' && user?.is_admin && <UserPanel client={client} />}
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
        colorPrimary: '#2563eb',
        colorInfo: '#2563eb',
        colorSuccess: '#15803d',
        colorWarning: '#b45309',
        colorError: '#dc2626',
        colorBgLayout: '#f6f7f9',
        colorText: '#182230',
        colorTextSecondary: '#667085',
        borderRadius: 8,
        controlHeight: 40,
        fontFamily: 'Inter, "Segoe UI", "Microsoft YaHei", system-ui, sans-serif',
      },
      components: {
        Card: { headerBg: 'transparent', paddingLG: 24 },
        Table: { headerBg: '#f8fafc', rowHoverBg: '#f8fbff' },
        Menu: { itemBorderRadius: 7, itemHeight: 42 },
        Button: { fontWeight: 600 },
      },
    }}
  >
    <AntApp><ToolboxApp /></AntApp>
  </ConfigProvider>,
);
