// File purpose: Project and environment page. Manage projects, environment configs, and environment health checks.
// How to change: edit UI layout here; keep API payload conversion in projectFeature.js.

import React, { useState } from 'react';
import { App as AntApp, Button, Card, Col, Form, Input, Row, Select, Space, Table, Tag } from 'antd';
import { ApiOutlined, DeleteOutlined, EditOutlined, PlusOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { formatDuration } from '../../shared/formatters.js';
import {
  buildEnvironmentFormValues,
  buildProjectFormValues,
  checkEnvironmentHealth,
  deleteEnvironment,
  deleteProject,
  saveEnvironment,
  saveProject,
} from './projectFeature.js';

const { TextArea } = Input;

// Project page: owns project CRUD, environment CRUD, and environment availability checks.
export function ProjectPanel({ client, projects, environments = [], reload }) {
  // State block: form instances and operation flags keep project and environment edits independent.
  const [projectForm] = Form.useForm();
  const [environmentForm] = Form.useForm();
  const [editingProjectId, setEditingProjectId] = useState(null);
  const [editingEnvironmentId, setEditingEnvironmentId] = useState(null);
  const [savingProject, setSavingProject] = useState(false);
  const [savingEnvironment, setSavingEnvironment] = useState(false);
  const [checkingEnvironmentId, setCheckingEnvironmentId] = useState(null);
  const [healthResults, setHealthResults] = useState({});
  const { message, modal } = AntApp.useApp();

  // Reset project edit state after saving or canceling an edit.
  function resetProjectForm() {
    setEditingProjectId(null);
    projectForm.resetFields();
  }

  // Reset environment edit state and restore a valid empty variables object.
  function resetEnvironmentForm() {
    setEditingEnvironmentId(null);
    environmentForm.resetFields();
    environmentForm.setFieldsValue({ variablesText: '{}' });
  }

  // Fill the project form with an existing record so the user can edit it.
  function startEditProject(item) {
    setEditingProjectId(item.id);
    projectForm.setFieldsValue(buildProjectFormValues(item));
  }

  // Fill the environment form with an existing record so the user can edit it.
  function startEditEnvironment(item) {
    setEditingEnvironmentId(item.id);
    environmentForm.setFieldsValue(buildEnvironmentFormValues(item));
  }

  // Submit project form values through the feature helper.
  async function submitProject(values) {
    setSavingProject(true);
    try {
      const result = await saveProject(client, editingProjectId, values);
      message.success(result === 'updated' ? '项目已更新' : '项目已创建');
      resetProjectForm();
      await reload();
    } catch (err) {
      message.error(err.message);
    } finally {
      setSavingProject(false);
    }
  }

  // Submit environment form values through the feature helper, including JSON validation.
  async function submitEnvironment(values) {
    setSavingEnvironment(true);
    try {
      const result = await saveEnvironment(client, editingEnvironmentId, values);
      message.success(result === 'updated' ? '环境已更新' : '环境已创建');
      resetEnvironmentForm();
      await reload();
    } catch (err) {
      message.error(err.message);
    } finally {
      setSavingEnvironment(false);
    }
  }

  // Confirm project deletion because it also removes related legacy cases and runs.
  function removeProject(item) {
    modal.confirm({
      title: `删除项目「${item.name}」？`,
      content: '关联接口用例、UI 用例和执行记录也会一起删除。',
      okText: '删除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: async () => {
        await deleteProject(client, item.id);
        if (editingProjectId === item.id) resetProjectForm();
        message.success('项目已删除');
        await reload();
      },
    });
  }

  // Confirm environment deletion; backend refuses deletion when historical references exist.
  function removeEnvironment(item) {
    modal.confirm({
      title: `删除环境「${item.name}」？`,
      content: '如果环境已经被测试任务、执行结果或接口场景引用，后端会拒绝删除。',
      okText: '删除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: async () => {
        await deleteEnvironment(client, item.id);
        if (editingEnvironmentId === item.id) resetEnvironmentForm();
        message.success('环境已删除');
        await reload();
      },
    });
  }

  // Ask the backend to call the environment base URL and return availability evidence.
  async function runHealthCheck(item) {
    setCheckingEnvironmentId(item.id);
    try {
      const result = await checkEnvironmentHealth(client, item.id);
      setHealthResults((current) => ({ ...current, [item.id]: result }));
      if (result.status === 'ok') message.success(`环境可访问，耗时 ${formatDuration(result.elapsed_ms)}`);
      else message.warning(result.error || `环境返回状态码 ${result.status_code}`);
    } catch (err) {
      message.error(err.message);
    } finally {
      setCheckingEnvironmentId(null);
    }
  }

  const projectOptions = projects.map((item) => ({ value: item.id, label: item.name }));
  const projectNameById = new Map(projects.map((item) => [item.id, item.name]));

  // Render block: JSX below describes the project and environment management workspace.
  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={9}>
        <Card title={editingProjectId ? '修改项目' : '新建项目'} extra={editingProjectId && <Button onClick={resetProjectForm}>取消编辑</Button>}>
          <Form form={projectForm} layout="vertical" onFinish={submitProject}>
            <Form.Item label="项目名称" name="name" rules={[{ required: true, message: '请输入项目名称' }]}>
              <Input placeholder="例如：电商平台自动化" />
            </Form.Item>
            <Form.Item label="说明" name="description">
              <TextArea rows={5} placeholder="项目用途、业务范围或备注" />
            </Form.Item>
            <Button type="primary" htmlType="submit" loading={savingProject} icon={<PlusOutlined />}>
              {editingProjectId ? '更新项目' : '保存项目'}
            </Button>
          </Form>
        </Card>

        <Card title={editingEnvironmentId ? '修改环境' : '新建环境'} style={{ marginTop: 16 }} extra={editingEnvironmentId && <Button onClick={resetEnvironmentForm}>取消编辑</Button>}>
          <Form form={environmentForm} layout="vertical" onFinish={submitEnvironment} initialValues={{ variablesText: '{}' }}>
            <Form.Item label="所属项目" name="project_id" rules={[{ required: true, message: '请选择所属项目' }]}>
              <Select options={projectOptions} placeholder="选择项目" />
            </Form.Item>
            <Form.Item label="环境名称" name="name" rules={[{ required: true, message: '请输入环境名称' }]}>
              <Input placeholder="例如：测试环境 / 预发环境" />
            </Form.Item>
            <Form.Item label="Base URL" name="base_url" rules={[{ required: true, message: '请输入公网 HTTP/HTTPS 地址' }]}>
              <Input placeholder="例如：https://example.com" />
            </Form.Item>
            <Form.Item label="环境变量 JSON" name="variablesText">
              <TextArea className="code-input" rows={5} placeholder='例如：{"token":"xxx","tenantId":"1001"}' />
            </Form.Item>
            <Button type="primary" htmlType="submit" loading={savingEnvironment} icon={<ApiOutlined />}>
              {editingEnvironmentId ? '更新环境' : '保存环境'}
            </Button>
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
                    <Button icon={<EditOutlined />} onClick={() => startEditProject(record)}>修改</Button>
                    <Button danger icon={<DeleteOutlined />} onClick={() => removeProject(record)}>删除</Button>
                  </Space>
                ),
              },
            ]}
          />
        </Card>

        <Card title="环境列表" style={{ marginTop: 16 }}>
          <Table
            rowKey="id"
            dataSource={environments}
            pagination={{ pageSize: 6 }}
            scroll={{ x: 980 }}
            columns={[
              { title: 'ID', dataIndex: 'id', width: 70 },
              { title: '项目', dataIndex: 'project_id', width: 140, render: (value) => projectNameById.get(value) || value },
              { title: '环境', dataIndex: 'name', width: 140 },
              { title: 'Base URL', dataIndex: 'base_url', width: 260 },
              {
                title: '健康状态',
                width: 150,
                render: (_, record) => {
                  const result = healthResults[record.id];
                  if (!result) return <Tag>未检查</Tag>;
                  if (result.status === 'ok') return <Tag color="success">正常 {formatDuration(result.elapsed_ms)}</Tag>;
                  if (result.status === 'warning') return <Tag color="warning">状态码 {result.status_code}</Tag>;
                  return <Tag color="error">异常</Tag>;
                },
              },
              {
                title: '操作',
                fixed: 'right',
                width: 260,
                render: (_, record) => (
                  <Space className="table-actions" size={6} wrap>
                    <Button icon={<ThunderboltOutlined />} loading={checkingEnvironmentId === record.id} onClick={() => runHealthCheck(record)}>检查</Button>
                    <Button icon={<EditOutlined />} onClick={() => startEditEnvironment(record)}>修改</Button>
                    <Button danger icon={<DeleteOutlined />} onClick={() => removeEnvironment(record)}>删除</Button>
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

// Projects module: maintains project and environment records.
