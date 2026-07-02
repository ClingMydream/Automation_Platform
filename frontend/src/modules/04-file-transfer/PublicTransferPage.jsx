// File purpose: Public mobile transfer page. Download shared files or upload return files without login.
// How to change: edit UI text/layout in this file; move reusable logic into shared helpers or the module feature file.

import React, { useEffect, useMemo, useState } from 'react';
import { Alert, App as AntApp, Button, Card, Descriptions, Space, Typography, Upload } from 'antd';
import { CloudUploadOutlined, DownloadOutlined, InboxOutlined } from '@ant-design/icons';
import { apiClient } from '../../shared/apiClient';
import { transferKindLabel, TransferPreview } from '../../shared/fileTransfer.jsx';
import { formatBytes, formatTime } from '../../shared/formatters';

const { Text, Title } = Typography;
const { Dragger } = Upload;

// Public mobile transfer page: downloads a shared file or uploads a return file.
export function PublicTransferPage({ token }) {
  const client = useMemo(() => apiClient(), []);
  // State block: values here control loading, selection, form state, and visible page data.
  const [item, setItem] = useState(null);
  const [error, setError] = useState('');
  const [uploading, setUploading] = useState(false);
  const [returnedFile, setReturnedFile] = useState(null);
  const { message } = AntApp.useApp();

  // Load public transfer metadata for the scanned token.
  async function loadTransfer() {
    try {
      const data = await client.get(`/file-transfers/public/${token}`);
      setItem(data);
      setError('');
    } catch (err) {
      setError(err.message);
    }
  }

  // Effect block: code here reacts to token, route, or polling changes.
  useEffect(() => {
    loadTransfer();
  }, [token]);

  // Upload a mobile-side return file through the public token.
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

  // Render block: JSX below describes what the user sees on this page.
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

// Public transfer module: lets mobile devices download shared files or upload return files by token.
