import React, { useState } from 'react';
import { Alert, App as AntApp, Button, Card, Col, Form, Input, Row, Select, Space, Table } from 'antd';
import { DeleteOutlined, EditOutlined, PlayCircleOutlined, PlusOutlined } from '@ant-design/icons';
import { DEFAULT_UI_STEPS, UI_STEPS_EXAMPLE } from '../../../shared/constants';
import { JsonHelpCard } from '../../../shared/JsonHelpCard.jsx';
import {
  buildUiCaseFormValues,
  createUiCaseRun,
  deleteUiCase,
  navigateLiveRunWindow,
  openLiveRunWindow,
  saveUiCase,
} from '../feature/uiCaseFeature.js';

const { TextArea } = Input;

export function UiCasePanel({ client, projects, uiCases, reload, onRunCreated }) {
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
    form.setFieldsValue(buildUiCaseFormValues(item));
  }

  async function submit(values) {
    setSaving(true);
    try {
      const result = await saveUiCase(client, editingId, values);
      message.success(result === 'updated' ? 'UI 用例已更新' : 'UI 用例已创建');
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
        await deleteUiCase(client, item.id);
        if (editingId === item.id) resetForm();
        message.success('UI 用例已删除');
        await reload();
      },
    });
  }

  async function runCase(record) {
    const detailWindow = openLiveRunWindow();
    setRunningId(record.id);
    try {
      const run = await createUiCaseRun(client, record.id);
      navigateLiveRunWindow(detailWindow, run.id);
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
        <Space direction="vertical" size={16} className="full-width">
          <JsonHelpCard
            title="UI 步骤 JSON 使用说明"
            tips={[
              '步骤 JSON 必须是数组，每一行对象代表一个自动化步骤。',
              'goto 用 value 填要打开的网址，必须是公网 http/https 地址。',
              'click 用 selector 填要点击的元素，例如 text=登录、#submit、.btn-primary。',
              'fill 用 selector 定位输入框，用 value 填要输入的内容。',
              'wait 用 value 填等待毫秒数，例如 1000 表示等待 1 秒。',
              'assert_text 用 value 填期望页面出现的文字；screenshot 不需要额外字段。',
            ]}
            example={UI_STEPS_EXAMPLE}
          />
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
        </Space>
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

// 图片工具模块：调用后端图片接口完成生成、裁剪、格式转换。

