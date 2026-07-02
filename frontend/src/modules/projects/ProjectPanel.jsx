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

// 常改位置：表单字段、项目列表列配置、创建/编辑/删除按钮逻辑。
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
    form.setFieldsValue({ name: item.name, description: item.description || '' });
  }

  async function submit(values) {
    setSaving(true);
    try {
      if (editingId) {
        await client.put(`/projects/${editingId}`, values);
        message.success('项目已更新');
      } else {
        await client.post('/projects', values);
        message.success('项目已创建');
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
      title: `删除项目「${item.name}」？`,
      content: '关联接口用例、UI 用例和执行记录也会一起删除。',
      okText: '删除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: async () => {
        await client.delete(`/projects/${item.id}`);
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

