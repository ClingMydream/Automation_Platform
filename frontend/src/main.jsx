import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Activity, FileText, Globe, KeyRound, Play, Plus, RefreshCw, ShieldCheck, TerminalSquare } from 'lucide-react';
import './styles/app.css';

const API_BASE = '/api';

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
  };
}

function StatusBadge({ status }) {
  return <span className={`badge badge-${status || 'queued'}`}>{status || 'queued'}</span>;
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

function ProjectPanel({ client, projects, reload }) {
  const [form, setForm] = useState({ name: '', description: '' });
  async function submit(event) {
    event.preventDefault();
    await client.post('/projects', form);
    setForm({ name: '', description: '' });
    reload();
  }
  return (
    <div className="grid two">
      <section className="panel">
        <h2><Plus size={18} />新建项目</h2>
        <form onSubmit={submit} className="stack">
          <label>项目名称<input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></label>
          <label>说明<textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></label>
          <button className="primary"><Plus size={18} />保存项目</button>
        </form>
      </section>
      <section className="panel">
        <h2><FileText size={18} />项目列表</h2>
        <table>
          <thead><tr><th>ID</th><th>名称</th><th>说明</th></tr></thead>
          <tbody>{projects.map((item) => <tr key={item.id}><td>{item.id}</td><td>{item.name}</td><td>{item.description}</td></tr>)}</tbody>
        </table>
      </section>
    </div>
  );
}

function ApiCasePanel({ client, projects, apiCases, reload }) {
  const [form, setForm] = useState({ project_id: '', name: '', method: 'GET', url: '', headers: '{}', body: '', assert_status: 200, assert_text: '', assert_json_path: '', assert_json_value: '' });
  async function submit(event) {
    event.preventDefault();
    await client.post('/api-cases', { ...form, project_id: Number(form.project_id), headers: JSON.parse(form.headers || '{}'), assert_status: Number(form.assert_status) || null });
    reload();
  }
  return (
    <div className="grid two">
      <section className="panel">
        <h2><Globe size={18} />接口用例</h2>
        <form onSubmit={submit} className="stack">
          <label>所属项目<select value={form.project_id} onChange={(e) => setForm({ ...form, project_id: e.target.value })} required><option value="">选择项目</option>{projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
          <label>用例名称<input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></label>
          <div className="inline">
            <label>方法<select value={form.method} onChange={(e) => setForm({ ...form, method: e.target.value })}>{['GET', 'POST', 'PUT', 'PATCH', 'DELETE'].map((m) => <option key={m}>{m}</option>)}</select></label>
            <label>断言状态码<input type="number" value={form.assert_status} onChange={(e) => setForm({ ...form, assert_status: e.target.value })} /></label>
          </div>
          <label>完整 URL<input value={form.url} onChange={(e) => setForm({ ...form, url: e.target.value })} placeholder="https://example.com/api/health" required /></label>
          <label>请求头 JSON<textarea value={form.headers} onChange={(e) => setForm({ ...form, headers: e.target.value })} /></label>
          <label>请求体<textarea value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} /></label>
          <div className="inline">
            <label>响应包含文本<input value={form.assert_text} onChange={(e) => setForm({ ...form, assert_text: e.target.value })} /></label>
            <label>JSON 路径<input value={form.assert_json_path} onChange={(e) => setForm({ ...form, assert_json_path: e.target.value })} placeholder="$.data.name" /></label>
          </div>
          <label>JSON 期望值<input value={form.assert_json_value} onChange={(e) => setForm({ ...form, assert_json_value: e.target.value })} /></label>
          <button className="primary"><Plus size={18} />保存接口用例</button>
        </form>
      </section>
      <CaseList client={client} cases={apiCases} type="api" reload={reload} />
    </div>
  );
}

function UiCasePanel({ client, projects, uiCases, reload }) {
  const [form, setForm] = useState({ project_id: '', name: '', steps: '[{\"action\":\"goto\",\"value\":\"https://example.com\"},{\"action\":\"assert_text\",\"value\":\"Example Domain\"},{\"action\":\"screenshot\"}]' });
  async function submit(event) {
    event.preventDefault();
    await client.post('/ui-cases', { project_id: Number(form.project_id), name: form.name, steps: JSON.parse(form.steps) });
    reload();
  }
  return (
    <div className="grid two">
      <section className="panel">
        <h2><TerminalSquare size={18} />UI 用例</h2>
        <form onSubmit={submit} className="stack">
          <label>所属项目<select value={form.project_id} onChange={(e) => setForm({ ...form, project_id: e.target.value })} required><option value="">选择项目</option>{projects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label>
          <label>用例名称<input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required /></label>
          <label>步骤 JSON<textarea className="codebox" value={form.steps} onChange={(e) => setForm({ ...form, steps: e.target.value })} /></label>
          <p className="hint">支持 action: goto, click, fill, wait, assert_text, screenshot。公网部署默认禁止访问内网地址。</p>
          <button className="primary"><Plus size={18} />保存 UI 用例</button>
        </form>
      </section>
      <CaseList client={client} cases={uiCases} type="ui" reload={reload} />
    </div>
  );
}

function CaseList({ client, cases, type, reload }) {
  async function runCase(id) {
    await client.post('/runs', { case_type: type, case_id: id });
    reload();
  }
  return (
    <section className="panel">
      <h2><Play size={18} />{type === 'api' ? '接口' : 'UI'}用例列表</h2>
      <table>
        <thead><tr><th>ID</th><th>名称</th><th>操作</th></tr></thead>
        <tbody>{cases.map((item) => <tr key={item.id}><td>{item.id}</td><td>{item.name}</td><td><button className="ghost" onClick={() => runCase(item.id)}><Play size={16} />执行</button></td></tr>)}</tbody>
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
      setError(err.message);
    }
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
        {error && <div className="error">{error}</div>}
        {tab === 'projects' && <ProjectPanel client={client} projects={data.projects} reload={reload} />}
        {tab === 'api' && <ApiCasePanel client={client} projects={data.projects} apiCases={data.apiCases} reload={reload} />}
        {tab === 'ui' && <UiCasePanel client={client} projects={data.projects} uiCases={data.uiCases} reload={reload} />}
        {tab === 'runs' && <RunsPanel runs={data.runs} reload={reload} />}
      </main>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
