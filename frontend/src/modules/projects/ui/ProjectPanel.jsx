import React, { useState } from 'react';
import { App as AntApp, Button, Card, Col, Form, Input, Row, Space, Table } from 'antd';
import { DeleteOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons';
import { buildProjectFormValues, deleteProject, saveProject } from '../feature/projectFeature.js';

const { TextArea } = Input;

export function ProjectPanel({ client, projects, reload }) {
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
    form.setFieldsValue(buildProjectFormValues(item));
  }

  async function submit(values) {
    setSaving(true);
    try {
      const result = await saveProject(client, editingId, values);
      message.success(result === 'updated' ? '项目已更新' : '项目已创建');
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
        await deleteProject(client, item.id);
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

// 接口测试模块：维护接口用例，并向后端创建执行任务。

