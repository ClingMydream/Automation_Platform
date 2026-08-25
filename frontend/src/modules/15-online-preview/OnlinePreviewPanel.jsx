import React, { useEffect, useState } from 'react';
import { Alert, Button, Card, Descriptions, Select, Space, Tag, Typography, message } from 'antd';
import { ExportOutlined, ReloadOutlined, SyncOutlined } from '@ant-design/icons';
import { BranchRevisionStatus } from './BranchRevisionStatus.jsx';

const { Paragraph, Text, Title } = Typography;
const PREVIEW_URL = '/emote-preview/';

const STATUS_LABELS = {
  SUCCESS: ['成功', 'green'],
  FAILURE: ['失败', 'red'],
  ABORTED: ['已中止', 'orange'],
  NOT_BUILT: ['尚未同步', 'default'],
};

export function OnlinePreviewPanel({ client }) {
  const [branches, setBranches] = useState([]);
  const [branch, setBranch] = useState('dev-20260811-1.9.1');
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const [branchRows, currentStatus] = await Promise.all([
        client.get('/v1/online-preview/branches'),
        client.get('/v1/online-preview/status'),
      ]);
      setBranches(branchRows);
      setStatus(currentStatus);
      if (currentStatus.branch) setBranch(currentStatus.branch.replace(/^origin\//, ''));
    } catch (error) {
      message.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);
  useEffect(() => {
    if (!status?.building && !syncing) return undefined;
    const timer = window.setInterval(async () => {
      try {
        const nextStatus = await client.get('/v1/online-preview/status');
        setStatus(nextStatus);
        if (!nextStatus.building && nextStatus.result) setSyncing(false);
      } catch { /* 下一次轮询会继续读取状态 */ }
    }, 4000);
    return () => window.clearInterval(timer);
  }, [status?.building, syncing]);

  const synchronize = async () => {
    if (!branch) return message.warning('请先选择分支');
    setSyncing(true);
    try {
      await client.post('/v1/online-preview/sync', { branch });
      message.success(`已提交 ${branch} 分支同步任务`);
      window.setTimeout(load, 1500);
    } catch (error) {
      setSyncing(false);
      message.error(error.message);
    }
  };

  const statusValue = status?.building ? ['同步中', 'processing'] : (STATUS_LABELS[status?.result] || [status?.result || '未知', 'default']);
  return <div className="online-preview-panel">
    <section className="effect-studio__hero"><div><span>Emote 网页测试环境</span><Title level={2}>📱 在线预览</Title><Paragraph>选择远程分支并同步最新代码，整个过程只读拉取，不会提交或推送项目代码。</Paragraph></div><div>🔄</div></section>
    <Card title="分支同步" extra={<Button icon={<ReloadOutlined />} loading={loading} onClick={load}>刷新状态</Button>}>
      <Space orientation="vertical" size={18} style={{ width: '100%' }}>
        <Alert type="info" showIcon title="同步会重新构建网页预览" description="构建期间旧版本继续可用；任务成功后，刷新预览窗口即可查看新版本。" />
        <Space wrap>
          <Select
            showSearch
            value={branch}
            style={{ width: 360, maxWidth: '100%' }}
            placeholder="选择远程分支"
            options={branches.map((value) => ({ label: value, value }))}
            onChange={setBranch}
            optionFilterProp="label"
            loading={loading}
          />
          <Button type="primary" icon={<SyncOutlined spin={syncing || status?.building} />} loading={syncing || status?.building} onClick={synchronize}>同步最新代码</Button>
          <Button icon={<ExportOutlined />} onClick={() => window.open(PREVIEW_URL, 'cling-emote-preview', 'noopener,noreferrer')}>打开预览</Button>
        </Space>
        <BranchRevisionStatus client={client} branch={branch} buildStatus={status} label="预览代码状态" />
        <Descriptions bordered size="small" column={{ xs: 1, md: 2 }}>
          <Descriptions.Item label="当前状态"><Tag color={statusValue[1]}>{statusValue[0]}</Tag></Descriptions.Item>
          <Descriptions.Item label="构建编号">{status?.number ? `#${status.number}` : '暂无'}</Descriptions.Item>
          <Descriptions.Item label="预览分支">{status?.branch || '暂无'}</Descriptions.Item>
          <Descriptions.Item label="说明"><Text>{status?.description || '选择分支后点击同步'}</Text></Descriptions.Item>
        </Descriptions>
      </Space>
    </Card>
  </div>;
}
