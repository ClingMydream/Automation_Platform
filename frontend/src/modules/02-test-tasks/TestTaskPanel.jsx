// File purpose: Test task page. Maintain reusable tasks and start execution batches.

import React, { useMemo, useState } from 'react';
import { App as AntApp, Button, Card, Col, Form, Input, InputNumber, Row, Select, Space, Switch, Table, Tag } from 'antd';
import { DeleteOutlined, EditOutlined, PlayCircleOutlined, PlusOutlined } from '@ant-design/icons';
import { buildTaskFormValues, deleteTask, runTask, saveTask, TASK_TYPES, taskTypeLabel, TRIGGER_TYPES } from './testTaskFeature.js';

const { TextArea } = Input;

export function TestTaskPanel({ client, projects, testObjects, testTasks, reload }) {
  const [form] = Form.useForm();
  const [editingId, setEditingId] = useState(null);
  const [saving, setSaving] = useState(false);
  const { message, modal } = AntApp.useApp();
  const projectOptions = useMemo(() => projects.map((item) => ({ value: item.id, label: item.name })), [projects]);
  const objectOptions = useMemo(() => testObjects.map((item) => ({ value: item.id, label: `${item.code} ${item.name}` })), [testObjects]);

  function resetForm() {
    setEditingId(null);
    form.resetFields();
    form.setFieldsValue({ task_type: 'api', trigger_type: 'manual', runner_type: 'platform', retry_count: 0, is_active: true, configText: '{}' });
  }

  function startEdit(item) {
    setEditingId(item.id);
    form.setFieldsValue(buildTaskFormValues(item));
  }

  async function submit(values) {
    setSaving(true);
    try {
      const result = await saveTask(client, editingId, values);
      message.success(result === 'updated' ? '测试任务已更新' : '测试任务已创建');
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
      title: `删除测试任务「${item.name}」？`,
      content: '历史结果仍会保留在结果中心。',
      okText: '删除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: async () => {
        await deleteTask(client, item.id);
        message.success('测试任务已删除');
        await reload();
      },
    });
  }

  async function startRun(item) {
    try {
      const batch = await runTask(client, item.id);
      message.success(`已创建执行批次：${batch.batch_no}`);
      await reload();
    } catch (err) {
      message.error(err.message);
    }
  }

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={9}>
        <Card title={editingId ? '修改测试任务' : '新建测试任务'} extra={editingId && <Button onClick={resetForm}>取消编辑</Button>}>
          <Form form={form} layout="vertical" initialValues={{ task_type: 'api', trigger_type: 'manual', runner_type: 'platform', retry_count: 0, is_active: true, configText: '{}' }} onFinish={submit}>
            <Form.Item label="任务编号" name="code" rules={[{ required: true, message: '请输入任务编号' }]}><Input placeholder="TASK-SMOKE-001" /></Form.Item>
            <Form.Item label="任务名称" name="name" rules={[{ required: true, message: '请输入任务名称' }]}><Input placeholder="冒烟自动化任务" /></Form.Item>
            <Form.Item label="任务类型" name="task_type"><Select options={TASK_TYPES} /></Form.Item>
            <Form.Item label="所属项目" name="project_id"><Select allowClear options={projectOptions} placeholder="可选" /></Form.Item>
            <Form.Item label="关联测试对象" name="test_object_id"><Select allowClear showSearch options={objectOptions} placeholder="可选" /></Form.Item>
            <Form.Item label="触发方式" name="trigger_type"><Select options={TRIGGER_TYPES} /></Form.Item>
            <Form.Item label="执行来源" name="runner_type"><Input placeholder="platform / pytest / playwright / jmeter / ci" /></Form.Item>
            <Form.Item label="失败重试次数" name="retry_count"><InputNumber min={0} max={10} style={{ width: '100%' }} /></Form.Item>
            <Form.Item label="启用状态" name="is_active" valuePropName="checked"><Switch checkedChildren="启用" unCheckedChildren="停用" /></Form.Item>
            <Form.Item label="任务配置 JSON" name="configText"><TextArea rows={4} placeholder='{"case_ids":[1,2]}' /></Form.Item>
            <Form.Item label="说明" name="description"><TextArea rows={3} placeholder="测试范围、触发来源、注意事项" /></Form.Item>
            <Button type="primary" htmlType="submit" loading={saving} icon={<PlusOutlined />}>{editingId ? '更新任务' : '保存任务'}</Button>
          </Form>
        </Card>
      </Col>
      <Col xs={24} xl={15}>
        <Card title="测试任务列表">
          <Table
            rowKey="id"
            dataSource={testTasks}
            pagination={{ pageSize: 8 }}
            scroll={{ x: 980 }}
            columns={[
              { title: '编号', dataIndex: 'code', width: 150 },
              { title: '名称', dataIndex: 'name', width: 180 },
              { title: '类型', dataIndex: 'task_type', width: 90, render: (value) => <Tag color="cyan">{taskTypeLabel(value)}</Tag> },
              { title: '来源', dataIndex: 'runner_type', width: 110 },
              { title: '最近状态', dataIndex: 'last_status', width: 110, render: (value) => value || '-' },
              { title: '状态', dataIndex: 'is_active', width: 90, render: (value) => <Tag color={value ? 'green' : 'default'}>{value ? '启用' : '停用'}</Tag> },
              {
                title: '操作',
                width: 240,
                fixed: 'right',
                render: (_, record) => (
                  <Space className="table-actions" size={6} wrap>
                    <Button icon={<PlayCircleOutlined />} onClick={() => startRun(record)}>执行</Button>
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
