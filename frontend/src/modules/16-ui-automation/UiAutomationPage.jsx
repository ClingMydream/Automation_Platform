import React, { useEffect, useMemo, useState } from 'react';
import {
  Alert, Badge, Button, Card, Checkbox, Col, Drawer, Empty, Form, Input, Modal,
  Progress, Row, Select, Space, Spin, Tag, Timeline, Tooltip, Typography, message,
} from 'antd';
import {
  ArrowLeftOutlined, BranchesOutlined, CopyOutlined, DatabaseOutlined, DeleteOutlined, EditOutlined, ExperimentOutlined,
  FileAddOutlined, PlayCircleOutlined, ReloadOutlined, VideoCameraOutlined,
} from '@ant-design/icons';
import './ui-automation.css';
import './ui-automation-timeline.css';

const { Paragraph, Text, Title } = Typography;
const DEFAULT_BRANCH = 'dev-20260811-1.9.1';
const ACTIONS = [
  ['goto', '打开页面'], ['click', '点击'], ['fill', '输入'], ['select', '选择'],
  ['press', '键盘操作'], ['wait', '等待'], ['detect_visible', '检测元素是否出现'], ['assert_visible', '断言元素可见'],
  ['assert_text', '断言文本'], ['assert_url', '断言地址'], ['assert_count', '断言数量'],
  ['screenshot', '截图'], ['switch_account', '切换账号'],
];
const LOCATOR_TYPES = [
  ['testid', '测试 ID'], ['role', '角色 + 名称'], ['label', '表单标签'], ['placeholder', '占位文字'],
  ['text', '页面文本'], ['alt', '图片替代文字'], ['title', '标题属性'], ['id', '元素 ID'],
  ['css', 'CSS 选择器'], ['xpath', 'XPath'],
];
const STATUS = {
  queued: ['等待执行', 'default'], running: ['执行中', 'processing'], passed: ['通过', 'success'],
  failed: ['失败', 'error'], interrupted: ['已中断', 'warning'],
};

export function ArtifactViewer({ client, artifact }) {
  const [url, setUrl] = useState('');
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let objectUrl = '';
    setUrl(''); setError('');
    if (artifact?.kind === 'video' || artifact?.kind === 'screenshot') {
      client.download(artifact.url).then(({ blob }) => {
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      }).catch((reason) => { setUrl(''); setError(reason.message || '产物读取失败'); });
    }
    return () => { if (objectUrl) URL.revokeObjectURL(objectUrl); };
  }, [artifact?.id, retry]);
  if (!artifact) return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="执行后会在这里显示录屏和截图" />;
  if (error) return <Alert type="error" showIcon title="产物读取失败" description={<Space orientation="vertical"><span>{error}</span><Button size="small" onClick={() => setRetry((value) => value + 1)}>重新读取</Button></Space>} />;
  if (!url) return <Spin tip="正在读取鉴权产物" />;
  return artifact.kind === 'video'
    ? <video className="ui-auto-media" src={url} controls playsInline />
    : <img className="ui-auto-media" src={url} alt={artifact.name} />;
}

export function UiAutomationPage({ client, onClose, embedded = false }) {
  const [data, setData] = useState({ features: [], cases: [], requirements: [], runs: [] });
  const [branches, setBranches] = useState([]);
  const [dataSets, setDataSets] = useState([]);
  const [branch, setBranch] = useState(DEFAULT_BRANCH);
  const [viewport, setViewport] = useState('mobile');
  const [syncFirst, setSyncFirst] = useState(false);
  const [selectedCases, setSelectedCases] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState(null);
  const [selectedRun, setSelectedRun] = useState(null);
  const [evidenceCaseId, setEvidenceCaseId] = useState(null);
  const [selectedArtifactId, setSelectedArtifactId] = useState(null);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [runBusy, setRunBusy] = useState(false);
  const [runRequest, setRunRequest] = useState(null);
  const [credentialOpen, setCredentialOpen] = useState(false);
  const [caseOpen, setCaseOpen] = useState(false);
  const [requirementOpen, setRequirementOpen] = useState(false);
  const [dataSetOpen, setDataSetOpen] = useState(false);
  const [editingDataSet, setEditingDataSet] = useState(null);
  const [editingCase, setEditingCase] = useState(null);
  const [caseForm] = Form.useForm();
  const [credentialForm] = Form.useForm();
  const [requirementForm] = Form.useForm();
  const [dataSetForm] = Form.useForm();

  const load = async (quiet = false) => {
    if (!quiet) setLoading(true);
    try {
      const [overview, branchRows, savedDataSets] = await Promise.all([
        client.get('/v1/ui-automation/overview'), client.get('/v1/online-preview/branches'), client.get('/v1/ui-automation/data-sets'),
      ]);
      setData(overview); setBranches(branchRows); setDataSets(savedDataSets);
      if (!selectedRunId && overview.runs[0]) setSelectedRunId(overview.runs[0].id);
    } catch (error) { message.error(error.message); }
    finally { if (!quiet) setLoading(false); }
  };

  useEffect(() => { load(); }, []);
  useEffect(() => {
    if (!selectedRunId) { setSelectedRun(null); return undefined; }
    let active = true;
    const read = async () => {
      try { const row = await client.get(`/v1/ui-automation/runs/${selectedRunId}`); if (active) setSelectedRun(row); }
      catch (error) { if (active) message.error(error.message); }
    };
    read();
    const timer = window.setInterval(read, 3000);
    return () => { active = false; window.clearInterval(timer); };
  }, [selectedRunId]);

  const visibleCases = useMemo(() => data.cases.filter((item) => item.name.toLowerCase().includes(search.toLowerCase())), [data.cases, search]);
  const evidenceCases = (selectedRun?.case_ids || []).map((id) => data.cases.find((item) => item.id === id)).filter(Boolean);
  const caseArtifacts = (selectedRun?.artifacts || []).filter((item) => !evidenceCaseId || item.name.includes(`case-${evidenceCaseId}-`));
  const selectedArtifact = caseArtifacts.find((item) => item.id === selectedArtifactId)
    || [...caseArtifacts].reverse().find((item) => item.kind === (selectedRun?.status === 'running' ? 'screenshot' : 'video'))
    || [...caseArtifacts].reverse().find((item) => item.kind === 'screenshot');

  useEffect(() => {
    if (selectedRun?.case_ids?.length && !selectedRun.case_ids.includes(evidenceCaseId)) setEvidenceCaseId(selectedRun.case_ids[0]);
  }, [selectedRun?.id]);

  const waitForSync = async () => {
    await client.post('/v1/online-preview/sync', { branch });
    for (let index = 0; index < 90; index += 1) {
      await new Promise((resolve) => window.setTimeout(resolve, 3000));
      const status = await client.get('/v1/online-preview/status');
      if (!status.building && status.result === 'SUCCESS') return;
      if (!status.building && status.result && status.result !== 'SUCCESS') throw new Error(status.description || '预览同步失败');
    }
    throw new Error('等待预览同步超时');
  };

  const requestRun = (mode, directCaseIds = null) => {
    const caseIds = directCaseIds || selectedCases;
    if (mode === 'selected' && !caseIds.length) return message.warning('请先勾选要执行的用例');
    setRunRequest({ mode, case_ids: mode === 'selected' ? caseIds : [] });
    credentialForm.setFieldsValue({ data_set_id: dataSets.find((item) => item.is_default)?.id || dataSets[0]?.id }); setCredentialOpen(true);
  };

  const startRun = async () => {
    let executionWindow = null;
    try {
      executionWindow = window.open('/emote-ui-automation/run/waiting', 'cling-emote-live-execution', 'width=1220,height=900,resizable=yes,scrollbars=yes');
    } catch (_) { /* Browsers may block popups; the task itself can still run. */ }
    const credentials = await credentialForm.validateFields().catch((error) => { executionWindow?.close(); throw error; });
    setRunBusy(true);
    try {
      if (syncFirst) { message.loading({ content: '正在同步所选分支…', key: 'ui-sync', duration: 0 }); await waitForSync(); message.success({ content: '分支同步完成', key: 'ui-sync' }); }
      const run = await client.post('/v1/ui-automation/runs', {
        ...runRequest, branch, viewport, smoke_count: 10,
        data_set_id: credentials.data_set_id,
      });
      setSelectedRunId(run.id); setSelectedRun(run); setCredentialOpen(false);
      if (executionWindow) executionWindow.location.replace(`/emote-ui-automation/run/${run.id}`);
      message.success(`执行任务 #${run.id} 已进入队列`); await load(true);
    } catch (error) { executionWindow?.close(); message.error(error.message); }
    finally { setRunBusy(false); }
  };

  const openCase = (item) => {
    setEditingCase(item || null);
    caseForm.setFieldsValue(item || { feature_id: data.features[0]?.id, name: '', priority: 'P1', tags: ['regression'], enabled: false, preconditions: '', cleanup_note: '保留测试数据', steps: [{ action: 'goto', value: '/' }] });
    setCaseOpen(true);
  };

  const saveCase = async () => {
    try {
      const values = await caseForm.validateFields();
      values.tags = typeof values.tags === 'string' ? values.tags.split(',').map((x) => x.trim()).filter(Boolean) : values.tags;
      values.steps = (values.steps || []).map((step) => ({ ...step, index: step.match === 'nth' ? Number(step.index) : undefined }));
      if (editingCase) await client.put(`/v1/ui-automation/cases/${editingCase.id}`, values);
      else await client.post('/v1/ui-automation/cases', values);
      setCaseOpen(false); message.success('用例已保存'); await load(true);
    } catch (error) { if (error.message) message.error(error.message); }
  };

  const saveRequirement = async () => {
    try { await client.post('/v1/ui-automation/requirements', await requirementForm.validateFields()); setRequirementOpen(false); requirementForm.resetFields(); message.success('测试需求已保存为草稿'); await load(true); }
    catch (error) { if (error.message) message.error(error.message); }
  };

  const editDataSet = (item = null) => {
    setEditingDataSet(item);
    dataSetForm.setFieldsValue(item || { name: '', is_default: !dataSets.length, credentials: { account_a: {}, account_b: {}, registration: {} } });
    setDataSetOpen(true);
  };

  const saveDataSet = async () => {
    try {
      const values = await dataSetForm.validateFields();
      if (editingDataSet) await client.put(`/v1/ui-automation/data-sets/${editingDataSet.id}`, values);
      else await client.post('/v1/ui-automation/data-sets', values);
      setDataSetOpen(false); message.success('测试数据集已加密保存'); await load(true);
    } catch (error) { if (error.message) message.error(error.message); }
  };

  const clearExecutionData = () => Modal.confirm({
    title: '确认清空自动化执行数据？',
    content: '将永久删除全部历史执行记录、步骤日志、错误详情、截图、录屏和 Trace。测试用例与测试数据集会保留。',
    okText: '确认清空', cancelText: '取消', okButtonProps: { danger: true },
    onOk: async () => {
      const result = await client.delete('/v1/ui-automation/maintenance/execution-data');
      setSelectedRunId(null); setSelectedRun(null); setSelectedArtifactId(null);
      message.success(`已清空 ${result.runs} 次执行、${result.artifacts} 个产物`);
      await load(true);
    },
  });

  const download = async (artifact) => {
    try { const { blob, filename } = await client.download(artifact.url); const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = filename; a.click(); URL.revokeObjectURL(url); }
    catch (error) { message.error(error.message); }
  };

  return <main className={`ui-auto-page ${embedded ? 'ui-auto-page--embedded' : ''}`}>
    <header className="ui-auto-header">
      <div className="ui-auto-brand"><span>🎬</span><div><Text>cling · 测试中心</Text><Title level={3}>Emote UI 自动化</Title></div></div>
      <Space wrap>
        <Select showSearch value={branch} onChange={setBranch} options={branches.map((value) => ({ value, label: value }))} className="ui-auto-branch" suffixIcon={<BranchesOutlined />} />
        <Select value={viewport} onChange={setViewport} options={[{ value: 'mobile', label: '手机视口 390×844' }, { value: 'desktop', label: '桌面视口 1440×900' }]} />
        <Checkbox checked={syncFirst} onChange={(event) => setSyncFirst(event.target.checked)}>同步最新预览后执行</Checkbox>
        {!embedded && <Button icon={<ArrowLeftOutlined />} onClick={onClose}>返回私人空间</Button>}
      </Space>
    </header>
    <section className="ui-auto-actions">
      <div><b>可视化回归编排</b><span>选择用例 → 配置环境 → 脚本执行 → 按用例查看证据</span></div>
      <div className="ui-auto-action-buttons">
        <Button icon={<DatabaseOutlined />} onClick={() => editDataSet()}>测试数据集</Button>
        <Button danger icon={<DeleteOutlined />} onClick={clearExecutionData}>清空执行数据</Button>
        <Button icon={<FileAddOutlined />} onClick={() => setRequirementOpen(true)}>新增测试需求</Button>
        <Button icon={<PlayCircleOutlined />} onClick={() => requestRun('selected')}>执行已勾选</Button>
        <Button icon={<ExperimentOutlined />} onClick={() => requestRun('smoke')}>随机冒烟</Button>
        <Button type="primary" icon={<VideoCameraOutlined />} onClick={() => requestRun('regression')}>全部回归</Button>
      </div>
    </section>
    <div className="ui-auto-grid">
      <aside className="ui-auto-left">
        <div className="ui-auto-panel-title"><div><b>功能与用例</b><Text type="secondary">已覆盖 {data.features.length} 个功能</Text></div><Button type="text" icon={<ReloadOutlined />} onClick={() => load()} /></div>
        <Input.Search allowClear placeholder="搜索用例" value={search} onChange={(event) => setSearch(event.target.value)} />
        <Spin spinning={loading}>
          {data.features.map((feature) => {
            const rows = visibleCases.filter((item) => item.feature_id === feature.id);
            return <section className="ui-auto-feature" key={feature.id}>
              <div className="ui-auto-feature-head"><span>{feature.name}</span><Badge count={rows.length} showZero color="#6d5dfc" /></div>
              {rows.map((item) => <div className={`ui-auto-case ${selectedCases.includes(item.id) ? 'selected' : ''}`} key={item.id}>
                <Checkbox checked={selectedCases.includes(item.id)} onChange={(event) => setSelectedCases((old) => event.target.checked ? [...old, item.id] : old.filter((id) => id !== item.id))} />
                <button type="button" onClick={() => openCase(item)}><span>{item.name}</span><small><Tag color={item.enabled ? 'green' : 'default'}>{item.enabled ? '已启用' : '草稿'}</Tag>{item.steps.length} 步 · {item.priority}</small></button>
                <Tooltip title="立即执行此用例"><Button type="text" size="small" icon={<PlayCircleOutlined />} disabled={!item.enabled} onClick={() => requestRun('selected', [item.id])} /></Tooltip>
                <Tooltip title="复制用例"><Button type="text" size="small" icon={<CopyOutlined />} onClick={async () => { await client.post(`/v1/ui-automation/cases/${item.id}/duplicate`, {}); await load(true); }} /></Tooltip>
              </div>)}
            </section>;
          })}
        </Spin>
        <Button block type="dashed" icon={<FileAddOutlined />} onClick={() => openCase(null)}>新建结构化用例</Button>
      </aside>
      <section className="ui-auto-right">
        <Card className="ui-auto-run-card" title={selectedRun ? `执行 #${selectedRun.id}` : '执行过程'} extra={selectedRun && <Badge status={(STATUS[selectedRun.status] || STATUS.queued)[1]} text={(STATUS[selectedRun.status] || STATUS.queued)[0]} />}>
          {!selectedRun ? <Empty description="选择上方执行方式开始回归" /> : <>
            <div className="ui-auto-evidence-tabs">
              <Text type="secondary">用例证据</Text>
              {evidenceCases.map((item) => <Button size="small" type={evidenceCaseId === item.id ? 'primary' : 'default'} key={item.id} onClick={() => { setEvidenceCaseId(item.id); setSelectedArtifactId(null); }}>{item.name}</Button>)}
            </div>
            <Row gutter={[16, 16]}>
              <Col xs={24} lg={15}>
                <div className="ui-auto-screen"><ArtifactViewer client={client} artifact={selectedArtifact} /></div>
                <div className="ui-auto-artifact-strip">{caseArtifacts.filter((item) => item.kind !== 'trace').map((item) => <button type="button" className={item.id === selectedArtifact?.id ? 'active' : ''} key={item.id} onClick={() => setSelectedArtifactId(item.id)}>{item.kind === 'video' ? '🎥 录像' : '🖼️ 截图'}<small>{item.name.replace(`case-${evidenceCaseId}-`, '')}</small></button>)}</div>
              </Col>
              <Col xs={24} lg={9}>
                <Space orientation="vertical" size={14} style={{ width: '100%' }}>
                  <div><Text type="secondary">当前步骤</Text><Paragraph strong>{selectedRun.current_step || '等待 Runner 接收任务'}</Paragraph></div>
                  <Progress percent={selectedRun.progress || 0} status={selectedRun.status === 'failed' ? 'exception' : selectedRun.status === 'passed' ? 'success' : 'active'} />
                  <div className="ui-auto-meta"><span>分支 <b>{selectedRun.branch}</b></span><span>提交 <code>{selectedRun.commit_sha?.slice(0, 10) || '-'}</code></span><span>随机种子 <code>{selectedRun.random_seed || '-'}</code></span><span>视口 <b>{selectedRun.viewport === 'mobile' ? '390 × 844' : '1440 × 900'}</b></span></div>
                  {selectedRun.result_summary?.failure ? <Alert type="error" showIcon title={`${selectedRun.result_summary.failure.case_name} · 第 ${selectedRun.result_summary.failure.step_index} 步失败`} description={<div className="ui-auto-failure"><b>{selectedRun.result_summary.failure.reason}</b><span>动作：{selectedRun.result_summary.failure.action}{selectedRun.result_summary.failure.locator ? ` · 元素：${selectedRun.result_summary.failure.locator}` : ''}</span><span>建议：{selectedRun.result_summary.failure.suggestion}</span><details><summary>查看技术详情</summary><pre>{selectedRun.result_summary.failure.technical_detail}</pre></details></div>} /> : selectedRun.error_message && <Alert type="error" showIcon title="执行失败" description={selectedRun.error_message} />}
                  <Space wrap>{caseArtifacts.map((item) => <Button size="small" key={item.id} onClick={() => download(item)}>{item.kind === 'trace' ? '下载本用例 Trace' : item.kind === 'video' ? '下载本用例录像' : '下载步骤截图'}</Button>)}</Space>
                  {!!selectedRun.result_summary?.timeline?.length && <Timeline className="ui-auto-timeline" items={selectedRun.result_summary.timeline.filter((step) => !evidenceCaseId || step.case_id === evidenceCaseId).map((step) => ({ color: step.status === 'failed' ? 'red' : 'green', children: <span>{step.name}<small>{step.duration_ms} ms</small></span> }))} />}
                </Space>
              </Col>
            </Row>
          </>}
        </Card>
        <Card title="历史执行" size="small">
          <div className="ui-auto-history">{data.runs.map((run) => <button type="button" key={run.id} className={run.id === selectedRunId ? 'active' : ''} onClick={() => setSelectedRunId(run.id)}><b>#{run.id} · {(STATUS[run.status] || STATUS.queued)[0]}</b><span>{run.mode} · {run.branch}</span><small>{run.created_at ? new Date(run.created_at).toLocaleString('zh-CN') : ''}</small></button>)}</div>
        </Card>
      </section>
    </div>

    <Modal title="选择测试数据" open={credentialOpen} onCancel={() => setCredentialOpen(false)} onOk={startRun} okText="确认并开始执行" confirmLoading={runBusy} width={520} destroyOnHidden>
      <Alert type="info" showIcon title="复用已保存的测试数据" description="账号密码在服务器加密保存，执行时临时解密给 Runner，运行记录、截图说明和日志不会保存明文密码。" />
      <Form form={credentialForm} layout="vertical" className="ui-auto-credentials"><Form.Item name="data_set_id" label="测试数据集" rules={[{ required: true, message: '请先选择或新建测试数据集' }]}><Select placeholder="选择账号数据" options={dataSets.map((item) => ({ value: item.id, label: `${item.name}${item.is_default ? '（默认）' : ''}` }))} /></Form.Item><Button icon={<DatabaseOutlined />} onClick={() => editDataSet()}>新建测试数据集</Button></Form>
    </Modal>

    <Modal title={editingDataSet ? '编辑测试数据集' : '新建测试数据集'} open={dataSetOpen} onCancel={() => setDataSetOpen(false)} onOk={saveDataSet} okText="加密保存" width={760} destroyOnHidden>
      <Alert type="warning" showIcon title="敏感数据安全" description="密码与验证码使用服务器密钥加密入库；列表接口只返回 ******，不会返回密文或明文。" />
      <Form form={dataSetForm} layout="vertical" style={{ marginTop: 16 }}><Row gutter={16}><Col span={18}><Form.Item name="name" label="数据集名称" rules={[{ required: true }]}><Input placeholder="例如：Emote 测试环境账号" /></Form.Item></Col><Col span={6}><Form.Item name="is_default" label="默认使用" valuePropName="checked"><Checkbox>设为默认</Checkbox></Form.Item></Col></Row><Row gutter={16}><Col span={12}><Card size="small" title="账号 A"><Form.Item name={['credentials', 'account_a', 'username']} label="手机号/账号"><Input /></Form.Item><Form.Item name={['credentials', 'account_a', 'password']} label="密码"><Input.Password autoComplete="new-password" /></Form.Item></Card></Col><Col span={12}><Card size="small" title="账号 B（好友/聊天）"><Form.Item name={['credentials', 'account_b', 'username']} label="手机号/账号"><Input /></Form.Item><Form.Item name={['credentials', 'account_b', 'password']} label="密码"><Input.Password autoComplete="new-password" /></Form.Item></Card></Col></Row><Row gutter={16} style={{ marginTop: 12 }}><Col span={12}><Form.Item name={['credentials', 'registration', 'phone']} label="注册手机号"><Input /></Form.Item></Col><Col span={12}><Form.Item name={['credentials', 'registration', 'code']} label="注册验证码"><Input.Password /></Form.Item></Col></Row></Form>
      {!!dataSets.length && <div className="ui-auto-datasets"><Text type="secondary">已保存数据集</Text>{dataSets.map((item) => <Space key={item.id}><Button size="small" onClick={() => editDataSet(item)}>{item.name}{item.is_default ? '（默认）' : ''}</Button><Button danger size="small" icon={<DeleteOutlined />} onClick={async () => { await client.delete(`/v1/ui-automation/data-sets/${item.id}`); await load(true); }} /></Space>)}</div>}
    </Modal>

    <Modal title={editingCase ? '编辑测试用例' : '新建测试用例'} open={caseOpen} onCancel={() => setCaseOpen(false)} onOk={saveCase} okText="保存" width={980} destroyOnHidden>
      <Form form={caseForm} layout="vertical">
        <Row gutter={12}><Col span={10}><Form.Item name="name" label="用例名称" rules={[{ required: true }]}><Input /></Form.Item></Col><Col span={6}><Form.Item name="feature_id" label="所属功能" rules={[{ required: true }]}><Select options={data.features.map((x) => ({ value: x.id, label: x.name }))} /></Form.Item></Col><Col span={4}><Form.Item name="priority" label="优先级"><Select options={['P0', 'P1', 'P2'].map((x) => ({ value: x }))} /></Form.Item></Col><Col span={4}><Form.Item name="enabled" label="进入回归" valuePropName="checked"><Checkbox>确认并启用</Checkbox></Form.Item></Col></Row>
        <Form.Item name="tags" label="标签（英文逗号分隔）" getValueProps={(value) => ({ value: Array.isArray(value) ? value.join(',') : value })}><Input placeholder="smoke,regression" /></Form.Item>
        <Row gutter={12}><Col span={12}><Form.Item name="preconditions" label="前置条件"><Input.TextArea rows={2} /></Form.Item></Col><Col span={12}><Form.Item name="cleanup_note" label="清理说明"><Input.TextArea rows={2} /></Form.Item></Col></Row>
        <Form.List name="steps">{(fields, { add, remove, move }) => <div className="ui-auto-steps">
          <div className="ui-auto-step-title"><b>可视化步骤</b><Button size="small" onClick={() => add({ action: 'click', locator_type: 'testid' })}>添加步骤</Button></div>
          {fields.map((field, index) => <div className="ui-auto-step" key={field.key}><span>{index + 1}</span><Form.Item name={[field.name, 'action']} rules={[{ required: true }]}><Select options={ACTIONS.map(([value, label]) => ({ value, label }))} /></Form.Item><Form.Item name={[field.name, 'locator_type']}><Select placeholder="定位方式" options={LOCATOR_TYPES.map(([value, label]) => ({ value, label }))} /></Form.Item><Form.Item name={[field.name, 'role']}><Select allowClear placeholder="角色（role 时）" options={['button', 'heading', 'link', 'textbox', 'checkbox', 'radio', 'tab', 'dialog', 'listitem', 'img'].map((value) => ({ value, label: value }))} /></Form.Item><Form.Item name={[field.name, 'locator']}><Input placeholder="元素名称 / 选择器" /></Form.Item><Form.Item name={[field.name, 'value']}><Input placeholder="输入值 / 页面地址" /></Form.Item><Form.Item name={[field.name, 'match']}><Select allowClear placeholder="重复匹配" options={[{ value: 'first', label: '第一个' }, { value: 'last', label: '最后一个' }, { value: 'nth', label: '指定序号' }]} /></Form.Item><Form.Item name={[field.name, 'index']}><Input type="number" min={0} placeholder="序号(从0开始)" /></Form.Item><Form.Item name={[field.name, 'exact']} valuePropName="checked"><Checkbox>精确匹配</Checkbox></Form.Item><Space><Button size="small" disabled={index === 0} onClick={() => move(index, index - 1)}>↑</Button><Button size="small" disabled={index === fields.length - 1} onClick={() => move(index, index + 1)}>↓</Button><Button danger size="small" onClick={() => remove(field.name)}>删</Button></Space></div>)}
        </div>}</Form.List>
      </Form>
    </Modal>

    <Drawer title="新增自然语言测试需求" open={requirementOpen} onClose={() => setRequirementOpen(false)} width={520} extra={<Button type="primary" onClick={saveRequirement}>保存草稿</Button>}>
      <Alert type="warning" showIcon title="首版不会自动生成脚本" description="先记录你想测什么，再进入可视化步骤编辑器补充动作和断言，确认启用后才会加入回归。" />
      <Form form={requirementForm} layout="vertical" style={{ marginTop: 20 }}><Form.Item name="feature_id" label="所属功能"><Select allowClear options={data.features.map((x) => ({ value: x.id, label: x.name }))} /></Form.Item><Form.Item name="content" label="请用自然语言描述测试需求" rules={[{ required: true, min: 2 }]}><Input.TextArea rows={10} placeholder="例如：使用账号 A 登录，进入发帖页发布一条带 [AUTO] 标记的文字动态，并检查首页能看到它。" /></Form.Item></Form>
      {data.requirements.length > 0 && <><Title level={5}>最近草稿</Title><Timeline items={data.requirements.slice(0, 8).map((x) => ({ children: x.content }))} /></>}
    </Drawer>
  </main>;
}
