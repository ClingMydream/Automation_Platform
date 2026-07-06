// File purpose: Test object page. Create, edit, delete, and list platform-level test objects.
// How to change: edit UI text/layout in this file; move reusable logic into testObjectFeature.js.

import React, { useMemo, useState } from 'react';
import { App as AntApp, Button, Card, Col, Form, Input, Row, Select, Space, Switch, Table, Tag } from 'antd';
import { DeleteOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons';
import { buildTestObjectFormValues, deleteTestObject, saveTestObject, TEST_OBJECT_TYPES, testObjectTypeLabel } from './testObjectFeature.js';

const { TextArea } = Input;

// Test object page: manages the first platform layer, which describes what should be tested.
export function TestObjectPanel({ client, projects, testObjects, reload }) {
  // State block: values here control loading, selection, form state, and table filters.
  const [form] = Form.useForm();
  const [editingId, setEditingId] = useState(null);
  const [saving, setSaving] = useState(false);
  const [typeFilter, setTypeFilter] = useState('all');
  const [activeFilter, setActiveFilter] = useState('all');
  const { message, modal } = AntApp.useApp();

  // Project options are reused by the form and table display mapping.
  const projectOptions = useMemo(() => projects.map((project) => ({ value: project.id, label: project.name })), [projects]);
  const projectNameById = useMemo(() => new Map(projects.map((project) => [project.id, project.name])), [projects]);

  // Filter rows locally so the shared reload function can remain simple.
  const filteredObjects = useMemo(() => testObjects.filter((item) => {
    const typeMatched = typeFilter === 'all' || item.object_type === typeFilter;
    const activeMatched = activeFilter === 'all' || item.is_active === (activeFilter === 'active');
    return typeMatched && activeMatched;
  }), [testObjects, typeFilter, activeFilter]);

  // Reset edit state and restore default form values.
  function resetForm() {
    setEditingId(null);
    form.resetFields();
    form.setFieldsValue({ is_active: true, tags: [] });
  }

  // Fill the form with an existing test object so the user can edit it.
  function startEdit(item) {
    setEditingId(item.id);
    form.setFieldsValue(buildTestObjectFormValues(item));
  }

  // Submit the current form, save the test object, and refresh shared data.
  async function submit(values) {
    setSaving(true);
    try {
      const result = await saveTestObject(client, editingId, values);
      message.success(result === 'updated' ? '测试对象已更新' : '测试对象已创建');
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
      title: `删除测试对象「${item.name}」？`,
      content: '第一批改造中测试对象未强制绑定旧用例，删除不会影响现有接口用例、UI 用例和执行记录。',
      okText: '删除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: async () => {
        await deleteTestObject(client, item.id);
        if (editingId === item.id) resetForm();
        message.success('测试对象已删除');
        await reload();
      },
    });
  }

  // Render block: JSX below describes what the user sees on this page.
  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={9}>
        <Card title={editingId ? '修改测试对象' : '新建测试对象'} extra={editingId && <Button onClick={resetForm}>取消编辑</Button>}>
          <Form form={form} layout="vertical" initialValues={{ object_type: 'api', is_active: true, tags: [] }} onFinish={submit}>
            <Form.Item label="唯一编号" name="code" rules={[{ required: true, message: '请输入唯一编号' }]}>
              <Input placeholder="例如：API-LOGIN-001" />
            </Form.Item>
            <Form.Item label="对象名称" name="name" rules={[{ required: true, message: '请输入对象名称' }]}>
              <Input placeholder="例如：登录接口" />
            </Form.Item>
            <Form.Item label="对象类型" name="object_type" rules={[{ required: true, message: '请选择对象类型' }]}>
              <Select options={TEST_OBJECT_TYPES} />
            </Form.Item>
            <Form.Item label="所属项目" name="project_id">
              <Select allowClear placeholder="可选：选择所属项目" options={projectOptions} />
            </Form.Item>
            <Form.Item label="业务模块" name="business_module">
              <Input placeholder="例如：用户中心、订单中心" />
            </Form.Item>
            <Form.Item label="标签" name="tags">
              <Select mode="tags" placeholder="输入后回车，例如：冒烟、核心链路" tokenSeparators={[',', '，']} />
            </Form.Item>
            <Form.Item label="启用状态" name="is_active" valuePropName="checked">
              <Switch checkedChildren="启用" unCheckedChildren="停用" />
            </Form.Item>
            <Form.Item label="说明" name="description">
              <TextArea rows={4} placeholder="测试范围、风险点、维护人或备注" />
            </Form.Item>
            <Button type="primary" htmlType="submit" loading={saving} icon={<PlusOutlined />}>{editingId ? '更新对象' : '保存对象'}</Button>
          </Form>
        </Card>
      </Col>
      <Col xs={24} xl={15}>
        <Card
          title="测试对象列表"
          extra={(
            <Space wrap>
              <Select value={typeFilter} style={{ width: 130 }} onChange={setTypeFilter} options={[{ value: 'all', label: '全部类型' }, ...TEST_OBJECT_TYPES]} />
              <Select
                value={activeFilter}
                style={{ width: 120 }}
                onChange={setActiveFilter}
                options={[
                  { value: 'all', label: '全部状态' },
                  { value: 'active', label: '启用' },
                  { value: 'inactive', label: '停用' },
                ]}
              />
            </Space>
          )}
        >
          <Table
            rowKey="id"
            dataSource={filteredObjects}
            pagination={{ pageSize: 8 }}
            scroll={{ x: 980 }}
            columns={[
              { title: '编号', dataIndex: 'code', width: 150 },
              { title: '名称', dataIndex: 'name', width: 160 },
              { title: '类型', dataIndex: 'object_type', width: 110, render: (value) => <Tag color="cyan">{testObjectTypeLabel(value)}</Tag> },
              { title: '项目', dataIndex: 'project_id', width: 150, render: (value) => (value ? projectNameById.get(value) || `项目 ${value}` : '-') },
              { title: '业务模块', dataIndex: 'business_module', width: 130, render: (value) => value || '-' },
              { title: '标签', dataIndex: 'tags', width: 180, render: (tags = []) => <Space size={4} wrap>{tags.map((tag) => <Tag key={tag}>{tag}</Tag>)}</Space> },
              { title: '状态', dataIndex: 'is_active', width: 90, render: (value) => <Tag color={value ? 'green' : 'default'}>{value ? '启用' : '停用'}</Tag> },
              {
                title: '操作',
                width: 170,
                fixed: 'right',
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

// Test objects module: maintains the platform layer that describes what should be tested.
