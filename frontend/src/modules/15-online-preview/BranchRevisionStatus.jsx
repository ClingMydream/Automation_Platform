import React, { useEffect, useState } from 'react';
import { Alert, Space, Tag, Typography } from 'antd';

const { Text } = Typography;

function formatTime(value) {
  if (!value) return '未知时间';
  return new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
  }).format(new Date(value));
}

export function BranchRevisionStatus({ client, branch, buildStatus, label = '代码状态' }) {
  const [revision, setRevision] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!branch) return;
    let active = true;
    setLoading(true);
    setError('');
    client.get(`/v1/online-preview/revision?branch=${encodeURIComponent(branch)}`)
      .then((data) => { if (active) setRevision(data); })
      .catch((requestError) => { if (active) setError(requestError.message); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [branch]);

  const builtBranch = buildStatus?.branch?.replace(/^origin\//, '');
  let marker = ['正在检查', 'processing'];
  if (!loading && error) marker = ['检查失败', 'red'];
  else if (!loading && builtBranch !== branch) marker = ['该分支尚未同步', 'orange'];
  else if (!loading && !buildStatus?.commit_sha) marker = ['等待构建记录', 'blue'];
  else if (!loading && revision?.sha === buildStatus?.commit_sha) marker = ['远程最新', 'green'];
  else if (!loading) marker = ['有新代码', 'gold'];

  return <Alert
    type={marker[1] === 'red' ? 'error' : 'info'}
    showIcon
    title={<Space wrap><Text strong>{label}</Text><Tag color={marker[1]}>{marker[0]}</Tag><Text code>{branch || '未选择分支'}</Text></Space>}
    description={error || (revision
      ? <Space direction="vertical" size={2}>
          <Text>最新更新人：{revision.author}{revision.email ? `（${revision.email}）` : ''}</Text>
          <Text>最新更新时间：{formatTime(revision.committed_at)}</Text>
          <Text>最新提交：<Text code>{revision.sha.slice(0, 8)}</Text> {revision.subject}</Text>
        </Space>
      : '选择分支后自动读取远程最新提交信息')}
  />;
}
