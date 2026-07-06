// File purpose: Test capability page. Maintain API scenarios, mock rules, performance scenarios, and runners.

import React, { useEffect, useMemo, useState } from 'react';
import { App as AntApp, Button, Card, Col, Form, Input, InputNumber, Row, Select, Space, Switch, Table, Tabs, Tag } from 'antd';
import { DeleteOutlined, EditOutlined, HeartOutlined, PlusOutlined } from '@ant-design/icons';
import { CAPABILITY_TABS, deleteCapability, formValuesFor, loadCapabilities, runnerHeartbeat, saveCapability } from './capabilityFeature.js';

const { TextArea } = Input;

export function TestCapabilityPanel({ client, projects }) {
  const [form] = Form.useForm();
  const [activeTab, setActiveTab] = useState('apiScenarios');
  const [items, setItems] = useState({ apiScenarios: [], mockRules: [], performanceScenarios: [], runners: [] });
  const [editingId, setEditingId] = useState(null);
  const [loading, setLoading] = useState(false);
  const { message, modal } = AntApp.useApp();
  const projectOptions = useMemo(() => projects.map((item) => ({ value: item.id, label: item.name })), [projects]);

  async function reload() {
    setLoading(true);
    try {
      setItems(await loadCapabilities(client));
    } catch (err) {
      message.error(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { reload(); }, []);

  function resetForm() {
    setEditingId(null);
    form.resetFields();
    form.setFieldsValue(defaultValues(activeTab));
  }

  function switchTab(key) {
    setActiveTab(key);
    setEditingId(null);
    form.resetFields();
    setTimeout(() => form.setFieldsValue(defaultValues(key)), 0);
  }

  function startEdit(record) {
    setEditingId(record.id);
    form.setFieldsValue({ ...defaultValues(activeTab), ...formValuesFor(activeTab, record) });
  }

  async function submit(values) {
    try {
      const result = await saveCapability(client, activeTab, editingId, values);
      message.success(result === 'updated' ? '测试能力已更新' : '测试能力已创建');
      resetForm();
      await reload();
    } catch (err) {
      message.error(err.message);
    }
  }

  function remove(record) {
    modal.confirm({
      title: `删除「${record.name || record.code}」？`,
      okText: '删除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: async () => {
        await deleteCapability(client, activeTab, record.id);
        message.success('已删除');
        await reload();
      },
    });
  }

  async function heartbeat(record) {
    try {
      await runnerHeartbeat(client, record.id);
      message.success('Runner 心跳已更新');
      await reload();
    } catch (err) {
      message.error(err.message);
    }
  }

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={9}>
        <Card title={editingId ? '修改测试能力' : '新建测试能力'} extra={editingId && <Button onClick={resetForm}>取消编辑</Button>}>
          <Tabs activeKey={activeTab} items={CAPABILITY_TABS} onChange={switchTab} />
          <Form form={form} layout="vertical" initialValues={defaultValues(activeTab)} onFinish={submit}>
            {renderForm(activeTab, projectOptions)}
            <Button type="primary" htmlType="submit" icon={<PlusOutlined />}>{editingId ? '更新' : '保存'}</Button>
          </Form>
        </Card>
      </Col>
      <Col xs={24} xl={15}>
        <Card title={CAPABILITY_TABS.find((tab) => tab.key === activeTab)?.label}>
          <Table
            rowKey="id"
            loading={loading}
            dataSource={items[activeTab]}
            pagination={{ pageSize: 8 }}
            scroll={{ x: 900 }}
            columns={[
              { title: '编号/路径', dataIndex: activeTab === 'mockRules' ? 'path' : 'code', width: 170 },
              { title: '名称', dataIndex: 'name', width: 180 },
              { title: '类型', dataIndex: activeTab === 'runners' ? 'runner_type' : 'method', width: 100, render: (value) => value || '-' },
              { title: '状态', dataIndex: activeTab === 'runners' ? 'status' : 'is_active', width: 100, render: (value) => typeof value === 'boolean' ? <Tag color={value ? 'green' : 'default'}>{value ? '启用' : '停用'}</Tag> : <Tag>{value}</Tag> },
              {
                title: '操作',
                width: activeTab === 'runners' ? 240 : 170,
                render: (_, record) => (
                  <Space className="table-actions" size={6} wrap>
                    {activeTab === 'runners' && <Button icon={<HeartOutlined />} onClick={() => heartbeat(record)}>心跳</Button>}
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

function defaultValues(type) {
  if (type === 'apiScenarios') return { variablesText: '{}', apiCaseIdsText: '[]', assertionsText: '[]', is_active: true };
  if (type === 'mockRules') return { method: 'GET', status_code: 200, responseHeadersText: '{}', response_body: '{"message":"mock ok"}', delay_ms: 0, is_active: true };
  if (type === 'performanceScenarios') return { method: 'GET', headersText: '{}', concurrency: 10, duration_seconds: 60, ramp_up_seconds: 10, tags: [], is_active: true };
  return { runner_type: 'platform', status: 'offline', capabilities: [], is_active: true };
}

function baseFields(projectOptions, withCode = true) {
  return (
    <>
      {withCode && <Form.Item label="编号" name="code" rules={[{ required: true, message: '请输入编号' }]}><Input /></Form.Item>}
      <Form.Item label="名称" name="name" rules={[{ required: true, message: '请输入名称' }]}><Input /></Form.Item>
      <Form.Item label="所属项目" name="project_id"><Select allowClear options={projectOptions} placeholder="可选" /></Form.Item>
    </>
  );
}

function renderForm(type, projectOptions) {
  if (type === 'apiScenarios') {
    return <>{baseFields(projectOptions)}<Form.Item label="变量 JSON" name="variablesText"><TextArea rows={3} /></Form.Item><Form.Item label="接口用例 ID 数组" name="apiCaseIdsText"><TextArea rows={3} /></Form.Item><Form.Item label="场景断言 JSON 数组" name="assertionsText"><TextArea rows={3} /></Form.Item><Form.Item label="前置脚本说明" name="pre_script"><TextArea rows={2} /></Form.Item><Form.Item label="后置脚本说明" name="post_script"><TextArea rows={2} /></Form.Item><Form.Item label="启用状态" name="is_active" valuePropName="checked"><Switch checkedChildren="启用" unCheckedChildren="停用" /></Form.Item></>;
  }
  if (type === 'mockRules') {
    return <>{baseFields(projectOptions, false)}<Form.Item label="方法" name="method"><Select options={['GET', 'POST', 'PUT', 'PATCH', 'DELETE'].map((value) => ({ value, label: value }))} /></Form.Item><Form.Item label="路径" name="path" rules={[{ required: true, message: '请输入路径' }]}><Input placeholder="/api/demo" /></Form.Item><Form.Item label="状态码" name="status_code"><InputNumber min={100} max={599} style={{ width: '100%' }} /></Form.Item><Form.Item label="响应头 JSON" name="responseHeadersText"><TextArea rows={3} /></Form.Item><Form.Item label="响应体" name="response_body"><TextArea rows={4} /></Form.Item><Form.Item label="延迟 ms" name="delay_ms"><InputNumber min={0} max={30000} style={{ width: '100%' }} /></Form.Item><Form.Item label="启用状态" name="is_active" valuePropName="checked"><Switch checkedChildren="启用" unCheckedChildren="停用" /></Form.Item></>;
  }
  if (type === 'performanceScenarios') {
    return <>{baseFields(projectOptions)}<Form.Item label="目标 URL" name="target_url" rules={[{ required: true, message: '请输入公网 URL' }]}><Input placeholder="https://example.com" /></Form.Item><Form.Item label="方法" name="method"><Select options={['GET', 'POST', 'PUT', 'PATCH', 'DELETE'].map((value) => ({ value, label: value }))} /></Form.Item><Form.Item label="请求头 JSON" name="headersText"><TextArea rows={3} /></Form.Item><Form.Item label="并发数" name="concurrency"><InputNumber min={1} max={10000} style={{ width: '100%' }} /></Form.Item><Form.Item label="持续秒数" name="duration_seconds"><InputNumber min={1} style={{ width: '100%' }} /></Form.Item><Form.Item label="升压秒数" name="ramp_up_seconds"><InputNumber min={0} style={{ width: '100%' }} /></Form.Item><Form.Item label="P95 阈值 ms" name="threshold_p95_ms"><InputNumber min={1} style={{ width: '100%' }} /></Form.Item><Form.Item label="错误率阈值 %" name="threshold_error_rate"><InputNumber min={0} max={100} style={{ width: '100%' }} /></Form.Item><Form.Item label="标签" name="tags"><Select mode="tags" /></Form.Item><Form.Item label="启用状态" name="is_active" valuePropName="checked"><Switch checkedChildren="启用" unCheckedChildren="停用" /></Form.Item></>;
  }
  return <>{baseFields([], true)}<Form.Item label="Runner 类型" name="runner_type"><Input placeholder="platform / pytest / playwright / jmeter" /></Form.Item><Form.Item label="状态" name="status"><Select options={['offline', 'online', 'busy', 'disabled'].map((value) => ({ value, label: value }))} /></Form.Item><Form.Item label="回调 URL" name="base_url"><Input placeholder="可选公网 URL" /></Form.Item><Form.Item label="能力" name="capabilities"><Select mode="tags" placeholder="api、ui、performance" /></Form.Item><Form.Item label="启用状态" name="is_active" valuePropName="checked"><Switch checkedChildren="启用" unCheckedChildren="停用" /></Form.Item></>;
}
