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

export function Login({ onLogin, notice }) {
  const [loading, setLoading] = useState(false);
  const { message } = AntApp.useApp();

  async function submit(values) {
    setLoading(true);
    try {
      const data = await apiClient().post('/auth/login', values);
      localStorage.setItem('token', data.access_token);
      onLogin(data.access_token);
      message.success('登录成功');
    } catch (err) {
      message.error(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-screen">
      <Card className="login-card">
        <Space direction="vertical" size={24} className="full-width">
          <div className="login-brand">
            <SafetyCertificateOutlined />
            <div>
              <Title level={3}>Automation Platform</Title>
              <Text type="secondary">接口测试与低代码 UI 自动化控制台</Text>
            </div>
          </div>
          {notice && <Alert type="warning" showIcon message={notice} />}
          <Form layout="vertical" initialValues={{ username: 'admin', password: '' }} onFinish={submit}>
            <Form.Item label="管理员账号" name="username" rules={[{ required: true, message: '请输入账号' }]}>
              <Input size="large" />
            </Form.Item>
            <Form.Item label="管理员密码" name="password" rules={[{ required: true, message: '请输入密码' }]}>
              <Input.Password size="large" autoFocus />
            </Form.Item>
            <Button type="primary" size="large" htmlType="submit" loading={loading} block icon={<SafetyCertificateOutlined />}>登录平台</Button>
          </Form>
        </Space>
      </Card>
    </main>
  );
}

// 项目管理模块：维护项目基础信息。

