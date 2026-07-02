import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  App as AntApp,
  Button,
  Card,
  Checkbox,
  Col,
  Descriptions,
  Drawer,
  Empty,
  Form,
  Input,
  Modal,
  QRCode,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
  Upload,
} from 'antd';
import {
  ApiOutlined,
  BugOutlined,
  CloudUploadOutlined,
  CopyOutlined,
  ClockCircleOutlined,
  CloseOutlined,
  CodeOutlined,
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  EyeOutlined,
  FileDoneOutlined,
  FolderOutlined,
  InboxOutlined,
  LogoutOutlined,
  PictureOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
  RocketOutlined,
  SafetyCertificateOutlined,
  SwapOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { apiClient } from '../../shared/apiClient';
import { runCodec } from '../../shared/codec';
import { API_BASE, API_JSON_EXAMPLE, DEFAULT_UI_STEPS, UI_STEPS_EXAMPLE } from '../../shared/constants';
import { downloadBlob, transferKind, transferKindLabel, TransferPreview } from '../../shared/fileTransfer.jsx';
import { formatBytes, formatDuration, formatTime } from '../../shared/formatters';
import { compareJsonValues, parseJsonInput, stableStringifyJson } from '../../shared/jsonTools';
import { downloadReportHtml } from '../../shared/reportExport';
import { JsonHelpCard } from '../../shared/JsonHelpCard.jsx';
import { StatusTag } from '../../shared/StatusTag.jsx';

const { Text, Title, Paragraph } = Typography;
const { TextArea } = Input;
const { Dragger } = Upload;

// 常改位置：请求字段、断言字段、用例表格列、执行按钮行为。
export function ApiCasePanel({ client, projects, apiCases, reload, onRunCreated }) {
  const [form] = Form.useForm();
  const [editingId, setEditingId] = useState(null);
  const [saving, setSaving] = useState(false);
  const { message, modal } = AntApp.useApp();

  function resetForm() {
    setEditingId(null);
    form.resetFields();
    form.setFieldsValue({ method: 'GET', headers: '{}', assert_status: 200 });
  }

  function buildPayload(values) {
    return {
      ...values,
      project_id: Number(values.project_id),
      headers: JSON.parse(values.headers || '{}'),
      assert_status: Number(values.assert_status) || null,
      body: values.body || null,
      assert_text: values.assert_text || null,
      assert_json_path: values.assert_json_path || null,
      assert_json_value: values.assert_json_value || null,
    };
  }

  function startEdit(item) {
    setEditingId(item.id);
    form.setFieldsValue({
      project_id: item.project_id,
      name: item.name,
      method: item.method,
      url: item.url,
      headers: JSON.stringify(item.headers || {}, null, 2),
      body: item.body || '',
      assert_status: item.assert_status || '',
      assert_text: item.assert_text || '',
      assert_json_path: item.assert_json_path || '',
      assert_json_value: item.assert_json_value || '',
    });
  }

  async function submit(values) {
    setSaving(true);
    try {
      const body = buildPayload(values);
      if (editingId) {
        await client.put(`/api-cases/${editingId}`, body);
        message.success('接口用例已更新');
      } else {
        await client.post('/api-cases', body);
        message.success('接口用例已创建');
      }
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
      title: `删除接口用例「${item.name}」？`,
      content: '对应执行记录也会一起删除。',
      okText: '删除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: async () => {
        await client.delete(`/api-cases/${item.id}`);
        if (editingId === item.id) resetForm();
        message.success('接口用例已删除');
        await reload();
      },
    });
  }

  async function runCase(record) {
    try {
      const run = await client.post('/runs', { case_type: 'api', case_id: record.id });
      message.success(`已创建接口执行任务 #${run.id}`);
      await reload();
      onRunCreated(run, 'api', false);
    } catch (err) {
      message.error(err.message);
    }
  }

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={10}>
        <Space direction="vertical" size={16} className="full-width">
          <JsonHelpCard
            title="接口 JSON 使用说明"
            tips={[
              '请求头 JSON 必须是对象格式，最简单可以填 {}。',
              'POST/PUT/PATCH 的请求体可以填 JSON，也可以留空；GET 通常不用填请求体。',
              '响应包含文本用于检查返回内容里有没有某段文字。',
              'JSON 路径用于检查返回 JSON 的字段，格式类似 $.data.name 或 $.items.0.id。',
              'JSON 期望值会按文本比较，例如接口返回 200，期望值就填 200。',
            ]}
            example={API_JSON_EXAMPLE}
          />
          <Card title={editingId ? '修改接口用例' : '接口用例'} extra={editingId && <Button onClick={resetForm}>取消编辑</Button>}>
            <Form form={form} layout="vertical" onFinish={submit} initialValues={{ method: 'GET', headers: '{}', assert_status: 200 }}>
              <Form.Item label="所属项目" name="project_id" rules={[{ required: true, message: '请选择项目' }]}>
                <Select placeholder="选择项目" options={projects.map((project) => ({ value: project.id, label: project.name }))} />
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
              <Form.Item label="完整 URL" name="url" rules={[{ required: true, message: '请输入 URL' }]}>
                <Input placeholder="https://example.com" />
              </Form.Item>
              <Form.Item label="请求头 JSON" name="headers">
                <TextArea rows={4} className="code-input" />
              </Form.Item>
              <Form.Item label="请求体" name="body">
                <TextArea rows={4} className="code-input" />
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
              <Button type="primary" htmlType="submit" loading={saving} icon={<PlusOutlined />}>{editingId ? '更新接口用例' : '保存接口用例'}</Button>
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
            scroll={{ x: 980 }}
            columns={[
              { title: 'ID', dataIndex: 'id', width: 70 },
              { title: '名称', dataIndex: 'name' },
              { title: '方法', dataIndex: 'method', width: 90, render: (value) => <Tag color="blue">{value}</Tag> },
              { title: 'URL', dataIndex: 'url', ellipsis: true },
              {
                title: '操作',
                width: 180,
                fixed: 'right',
                render: (_, record) => (
                  <Space className="table-actions" size={6} wrap>
                    <Button type="primary" icon={<PlayCircleOutlined />} onClick={() => runCase(record)}>执行</Button>
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

// UI 测试模块：维护低代码 UI 步骤，并打开实时执行窗口。

