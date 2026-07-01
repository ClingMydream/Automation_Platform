import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Activity,
  ClipboardList,
  Edit3,
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

function StatusBadge({ status }) {
  return <span className={`badge badge-${status || 'queued'}`}>{status || 'queued'}</span>;
}

function TrialGuide() {
  const steps = [
    '项目：先保留“示例项目”，也可以新建自己的项目。',
    '接口测试：选择项目，填写 https://example.com，状态码填 200，保存后点执行。',
    'UI 测试：选择项目，使用默认步骤 JSON，保存后点执行。',
    '执行记录：刷新后查看 passed/failed、耗时、错误和报告内容。',
  ];
  return (
    <section className="trial-guide">
      <div className="trial-guide-title"><ClipboardList size={18} /><strong>快速试用方法</strong></div>
      <ol>{steps.map((step) => <li key={step}>{step}</li>)}</ol>
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
    setRunningId(id);
    try {
      const run = await client.post('/runs', { case_type: type, case_id: id });
      await reload();
      onRunCreated(run);
    } catch (err) {
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

function RunsPanel({ runs, reload }) {
  return (
    <section className="panel">
      <div className="panel-title">
        <h2><Activity size={18} />执行记录</h2>
        <button className="ghost" onClick={reload}><RefreshCw size={16} />刷新</button>
      </div>
      <table>
        <thead><tr><th>ID</th><th>类型</th><th>用例</th><th>状态</th><th>耗时</th><th>错误</th></tr></thead>
        <tbody>{runs.map((run) => <tr key={run.id}><td>{run.id}</td><td>{run.case_type}</td><td>{run.case_id}</td><td><StatusBadge status={run.status} /></td><td>{run.duration_ms ?? '-'}</td><td className="clip">{run.error}</td></tr>)}</tbody>
      </table>
      <pre className="report">{JSON.stringify(runs[0]?.report || {}, null, 2)}</pre>
    </section>
  );
}

function App() {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [tab, setTab] = useState('projects');
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

  function handleRunCreated(run) {
    setTab('runs');
    handleNotice(`已创建执行任务 #${run.id}，正在后台运行。请稍后刷新查看最新状态。`);
    setTimeout(() => reload(), 1200);
    setTimeout(() => reload(), 3500);
  }

  useEffect(() => { reload(); }, [token]);
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
        <TrialGuide />
        {notice && <div className="notice">{notice}</div>}
        {error && <div className="error">{error}</div>}
        {tab === 'projects' && <ProjectPanel client={client} projects={data.projects} reload={reload} onNotice={handleNotice} onError={handleError} />}
        {tab === 'api' && <ApiCasePanel client={client} projects={data.projects} apiCases={data.apiCases} reload={reload} onRunCreated={handleRunCreated} onNotice={handleNotice} onError={handleError} />}
        {tab === 'ui' && <UiCasePanel client={client} projects={data.projects} uiCases={data.uiCases} reload={reload} onRunCreated={handleRunCreated} onNotice={handleNotice} onError={handleError} />}
        {tab === 'runs' && <RunsPanel runs={data.runs} reload={reload} />}
      </main>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
