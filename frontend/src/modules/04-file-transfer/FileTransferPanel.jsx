// File purpose: File transfer admin page. Upload files, show QR links, and manage temporary records.
// How to change: edit UI text/layout in this file; move reusable logic into shared helpers or the module feature file.

import React, { useEffect, useState } from 'react';
import { Alert, App as AntApp, Button, Card, Col, Descriptions, QRCode, Row, Select, Space, Table, Tag, Upload } from 'antd';
import { CopyOutlined, DeleteOutlined, DownloadOutlined, EyeOutlined, InboxOutlined, ReloadOutlined } from '@ant-design/icons';
import { transferKind, transferKindLabel, TransferPreview } from '../../shared/fileTransfer.jsx';
import { formatBytes, formatTime } from '../../shared/formatters';

const { Dragger } = Upload;

// File transfer admin page: uploads temporary files and manages QR download links.
export function FileTransferPanel({ client }) {
  // State block: values here control loading, selection, form state, and visible page data.
  const [transfers, setTransfers] = useState([]);
  const [selected, setSelected] = useState(null);
  const [expiresHours, setExpiresHours] = useState(24);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const { message, modal } = AntApp.useApp();

  // Load temporary file transfer records from the backend.
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

  // Effect block: code here reacts to token, route, or polling changes.
  useEffect(() => {
    loadTransfers();
  }, []);

  // Upload one admin-side temporary file and refresh the transfer list.
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

  // Copy a share URL to the clipboard.
  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
      message.success('链接已复制');
    } catch {
      message.warning('复制失败，请手动复制链接');
    }
  }

  // Confirm deletion, call the delete API, and refresh the list.
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

  // Render block: JSX below describes what the user sees on this page.
  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={9}>
        <Card title="上传临时文件">
          <Space orientation="vertical" size={16} className="full-width">
            <Alert type="info" showIcon title="文件默认临时保存，过期后会自动清理。手机扫码页面免登录，请只分享给可信设备。" />
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
            <Space orientation="vertical" size={14} className="full-width">
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

// File transfer module: manages desktop uploads, QR links, previews, and temporary file records.
