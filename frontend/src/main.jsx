import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Login } from './modules/auth/Login.jsx';
import { ApiCasePanel } from './modules/apiTesting/ApiCasePanel.jsx';
import { CodecPanel } from './modules/codec/CodecPanel.jsx';
import { FileTransferPanel } from './modules/fileTransfer/FileTransferPanel.jsx';
import { PublicTransferPage } from './modules/fileTransfer/PublicTransferPage.jsx';
import { ImageToolPanel } from './modules/imageTools/ImageToolPanel.jsx';
import { JsonToolsPanel } from './modules/jsonTools/JsonToolsPanel.jsx';
import { LiveRunWindow } from './modules/liveRun/LiveRunWindow.jsx';
import { ProjectPanel } from './modules/projects/ProjectPanel.jsx';
import { ReportsPanel } from './modules/reports/ReportsPanel.jsx';
import { RunsPanel } from './modules/runs/RunsPanel.jsx';
import { UiCasePanel } from './modules/uiTesting/UiCasePanel.jsx';
import { UserPanel } from './modules/users/UserPanel.jsx';
import { apiClient } from './shared/apiClient';
import { PageGuide } from './shared/PageGuide.jsx';
import { AUTH_EXPIRED_EVENT } from './shared/constants';
import {
  Alert,
  App as AntApp,
  Button,
  Card,
  Checkbox,
  Col,
  ConfigProvider,
  Descriptions,
  Drawer,
  Empty,
  Form,
  Input,
  Layout,
  Menu,
  Modal,
  QRCode,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
  Upload,
  theme,
} from 'antd';
import {
  ApiOutlined,
  BugOutlined,
  CloudUploadOutlined,
  CopyOutlined,
  ClockCircleOutlined,
  CloseOutlined,
  CodeOutlined,
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  EyeOutlined,
  FileDoneOutlined,
  FolderOutlined,
  InboxOutlined,
  LogoutOutlined,
  PictureOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
  RocketOutlined,
  SafetyCertificateOutlined,
  SwapOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import 'antd/dist/reset.css';
import './styles/app.css';

const { Header, Sider, Content } = Layout;
const { Text, Title, Paragraph } = Typography;
const { TextArea } = Input;
const { Dragger } = Upload;


// 常改位置：左侧菜单、reload 数据源、tab 到页面组件的映射。
function PlatformApp() {
  const params = new URLSearchParams(window.location.search);
  const initialRunId = Number(params.get('runId')) || null;
  const liveRunId = Number(params.get('liveRunId')) || null;
  const transferToken = params.get('transferToken');
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [tab, setTab] = useState(initialRunId ? 'runs' : 'projects');
  const [selectedRunId, setSelectedRunId] = useState(initialRunId);
  const [data, setData] = useState({ projects: [], apiCases: [], uiCases: [], runs: [], reports: [] });
  const [currentUser, setCurrentUser] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [loginNotice, setLoginNotice] = useState('');
  const authExpiredShownRef = useRef(false);
  const { message } = AntApp.useApp();
  const client = useMemo(() => apiClient(token), [token]);

  function handleLogin(nextToken) {
    authExpiredShownRef.current = false;
    setLoginNotice('');
    setToken(nextToken);
  }

  function logoutExpired() {
    localStorage.removeItem('token');
    setToken('');
    setTab('projects');
    setSelectedRunId(null);
    setData({ projects: [], apiCases: [], uiCases: [], runs: [], reports: [] });
    setCurrentUser(null);
    setLoginNotice('登录已过期，请重新登录');
    const url = new URL(window.location.href);
    url.searchParams.delete('runId');
    url.searchParams.delete('liveRunId');
    window.history.replaceState(null, '', url);
    if (!authExpiredShownRef.current) {
      authExpiredShownRef.current = true;
      message.warning('登录已过期，请重新登录');
    }
  }

  async function reload() {
    if (!token) return;
    setRefreshing(true);
    try {
      const me = await client.get('/auth/me');
      setCurrentUser(me);
      const allowed = new Set(me.is_admin ? ['projects', 'api', 'ui', 'files', 'images', 'json_tools', 'codec', 'runs', 'reports', 'users'] : me.menu_permissions || []);
      const [projects, apiCases, uiCases, runs, reports] = await Promise.all([
        allowed.has('projects') ? client.get('/projects') : Promise.resolve([]),
        allowed.has('api') ? client.get('/api-cases') : Promise.resolve([]),
        allowed.has('ui') ? client.get('/ui-cases') : Promise.resolve([]),
        allowed.has('runs') ? client.get('/runs') : Promise.resolve([]),
        allowed.has('reports') ? client.get('/reports') : Promise.resolve([]),
      ]);
      setData({ projects, apiCases, uiCases, runs, reports });
      const availableTabs = menuItemsForUser(me).map((item) => item.key);
      if (availableTabs.length > 0 && !availableTabs.includes(tab)) {
        setTab(availableTabs[0]);
      }
    } catch (err) {
      if (err.authExpired) return;
      message.error(err.message);
    } finally {
      setRefreshing(false);
    }
  }

  function handleSelectRun(runId) {
    setSelectedRunId(runId);
    const url = new URL(window.location.href);
    if (runId) url.searchParams.set('runId', runId);
    else url.searchParams.delete('runId');
    window.history.replaceState(null, '', url);
  }

  function handleRunCreated(run, type, detailWindowOpened) {
    setTab('runs');
    handleSelectRun(run.id);
    if (type === 'ui' && !detailWindowOpened) {
      message.warning('浏览器拦截了新窗口，请在执行记录里点详情查看截图。');
    }
    setTimeout(reload, 1000);
    setTimeout(reload, 3000);
  }

  useEffect(() => { reload(); }, [token]);

  useEffect(() => {
    window.addEventListener(AUTH_EXPIRED_EVENT, logoutExpired);
    return () => window.removeEventListener(AUTH_EXPIRED_EVENT, logoutExpired);
  }, []);

  useEffect(() => {
    if (!token || tab !== 'runs') return undefined;
    const selected = data.runs.find((run) => run.id === selectedRunId);
    if (!selected || !['queued', 'running'].includes(selected.status)) return undefined;
    const timer = window.setInterval(reload, 2000);
    return () => window.clearInterval(timer);
  }, [token, tab, selectedRunId, data.runs]);

  if (transferToken) return <PublicTransferPage token={transferToken} />;
  if (!token) return <Login onLogin={handleLogin} notice={loginNotice} />;
  if (liveRunId) return <LiveRunWindow token={token} runId={liveRunId} />;

  const allMenuItems = [
    { key: 'projects', icon: <FolderOutlined />, label: '项目' },
    { key: 'api', icon: <ApiOutlined />, label: '接口测试' },
    { key: 'ui', icon: <BugOutlined />, label: 'UI 测试' },
    { key: 'files', icon: <CloudUploadOutlined />, label: '文件快传' },
    { key: 'images', icon: <PictureOutlined />, label: '图片工具' },
    { key: 'json_tools', icon: <CodeOutlined />, label: 'JSON 工具' },
    { key: 'codec', icon: <SwapOutlined />, label: '转码工具' },
    { key: 'runs', icon: <ClockCircleOutlined />, label: '执行记录' },
    { key: 'reports', icon: <FileDoneOutlined />, label: '测试报告' },
    { key: 'users', icon: <SafetyCertificateOutlined />, label: '用户管理' },
  ];
  function menuItemsForUser(user) {
    if (!user) return [];
    const allowed = new Set(user.is_admin ? allMenuItems.map((item) => item.key) : user.menu_permissions || []);
    return allMenuItems.filter((item) => allowed.has(item.key));
  }
  const menuItems = menuItemsForUser(currentUser);
  const currentTitle = menuItems.find((item) => item.key === tab)?.label || '加载中';

  return (
    <Layout className="app-layout">
      <Sider width={248} className="app-sider">
        <div className="brand">
          <SafetyCertificateOutlined />
          <div>
            <strong>Automation</strong>
            <span>Testing Platform</span>
          </div>
        </div>
        <Menu theme="dark" mode="inline" selectedKeys={[tab]} items={menuItems} onClick={({ key }) => setTab(key)} />
        <Button className="logout-button" icon={<LogoutOutlined />} onClick={() => { localStorage.removeItem('token'); setCurrentUser(null); setToken(''); }}>退出登录</Button>
      </Sider>
      <Layout>
        <Header className="app-header">
          <div>
            <Title level={3}>{currentTitle}</Title>
            <Text type="secondary">专业化自动化测试控制台</Text>
          </div>
          <Button icon={<ReloadOutlined />} loading={refreshing} onClick={reload}>刷新数据</Button>
        </Header>
        <Content className="app-content">
          <PageGuide tab={tab} />
          {tab === 'projects' && <ProjectPanel client={client} projects={data.projects} reload={reload} />}
          {tab === 'api' && <ApiCasePanel client={client} projects={data.projects} apiCases={data.apiCases} reload={reload} onRunCreated={handleRunCreated} />}
          {tab === 'ui' && <UiCasePanel client={client} projects={data.projects} uiCases={data.uiCases} reload={reload} onRunCreated={handleRunCreated} />}
          {tab === 'files' && <FileTransferPanel client={client} />}
          {tab === 'images' && <ImageToolPanel token={token} />}
          {tab === 'json_tools' && <JsonToolsPanel />}
          {tab === 'codec' && <CodecPanel />}
          {tab === 'users' && currentUser?.is_admin && <UserPanel client={client} />}
          {tab === 'runs' && <RunsPanel runs={data.runs} reload={reload} refreshing={refreshing} selectedRunId={selectedRunId} onSelectRun={handleSelectRun} />}
          {tab === 'reports' && <ReportsPanel reports={data.reports} reload={reload} refreshing={refreshing} />}
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
        colorPrimary: '#0f766e',
        borderRadius: 6,
        fontFamily: 'Inter, "Segoe UI", system-ui, sans-serif',
      },
    }}
  >
    <AntApp>
      <PlatformApp />
    </AntApp>
  </ConfigProvider>,
);
