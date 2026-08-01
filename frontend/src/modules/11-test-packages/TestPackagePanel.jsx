import React, { useEffect, useState } from 'react';
import { Alert, Button, Card, Col, Descriptions, Form, Input, QRCode, Row, Space, Tag, Typography, Upload, message } from 'antd';
import { CopyOutlined, DownloadOutlined, InboxOutlined, ReloadOutlined } from '@ant-design/icons';
import { formatBytes, formatTime } from '../../shared/formatters';
import './test-package.css';

const { Dragger } = Upload;
const { Paragraph, Text, Title } = Typography;

export function TestPackagePanel({ client }) {
  const [item, setItem] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [version, setVersion] = useState('');
  const [notes, setNotes] = useState('');
  const stableUrl = item?.share_url || `${window.location.origin}/?testPackage=latest`;

  async function load() {
    try { setItem(await client.get('/test-packages/latest')); }
    catch (error) { message.error(error.message); }
  }
  useEffect(() => { load(); }, []);

  async function upload({ file, onSuccess, onError }) {
    setUploading(true);
    try {
      const body = new FormData();
      body.append('file', file);
      body.append('version', version);
      body.append('notes', notes);
      const result = await client.post('/test-packages/latest', body);
      setItem(result);
      message.success('最新测试包已更新，原二维码保持不变');
      onSuccess?.(result);
    } catch (error) {
      message.error(error.message); onError?.(error);
    } finally { setUploading(false); }
  }

  async function copyLink() {
    await navigator.clipboard.writeText(stableUrl);
    message.success('固定下载地址已复制');
  }

  return <div className="test-package-page">
    <div className="package-heading"><div><Text>固定二维码 · 自动获取最新版</Text><Title level={2}>📦 测试包安装</Title><Paragraph type="secondary">电脑上传新包后会自动覆盖旧包，二维码和扫码地址始终不变。</Paragraph></div><Button icon={<ReloadOutlined />} onClick={load}>刷新</Button></div>
    <Row gutter={[16, 16]} align="stretch">
      <Col xs={24} xl={14}><Card title="上传最新测试包" className="package-card">
        <Alert type="info" showIcon title="支持 APK、IPA、AAB 和 ZIP，单个文件最大 1GB。上传成功后旧包才会被删除。" />
        <Form layout="vertical" className="package-form"><Row gutter={12}><Col xs={24} md={8}><Form.Item label="版本号（可选）"><Input value={version} onChange={(event) => setVersion(event.target.value)} placeholder="例如 2.3.1" /></Form.Item></Col><Col xs={24} md={16}><Form.Item label="更新说明（可选）"><Input value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="例如：修复登录问题" /></Form.Item></Col></Row></Form>
        <Dragger accept=".apk,.ipa,.aab,.zip" multiple={false} showUploadList={false} customRequest={upload} disabled={uploading}>
          <p className="ant-upload-drag-icon"><InboxOutlined /></p><p className="ant-upload-text">点击或拖拽测试包到这里</p><p className="ant-upload-hint">每次上传都会更新“最新版”，固定二维码不会变化</p>
        </Dragger>
        {item && <Descriptions bordered size="small" column={1} className="package-details"><Descriptions.Item label="当前文件">{item.original_name}</Descriptions.Item><Descriptions.Item label="版本">{item.version || '未填写'}</Descriptions.Item><Descriptions.Item label="大小">{formatBytes(item.size_bytes)}</Descriptions.Item><Descriptions.Item label="更新时间">{formatTime(item.updated_at)}</Descriptions.Item><Descriptions.Item label="累计上传">{item.upload_count} 次</Descriptions.Item><Descriptions.Item label="更新说明">{item.notes || '无'}</Descriptions.Item></Descriptions>}
      </Card></Col>
      <Col xs={24} xl={10}><Card title="测试机扫码安装" className="package-card qr-card" extra={<Tag color="green">二维码永久不变</Tag>}>
        <div className="package-qr"><QRCode value={stableUrl} size={220} /></div>
        <Paragraph>测试机扫码后会进入中文下载页，并自动下载服务器上的最新测试包。</Paragraph>
        {!item && <Alert type="warning" showIcon title="当前还没有测试包，二维码可以先保存，上传后立即可用。" />}
        <Space wrap><Button icon={<CopyOutlined />} onClick={copyLink}>复制固定链接</Button>{item && <Button type="primary" icon={<DownloadOutlined />} onClick={() => window.open(item.download_url, '_blank')}>下载当前包</Button>}</Space>
      </Card></Col>
    </Row>
  </div>;
}
