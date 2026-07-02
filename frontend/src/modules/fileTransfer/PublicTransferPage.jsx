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

// 常改位置：手机端文案、上传入口、下载按钮和预览区域。
export function PublicTransferPage({ token }) {
  const client = useMemo(() => apiClient(), []);
  const [item, setItem] = useState(null);
  const [error, setError] = useState('');
  const [uploading, setUploading] = useState(false);
  const [returnedFile, setReturnedFile] = useState(null);
  const { message } = AntApp.useApp();

  async function loadTransfer() {
    try {
      const data = await client.get(`/file-transfers/public/${token}`);
      setItem(data);
      setError('');
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    loadTransfer();
  }, [token]);

  async function uploadBack({ file, onSuccess, onError }) {
    setUploading(true);
    try {
      const body = new FormData();
      body.append('file', file);
      const data = await client.post(`/file-transfers/public/${token}/upload`, body);
      setReturnedFile(data);
      message.success('已上传回传文件，电脑端刷新列表即可看到');
      onSuccess?.(data);
    } catch (err) {
      message.error(err.message);
      onError?.(err);
    } finally {
      setUploading(false);
    }
  }

  return (
    <main className="public-transfer-screen">
      <Card className="public-transfer-card">
        <Space direction="vertical" size={18} className="full-width">
          <div className="public-transfer-title">
            <CloudUploadOutlined />
            <div>
              <Title level={3}>文件快传</Title>
              <Text type="secondary">免登录临时传文件</Text>
            </div>
          </div>
          {error && <Alert type="error" showIcon message={error} />}
          {item && (
            <>
              <Descriptions bordered column={1} size="small">
                <Descriptions.Item label="文件名">{item.original_name}</Descriptions.Item>
                <Descriptions.Item label="类型">{transferKindLabel(item)}</Descriptions.Item>
                <Descriptions.Item label="大小">{formatBytes(item.size_bytes)}</Descriptions.Item>
                <Descriptions.Item label="来源">{item.source === 'public' ? '手机回传' : '电脑上传'}</Descriptions.Item>
                <Descriptions.Item label="过期时间">{formatTime(item.expires_at)}</Descriptions.Item>
              </Descriptions>
              <TransferPreview item={item} />
              <Button type="primary" size="large" block icon={<DownloadOutlined />} onClick={() => window.open(item.download_url, '_self')}>下载到手机</Button>
              <Alert type="info" showIcon message="也可以从手机上传文件回电脑，电脑端在文件快传列表刷新即可看到。" />
              <Dragger multiple={false} showUploadList={false} customRequest={uploadBack} disabled={uploading}>
                <p className="ant-upload-drag-icon"><InboxOutlined /></p>
                <p className="ant-upload-text">从手机选择文件回传</p>
                <p className="ant-upload-hint">支持图片、视频和常见文件，上传后会生成新的临时文件记录。</p>
              </Dragger>
              {returnedFile && (
                <Alert
                  type="success"
                  showIcon
                  message="回传成功"
                  description={`已上传：${returnedFile.original_name}，电脑端刷新“文件快传”列表即可下载。`}
                />
              )}
            </>
          )}
        </Space>
      </Card>
    </main>
  );
}

// 执行详情组件：展示一次测试任务的日志、断言、截图和错误信息。

