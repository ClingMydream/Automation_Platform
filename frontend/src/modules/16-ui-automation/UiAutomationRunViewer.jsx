import React, { useEffect, useMemo, useState } from 'react';
import { Alert, Badge, Button, Empty, Progress, Space, Spin, Tag, Timeline, Typography } from 'antd';
import { ArtifactViewer } from './UiAutomationPage.jsx';
import './ui-automation.css';

const { Text, Title } = Typography;
const STATUS = { queued: ['等待 Runner', 'default'], running: ['脚本执行中', 'processing'], passed: ['执行通过', 'success'], failed: ['执行失败', 'error'], interrupted: ['执行中断', 'warning'] };

export function UiAutomationRunViewer({ client, runId }) {
  const [run, setRun] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => {
    if (runId === 'waiting') return undefined;
    let active = true;
    const read = async () => {
      try { const value = await client.get(`/v1/ui-automation/runs/${runId}`); if (active) { setRun(value); setError(''); } }
      catch (reason) { if (active) setError(reason.message); }
    };
    read(); const timer = window.setInterval(read, 1500);
    return () => { active = false; window.clearInterval(timer); };
  }, [runId]);

  const latestScreenshot = useMemo(() => [...(run?.artifacts || [])].reverse().find((item) => item.kind === 'screenshot'), [run?.artifacts]);
  const failure = run?.result_summary?.failure;
  const [statusText, badge] = STATUS[run?.status] || STATUS.queued;
  if (runId === 'waiting' || (!run && !error)) return <main className="ui-run-viewer ui-run-viewer--waiting"><Spin size="large" /><Title level={3}>正在创建自动化任务</Title><Text type="secondary">脚本准备完成后，这里会显示 Emote 页面执行画面。</Text></main>;
  if (error) return <main className="ui-run-viewer"><Alert type="error" showIcon title="无法读取执行任务" description={error} /></main>;
  return <main className="ui-run-viewer">
    <header><div><Text>Emote · Playwright 实时执行窗口</Text><Title level={3}>脚本任务 #{run.id}</Title></div><Space><Tag color="blue">{run.viewport === 'mobile' ? '390 × 844' : '1440 × 900'}</Tag><Badge status={badge} text={statusText} /></Space></header>
    <section className="ui-run-viewer__status"><div><b>{run.current_step || '等待 Runner 接收任务'}</b><Text type="secondary">分支 {run.branch} · {run.commit_sha?.slice(0, 10) || '-'}</Text></div><Progress percent={run.progress || 0} status={run.status === 'failed' ? 'exception' : run.status === 'passed' ? 'success' : 'active'} /></section>
    <div className="ui-run-viewer__grid">
      <section className="ui-run-viewer__screen"><div className="ui-run-viewer__browser"><i /><i /><i /><span>{run.current_step || 'Emote 自动化页面'}</span></div><ArtifactViewer client={client} artifact={latestScreenshot} /></section>
      <aside>
        {failure && <Alert type="error" showIcon title={`${failure.case_name} · 第 ${failure.step_index} 步`} description={<div className="ui-auto-failure"><b>{failure.reason}</b><span>执行动作：{failure.action}</span>{failure.locator && <span>目标元素：{failure.locator_type} = {failure.locator}</span>}<span>处理建议：{failure.suggestion}</span><details><summary>技术详情</summary><pre>{failure.technical_detail}</pre></details></div>} />}
        {!run.result_summary?.timeline?.length ? <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="等待第一步执行" /> : <Timeline items={run.result_summary.timeline.map((step) => ({ color: step.status === 'failed' ? 'red' : 'green', children: <div className="ui-run-viewer__step"><b>{step.case_name || step.name}</b><span>第 {step.step_index || '-'} 步 · {step.action || ''}</span><small>{step.duration_ms} ms</small></div> }))} />}
        {(run.status === 'passed' || run.status === 'failed') && <Button type="primary" block onClick={() => window.close()}>关闭执行窗口</Button>}
      </aside>
    </div>
  </main>;
}
