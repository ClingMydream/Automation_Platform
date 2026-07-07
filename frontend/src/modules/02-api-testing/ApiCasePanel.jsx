// File purpose: API testing page. Edit API cases, reuse environments, explain JSON fields, and start API runs.
// How to change: edit visual layout here; keep payload shaping and backend calls in apiCaseFeature.js.

import React, { useEffect, useMemo, useState } from 'react';
import { App as AntApp, Button, Card, Col, Form, Input, Row, Select, Space, Table, Tag, Tooltip } from 'antd';
import { DeleteOutlined, EditOutlined, PlayCircleOutlined, PlusOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { API_JSON_EXAMPLE } from '../../shared/constants';
import { JsonHelpCard } from '../../shared/JsonHelpCard.jsx';
import { ApiDebugDrawer } from './ApiDebugDrawer.jsx';
import {
  buildApiCaseFormValues,
  createApiCaseDebugRun,
  createApiCaseRun,
  deleteApiCase,
  getApiCaseDebugRun,
  saveApiCase,
} from './apiCaseFeature.js';

const { TextArea } = Input;

// API testing page: renders the case form, environment selector, case table, and run action.
export function ApiCasePanel({ client, projects, environments = [], apiCases, reload, onRunCreated }) {
  // State block: values here control edit mode, selected project, and save/run loading.
  const [form] = Form.useForm();
  const [editingId, setEditingId] = useState(null);
  const [selectedProjectId, setSelectedProjectId] = useState(null);
  const [saving, setSaving] = useState(false);
  const [debugOpen, setDebugOpen] = useState(false);
  const [debugRun, setDebugRun] = useState(null);
  const [debugLoading, setDebugLoading] = useState(false);
  const { message, modal } = AntApp.useApp();

  // Build quick lookup maps so table renderers stay simple and cheap.
  const projectNameById = useMemo(() => new Map(projects.map((item) => [item.id, item.name])), [projects]);
  const environmentById = useMemo(() => new Map(environments.map((item) => [item.id, item])), [environments]);
  const availableEnvironments = environments.filter((item) => !selectedProjectId || item.project_id === selectedProjectId);

  // Poll the active debug run until the worker finishes it.
  useEffect(() => {
    if (!debugOpen || !debugRun || !['queued', 'running'].includes(debugRun.status)) return undefined;
    const timer = window.setInterval(() => refreshDebugRun(debugRun.id, false), 1600);
    return () => window.clearInterval(timer);
  }, [debugOpen, debugRun?.id, debugRun?.status]);

  // Reset edit state and restore default form values.
  function resetForm() {
    setEditingId(null);
    setSelectedProjectId(null);
    form.resetFields();
    form.setFieldsValue({ method: 'GET', headers: '{}', assert_status: 200 });
  }

  // Fill the form with an existing record so the user can edit it.
  function startEdit(item) {
    setEditingId(item.id);
    setSelectedProjectId(item.project_id);
    form.setFieldsValue(buildApiCaseFormValues(item));
  }

  // Keep environment options scoped to the selected project.
  function handleProjectChange(projectId) {
    setSelectedProjectId(projectId);
    form.setFieldValue('environment_id', undefined);
  }

  // Submit the current form and refresh the list after saving.
  async function submit(values) {
    setSaving(true);
    try {
      const result = await saveApiCase(client, editingId, values);
      message.success(result === 'updated' ? '接口用例已更新' : '接口用例已创建');
      resetForm();
      await reload();
    } catch (err) {
      message.error(err.message);
    } finally {
      setSaving(false);
    }
  }

  // Confirm deletion, call the delete API, and refresh the list.
  function remove(item) {
    modal.confirm({
      title: `删除接口用例「${item.name}」？`,
      content: '对应执行记录也会一起删除。',
      okText: '删除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: async () => {
        await deleteApiCase(client, item.id);
        if (editingId === item.id) resetForm();
        message.success('接口用例已删除');
        await reload();
      },
    });
  }

  // Create an execution task for the selected test case.
  async function runCase(record) {
    try {
      const run = await createApiCaseRun(client, record.id);
      message.success(`已创建接口执行任务 #${run.id}`);
      await reload();
      onRunCreated(run, 'api', false);
    } catch (err) {
      message.error(err.message);
    }
  }

  // Refresh one debug run; silent refresh is used by polling so the drawer does not flicker.
  async function refreshDebugRun(runId = debugRun?.id, showLoading = true) {
    if (!runId) return;
    if (showLoading) setDebugLoading(true);
    try {
      const nextRun = await getApiCaseDebugRun(client, runId);
      setDebugRun(nextRun);
    } catch (err) {
      message.error(err.message);
    } finally {
      if (showLoading) setDebugLoading(false);
    }
  }

  // Start a debug run and keep the user on the API testing page.
  async function debugCase(record) {
    setDebugOpen(true);
    setDebugLoading(true);
    try {
      const run = await createApiCaseDebugRun(client, record.id);
      setDebugRun(run);
      message.success(`已创建接口调试任务 #${run.id}`);
      await reload();
      window.setTimeout(() => refreshDebugRun(run.id, false), 800);
    } catch (err) {
      message.error(err.message);
    } finally {
      setDebugLoading(false);
    }
  }

  // Render block: JSX below describes what the user sees on this page.
  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={10}>
        <Space direction="vertical" size={16} className="full-width">
          <JsonHelpCard
            title="接口 JSON 使用说明"
            tips={[
              '选择环境后，URL 可以只填相对路径，例如 /api/users；不选环境时必须填写完整公网 URL。',
              '请求头 JSON 必须是对象格式，最简单可以填 {}。',
              '请求头、请求体和 URL 支持 {{变量名}}，会从环境变量 JSON 中取值替换。',
              'JSON 路径用于检查返回 JSON 的字段，格式类似 $.data.name 或 $.items.0.id。',
              '响应包含文本用于检查返回内容里有没有某段文字。',
            ]}
            example={API_JSON_EXAMPLE}
          />
          <Card title={editingId ? '修改接口用例' : '接口用例'} extra={editingId && <Button onClick={resetForm}>取消编辑</Button>}>
            <Form form={form} layout="vertical" onFinish={submit} initialValues={{ method: 'GET', headers: '{}', assert_status: 200 }}>
              <Form.Item label="所属项目" name="project_id" rules={[{ required: true, message: '请选择项目' }]}>
                <Select
                  placeholder="选择项目"
                  options={projects.map((project) => ({ value: project.id, label: project.name }))}
                  onChange={handleProjectChange}
                />
              </Form.Item>
              <Form.Item label="测试环境" name="environment_id">
                <Select
                  allowClear
                  placeholder="可选；选择后 URL 可填写 /path"
                  options={availableEnvironments.map((item) => ({ value: item.id, label: `${item.name} - ${item.base_url}` }))}
                />
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
              <Form.Item label="URL 或路径" name="url" rules={[{ required: true, message: '请输入 URL 或 /path' }]}>
                <Input placeholder="例如：https://example.com/api/users 或 /api/users" />
              </Form.Item>
              <Form.Item label="请求头 JSON" name="headers">
                <TextArea rows={4} className="code-input" />
              </Form.Item>
              <Form.Item label="请求体" name="body">
                <TextArea rows={4} className="code-input" placeholder='例如：{"name":"{{username}}"}' />
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
              <Button type="primary" htmlType="submit" loading={saving} icon={<PlusOutlined />}>
                {editingId ? '更新接口用例' : '保存接口用例'}
              </Button>
            </Form>
          </Card>
        </Space>
      </Col>
      <Col xs={24} xl={14}>
        <Card title="接口用例列表">
          <Table
            rowKey="id"
            dataSource={apiCases}
            pagination={{ pageSize: 8 }}
            scroll={{ x: 1120 }}
            columns={[
              { title: 'ID', dataIndex: 'id', width: 70 },
              { title: '名称', dataIndex: 'name', width: 180 },
              { title: '项目', dataIndex: 'project_id', width: 130, render: (value) => projectNameById.get(value) || value },
              { title: '环境', dataIndex: 'environment_id', width: 160, render: (value) => value ? environmentById.get(value)?.name || value : <Tag>完整 URL</Tag> },
              { title: '方法', dataIndex: 'method', width: 90, render: (value) => <Tag color="blue">{value}</Tag> },
              { title: 'URL / 路径', dataIndex: 'url', ellipsis: true },
              {
                title: '操作',
                width: 180,
                fixed: 'right',
                render: (_, record) => (
                  <Space className="table-actions" size={6} wrap>
                    <Tooltip title="调试接口">
                      <Button aria-label="调试接口" size="small" icon={<ThunderboltOutlined />} onClick={() => debugCase(record)} />
                    </Tooltip>
                    <Tooltip title="执行用例">
                      <Button aria-label="执行用例" size="small" type="primary" icon={<PlayCircleOutlined />} onClick={() => runCase(record)} />
                    </Tooltip>
                    <Tooltip title="修改用例">
                      <Button aria-label="修改用例" size="small" icon={<EditOutlined />} onClick={() => startEdit(record)} />
                    </Tooltip>
                    <Tooltip title="删除用例">
                      <Button aria-label="删除用例" size="small" danger icon={<DeleteOutlined />} onClick={() => remove(record)} />
                    </Tooltip>
                  </Space>
                ),
              },
            ]}
          />
        </Card>
      </Col>
      <ApiDebugDrawer
        run={debugRun}
        open={debugOpen}
        loading={debugLoading}
        onClose={() => setDebugOpen(false)}
        onRefresh={() => refreshDebugRun()}
      />
    </Row>
  );
}

// API testing module: this file only owns the interface-test page UI.
