// File purpose: Application entry. It wires login state, permission menus, routing, and shared page data.
// How to change: edit UI text/layout in this file; move reusable logic into shared helpers or the module feature file.

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Login } from './modules/00-auth/Login.jsx';
import { ProjectPanel } from './modules/01-projects/ProjectPanel.jsx';
import { ApiCasePanel } from './modules/02-api-testing/ApiCasePanel.jsx';
import { UiCasePanel } from './modules/03-ui-testing/UiCasePanel.jsx';
import { FileTransferPanel } from './modules/04-file-transfer/FileTransferPanel.jsx';
import { PublicTransferPage } from './modules/04-file-transfer/PublicTransferPage.jsx';
import { ImageToolPanel } from './modules/05-image-tools/ImageToolPanel.jsx';
import { JsonToolsPanel } from './modules/06-json-tools/JsonToolsPanel.jsx';
import { CodecPanel } from './modules/07-codec-tools/CodecPanel.jsx';
import { RunsPanel } from './modules/08-run-history/RunsPanel.jsx';
import { ReportsPanel } from './modules/09-test-reports/ReportsPanel.jsx';
import { UserPanel } from './modules/10-user-management/UserPanel.jsx';
import { TestObjectPanel } from './modules/01-test-objects/TestObjectPanel.jsx';
import { TestCapabilityPanel } from './modules/02-test-capabilities/TestCapabilityPanel.jsx';
import { TestTaskPanel } from './modules/02-test-tasks/TestTaskPanel.jsx';
import { ResultCenterPanel } from './modules/03-result-center/ResultCenterPanel.jsx';
import { ProblemDiagnosisPanel } from './modules/04-problem-diagnosis/ProblemDiagnosisPanel.jsx';
import { QualityAnalysisPanel } from './modules/04-quality-analysis/QualityAnalysisPanel.jsx';
import { TestDatasetPanel } from './modules/05-test-datasets/TestDatasetPanel.jsx';
import { IntegrationPanel } from './modules/06-integrations/IntegrationPanel.jsx';
import { LiveRunWindow } from './modules/90-live-run/LiveRunWindow.jsx';
import { apiClient } from './shared/apiClient';
import { PageGuide } from './shared/PageGuide.jsx';
import { AUTH_EXPIRED_EVENT } from './shared/constants';
import {
  App as AntApp,
  Button,
  ConfigProvider,
  Layout,
  Menu,
  Typography,
  theme,
} from 'antd';
import {
  ApiOutlined,
  AimOutlined,
  BugOutlined,
  CloudUploadOutlined,
  ClockCircleOutlined,
  CodeOutlined,
  DatabaseOutlined,
  DeploymentUnitOutlined,
  FileDoneOutlined,
  FolderOutlined,
  LineChartOutlined,
  LogoutOutlined,
  NodeIndexOutlined,
  PictureOutlined,
  ProfileOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  SwapOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import 'antd/dist/reset.css';
import './styles/app.css';

const { Header, Sider, Content } = Layout;
const { Text, Title } = Typography;


// 常改位置：左侧菜单、reload 数据源、tab 到页面组件的映射。
function PlatformApp() {
  const params = new URLSearchParams(window.location.search);
  const initialRunId = Number(params.get('runId')) || null;
  const liveRunId = Number(params.get('liveRunId')) || null;
  const transferToken = params.get('transferToken');
  // State block: values here control loading, selection, form state, and visible page data.
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [tab, setTab] = useState(initialRunId ? 'runs' : 'projects');
  const [selectedRunId, setSelectedRunId] = useState(initialRunId);
  const [data, setData] = useState({
    projects: [],
    testObjects: [],
    testTasks: [],
    batches: [],
    results: [],
    problemFindings: [],
    qualitySummary: {},
    qualityTrend: [],
    datasets: [],
    integrations: [],
    apiCases: [],
    uiCases: [],
    runs: [],
    reports: [],
  });
  const [currentUser, setCurrentUser] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [loginNotice, setLoginNotice] = useState('');
  const authExpiredShownRef = useRef(false);
  const { message } = AntApp.useApp();
  const client = useMemo(() => apiClient(token), [token]);

  // Store the new token after login and load protected data.
  function handleLogin(nextToken) {
    authExpiredShownRef.current = false;
    setLoginNotice('');
    setToken(nextToken);
  }

  // Clear local login state when the API reports an expired token.
  function logoutExpired() {
    localStorage.removeItem('token');
    setToken('');
    setTab('projects');
    setSelectedRunId(null);
    setData({
      projects: [],
      testObjects: [],
      testTasks: [],
      batches: [],
      results: [],
      problemFindings: [],
      qualitySummary: {},
      qualityTrend: [],
      datasets: [],
      integrations: [],
      apiCases: [],
      uiCases: [],
      runs: [],
      reports: [],
    });
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

  // Reload all dashboard data that is shared by multiple pages.
  async function reload() {
    if (!token) return;
    setRefreshing(true);
    try {
      const me = await client.get('/auth/me');
      setCurrentUser(me);
      const allowed = new Set(me.is_admin ? ['projects', 'test_objects', 'capabilities', 'test_tasks', 'results', 'diagnosis', 'quality', 'datasets', 'api', 'ui', 'files', 'images', 'json_tools', 'codec', 'runs', 'reports', 'integrations', 'users'] : me.menu_permissions || []);
      const [projects, testObjects, testTasks, batches, results, problemFindings, qualitySummary, qualityTrend, datasets, integrations, apiCases, uiCases, runs, reports] = await Promise.all([
        allowed.has('projects') ? client.get('/projects') : Promise.resolve([]),
        allowed.has('test_objects') ? client.get('/v1/test-objects') : Promise.resolve([]),
        allowed.has('test_tasks') ? client.get('/v1/test-tasks') : Promise.resolve([]),
        allowed.has('results') ? client.get('/v1/execution-batches') : Promise.resolve([]),
        allowed.has('results') ? client.get('/v1/test-results') : Promise.resolve([]),
        allowed.has('diagnosis') ? client.get('/v1/problem-findings') : Promise.resolve([]),
        allowed.has('quality') ? client.get('/v1/quality/summary') : Promise.resolve({}),
        allowed.has('quality') ? client.get('/v1/reports/quality-trend') : Promise.resolve([]),
        allowed.has('datasets') ? client.get('/v1/test-datasets') : Promise.resolve([]),
        allowed.has('integrations') ? client.get('/v1/integrations/webhooks') : Promise.resolve([]),
        allowed.has('api') ? client.get('/api-cases') : Promise.resolve([]),
        allowed.has('ui') ? client.get('/ui-cases') : Promise.resolve([]),
        allowed.has('runs') ? client.get('/runs') : Promise.resolve([]),
        allowed.has('reports') ? client.get('/reports') : Promise.resolve([]),
      ]);
      setData({ projects, testObjects, testTasks, batches, results, problemFindings, qualitySummary, qualityTrend, datasets, integrations, apiCases, uiCases, runs, reports });
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

  // Select a run and switch to the run-history page when needed.
  function handleSelectRun(runId) {
    setSelectedRunId(runId);
    const url = new URL(window.location.href);
    if (runId) url.searchParams.set('runId', runId);
    else url.searchParams.delete('runId');
    window.history.replaceState(null, '', url);
  }

  // Handle a newly created run and optionally open the history view.
  function handleRunCreated(run, type, detailWindowOpened) {
    setTab('runs');
    handleSelectRun(run.id);
    if (type === 'ui' && !detailWindowOpened) {
      message.warning('浏览器拦截了新窗口，请在执行记录里点详情查看截图。');
    }
    setTimeout(reload, 1000);
    setTimeout(reload, 3000);
  }

  // Effect block: code here reacts to token, route, or polling changes.
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
    { key: 'test_objects', icon: <AimOutlined />, label: '测试对象' },
    { key: 'capabilities', icon: <DeploymentUnitOutlined />, label: '测试能力' },
    { key: 'test_tasks', icon: <ProfileOutlined />, label: '测试任务' },
    { key: 'results', icon: <NodeIndexOutlined />, label: '结果中心' },
    { key: 'diagnosis', icon: <WarningOutlined />, label: '问题定位' },
    { key: 'quality', icon: <LineChartOutlined />, label: '质量分析' },
    { key: 'datasets', icon: <DatabaseOutlined />, label: '测试数据' },
    { key: 'api', icon: <ApiOutlined />, label: '接口测试' },
    { key: 'ui', icon: <BugOutlined />, label: 'UI 测试' },
    { key: 'files', icon: <CloudUploadOutlined />, label: '文件快传' },
    { key: 'images', icon: <PictureOutlined />, label: '图片工具' },
    { key: 'json_tools', icon: <CodeOutlined />, label: 'JSON 工具' },
    { key: 'codec', icon: <SwapOutlined />, label: '转码工具' },
    { key: 'runs', icon: <ClockCircleOutlined />, label: '执行记录' },
    { key: 'reports', icon: <FileDoneOutlined />, label: '测试报告' },
    { key: 'integrations', icon: <DeploymentUnitOutlined />, label: '集成配置' },
    { key: 'users', icon: <SafetyCertificateOutlined />, label: '用户管理' },
  ];
  // Build sidebar menu items from the current user permissions.
  function menuItemsForUser(user) {
    if (!user) return [];
    const allowed = new Set(user.is_admin ? allMenuItems.map((item) => item.key) : user.menu_permissions || []);
    return allMenuItems.filter((item) => allowed.has(item.key));
  }
  const menuItems = menuItemsForUser(currentUser);
  const currentTitle = menuItems.find((item) => item.key === tab)?.label || '加载中';
  const headerStats = [
    { label: '项目', value: data.projects.length },
    { label: '用例', value: data.apiCases.length + data.uiCases.length },
    { label: '运行', value: data.runs.length + data.batches.length },
  ];

  // Render block: JSX below describes the shell layout, sidebar menu, header, and active page.
  return (
    <Layout className="app-layout">
      <Sider width={236} className="app-sider">
        <div className="brand">
          <span className="brand-mark">ATP</span>
          <div>
            <strong>Automation</strong>
            <span>Test Platform</span>
          </div>
        </div>
        <div className="workspace-switcher">
          <span>默认空间</span>
          <strong>{currentUser?.display_name || currentUser?.username || 'admin'}</strong>
        </div>
        <Menu className="app-menu" mode="inline" selectedKeys={[tab]} items={menuItems} onClick={({ key }) => setTab(key)} />
        <Button className="logout-button" icon={<LogoutOutlined />} onClick={() => { localStorage.removeItem('token'); setCurrentUser(null); setToken(''); }}>退出登录</Button>
      </Sider>
      <Layout>
        <Header className="app-header">
          <div className="header-title-block">
            <Text className="module-eyebrow">Continuous Testing</Text>
            <Title level={3}>{currentTitle}</Title>
          </div>
          <div className="header-actions">
            <div className="header-stat-strip">
              {headerStats.map((item) => (
                <div className="header-stat" key={item.label}>
                  <span>{item.label}</span>
                  <strong>{item.value}</strong>
                </div>
              ))}
            </div>
            <Button className="refresh-button" icon={<ReloadOutlined />} loading={refreshing} onClick={reload}>刷新</Button>
          </div>
        </Header>
        <Content className="app-content">
          <div className="content-shell">
            <PageGuide tab={tab} />
            {tab === 'projects' && <ProjectPanel client={client} projects={data.projects} reload={reload} />}
            {tab === 'test_objects' && <TestObjectPanel client={client} projects={data.projects} testObjects={data.testObjects} reload={reload} />}
            {tab === 'capabilities' && <TestCapabilityPanel client={client} projects={data.projects} />}
            {tab === 'test_tasks' && <TestTaskPanel client={client} projects={data.projects} testObjects={data.testObjects} testTasks={data.testTasks} reload={reload} />}
            {tab === 'results' && <ResultCenterPanel batches={data.batches} results={data.results} />}
            {tab === 'diagnosis' && <ProblemDiagnosisPanel client={client} results={data.results} findings={data.problemFindings} reload={reload} />}
            {tab === 'quality' && <QualityAnalysisPanel qualitySummary={data.qualitySummary} qualityTrend={data.qualityTrend} />}
            {tab === 'datasets' && <TestDatasetPanel client={client} projects={data.projects} datasets={data.datasets} reload={reload} />}
            {tab === 'api' && <ApiCasePanel client={client} projects={data.projects} apiCases={data.apiCases} reload={reload} onRunCreated={handleRunCreated} />}
            {tab === 'ui' && <UiCasePanel client={client} projects={data.projects} uiCases={data.uiCases} reload={reload} onRunCreated={handleRunCreated} />}
            {tab === 'files' && <FileTransferPanel client={client} />}
            {tab === 'images' && <ImageToolPanel token={token} />}
            {tab === 'json_tools' && <JsonToolsPanel />}
            {tab === 'codec' && <CodecPanel />}
            {tab === 'runs' && <RunsPanel runs={data.runs} reload={reload} refreshing={refreshing} selectedRunId={selectedRunId} onSelectRun={handleSelectRun} />}
            {tab === 'reports' && <ReportsPanel reports={data.reports} reload={reload} refreshing={refreshing} />}
            {tab === 'integrations' && <IntegrationPanel client={client} integrations={data.integrations} reload={reload} />}
            {tab === 'users' && currentUser?.is_admin && <UserPanel client={client} />}
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
        colorPrimary: '#2468f2',
        colorInfo: '#2468f2',
        colorSuccess: '#16a34a',
        colorWarning: '#d97706',
        colorError: '#dc2626',
        colorBgLayout: '#f4f7fb',
        colorText: '#1f2937',
        colorTextSecondary: '#667085',
        borderRadius: 6,
        controlHeight: 34,
        fontFamily: 'Inter, "Segoe UI", system-ui, sans-serif',
      },
      components: {
        Layout: {
          headerBg: '#ffffff',
          siderBg: '#ffffff',
        },
        Card: {
          headerBg: '#ffffff',
        },
        Table: {
          headerBg: '#f8fafc',
          rowHoverBg: '#f5f8ff',
        },
        Menu: {
          itemBorderRadius: 6,
          itemSelectedBg: '#eaf1ff',
          itemSelectedColor: '#2468f2',
        },
      },
    }}
  >
    <AntApp>
      <PlatformApp />
    </AntApp>
  </ConfigProvider>,
);
