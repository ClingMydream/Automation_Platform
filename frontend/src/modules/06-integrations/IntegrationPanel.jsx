// File purpose: Integration page. Maintain webhook configurations for notifications and external systems.

import React, { useState } from 'react';
import { App as AntApp, Button, Card, Col, Form, Input, Row, Select, Space, Switch, Table, Tag } from 'antd';
import { DeleteOutlined, EditOutlined, PlusOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { buildWebhookFormValues, deleteWebhook, saveWebhook, testWebhook, WEBHOOK_EVENT_OPTIONS } from './integrationFeature.js';

const { TextArea } = Input;

export function IntegrationPanel({ client, integrations, reload }) {
  const [form] = Form.useForm();
  const [editingId, setEditingId] = useState(null);
  const [saving, setSaving] = useState(false);
  const { message, modal } = AntApp.useApp();

  function resetForm() {
    setEditingId(null);
    form.resetFields();
    form.setFieldsValue({ integration_type: 'webhook', events: [], is_active: true });
  }

  function startEdit(item) {
    setEditingId(item.id);
    form.setFieldsValue(buildWebhookFormValues(item));
  }

  async function submit(values) {
    setSaving(true);
    try {
      const result = await saveWebhook(client, editingId, values);
      message.success(result === 'updated' ? '集成配置已更新' : '集成配置已创建');
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
      title: `删除集成「${item.name}」？`,
      okText: '删除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: async () => {
        await deleteWebhook(client, item.id);
        message.success('集成配置已删除');
        await reload();
      },
    });
  }

  async function test(item) {
    try {
      const result = await testWebhook(client, item.id);
      message.success(result.message || '配置可用');
    } catch (err) {
      message.error(err.message);
    }
  }

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={9}>
        <Card title={editingId ? '修改集成配置' : '新建集成配置'} extra={editingId && <Button onClick={resetForm}>取消编辑</Button>}>
          <Form form={form} layout="vertical" initialValues={{ integration_type: 'webhook', events: [], is_active: true }} onFinish={submit}>
            <Form.Item label="名称" name="name" rules={[{ required: true, message: '请输入名称' }]}><Input placeholder="团队通知机器人" /></Form.Item>
            <Form.Item label="类型" name="integration_type"><Input placeholder="webhook / dingtalk / wechat / feishu" /></Form.Item>
            <Form.Item label="Webhook 地址" name="webhook_url" rules={[{ required: true, message: '请输入公网 Webhook 地址' }]}><Input placeholder="https://example.com/webhook" /></Form.Item>
            <Form.Item label="订阅事件" name="events">
              <Select mode="tags" options={WEBHOOK_EVENT_OPTIONS} placeholder="不选择表示接收全部事件" />
            </Form.Item>
            <Form.Item label="密钥变量名" name="secret_name"><Input placeholder="可选：SERVER_WEBHOOK_SECRET" /></Form.Item>
            <Form.Item label="启用状态" name="is_active" valuePropName="checked"><Switch checkedChildren="启用" unCheckedChildren="停用" /></Form.Item>
            <Form.Item label="说明" name="description"><TextArea rows={3} /></Form.Item>
            <Button type="primary" htmlType="submit" loading={saving} icon={<PlusOutlined />}>{editingId ? '更新配置' : '保存配置'}</Button>
          </Form>
        </Card>
      </Col>
      <Col xs={24} xl={15}>
        <Card title="集成配置列表">
          <Table
            rowKey="id"
            dataSource={integrations}
            pagination={{ pageSize: 8 }}
            scroll={{ x: 900 }}
            columns={[
              { title: '名称', dataIndex: 'name', width: 160 },
              { title: '类型', dataIndex: 'integration_type', width: 120 },
              { title: '事件', dataIndex: 'events', render: (events = []) => <Space wrap>{events.map((event) => <Tag key={event}>{event}</Tag>)}</Space> },
              { title: '状态', dataIndex: 'is_active', width: 90, render: (value) => <Tag color={value ? 'green' : 'default'}>{value ? '启用' : '停用'}</Tag> },
              { title: '操作', width: 240, render: (_, record) => <Space><Button icon={<ThunderboltOutlined />} onClick={() => test(record)}>测试</Button><Button icon={<EditOutlined />} onClick={() => startEdit(record)}>修改</Button><Button danger icon={<DeleteOutlined />} onClick={() => remove(record)}>删除</Button></Space> },
            ]}
          />
        </Card>
      </Col>
    </Row>
  );
}
