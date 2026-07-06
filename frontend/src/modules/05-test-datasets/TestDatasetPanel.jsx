// File purpose: Test dataset page. Maintain variables, test accounts, and data pools.

import React, { useMemo, useState } from 'react';
import { App as AntApp, Button, Card, Col, Form, Input, Row, Select, Space, Switch, Table, Tag } from 'antd';
import { DeleteOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons';
import { buildDatasetFormValues, DATASET_TYPES, deleteDataset, saveDataset } from './testDatasetFeature.js';

const { TextArea } = Input;

export function TestDatasetPanel({ client, projects, datasets, reload }) {
  const [form] = Form.useForm();
  const [editingId, setEditingId] = useState(null);
  const [saving, setSaving] = useState(false);
  const { message, modal } = AntApp.useApp();
  const projectOptions = useMemo(() => projects.map((item) => ({ value: item.id, label: item.name })), [projects]);
  const projectNameById = useMemo(() => new Map(projects.map((item) => [item.id, item.name])), [projects]);

  function resetForm() {
    setEditingId(null);
    form.resetFields();
    form.setFieldsValue({ dataset_type: 'variables', variablesText: '{}', rowsText: '[]', is_active: true });
  }

  function startEdit(item) {
    setEditingId(item.id);
    form.setFieldsValue(buildDatasetFormValues(item));
  }

  async function submit(values) {
    setSaving(true);
    try {
      const result = await saveDataset(client, editingId, values);
      message.success(result === 'updated' ? '测试数据已更新' : '测试数据已创建');
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
      title: `删除测试数据「${item.name}」？`,
      okText: '删除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: async () => {
        await deleteDataset(client, item.id);
        message.success('测试数据已删除');
        await reload();
      },
    });
  }

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={9}>
        <Card title={editingId ? '修改测试数据' : '新建测试数据'} extra={editingId && <Button onClick={resetForm}>取消编辑</Button>}>
          <Form form={form} layout="vertical" initialValues={{ dataset_type: 'variables', variablesText: '{}', rowsText: '[]', is_active: true }} onFinish={submit}>
            <Form.Item label="名称" name="name" rules={[{ required: true, message: '请输入名称' }]}><Input placeholder="测试账号池" /></Form.Item>
            <Form.Item label="所属项目" name="project_id"><Select allowClear options={projectOptions} placeholder="可选" /></Form.Item>
            <Form.Item label="类型" name="dataset_type"><Select options={DATASET_TYPES} /></Form.Item>
            <Form.Item label="变量 JSON" name="variablesText"><TextArea rows={4} placeholder='{"baseUser":"tester"}' /></Form.Item>
            <Form.Item label="数据行 JSON 数组" name="rowsText"><TextArea rows={5} placeholder='[{"username":"u1","password":"p1"}]' /></Form.Item>
            <Form.Item label="启用状态" name="is_active" valuePropName="checked"><Switch checkedChildren="启用" unCheckedChildren="停用" /></Form.Item>
            <Form.Item label="说明" name="description"><TextArea rows={3} /></Form.Item>
            <Button type="primary" htmlType="submit" loading={saving} icon={<PlusOutlined />}>{editingId ? '更新数据' : '保存数据'}</Button>
          </Form>
        </Card>
      </Col>
      <Col xs={24} xl={15}>
        <Card title="测试数据列表">
          <Table
            rowKey="id"
            dataSource={datasets}
            pagination={{ pageSize: 8 }}
            scroll={{ x: 820 }}
            columns={[
              { title: '名称', dataIndex: 'name' },
              { title: '项目', dataIndex: 'project_id', render: (value) => (value ? projectNameById.get(value) || `项目 ${value}` : '-') },
              { title: '类型', dataIndex: 'dataset_type', render: (value) => <Tag>{DATASET_TYPES.find((item) => item.value === value)?.label || value}</Tag> },
              { title: '数据行', dataIndex: 'rows', render: (value = []) => value.length },
              { title: '状态', dataIndex: 'is_active', render: (value) => <Tag color={value ? 'green' : 'default'}>{value ? '启用' : '停用'}</Tag> },
              { title: '操作', width: 170, render: (_, record) => <Space><Button icon={<EditOutlined />} onClick={() => startEdit(record)}>修改</Button><Button danger icon={<DeleteOutlined />} onClick={() => remove(record)}>删除</Button></Space> },
            ]}
          />
        </Card>
      </Col>
    </Row>
  );
}
