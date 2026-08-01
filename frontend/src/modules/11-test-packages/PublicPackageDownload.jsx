import React, { useEffect, useState } from 'react';
import { Alert, Button, Card, Descriptions, Progress, Space, Typography } from 'antd';
import { DownloadOutlined } from '@ant-design/icons';
import { apiClient } from '../../shared/apiClient';
import { formatBytes, formatTime } from '../../shared/formatters';
import './test-package.css';

const { Text, Title } = Typography;

export function PublicPackageDownload() {
  const [item, setItem] = useState(null);
  const [error, setError] = useState('');
  const [seconds, setSeconds] = useState(2);

  useEffect(() => {
    apiClient().get('/test-packages/public/latest').then(setItem).catch((reason) => setError(reason.message));
  }, []);
  useEffect(() => {
    if (!item) return undefined;
    const timer = window.setInterval(() => setSeconds((value) => Math.max(0, value - 1)), 1000);
    const download = window.setTimeout(() => window.location.assign(`${item.download_url}?t=${Date.now()}`), 2000);
    return () => { window.clearInterval(timer); window.clearTimeout(download); };
  }, [item]);

  return <main className="public-package-screen"><Card className="public-package-card"><Space orientation="vertical" size={18} className="full-width"><div className="public-package-title"><span>📦</span><div><Title level={3}>测试包下载</Title><Text type="secondary">自动获取服务器上的最新版本</Text></div></div>{error && <Alert type="error" showIcon title={error} />}{item && <><Alert type="success" showIcon title={`已找到最新测试包，${seconds} 秒后自动下载`} /><Progress percent={(2-seconds)*50} showInfo={false} /><Descriptions bordered column={1} size="small"><Descriptions.Item label="文件名">{item.original_name}</Descriptions.Item><Descriptions.Item label="版本">{item.version || '未填写'}</Descriptions.Item><Descriptions.Item label="大小">{formatBytes(item.size_bytes)}</Descriptions.Item><Descriptions.Item label="更新时间">{formatTime(item.updated_at)}</Descriptions.Item><Descriptions.Item label="更新说明">{item.notes || '无'}</Descriptions.Item></Descriptions><Button type="primary" size="large" block icon={<DownloadOutlined />} onClick={() => window.location.assign(`${item.download_url}?t=${Date.now()}`)}>立即下载</Button><Alert type="info" showIcon title="Android 下载 APK 后请按系统提示安装；iOS 的 IPA 是否能直接安装取决于签名和企业分发配置。" /></>}</Space></Card></main>;
}
