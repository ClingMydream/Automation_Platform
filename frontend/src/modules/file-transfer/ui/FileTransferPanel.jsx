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
import { apiClient } from '../../../shared/apiClient';
import { runCodec } from '../../../shared/codec';
import { API_BASE, API_JSON_EXAMPLE, DEFAULT_UI_STEPS, UI_STEPS_EXAMPLE } from '../../../shared/constants';
import { downloadBlob, transferKind, transferKindLabel, TransferPreview } from '../../../shared/fileTransfer.jsx';
import { formatBytes, formatDuration, formatTime } from '../../../shared/formatters';
import { compareJsonValues, parseJsonInput, stableStringifyJson } from '../../../shared/jsonTools';
import { downloadReportHtml } from '../../../shared/reportExport';
import { JsonHelpCard } from '../../../shared/JsonHelpCard.jsx';
import { StatusTag } from '../../../shared/StatusTag.jsx';

const { Text, Title, Paragraph } = Typography;
const { TextArea } = Input;
const { Dragger } = Upload;

// 常改位置：过期时间、文件大小限制、文件预览与下载展示方式。
export function FileTransferPanel({ client }) {
  const [transfers, setTransfers] = useState([]);
  const [selected, setSelected] = useState(null);
  const [expiresHours, setExpiresHours] = useState(24);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const { message, modal } = AntApp.useApp();

  async function loadTransfers() {
    setLoading(true);
    try {
      const data = await client.get('/file-transfers');
      setTransfers(data);
      if (!selected && data.length > 0) setSelected(data[0]);
    } catch (err) {
      message.error(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadTransfers();
  }, []);

  async function uploadFile({ file, onSuccess, onError }) {
    setUploading(true);
    try {
      const body = new FormData();
      body.append('file', file);
      const item = await client.post(`/file-transfers?expires_hours=${expiresHours}`, body);
      setSelected(item);
      message.success('文件已上传，二维码已生成');
      await loadTransfers();
      onSuccess?.(item);
    } catch (err) {
      message.error(err.message);
      onError?.(err);
    } finally {
      setUploading(false);
    }
  }

  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
      message.success('链接已复制');
    } catch {
      message.warning('复制失败，请手动复制链接');
    }
  }

  function remove(item) {
    modal.confirm({
      title: `删除临时文件「${item.original_name}」？`,
      content: '删除后二维码和下载链接会立即失效。',
      okText: '删除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: async () => {
        await client.delete(`/file-transfers/${item.id}`);
        message.success('临时文件已删除');
        if (selected?.id === item.id) setSelected(null);
        await loadTransfers();
      },
    });
  }

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={9}>
        <Card title="上传临时文件">
          <Space direction="vertical" size={16} className="full-width">
            <Alert type="info" showIcon message="文件默认临时保存，过期后会自动清理。手机扫码页面免登录，请只分享给可信设备。" />
            <Select
              className="full-width"
              value={expiresHours}
              onChange={setExpiresHours}
              options={[
                { value: 1, label: '1 小时后过期' },
                { value: 6, label: '6 小时后过期' },
                { value: 24, label: '24 小时后过期' },
                { value: 72, label: '3 天后过期' },
                { value: 168, label: '7 天后过期' },
              ]}
            />
            <Dragger multiple={false} showUploadList={false} customRequest={uploadFile} disabled={uploading}>
              <p className="ant-upload-drag-icon"><InboxOutlined /></p>
              <p className="ant-upload-text">点击或拖拽文件到这里上传</p>
              <p className="ant-upload-hint">支持图片、视频、压缩包和常见文档，单文件最大 1GB；手机扫码可预览图片/视频，也可直接下载。</p>
            </Dragger>
          </Space>
        </Card>
        {selected && (
          <Card className="share-card" title="扫码下载" extra={<Tag color={selected.source === 'public' ? 'purple' : 'green'}>{selected.source === 'public' ? '手机回传' : '电脑上传'}</Tag>}>
            <Space direction="vertical" size={14} className="full-width">
              <div className="qr-wrap"><QRCode value={selected.share_url} size={196} /></div>
              <Descriptions size="small" column={1}>
                <Descriptions.Item label="文件名">{selected.original_name}</Descriptions.Item>
                <Descriptions.Item label="类型">{transferKindLabel(selected)}</Descriptions.Item>
                <Descriptions.Item label="大小">{formatBytes(selected.size_bytes)}</Descriptions.Item>
                <Descriptions.Item label="过期时间">{formatTime(selected.expires_at)}</Descriptions.Item>
              </Descriptions>
              <TransferPreview item={selected} />
              <Space wrap>
                <Button type="primary" icon={<DownloadOutlined />} onClick={() => window.open(selected.download_url, '_blank')}>下载</Button>
                <Button icon={<CopyOutlined />} onClick={() => copyText(selected.share_url)}>复制扫码链接</Button>
              </Space>
            </Space>
          </Card>
        )}
      </Col>
      <Col xs={24} xl={15}>
        <Card title="临时文件列表" extra={<Button icon={<ReloadOutlined />} loading={loading} onClick={loadTransfers}>刷新</Button>}>
          <Table
            rowKey="id"
            dataSource={transfers}
            loading={loading}
            pagination={{ pageSize: 8 }}
            scroll={{ x: 940 }}
            columns={[
              { title: 'ID', dataIndex: 'id', width: 70 },
              { title: '文件名', dataIndex: 'original_name', ellipsis: true },
              { title: '类型', width: 90, render: (_, record) => <Tag color={transferKind(record) === 'video' ? 'volcano' : transferKind(record) === 'image' ? 'cyan' : 'default'}>{transferKindLabel(record)}</Tag> },
              { title: '大小', dataIndex: 'size_bytes', width: 110, render: formatBytes },
              { title: '来源', dataIndex: 'source', width: 100, render: (value) => <Tag color={value === 'public' ? 'purple' : 'green'}>{value === 'public' ? '手机回传' : '电脑上传'}</Tag> },
              { title: '创建时间', dataIndex: 'created_at', width: 180, render: formatTime },
              { title: '过期时间', dataIndex: 'expires_at', width: 180, render: formatTime },
              {
                title: '操作',
                width: 230,
                fixed: 'right',
                render: (_, record) => (
                  <Space className="table-actions transfer-actions" size={6} wrap>
                    <Button icon={<EyeOutlined />} onClick={() => setSelected(record)}>二维码</Button>
                    <Button icon={<DownloadOutlined />} onClick={() => window.open(record.download_url, '_blank')}>下载</Button>
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

// 手机扫码公开页面：不进入后台菜单，只根据 token 访问临时文件。

