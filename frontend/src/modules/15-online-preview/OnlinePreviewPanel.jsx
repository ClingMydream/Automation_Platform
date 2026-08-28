import React, { useEffect, useState } from 'react';
import { Alert, Button, Card, Descriptions, Select, Space, Steps, Tag, Typography, message } from 'antd';
import { CheckCircleOutlined, ExportOutlined, MobileOutlined, ReloadOutlined, SafetyCertificateOutlined, SyncOutlined } from '@ant-design/icons';
import { BranchRevisionStatus } from './BranchRevisionStatus.jsx';

const { Paragraph, Text, Title } = Typography;
const PREVIEW_URL = '/emote-preview/';
const STATUS_LABELS = { SUCCESS: ['构建成功', 'green'], FAILURE: ['构建失败', 'red'], ABORTED: ['已中止', 'orange'], NOT_BUILT: ['尚未同步', 'default'] };
const STAGE_LABELS = { '只读拉取代码': '读取远程代码', '安装依赖': '安装依赖', '兼容 Linux 文件名': '检查资源兼容性', '构建预览页面': '生成网页预览', '适配预览子路径': '适配预览地址', '发布在线预览': '发布到线上预览' };

function shortSha(value) { return value ? value.slice(0, 8) : '暂无'; }
function stageState(stage) {
  if (stage.status === 'SUCCESS') return 'finish';
  if (stage.status === 'IN_PROGRESS' || stage.status === 'PAUSED_PENDING_INPUT') return 'process';
  if (stage.status === 'FAILED' || stage.status === 'ABORTED') return 'error';
  return 'wait';
}

export function OnlinePreviewPanel({ client }) {
  const [branches, setBranches] = useState([]);
  const [branch, setBranch] = useState('dev-20260811-1.9.1');
  const [status, setStatus] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [checking, setChecking] = useState(false);

  const loadStatus = async () => {
    const nextStatus = await client.get('/v1/online-preview/status');
    setStatus(nextStatus);
    return nextStatus;
  };
  const compare = async (showMessage = false) => {
    if (!branch) return null;
    setChecking(true);
    try {
      const result = await client.get(`/v1/online-preview/comparison?branch=${encodeURIComponent(branch)}`);
      setComparison(result);
      if (showMessage) message[result.matches ? 'success' : 'warning'](result.message);
      return result;
    } catch (error) {
      if (showMessage) message.error(error.message);
      return null;
    } finally { setChecking(false); }
  };
  const load = async () => {
    setLoading(true);
    try {
      const [branchRows, currentStatus] = await Promise.all([client.get('/v1/online-preview/branches'), loadStatus()]);
      setBranches(branchRows);
      if (currentStatus.branch) setBranch(currentStatus.branch.replace(/^origin\//, ''));
    } catch (error) { message.error(error.message); } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);
  useEffect(() => { compare(); }, [branch]);
  useEffect(() => {
    if (!status?.building && !syncing) return undefined;
    const timer = window.setInterval(async () => {
      try {
        const nextStatus = await loadStatus();
        if (!nextStatus.building && nextStatus.result) {
          setSyncing(false);
          if (nextStatus.result === 'SUCCESS') compare(true);
        }
      } catch { /* 下一轮会重试 */ }
    }, 3500);
    return () => window.clearInterval(timer);
  }, [status?.building, syncing, branch]);
  const synchronize = async () => {
    if (!branch) return message.warning('请先选择分支');
    setSyncing(true); setComparison(null);
    try {
      const task = await client.post('/v1/online-preview/sync', { branch });
      message.success(`${branch} 已进入构建队列${task.queue_id ? `（队列 #${task.queue_id}）` : ''}`);
      window.setTimeout(loadStatus, 1200);
    } catch (error) { setSyncing(false); message.error(error.message); }
  };
  const statusValue = status?.building ? ['正在构建', 'processing'] : (STATUS_LABELS[status?.result] || [status?.result || '读取中', 'default']);
  const deployed = comparison?.deployed || status?.deployed_revision;
  const isMatch = comparison?.matches;
  const stages = status?.stages || [];
  return <div className="online-preview-panel">
    <section className="effect-studio__hero"><div><span>Emote 网页测试环境</span><Title level={2}>📱 在线预览</Title><Paragraph>同步过程、构建阶段与线上实际版本均可核验。系统仅以只读方式拉取代码，不会提交或推送项目代码。</Paragraph></div><div>🔄</div></section>
    <Card title="分支同步与版本核验" extra={<Button icon={<ReloadOutlined />} loading={loading} onClick={load}>刷新状态</Button>}>
      <Space orientation="vertical" size={18} style={{ width: '100%' }}>
        <Alert type="info" showIcon title="不再黑盒构建" description="同步后可看到当前构建阶段；构建成功后会自动比较远程最新提交与线上实际服务的提交，只有两者一致才会显示“已确认一致”。" />
        <Space wrap>
          <Select showSearch value={branch} style={{ width: 360, maxWidth: '100%' }} placeholder="选择远程分支" options={branches.map((value) => ({ label: value, value }))} onChange={setBranch} optionFilterProp="label" loading={loading} />
          <Button type="primary" icon={<SyncOutlined spin={syncing || status?.building} />} loading={syncing || status?.building} onClick={synchronize}>同步最新代码</Button>
          <Button icon={<SafetyCertificateOutlined />} loading={checking} onClick={() => compare(true)}>比对线上版本</Button>
          <Button icon={<MobileOutlined />} onClick={() => window.open('/emote-mobile-preview', 'cling-emote-mobile-preview', 'noopener,noreferrer')}>手机应用预览</Button>
          <Button icon={<ExportOutlined />} onClick={() => window.open(PREVIEW_URL, 'cling-emote-preview', 'noopener,noreferrer')}>网页调试模式</Button>
        </Space>
        <Descriptions bordered size="small" column={{ xs: 1, md: 2 }}>
          <Descriptions.Item label="构建状态"><Tag color={statusValue[1]}>{statusValue[0]}</Tag></Descriptions.Item>
          <Descriptions.Item label="构建编号">{status?.number ? `#${status.number}` : '暂无'}</Descriptions.Item>
          <Descriptions.Item label="本次构建分支">{status?.branch || '暂无'}</Descriptions.Item>
          <Descriptions.Item label="构建提交"><Text code>{shortSha(status?.commit_sha)}</Text></Descriptions.Item>
        </Descriptions>
        {stages.length > 0 && <Card size="small" title="构建进度"><Steps size="small" responsive items={stages.map((stage) => ({ title: STAGE_LABELS[stage.name] || stage.name, status: stageState(stage), description: stage.status === 'IN_PROGRESS' ? '正在执行' : undefined }))} /></Card>}
        <Alert type={isMatch ? 'success' : comparison ? 'warning' : 'info'} showIcon icon={isMatch ? <CheckCircleOutlined /> : undefined} title={comparison?.message || '正在读取线上预览版本'} description={<Space direction="vertical" size={2}><Text>远程最新：<Text code>{shortSha(comparison?.remote?.sha)}</Text>　线上实际：<Text code>{shortSha(deployed?.sha)}</Text></Text><Text>线上分支：{deployed?.branch || '尚未检测到版本清单'}　发布构建：{deployed?.build_number ? `#${deployed.build_number}` : '暂无'}</Text></Space>} />
        <BranchRevisionStatus client={client} branch={branch} buildStatus={status} label="远程代码状态" />
      </Space>
    </Card>
  </div>;
}
