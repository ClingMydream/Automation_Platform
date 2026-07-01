import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Activity,
  ClipboardList,
  Clock,
  Edit3,
  Eye,
  FileText,
  Globe,
  KeyRound,
  Play,
  Plus,
  RefreshCw,
  ShieldCheck,
  TerminalSquare,
  Trash2,
  X,
} from 'lucide-react';
import './styles/app.css';

const API_BASE = '/api';
const DEFAULT_UI_STEPS = '[{"action":"goto","value":"https://example.com"},{"action":"assert_text","value":"Example Domain"},{"action":"screenshot"}]';

function apiClient(token) {
  async function request(path, options = {}) {
    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.headers || {}),
      },
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || '请求失败');
    return data;
  }
  return {
    get: (path) => request(path),
    post: (path, body) => request(path, { method: 'POST', body: JSON.stringify(body) }),
    put: (path, body) => request(path, { method: 'PUT', body: JSON.stringify(body) }),
    delete: (path) => request(path, { method: 'DELETE' }),
  };
}

function formatTime(value) {
  if (!value) return '-';
  return new Date(value).toLocaleString('zh-CN', { hour12: false });
}

function formatDuration(ms) {
  if (ms === null || ms === undefined) return '-';
  if (ms < 1000) return `${ms} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

function StatusBadge({ status }) {
  return <span className={`badge badge-${status || 'queued'}`}>{status || 'queued'}</span>;
}

function PageGuide({ tab }) {
  const guides = {
    projects: {
      title: '项目页试用方法',
      steps: ['新建一个项目作为用例归属。', '已有“示例项目”可以直接使用。', '点“修改”可回填表单，点“删除”会连同关联用例和执行记录一起清理。'],
    },
    api: {
      title: '接口测试试用方法',
      steps: ['选择项目，URL 填 https://example.com。', '断言状态码填 200，响应包含文本填 Example Domain。', '保存后点“执行”，系统会自动跳到执行记录查看结果。'],
    },
    ui: {
      title: 'UI 测试试用方法',
      steps: ['选择项目，步骤 JSON 可先使用默认内容。', '保存后点“执行”，系统会单独打开执行详情窗口。', '详情窗口会自动刷新状态，并展示每一步后的页面截图。'],
    },
    runs: {
      title: '执行记录查看方法',
      steps: ['查看创建时间、更新时间、耗时和状态。', '点“详情”可查看断言、步骤日志、错误信息和 UI 截图。', 'queued/running 状态下可点刷新，详情页也会自动轮询。'],
    },
  };
  const guide = guides[tab] || guides.projects;
  return (
    <section className="trial-guide">
      <div className="trial-guide-title"><ClipboardList size={18} /><strong>{guide.title}</strong></div>
      <ol>{guide.steps.map((step) => <li key={step}>{step}</li>)}</ol>
    </section>
  );
}

function Login({ onLogin }) {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setLoading(true);
    setError('');
    try {
      const data = await apiClient().post('/auth/login', { username, password });
      localStorage.setItem('token', data.access_token);
      onLogin(data.access_token);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-shell">
      <section className="login-panel">
        <div className="brand-row">
          <ShieldCheck size={30} />
          <div>
            <h1>Automation Platform</h1>
            <p>接口测试与低代码 UI 测试控制台</p>
          </div>
        </div>
        <form onSubmit={submit} className="stack">
          <label>管理员账号<input value={username} onChange={(e) => setUsername(e.target.value)} /></label>
          <label>管理员密码<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} autoFocus /></label>
          {error && <div className="error">{error}</div>}
          <button className="primary" disabled={loading}><KeyRound size={18} />{loading ? '登录中' : '登录'}</button>
        </form>
      </section>
    </main>
  );
}

function ProjectPanel({ client, projects, reload, onNotice, onError }) {
  const emptyForm = { name: '', description: '' };
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [saving, setSaving] = useState(false);

  function startEdit(item) {
    setEditingId(item.id);
    setForm({ name: item.name, description: item.description || '' });
  }

  function cancelEdit() {
    setEditingId(null);
    setForm(emptyForm);
  }

  async function submit(event) {
    event.preventDefault();
    setSaving(true);
    try {
      if (editingId) {
        await client.put(`/projects/${editingId}`, form);
        onNotice('项目已更新');
      } else {
        await client.post('/projects', form);
        onNotice('项目已创建');
      }
      cancelEdit();
      await reload();
    } catch (err) {
      onError(err);
    } finally {
      setSaving(false);
    }
  }

  async function remove(item) {
    if (!window.confirm(`确认删除项目“${item.name}”？关联用例和执行记录也会删除。`)) return;
    try {
      await client.delete(`/projects/${item.id}`);
      if (editingId === item.id) cancelEdit();
      onNotice('项目已删除');
      await reload();
    } catch (err) {
      onError(err);
    }
  }

  return (
    <div className="grid two">
      <section className="panel">
        <h2><Plus size={18} />{editingId ? '修改项目' : '新建项目'}</h2>
        <form onSubmit={submit} className="stack">
          <label>项目名称<input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></label>
          <label>说明<textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></label>
          <div className="actions">
            <button className="primary" disabled={saving}><Plus size={18} />{saving ? '保存中' : editingId ? '更新项目' : '保存项目'}</button>
            {editingId && <button type="button" className="ghost" onClick={cancelEdit}><X size={16} />取消</button>}
          </div>
        </form>
      </section>
      <section className="panel">
        <h2><FileText size={18} />项目列表</h2>
        <table>
          <thead><tr><th>ID</th><th>名称</th><th>说明</th><th>操作</th></tr></thead>
          <tbody>{projects.map((item) => (
            <tr key={item.id}>
              <td>{item.id}</td>
              <td>{item.name}</td>
              <td>{item.description}</td>
              <td><RowActions onEdit={() => startEdit(item)} onDelete={() => remove(item)} /></td>
            </tr>
          ))}</tbody>
        </table>
      </section>
    </div>
  );
}

function ApiCasePanel({ client, projects, apiCases, reload, onRunCreated, onNotice, onError }) {
  const emptyForm = { project_id: '', name: '', method: 'GET', url: '', headers: '{}', body: '', assert_status: 200, assert_text: '', assert_json_path: '', assert_json_value: '' };
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [saving, setSaving] = useState(false);

  function payload() {
    return { ...form, project_id: Number(form.project_id), headers: JSON.parse(form.headers || '{}'), assert_status: Number(form.assert_status) || null };
  }

  function startEdit(item) {
    setEditingId(item.id);
    setForm({
      project_id: String(item.project_id),
      name: item.name,
      method: item.method,
      url: item.url,
      headers: JSON.stringify(item.headers || {}, null, 2),
      body: item.body || '',
      assert_status: item.assert_status || '',
      assert_text: item.assert_text || '',
      assert_json_path: item.assert_json_path || '',
      assert_json_value: item.assert_json_value || '',
    });
  }

  function cancelEdit() {
    setEditingId(null);
    setForm(emptyForm);
  }

  async function submit(event) {
    event.preventDefault();
    setSaving(true);
    try {
      if (editingId) {
        await client.put(`/api-cases/${editingId}`, payload());
        onNotice('接口用例已更新');
      } else {
        await client.post('/api-cases', payload());
        onNotice('接口用例已创建');
      }
      cancelEdit();
      await reload();
    } catch (err) {
      onError(err);
    } finally {
      setSaving(false);
    }
  }

  async function remove(item) {
    if (!window.confirm(`确认删除接口用例“${item.name}”？对应执行记录也会删除。`)) return;
    try {
      await client.delete(`/api-cases/${item.id}`);
      if (editingId === item.id) cancelEdit();
      onNotice('接口用例已删除');
      await reload();
    } catch (err) {
      onError(err);
    }
  }

  return (
    <div className="grid two">
      <section className="panel">
        <h2><Globe size={18} />{editingId ? '修改接口用例' : '接口用例'}</h2>
        <form onSubmit={submit} className="stack">
          <label>所属项目<select value={form.project_id} onChange={(e) => setForm({ ...form, project_id: e.target.value })} required><option value="">选择项目</option>{projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
          <label>用例名称<input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></label>
          <div className="inline">
            <label>方法<select value={form.method} onChange={(e) => setForm({ ...form, method: e.target.value })}>{['GET', 'POST', 'PUT', 'PATCH', 'DELETE'].map((m) => <option key={m}>{m}</option>)}</select></label>
            <label>断言状态码<input type="number" value={form.assert_status} onChange={(e) => setForm({ ...form, assert_status: e.target.value })} /></label>
          </div>
          <label>完整 URL<input value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} placeholder="https://example.com" required /></label>
          <label>请求头 JSON<textarea value={form.headers} onChange={(e) => setForm({ ...form, headers: e.target.value })} /></label>
          <label>请求体<textarea value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} /></label>
          <div className="inline">
            <label>响应包含文本<input value={form.assert_text} onChange={(e) => setForm({ ...form, assert_text: e.target.value })} /></label>
            <label>JSON 路径<input value={form.assert_json_path} onChange={(e) => setForm({ ...form, assert_json_path: e.target.value })} placeholder="$.data.name" /></label>
          </div>
          <label>JSON 期望值<input value={form.assert_json_value} onChange={(e) => setForm({ ...form, assert_json_value: e.target.value })} /></label>
          <div className="actions">
            <button className="primary" disabled={saving}><Plus size={18} />{saving ? '保存中' : editingId ? '更新接口用例' : '保存接口用例'}</button>
            {editingId && <button type="button" className="ghost" onClick={cancelEdit}><X size={16} />取消</button>}
          </div>
        </form>
      </section>
      <CaseList client={client} cases={apiCases} type="api" reload={reload} onRunCreated={onRunCreated} onEdit={startEdit} onDelete={remove} onError={onError} />
    </div>
  );
}

function UiCasePanel({ client, projects, uiCases, reload, onRunCreated, onNotice, onError }) {
  const emptyForm = { project_id: '', name: '', steps: DEFAULT_UI_STEPS };
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [saving, setSaving] = useState(false);

  function startEdit(item) {
    setEditingId(item.id);
    setForm({
      project_id: String(item.project_id),
      name: item.name,
      steps: JSON.stringify(item.steps || [], null, 2),
    });
  }

  function cancelEdit() {
    setEditingId(null);
    setForm(emptyForm);
  }

  async function submit(event) {
    event.preventDefault();
    setSaving(true);
    try {
      const body = { project_id: Number(form.project_id), name: form.name, steps: JSON.parse(form.steps) };
      if (editingId) {
        await client.put(`/ui-cases/${editingId}`, body);
        onNotice('UI 用例已更新');
      } else {
        await client.post('/ui-cases', body);
        onNotice('UI 用例已创建');
      }
      cancelEdit();
      await reload();
    } catch (err) {
      onError(err);
    } finally {
      setSaving(false);
    }
  }

  async function remove(item) {
    if (!window.confirm(`确认删除 UI 用例“${item.name}”？对应执行记录也会删除。`)) return;
    try {
      await client.delete(`/ui-cases/${item.id}`);
      if (editingId === item.id) cancelEdit();
      onNotice('UI 用例已删除');
      await reload();
    } catch (err) {
      onError(err);
    }
  }

  return (
    <div className="grid two">
      <section className="panel">
        <h2><TerminalSquare size={18} />{editingId ? '修改 UI 用例' : 'UI 用例'}</h2>
        <form onSubmit={submit} className="stack">
          <label>所属项目<select value={form.project_id} onChange={(e) => setForm({ ...form, project_id: e.target.value })} required><option value="">选择项目</option>{projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
          <label>用例名称<input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></label>
          <label>步骤 JSON<textarea className="codebox" value={form.steps} onChange={(e) => setForm({ ...form, steps: e.target.value })} /></label>
          <p className="hint">支持 action: goto, click, fill, wait, assert_text, screenshot。公网部署默认禁止访问内网地址。</p>
          <div className="actions">
            <button className="primary" disabled={saving}><Plus size={18} />{saving ? '保存中' : editingId ? '更新 UI 用例' : '保存 UI 用例'}</button>
            {editingId && <button type="button" className="ghost" onClick={cancelEdit}><X size={16} />取消</button>}
          </div>
        </form>
      </section>
      <CaseList client={client} cases={uiCases} type="ui" reload={reload} onRunCreated={onRunCreated} onEdit={startEdit} onDelete={remove} onError={onError} />
    </div>
  );
}

function RowActions({ onEdit, onDelete, children }) {
  return (
    <div className="row-actions">
      {children}
      <button type="button" className="ghost" onClick={onEdit}><Edit3 size={15} />修改</button>
      <button type="button" className="danger" onClick={onDelete}><Trash2 size={15} />删除</button>
    </div>
  );
}

function CaseList({ client, cases, type, reload, onRunCreated, onEdit, onDelete, onError }) {
  const [runningId, setRunningId] = useState(null);

  async function runCase(id) {
    let detailWindow = null;
    if (type === 'ui') {
      detailWindow = window.open('', `ui-run-${Date.now()}`, 'width=1180,height=820');
      if (detailWindow) {
        detailWindow.document.write('<!doctype html><title>UI 执行详情</title><body style="font-family:system-ui;padding:24px;">正在创建 UI 执行任务，请稍候...</body>');
      }
    }
    setRunningId(id);
    try {
      const run = await client.post('/runs', { case_type: type, case_id: id });
      if (detailWindow) {
        detailWindow.location.href = `${window.location.origin}${window.location.pathname}?runId=${run.id}`;
      }
      await reload();
      onRunCreated(run, type, Boolean(detailWindow));
    } catch (err) {
      if (detailWindow) detailWindow.close();
      onError(err);
    } finally {
      setRunningId(null);
    }
  }

  return (
    <section className="panel">
      <h2><Play size={18} />{type === 'api' ? '接口' : 'UI'}用例列表</h2>
      <table>
        <thead><tr><th>ID</th><th>名称</th><th>操作</th></tr></thead>
        <tbody>{cases.map((item) => (
          <tr key={item.id}>
            <td>{item.id}</td>
            <td>{item.name}</td>
            <td>
              <RowActions onEdit={() => onEdit(item)} onDelete={() => onDelete(item)}>
                <button type="button" className="primary slim" disabled={runningId === item.id} onClick={() => runCase(item.id)}>
                  <Play size={15} />{runningId === item.id ? '执行中' : '执行'}
                </button>
              </RowActions>
            </td>
          </tr>
        ))}</tbody>
      </table>
    </section>
  );
}

function RunDetail({ run, onClose, onRefresh }) {
  if (!run) {
    return (
      <section className="panel run-detail">
        <div className="panel-title"><h2><Eye size={18} />执行详情</h2><button className="ghost" onClick={onRefresh}><RefreshCw size={16} />刷新</button></div>
        <p className="hint">暂无执行详情，点击列表里的“详情”查看。</p>
      </section>
    );
  }
  const report = run.report || {};
  const events = report.events || [];
  const checks = report.checks || [];
  const screenshots = report.screenshots || [];
  return (
    <section className="panel run-detail">
      <div className="panel-title">
        <h2><Eye size={18} />执行详情 #{run.id}</h2>
        <div className="actions">
          <button className="ghost" onClick={onRefresh}><RefreshCw size={16} />刷新</button>
          <button className="ghost" onClick={onClose}><X size={16} />关闭详情</button>
        </div>
      </div>
      <div className="detail-grid">
        <div><span>类型</span><strong>{run.case_type}</strong></div>
        <div><span>用例 ID</span><strong>{run.case_id}</strong></div>
        <div><span>状态</span><StatusBadge status={run.status} /></div>
        <div><span>耗时</span><strong>{formatDuration(run.duration_ms)}</strong></div>
        <div><span>创建时间</span><strong>{formatTime(run.created_at)}</strong></div>
        <div><span>更新时间</span><strong>{formatTime(run.updated_at)}</strong></div>
      </div>
      {run.logs && <p className="hint"><Clock size={14} /> {run.logs}</p>}
      {run.error && <div className="error">{run.error}</div>}
      {report.latest_screenshot && (
        <div className="screenshot-box">
          <h3>当前页面截图</h3>
          <img src={report.latest_screenshot} alt={`run-${run.id}-latest`} />
        </div>
      )}
      {events.length > 0 && (
        <div className="detail-section">
          <h3>UI 步骤</h3>
          <table>
            <thead><tr><th>步骤</th><th>动作</th><th>目标</th><th>值</th><th>耗时</th><th>页面</th></tr></thead>
            <tbody>{events.map((event) => (
              <tr key={`${event.step}-${event.action}`}>
                <td>{event.step}</td>
                <td>{event.action}</td>
                <td className="clip">{event.target || '-'}</td>
                <td className="clip">{event.value || '-'}</td>
                <td>{formatDuration(event.elapsed_ms)}</td>
                <td className="clip">{event.title || event.url || '-'}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
      {checks.length > 0 && (
        <div className="detail-section">
          <h3>接口断言</h3>
          <table>
            <thead><tr><th>名称</th><th>结果</th><th>期望</th><th>实际</th></tr></thead>
            <tbody>{checks.map((check) => (
              <tr key={check.name}>
                <td>{check.name}</td>
                <td>{check.passed ? '通过' : '失败'}</td>
                <td>{String(check.expected ?? '-')}</td>
                <td>{String(check.actual ?? '-')}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
      {report.response && (
        <div className="detail-section">
          <h3>接口响应</h3>
          <pre className="report">{JSON.stringify(report.response, null, 2)}</pre>
        </div>
      )}
      {screenshots.length > 0 && (
        <div className="detail-section screenshot-grid">
          <h3>截图清单</h3>
          {screenshots.map((item) => <img key={`${item.step}-${item.title}`} src={item.image} alt={item.title} />)}
        </div>
      )}
    </section>
  );
}

function RunsPanel({ runs, reload, selectedRunId, onSelectRun }) {
  const selectedRun = runs.find((run) => run.id === selectedRunId) || runs[0];
  return (
    <div className="grid runs-layout">
      <section className="panel">
        <div className="panel-title">
          <h2><Activity size={18} />执行记录</h2>
          <button className="ghost" onClick={reload}><RefreshCw size={16} />刷新</button>
        </div>
        <table>
          <thead><tr><th>ID</th><th>类型</th><th>用例</th><th>状态</th><th>创建时间</th><th>更新时间</th><th>耗时</th><th>操作</th></tr></thead>
          <tbody>{runs.map((run) => (
            <tr key={run.id} className={selectedRun?.id === run.id ? 'selected-row' : ''}>
              <td>{run.id}</td>
              <td>{run.case_type}</td>
              <td>{run.case_id}</td>
              <td><StatusBadge status={run.status} /></td>
              <td>{formatTime(run.created_at)}</td>
              <td>{formatTime(run.updated_at)}</td>
              <td>{formatDuration(run.duration_ms)}</td>
              <td><button className="ghost slim" onClick={() => onSelectRun(run.id)}><Eye size={15} />详情</button></td>
            </tr>
          ))}</tbody>
        </table>
      </section>
      <RunDetail run={selectedRun} onClose={() => onSelectRun(null)} onRefresh={reload} />
    </div>
  );
}

function App() {
  const initialRunId = Number(new URLSearchParams(window.location.search).get('runId')) || null;
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [tab, setTab] = useState(initialRunId ? 'runs' : 'projects');
  const [selectedRunId, setSelectedRunId] = useState(initialRunId);
  const [data, setData] = useState({ projects: [], apiCases: [], uiCases: [], runs: [] });
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const client = useMemo(() => apiClient(token), [token]);

  async function reload() {
    if (!token) return;
    try {
      const [projects, apiCases, uiCases, runs] = await Promise.all([
        client.get('/projects'),
        client.get('/api-cases'),
        client.get('/ui-cases'),
        client.get('/runs'),
      ]);
      setData({ projects, apiCases, uiCases, runs });
      setError('');
    } catch (err) {
      handleError(err);
    }
  }

  function handleError(err) {
    setError(err.message || '操作失败');
    setNotice('');
  }

  function handleNotice(message) {
    setNotice(message);
    setError('');
  }

  function handleSelectRun(runId) {
    setSelectedRunId(runId);
    if (runId) {
      const url = new URL(window.location.href);
      url.searchParams.set('runId', runId);
      window.history.replaceState(null, '', url);
    } else {
      window.history.replaceState(null, '', window.location.pathname);
    }
  }

  function handleRunCreated(run, type, detailWindowOpened) {
    setTab('runs');
    handleSelectRun(run.id);
    if (type === 'ui') {
      handleNotice(detailWindowOpened ? `已创建 UI 执行任务 #${run.id}，详情窗口会自动刷新截图。` : `已创建 UI 执行任务 #${run.id}。浏览器拦截了新窗口，请在执行记录里点详情查看截图。`);
    } else {
      handleNotice(`已创建接口执行任务 #${run.id}，正在后台运行。`);
    }
    setTimeout(() => reload(), 1000);
    setTimeout(() => reload(), 3000);
  }

  useEffect(() => { reload(); }, [token]);

  useEffect(() => {
    if (!token || tab !== 'runs') return undefined;
    const selected = data.runs.find((run) => run.id === selectedRunId);
    if (!selected || !['queued', 'running'].includes(selected.status)) return undefined;
    const timer = window.setInterval(() => reload(), 2000);
    return () => window.clearInterval(timer);
  }, [token, tab, selectedRunId, data.runs]);

  if (!token) return <Login onLogin={setToken} />;

  const tabs = [
    ['projects', '项目'],
    ['api', '接口测试'],
    ['ui', 'UI 测试'],
    ['runs', '执行记录'],
  ];

  return (
    <div className="app-shell">
      <aside>
        <div className="brand-row small"><ShieldCheck size={24} /><strong>Automation Platform</strong></div>
        <nav>{tabs.map(([key, label]) => <button key={key} className={tab === key ? 'active' : ''} onClick={() => setTab(key)}>{label}</button>)}</nav>
        <button className="logout" onClick={() => { localStorage.removeItem('token'); setToken(''); }}>退出登录</button>
      </aside>
      <main className="content">
        <header><h1>{tabs.find(([key]) => key === tab)?.[1]}</h1><button className="ghost" onClick={reload}><RefreshCw size={16} />刷新</button></header>
        <PageGuide tab={tab} />
        {notice && <div className="notice">{notice}</div>}
        {error && <div className="error">{error}</div>}
        {tab === 'projects' && <ProjectPanel client={client} projects={data.projects} reload={reload} onNotice={handleNotice} onError={handleError} />}
        {tab === 'api' && <ApiCasePanel client={client} projects={data.projects} apiCases={data.apiCases} reload={reload} onRunCreated={handleRunCreated} onNotice={handleNotice} onError={handleError} />}
        {tab === 'ui' && <UiCasePanel client={client} projects={data.projects} uiCases={data.uiCases} reload={reload} onRunCreated={handleRunCreated} onNotice={handleNotice} onError={handleError} />}
        {tab === 'runs' && <RunsPanel runs={data.runs} reload={reload} selectedRunId={selectedRunId} onSelectRun={handleSelectRun} />}
      </main>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
