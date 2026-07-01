import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Alert,
  App as AntApp,
  Button,
  Card,
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
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  EyeOutlined,
  FolderOutlined,
  InboxOutlined,
  LogoutOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
  RocketOutlined,
  SafetyCertificateOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import 'antd/dist/reset.css';
import './styles/app.css';

const { Header, Sider, Content } = Layout;
const { Text, Title, Paragraph } = Typography;
const { TextArea } = Input;
const { Dragger } = Upload;

const API_BASE = '/api';
const DEFAULT_UI_STEPS = '[{"action":"goto","value":"https://example.com"},{"action":"assert_text","value":"Example Domain"},{"action":"screenshot"}]';

function apiClient(token) {
  async function request(path, options = {}) {
    const isFormData = options.body instanceof FormData;
    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
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
    post: (path, body) => request(path, { method: 'POST', body: body instanceof FormData ? body : JSON.stringify(body) }),
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

function formatBytes(value) {
  if (!value && value !== 0) return '-';
  const units = ['B', 'KB', 'MB', 'GB'];
  let size = value;
  let index = 0;
  while (size >= 1024 && index < units.length - 1) {
    size /= 1024;
    index += 1;
  }
  return `${size.toFixed(index === 0 ? 0 : 1)} ${units[index]}`;
}

function transferKind(item) {
  const contentType = (item?.content_type || '').toLowerCase();
  const name = (item?.original_name || '').toLowerCase();
  if (contentType.startsWith('image/') || /\.(apng|avif|bmp|gif|heic|heif|ico|jpe?g|png|svg|webp)$/.test(name)) return 'image';
  if (contentType.startsWith('video/') || /\.(3gp|avi|m4v|mkv|mov|mp4|mpeg|mpg|ogv|webm)$/.test(name)) return 'video';
  return 'file';
}

function transferKindLabel(item) {
  return { image: '图片', video: '视频', file: '文件' }[transferKind(item)];
}

function TransferPreview({ item }) {
  if (!item) return null;
  const kind = transferKind(item);
  if (kind === 'image') {
    return (
      <div className="transfer-preview">
        <img src={item.preview_url || item.download_url} alt={item.original_name} />
      </div>
    );
  }
  if (kind === 'video') {
    return (
      <div className="transfer-preview transfer-preview-video">
        <video controls preload="metadata" src={item.preview_url || item.download_url}>
          <track kind="captions" />
        </video>
      </div>
    );
  }
  return null;
}

function statusColor(status) {
  return {
    queued: 'gold',
    running: 'processing',
    passed: 'success',
    failed: 'error',
  }[status || 'queued'] || 'default';
}

function StatusTag({ status }) {
  return <Tag color={statusColor(status)}>{status || 'queued'}</Tag>;
}

function PageGuide({ tab }) {
  const guides = {
    projects: {
      title: '项目管理',
      description: '项目是用例的归属空间。可以先使用示例项目，也可以创建自己的业务项目。',
      steps: ['新建项目', '在接口或 UI 页面选择项目', '必要时修改或删除项目'],
    },
    api: {
      title: '接口测试',
      description: '填写请求地址、方法、请求头和断言条件，保存后即可执行。',
      steps: ['URL 填 https://example.com', '状态码填 200', '响应文本填 Example Domain'],
    },
    ui: {
      title: 'UI 自动化',
      description: '用低代码 JSON 描述页面步骤。执行时会打开独立的实时执行窗口。',
      steps: ['使用默认步骤 JSON', '保存 UI 用例', '点击执行查看实时窗口'],
    },
    runs: {
      title: '执行记录',
      description: '查看任务状态、耗时、执行时间、接口断言、UI 步骤和截图。',
      steps: ['点击详情查看报告', '运行中自动刷新', '失败时查看错误信息'],
    },
    files: {
      title: '文件快传',
      description: '上传临时文件并生成二维码，手机扫码免登录下载，也可以从手机回传文件到电脑端列表。',
      steps: ['上传临时文件', '手机扫码下载', '手机页面可回传文件'],
    },
  };
  const guide = guides[tab] || guides.projects;
  return (
    <Card className="guide-card" size="small">
      <Space align="start" size={14}>
        <div className="guide-icon"><RocketOutlined /></div>
        <div>
          <Title level={5}>{guide.title}</Title>
          <Paragraph>{guide.description}</Paragraph>
          <Space wrap>{guide.steps.map((step, index) => <Tag key={step} color="cyan">{index + 1}. {step}</Tag>)}</Space>
        </div>
      </Space>
    </Card>
  );
}

function Login({ onLogin }) {
  const [loading, setLoading] = useState(false);
  const { message } = AntApp.useApp();

  async function submit(values) {
    setLoading(true);
    try {
      const data = await apiClient().post('/auth/login', values);
      localStorage.setItem('token', data.access_token);
      onLogin(data.access_token);
      message.success('登录成功');
    } catch (err) {
      message.error(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-screen">
      <Card className="login-card">
        <Space direction="vertical" size={24} className="full-width">
          <div className="login-brand">
            <SafetyCertificateOutlined />
            <div>
              <Title level={3}>Automation Platform</Title>
              <Text type="secondary">接口测试与低代码 UI 自动化控制台</Text>
            </div>
          </div>
          <Form layout="vertical" initialValues={{ username: 'admin', password: '' }} onFinish={submit}>
            <Form.Item label="管理员账号" name="username" rules={[{ required: true, message: '请输入账号' }]}>
              <Input size="large" />
            </Form.Item>
            <Form.Item label="管理员密码" name="password" rules={[{ required: true, message: '请输入密码' }]}>
              <Input.Password size="large" autoFocus />
            </Form.Item>
            <Button type="primary" size="large" htmlType="submit" loading={loading} block icon={<SafetyCertificateOutlined />}>登录平台</Button>
          </Form>
        </Space>
      </Card>
    </main>
  );
}

function ProjectPanel({ client, projects, reload }) {
  const [form] = Form.useForm();
  const [editingId, setEditingId] = useState(null);
  const [saving, setSaving] = useState(false);
  const { message, modal } = AntApp.useApp();

  function resetForm() {
    setEditingId(null);
    form.resetFields();
  }

  function startEdit(item) {
    setEditingId(item.id);
    form.setFieldsValue({ name: item.name, description: item.description || '' });
  }

  async function submit(values) {
    setSaving(true);
    try {
      if (editingId) {
        await client.put(`/projects/${editingId}`, values);
        message.success('项目已更新');
      } else {
        await client.post('/projects', values);
        message.success('项目已创建');
      }
      resetForm();
      await reload();
    } catch (err) {
      message.error(err.message);
    } finally {
      setSaving(false);
    }
  }

  function remove(item) {
    modal.confirm({
      title: `删除项目「${item.name}」？`,
      content: '关联接口用例、UI 用例和执行记录也会一起删除。',
      okText: '删除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: async () => {
        await client.delete(`/projects/${item.id}`);
        if (editingId === item.id) resetForm();
        message.success('项目已删除');
        await reload();
      },
    });
  }

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={9}>
        <Card title={editingId ? '修改项目' : '新建项目'} extra={editingId && <Button onClick={resetForm}>取消编辑</Button>}>
          <Form form={form} layout="vertical" onFinish={submit}>
            <Form.Item label="项目名称" name="name" rules={[{ required: true, message: '请输入项目名称' }]}>
              <Input placeholder="例如：电商平台自动化" />
            </Form.Item>
            <Form.Item label="说明" name="description">
              <TextArea rows={5} placeholder="项目用途、业务范围或备注" />
            </Form.Item>
            <Button type="primary" htmlType="submit" loading={saving} icon={<PlusOutlined />}>{editingId ? '更新项目' : '保存项目'}</Button>
          </Form>
        </Card>
      </Col>
      <Col xs={24} xl={15}>
        <Card title="项目列表">
          <Table
            rowKey="id"
            dataSource={projects}
            pagination={{ pageSize: 8 }}
            scroll={{ x: 720 }}
            columns={[
              { title: 'ID', dataIndex: 'id', width: 80 },
              { title: '名称', dataIndex: 'name' },
              { title: '说明', dataIndex: 'description', render: (value) => value || '-' },
              {
                title: '操作',
                width: 170,
                render: (_, record) => (
                  <Space className="table-actions" size={6} wrap>
                    <Button icon={<EditOutlined />} onClick={() => startEdit(record)}>修改</Button>
                    <Button danger icon={<DeleteOutlined />} onClick={() => remove(record)}>删除</Button>
                  </Space>
                ),
              },
            ]}
          />
        </Card>
      </Col>
    </Row>
  );
}

function ApiCasePanel({ client, projects, apiCases, reload, onRunCreated }) {
  const [form] = Form.useForm();
  const [editingId, setEditingId] = useState(null);
  const [saving, setSaving] = useState(false);
  const { message, modal } = AntApp.useApp();

  function resetForm() {
    setEditingId(null);
    form.resetFields();
    form.setFieldsValue({ method: 'GET', headers: '{}', assert_status: 200 });
  }

  function buildPayload(values) {
    return {
      ...values,
      project_id: Number(values.project_id),
      headers: JSON.parse(values.headers || '{}'),
      assert_status: Number(values.assert_status) || null,
      body: values.body || null,
      assert_text: values.assert_text || null,
      assert_json_path: values.assert_json_path || null,
      assert_json_value: values.assert_json_value || null,
    };
  }

  function startEdit(item) {
    setEditingId(item.id);
    form.setFieldsValue({
      project_id: item.project_id,
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

  async function submit(values) {
    setSaving(true);
    try {
      const body = buildPayload(values);
      if (editingId) {
        await client.put(`/api-cases/${editingId}`, body);
        message.success('接口用例已更新');
      } else {
        await client.post('/api-cases', body);
        message.success('接口用例已创建');
      }
      resetForm();
      await reload();
    } catch (err) {
      message.error(err.message);
    } finally {
      setSaving(false);
    }
  }

  function remove(item) {
    modal.confirm({
      title: `删除接口用例「${item.name}」？`,
      content: '对应执行记录也会一起删除。',
      okText: '删除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: async () => {
        await client.delete(`/api-cases/${item.id}`);
        if (editingId === item.id) resetForm();
        message.success('接口用例已删除');
        await reload();
      },
    });
  }

  async function runCase(record) {
    try {
      const run = await client.post('/runs', { case_type: 'api', case_id: record.id });
      message.success(`已创建接口执行任务 #${run.id}`);
      await reload();
      onRunCreated(run, 'api', false);
    } catch (err) {
      message.error(err.message);
    }
  }

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={10}>
        <Card title={editingId ? '修改接口用例' : '接口用例'} extra={editingId && <Button onClick={resetForm}>取消编辑</Button>}>
          <Form form={form} layout="vertical" onFinish={submit} initialValues={{ method: 'GET', headers: '{}', assert_status: 200 }}>
            <Form.Item label="所属项目" name="project_id" rules={[{ required: true, message: '请选择项目' }]}>
              <Select placeholder="选择项目" options={projects.map((project) => ({ value: project.id, label: project.name }))} />
            </Form.Item>
            <Form.Item label="用例名称" name="name" rules={[{ required: true, message: '请输入用例名称' }]}>
              <Input placeholder="例如：检查首页可访问" />
            </Form.Item>
            <Row gutter={12}>
              <Col span={10}>
                <Form.Item label="请求方法" name="method">
                  <Select options={['GET', 'POST', 'PUT', 'PATCH', 'DELETE'].map((value) => ({ value, label: value }))} />
                </Form.Item>
              </Col>
              <Col span={14}>
                <Form.Item label="断言状态码" name="assert_status">
                  <Input type="number" />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item label="完整 URL" name="url" rules={[{ required: true, message: '请输入 URL' }]}>
              <Input placeholder="https://example.com" />
            </Form.Item>
            <Form.Item label="请求头 JSON" name="headers">
              <TextArea rows={4} className="code-input" />
            </Form.Item>
            <Form.Item label="请求体" name="body">
              <TextArea rows={4} className="code-input" />
            </Form.Item>
            <Row gutter={12}>
              <Col span={12}>
                <Form.Item label="响应包含文本" name="assert_text">
                  <Input placeholder="Example Domain" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item label="JSON 路径" name="assert_json_path">
                  <Input placeholder="$.data.name" />
                </Form.Item>
              </Col>
            </Row>
            <Form.Item label="JSON 期望值" name="assert_json_value">
              <Input />
            </Form.Item>
            <Button type="primary" htmlType="submit" loading={saving} icon={<PlusOutlined />}>{editingId ? '更新接口用例' : '保存接口用例'}</Button>
          </Form>
        </Card>
      </Col>
      <Col xs={24} xl={14}>
        <Card title="接口用例列表">
          <Table
            rowKey="id"
            dataSource={apiCases}
            pagination={{ pageSize: 8 }}
            scroll={{ x: 980 }}
            columns={[
              { title: 'ID', dataIndex: 'id', width: 70 },
              { title: '名称', dataIndex: 'name' },
              { title: '方法', dataIndex: 'method', width: 90, render: (value) => <Tag color="blue">{value}</Tag> },
              { title: 'URL', dataIndex: 'url', ellipsis: true },
              {
                title: '操作',
                width: 180,
                fixed: 'right',
                render: (_, record) => (
                  <Space className="table-actions" size={6} wrap>
                    <Button type="primary" icon={<PlayCircleOutlined />} onClick={() => runCase(record)}>执行</Button>
                    <Button icon={<EditOutlined />} onClick={() => startEdit(record)}>修改</Button>
                    <Button danger icon={<DeleteOutlined />} onClick={() => remove(record)}>删除</Button>
                  </Space>
                ),
              },
            ]}
          />
        </Card>
      </Col>
    </Row>
  );
}

function UiCasePanel({ client, projects, uiCases, reload, onRunCreated }) {
  const [form] = Form.useForm();
  const [editingId, setEditingId] = useState(null);
  const [saving, setSaving] = useState(false);
  const [runningId, setRunningId] = useState(null);
  const { message, modal } = AntApp.useApp();

  function resetForm() {
    setEditingId(null);
    form.resetFields();
    form.setFieldsValue({ steps: DEFAULT_UI_STEPS });
  }

  function startEdit(item) {
    setEditingId(item.id);
    form.setFieldsValue({
      project_id: item.project_id,
      name: item.name,
      steps: JSON.stringify(item.steps || [], null, 2),
    });
  }

  async function submit(values) {
    setSaving(true);
    try {
      const body = { project_id: Number(values.project_id), name: values.name, steps: JSON.parse(values.steps) };
      if (editingId) {
        await client.put(`/ui-cases/${editingId}`, body);
        message.success('UI 用例已更新');
      } else {
        await client.post('/ui-cases', body);
        message.success('UI 用例已创建');
      }
      resetForm();
      await reload();
    } catch (err) {
      message.error(err.message);
    } finally {
      setSaving(false);
    }
  }

  function remove(item) {
    modal.confirm({
      title: `删除 UI 用例「${item.name}」？`,
      content: '对应执行记录也会一起删除。',
      okText: '删除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: async () => {
        await client.delete(`/ui-cases/${item.id}`);
        if (editingId === item.id) resetForm();
        message.success('UI 用例已删除');
        await reload();
      },
    });
  }

  async function runCase(record) {
    let detailWindow = window.open('', `ui-run-${Date.now()}`, 'width=1200,height=860');
    if (detailWindow) {
      detailWindow.document.write('<!doctype html><title>UI 自动化执行窗口</title><body style="font-family:system-ui;padding:24px;background:#101820;color:#fff;">正在启动 UI 自动化执行窗口，请稍候...</body>');
    }
    setRunningId(record.id);
    try {
      const run = await client.post('/runs', { case_type: 'ui', case_id: record.id });
      if (detailWindow) {
        detailWindow.location.href = `${window.location.origin}${window.location.pathname}?liveRunId=${run.id}`;
      }
      message.success(`已创建 UI 执行任务 #${run.id}`);
      await reload();
      onRunCreated(run, 'ui', Boolean(detailWindow));
    } catch (err) {
      if (detailWindow) detailWindow.close();
      message.error(err.message);
    } finally {
      setRunningId(null);
    }
  }

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={10}>
        <Card title={editingId ? '修改 UI 用例' : 'UI 用例'} extra={editingId && <Button onClick={resetForm}>取消编辑</Button>}>
          <Form form={form} layout="vertical" onFinish={submit} initialValues={{ steps: DEFAULT_UI_STEPS }}>
            <Form.Item label="所属项目" name="project_id" rules={[{ required: true, message: '请选择项目' }]}>
              <Select placeholder="选择项目" options={projects.map((project) => ({ value: project.id, label: project.name }))} />
            </Form.Item>
            <Form.Item label="用例名称" name="name" rules={[{ required: true, message: '请输入用例名称' }]}>
              <Input placeholder="例如：打开示例页面并断言文本" />
            </Form.Item>
            <Form.Item label="步骤 JSON" name="steps" rules={[{ required: true, message: '请输入步骤 JSON' }]}>
              <TextArea rows={12} className="code-input" />
            </Form.Item>
            <Alert type="info" showIcon message="支持 action: goto, click, fill, wait, assert_text, screenshot。公网部署默认禁止访问内网地址。" />
            <Button className="form-submit" type="primary" htmlType="submit" loading={saving} icon={<PlusOutlined />}>{editingId ? '更新 UI 用例' : '保存 UI 用例'}</Button>
          </Form>
        </Card>
      </Col>
      <Col xs={24} xl={14}>
        <Card title="UI 用例列表">
          <Table
            rowKey="id"
            dataSource={uiCases}
            pagination={{ pageSize: 8 }}
            scroll={{ x: 860 }}
            columns={[
              { title: 'ID', dataIndex: 'id', width: 70 },
              { title: '名称', dataIndex: 'name' },
              { title: '项目', dataIndex: 'project_id', width: 90 },
              { title: '步骤数', dataIndex: 'steps', width: 90, render: (steps) => steps?.length || 0 },
              {
                title: '操作',
                width: 180,
                fixed: 'right',
                render: (_, record) => (
                  <Space className="table-actions" size={6} wrap>
                    <Button type="primary" icon={<PlayCircleOutlined />} loading={runningId === record.id} onClick={() => runCase(record)}>执行</Button>
                    <Button icon={<EditOutlined />} onClick={() => startEdit(record)}>修改</Button>
                    <Button danger icon={<DeleteOutlined />} onClick={() => remove(record)}>删除</Button>
                  </Space>
                ),
              },
            ]}
          />
        </Card>
      </Col>
    </Row>
  );
}

function FileTransferPanel({ client }) {
  const [transfers, setTransfers] = useState([]);
  const [selected, setSelected] = useState(null);
  const [expiresHours, setExpiresHours] = useState(24);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const { message, modal } = AntApp.useApp();

  async function loadTransfers() {
    setLoading(true);
    try {
      const data = await client.get('/file-transfers');
      setTransfers(data);
      if (!selected && data.length > 0) setSelected(data[0]);
    } catch (err) {
      message.error(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadTransfers();
  }, []);

  async function uploadFile({ file, onSuccess, onError }) {
    setUploading(true);
    try {
      const body = new FormData();
      body.append('file', file);
      const item = await client.post(`/file-transfers?expires_hours=${expiresHours}`, body);
      setSelected(item);
      message.success('文件已上传，二维码已生成');
      await loadTransfers();
      onSuccess?.(item);
    } catch (err) {
      message.error(err.message);
      onError?.(err);
    } finally {
      setUploading(false);
    }
  }

  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
      message.success('链接已复制');
    } catch {
      message.warning('复制失败，请手动复制链接');
    }
  }

  function remove(item) {
    modal.confirm({
      title: `删除临时文件「${item.original_name}」？`,
      content: '删除后二维码和下载链接会立即失效。',
      okText: '删除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: async () => {
        await client.delete(`/file-transfers/${item.id}`);
        message.success('临时文件已删除');
        if (selected?.id === item.id) setSelected(null);
        await loadTransfers();
      },
    });
  }

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={9}>
        <Card title="上传临时文件">
          <Space direction="vertical" size={16} className="full-width">
            <Alert type="info" showIcon message="文件默认临时保存，过期后会自动清理。手机扫码页面免登录，请只分享给可信设备。" />
            <Select
              className="full-width"
              value={expiresHours}
              onChange={setExpiresHours}
              options={[
                { value: 1, label: '1 小时后过期' },
                { value: 6, label: '6 小时后过期' },
                { value: 24, label: '24 小时后过期' },
                { value: 72, label: '3 天后过期' },
                { value: 168, label: '7 天后过期' },
              ]}
            />
            <Dragger multiple={false} showUploadList={false} customRequest={uploadFile} disabled={uploading}>
              <p className="ant-upload-drag-icon"><InboxOutlined /></p>
              <p className="ant-upload-text">点击或拖拽文件到这里上传</p>
              <p className="ant-upload-hint">支持图片、视频、压缩包和常见文档，单文件最大 1GB；手机扫码可预览图片/视频，也可直接下载。</p>
            </Dragger>
          </Space>
        </Card>
        {selected && (
          <Card className="share-card" title="扫码下载" extra={<Tag color={selected.source === 'public' ? 'purple' : 'green'}>{selected.source === 'public' ? '手机回传' : '电脑上传'}</Tag>}>
            <Space direction="vertical" size={14} className="full-width">
              <div className="qr-wrap"><QRCode value={selected.share_url} size={196} /></div>
              <Descriptions size="small" column={1}>
                <Descriptions.Item label="文件名">{selected.original_name}</Descriptions.Item>
                <Descriptions.Item label="类型">{transferKindLabel(selected)}</Descriptions.Item>
                <Descriptions.Item label="大小">{formatBytes(selected.size_bytes)}</Descriptions.Item>
                <Descriptions.Item label="过期时间">{formatTime(selected.expires_at)}</Descriptions.Item>
              </Descriptions>
              <TransferPreview item={selected} />
              <Space wrap>
                <Button type="primary" icon={<DownloadOutlined />} onClick={() => window.open(selected.download_url, '_blank')}>下载</Button>
                <Button icon={<CopyOutlined />} onClick={() => copyText(selected.share_url)}>复制扫码链接</Button>
              </Space>
            </Space>
          </Card>
        )}
      </Col>
      <Col xs={24} xl={15}>
        <Card title="临时文件列表" extra={<Button icon={<ReloadOutlined />} loading={loading} onClick={loadTransfers}>刷新</Button>}>
          <Table
            rowKey="id"
            dataSource={transfers}
            loading={loading}
            pagination={{ pageSize: 8 }}
            scroll={{ x: 940 }}
            columns={[
              { title: 'ID', dataIndex: 'id', width: 70 },
              { title: '文件名', dataIndex: 'original_name', ellipsis: true },
              { title: '类型', width: 90, render: (_, record) => <Tag color={transferKind(record) === 'video' ? 'volcano' : transferKind(record) === 'image' ? 'cyan' : 'default'}>{transferKindLabel(record)}</Tag> },
              { title: '大小', dataIndex: 'size_bytes', width: 110, render: formatBytes },
              { title: '来源', dataIndex: 'source', width: 100, render: (value) => <Tag color={value === 'public' ? 'purple' : 'green'}>{value === 'public' ? '手机回传' : '电脑上传'}</Tag> },
              { title: '创建时间', dataIndex: 'created_at', width: 180, render: formatTime },
              { title: '过期时间', dataIndex: 'expires_at', width: 180, render: formatTime },
              {
                title: '操作',
                width: 230,
                fixed: 'right',
                render: (_, record) => (
                  <Space className="table-actions transfer-actions" size={6} wrap>
                    <Button icon={<EyeOutlined />} onClick={() => setSelected(record)}>二维码</Button>
                    <Button icon={<DownloadOutlined />} onClick={() => window.open(record.download_url, '_blank')}>下载</Button>
                    <Button danger icon={<DeleteOutlined />} onClick={() => remove(record)}>删除</Button>
                  </Space>
                ),
              },
            ]}
          />
        </Card>
      </Col>
    </Row>
  );
}

function PublicTransferPage({ token }) {
  const client = useMemo(() => apiClient(), []);
  const [item, setItem] = useState(null);
  const [error, setError] = useState('');
  const [uploading, setUploading] = useState(false);
  const [returnedFile, setReturnedFile] = useState(null);
  const { message } = AntApp.useApp();

  async function loadTransfer() {
    try {
      const data = await client.get(`/file-transfers/public/${token}`);
      setItem(data);
      setError('');
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    loadTransfer();
  }, [token]);

  async function uploadBack({ file, onSuccess, onError }) {
    setUploading(true);
    try {
      const body = new FormData();
      body.append('file', file);
      const data = await client.post(`/file-transfers/public/${token}/upload`, body);
      setReturnedFile(data);
      message.success('已上传回传文件，电脑端刷新列表即可看到');
      onSuccess?.(data);
    } catch (err) {
      message.error(err.message);
      onError?.(err);
    } finally {
      setUploading(false);
    }
  }

  return (
    <main className="public-transfer-screen">
      <Card className="public-transfer-card">
        <Space direction="vertical" size={18} className="full-width">
          <div className="public-transfer-title">
            <CloudUploadOutlined />
            <div>
              <Title level={3}>文件快传</Title>
              <Text type="secondary">免登录临时传文件</Text>
            </div>
          </div>
          {error && <Alert type="error" showIcon message={error} />}
          {item && (
            <>
              <Descriptions bordered column={1} size="small">
                <Descriptions.Item label="文件名">{item.original_name}</Descriptions.Item>
                <Descriptions.Item label="类型">{transferKindLabel(item)}</Descriptions.Item>
                <Descriptions.Item label="大小">{formatBytes(item.size_bytes)}</Descriptions.Item>
                <Descriptions.Item label="来源">{item.source === 'public' ? '手机回传' : '电脑上传'}</Descriptions.Item>
                <Descriptions.Item label="过期时间">{formatTime(item.expires_at)}</Descriptions.Item>
              </Descriptions>
              <TransferPreview item={item} />
              <Button type="primary" size="large" block icon={<DownloadOutlined />} onClick={() => window.open(item.download_url, '_self')}>下载到手机</Button>
              <Alert type="info" showIcon message="也可以从手机上传文件回电脑，电脑端在文件快传列表刷新即可看到。" />
              <Dragger multiple={false} showUploadList={false} customRequest={uploadBack} disabled={uploading}>
                <p className="ant-upload-drag-icon"><InboxOutlined /></p>
                <p className="ant-upload-text">从手机选择文件回传</p>
                <p className="ant-upload-hint">支持图片、视频和常见文件，上传后会生成新的临时文件记录。</p>
              </Dragger>
              {returnedFile && (
                <Alert
                  type="success"
                  showIcon
                  message="回传成功"
                  description={`已上传：${returnedFile.original_name}，电脑端刷新“文件快传”列表即可下载。`}
                />
              )}
            </>
          )}
        </Space>
      </Card>
    </main>
  );
}

function RunDetail({ run, open, onClose, onRefresh, refreshing }) {
  const report = run?.report || {};
  const events = report.events || [];
  const checks = report.checks || [];
  const screenshots = report.screenshots || [];
  return (
    <Drawer title={run ? `执行详情 #${run.id}` : '执行详情'} width={720} open={open} onClose={onClose} extra={<Button icon={<ReloadOutlined />} onClick={onRefresh} loading={refreshing}>刷新</Button>}>
      {!run ? <Empty description="请选择一条执行记录" /> : (
        <Space direction="vertical" size={18} className="full-width">
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label="类型">{run.case_type}</Descriptions.Item>
            <Descriptions.Item label="用例 ID">{run.case_id}</Descriptions.Item>
            <Descriptions.Item label="状态"><StatusTag status={run.status} /></Descriptions.Item>
            <Descriptions.Item label="耗时">{formatDuration(run.duration_ms)}</Descriptions.Item>
            <Descriptions.Item label="创建时间">{formatTime(run.created_at)}</Descriptions.Item>
            <Descriptions.Item label="更新时间">{formatTime(run.updated_at)}</Descriptions.Item>
          </Descriptions>
          {run.logs && <Alert type="info" showIcon message={run.logs} />}
          {run.error && <Alert type="error" showIcon message={run.error} />}
          {report.latest_screenshot && (
            <Card title="当前页面截图" size="small">
              <img className="report-image" src={report.latest_screenshot} alt={`run-${run.id}-latest`} />
            </Card>
          )}
          {events.length > 0 && (
            <Card title="UI 步骤" size="small">
              <Table
                rowKey={(event) => `${event.step}-${event.action}`}
                size="small"
                pagination={false}
                dataSource={events}
                columns={[
                  { title: '步骤', dataIndex: 'step', width: 70 },
                  { title: '动作', dataIndex: 'action', width: 110 },
                  { title: '目标', dataIndex: 'target', ellipsis: true, render: (value) => value || '-' },
                  { title: '值', dataIndex: 'value', ellipsis: true, render: (value) => value || '-' },
                  { title: '耗时', dataIndex: 'elapsed_ms', width: 100, render: formatDuration },
                ]}
              />
            </Card>
          )}
          {checks.length > 0 && (
            <Card title="接口断言" size="small">
              <Table
                rowKey="name"
                size="small"
                pagination={false}
                dataSource={checks}
                columns={[
                  { title: '名称', dataIndex: 'name' },
                  { title: '结果', dataIndex: 'passed', render: (value) => value ? <Tag color="success">通过</Tag> : <Tag color="error">失败</Tag> },
                  { title: '期望', dataIndex: 'expected', render: (value) => String(value ?? '-') },
                  { title: '实际', dataIndex: 'actual', render: (value) => String(value ?? '-') },
                ]}
              />
            </Card>
          )}
          {report.response && (
            <Card title="接口响应" size="small">
              <pre className="json-report">{JSON.stringify(report.response, null, 2)}</pre>
            </Card>
          )}
          {screenshots.length > 0 && (
            <Card title="截图清单" size="small">
              <div className="thumb-grid">{screenshots.map((item) => <img key={`${item.step}-${item.title}`} src={item.image} alt={item.title} />)}</div>
            </Card>
          )}
        </Space>
      )}
    </Drawer>
  );
}

function RunsPanel({ runs, reload, refreshing, selectedRunId, onSelectRun }) {
  const selectedRun = runs.find((run) => run.id === selectedRunId) || null;
  const summary = {
    total: runs.length,
    running: runs.filter((run) => ['queued', 'running'].includes(run.status)).length,
    passed: runs.filter((run) => run.status === 'passed').length,
    failed: runs.filter((run) => run.status === 'failed').length,
  };
  return (
    <Space direction="vertical" size={16} className="full-width">
      <Row gutter={[16, 16]}>
        <Col xs={12} lg={6}><Card><Statistic title="最近任务" value={summary.total} prefix={<ClockCircleOutlined />} /></Card></Col>
        <Col xs={12} lg={6}><Card><Statistic title="运行中" value={summary.running} valueStyle={{ color: '#1677ff' }} /></Card></Col>
        <Col xs={12} lg={6}><Card><Statistic title="通过" value={summary.passed} valueStyle={{ color: '#16a34a' }} /></Card></Col>
        <Col xs={12} lg={6}><Card><Statistic title="失败" value={summary.failed} valueStyle={{ color: '#dc2626' }} /></Card></Col>
      </Row>
      <Card title="执行记录" extra={<Button icon={<ReloadOutlined />} loading={refreshing} onClick={reload}>刷新</Button>}>
        <Table
          rowKey="id"
          dataSource={runs}
          pagination={{ pageSize: 10 }}
          scroll={{ x: 1180 }}
          columns={[
            { title: 'ID', dataIndex: 'id', width: 80 },
            { title: '类型', dataIndex: 'case_type', width: 90, render: (value) => <Tag>{value}</Tag> },
            { title: '用例', dataIndex: 'case_id', width: 90 },
            { title: '状态', dataIndex: 'status', width: 110, render: (value) => <StatusTag status={value} /> },
            { title: '创建时间', dataIndex: 'created_at', render: formatTime },
            { title: '更新时间', dataIndex: 'updated_at', render: formatTime },
            { title: '耗时', dataIndex: 'duration_ms', width: 110, render: formatDuration },
            { title: '错误', dataIndex: 'error', ellipsis: true, render: (value) => value || '-' },
            { title: '操作', width: 100, render: (_, record) => <Button icon={<EyeOutlined />} onClick={() => onSelectRun(record.id)}>详情</Button> },
          ]}
        />
      </Card>
      <RunDetail run={selectedRun} open={Boolean(selectedRunId)} onClose={() => onSelectRun(null)} onRefresh={reload} refreshing={refreshing} />
    </Space>
  );
}

function LiveRunWindow({ token, runId }) {
  const client = useMemo(() => apiClient(token), [token]);
  const [run, setRun] = useState(null);
  const [error, setError] = useState('');

  async function loadRun() {
    try {
      const data = await client.get(`/runs/${runId}`);
      setRun(data);
      setError('');
    } catch (err) {
      setError(err.message || '读取执行状态失败');
    }
  }

  useEffect(() => {
    loadRun();
    const timer = window.setInterval(loadRun, 800);
    return () => window.clearInterval(timer);
  }, [runId, token]);

  const report = run?.report || {};
  const events = report.events || [];
  const current = report.current_step && report.total_steps ? `${report.current_step}/${report.total_steps}` : '-';
  const isRunning = run && ['queued', 'running'].includes(run.status);

  return (
    <main className="live-shell">
      <header className="live-header">
        <div>
          <h1>UI 自动化执行窗口</h1>
          <p>任务 #{runId} {run ? `· ${run.status}` : '· 正在连接'}</p>
        </div>
        <div className="live-stats">
          <div><span>当前步骤</span><strong>{current}</strong></div>
          <div><span>当前动作</span><strong>{report.current_action || '-'}</strong></div>
          <div><span>耗时</span><strong>{formatDuration(run?.duration_ms)}</strong></div>
        </div>
      </header>
      {error && <Alert type="error" showIcon message={error} />}
      <section className="live-stage">
        <div className="browser-chrome">
          <span></span><span></span><span></span>
          <strong>{events[events.length - 1]?.url || 'about:blank'}</strong>
        </div>
        <div className="browser-screen">
          {report.latest_screenshot ? (
            <img src={report.latest_screenshot} alt="UI 自动化当前页面" />
          ) : (
            <div className="live-empty">
              <ThunderboltOutlined />
              <strong>{isRunning ? '浏览器正在启动，等待第一张画面...' : '暂无页面画面'}</strong>
            </div>
          )}
          {isRunning && <div className="live-running">正在执行</div>}
        </div>
      </section>
      <section className="live-steps">
        <h2>执行过程</h2>
        <div className="step-strip">
          {events.length === 0 && <span className="hint">等待 worker 开始执行步骤...</span>}
          {events.map((event) => (
            <div className="step-pill" key={`${event.step}-${event.action}`}>
              <strong>{event.step}. {event.action}</strong>
              <span>{formatDuration(event.elapsed_ms)} · {event.title || event.url || '-'}</span>
            </div>
          ))}
        </div>
        {run?.error && <Alert className="live-error" type="error" showIcon message={run.error} />}
      </section>
    </main>
  );
}

function PlatformApp() {
  const params = new URLSearchParams(window.location.search);
  const initialRunId = Number(params.get('runId')) || null;
  const liveRunId = Number(params.get('liveRunId')) || null;
  const transferToken = params.get('transferToken');
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [tab, setTab] = useState(initialRunId ? 'runs' : 'projects');
  const [selectedRunId, setSelectedRunId] = useState(initialRunId);
  const [data, setData] = useState({ projects: [], apiCases: [], uiCases: [], runs: [] });
  const [refreshing, setRefreshing] = useState(false);
  const { message } = AntApp.useApp();
  const client = useMemo(() => apiClient(token), [token]);

  async function reload() {
    if (!token) return;
    setRefreshing(true);
    try {
      const [projects, apiCases, uiCases, runs] = await Promise.all([
        client.get('/projects'),
        client.get('/api-cases'),
        client.get('/ui-cases'),
        client.get('/runs'),
      ]);
      setData({ projects, apiCases, uiCases, runs });
    } catch (err) {
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
    if (!token || tab !== 'runs') return undefined;
    const selected = data.runs.find((run) => run.id === selectedRunId);
    if (!selected || !['queued', 'running'].includes(selected.status)) return undefined;
    const timer = window.setInterval(reload, 2000);
    return () => window.clearInterval(timer);
  }, [token, tab, selectedRunId, data.runs]);

  if (transferToken) return <PublicTransferPage token={transferToken} />;
  if (!token) return <Login onLogin={setToken} />;
  if (liveRunId) return <LiveRunWindow token={token} runId={liveRunId} />;

  const menuItems = [
    { key: 'projects', icon: <FolderOutlined />, label: '项目' },
    { key: 'api', icon: <ApiOutlined />, label: '接口测试' },
    { key: 'ui', icon: <BugOutlined />, label: 'UI 测试' },
    { key: 'files', icon: <CloudUploadOutlined />, label: '文件快传' },
    { key: 'runs', icon: <ClockCircleOutlined />, label: '执行记录' },
  ];
  const currentTitle = menuItems.find((item) => item.key === tab)?.label;

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
        <Button className="logout-button" icon={<LogoutOutlined />} onClick={() => { localStorage.removeItem('token'); setToken(''); }}>退出登录</Button>
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
          {tab === 'runs' && <RunsPanel runs={data.runs} reload={reload} refreshing={refreshing} selectedRunId={selectedRunId} onSelectRun={handleSelectRun} />}
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
