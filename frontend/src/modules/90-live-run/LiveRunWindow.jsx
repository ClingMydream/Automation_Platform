// File purpose: Live UI run window. Poll and display current automation progress, screenshots, recordings, and evidence attachments.
// How to change: edit UI text/layout in this file; move reusable logic into shared helpers or the module feature file.

import React, { useEffect, useMemo, useState } from 'react';
import { Alert, Button, Collapse, Space, Tag } from 'antd';
import { DownloadOutlined, PaperClipOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { apiClient } from '../../shared/apiClient';
import { formatBytes, formatDuration } from '../../shared/formatters';
import { downloadAttachment, listResultAttachments } from '../03-result-center/resultCenterFeature.js';

// Live run window: shows UI automation progress, current step, latest screenshot, and final recording.
export function LiveRunWindow({ token, runId }) {
  const client = useMemo(() => apiClient(token), [token]);
  // State block: values here control the live run display and downloadable evidence.
  const [run, setRun] = useState(null);
  const [attachments, setAttachments] = useState([]);
  const [error, setError] = useState('');

  // Reload live run status for the execution window.
  async function loadRun() {
    try {
      const data = await client.get(`/runs/${runId}`);
      setRun(data);
      setError('');
    } catch (err) {
      setError(err.message || '读取执行状态失败');
    }
  }

  // Download one persisted recording or evidence attachment.
  async function handleDownload(attachment) {
    try {
      await downloadAttachment(client, attachment);
    } catch (err) {
      setError(err.message || '下载录屏附件失败');
    }
  }

  // Effect block: code here reacts to token, route, or polling changes.
  useEffect(() => {
    loadRun();
    const timer = window.setInterval(loadRun, 800);
    return () => window.clearInterval(timer);
  }, [runId, token]);

  // Load result attachments after the worker has persisted the result-center row.
  useEffect(() => {
    if (!run?.result_id) {
      setAttachments([]);
      return undefined;
    }
    let ignore = false;
    async function loadAttachments() {
      try {
        const rows = await listResultAttachments(client, run.result_id);
        if (!ignore) setAttachments(rows);
      } catch (err) {
        if (!ignore) setError(err.message || '读取录屏附件失败');
      }
    }
    loadAttachments();
    return () => { ignore = true; };
  }, [client, run?.result_id]);

  const report = run?.report || {};
  const events = report.events || [];
  const failedEvent = events.find((event) => event.status === 'failed');
  const current = report.current_step && report.total_steps ? `${report.current_step}/${report.total_steps}` : '-';
  const isRunning = run && ['queued', 'running'].includes(run.status);
  const recordingAttachments = attachments.filter((item) => item.attachment_type === 'recording');

  // Render block: JSX below draws the live browser frame, run stats, timeline, and recording evidence.
  return (
    <main className="live-shell">
      <header className="live-header">
        <div>
          <h1>UI 自动化执行窗口</h1>
          <p>任务 #{runId} {run ? `· ${run.status}` : '· 正在连接'}</p>
        </div>
        <div className="live-stats">
          <div><span>当前步骤</span><strong>{current}</strong></div>
          <div><span>当前动作</span><strong>{report.current_action || '-'}</strong></div>
          <div><span>耗时</span><strong>{formatDuration(run?.duration_ms)}</strong></div>
        </div>
      </header>

      {error && <Alert type="error" showIcon message={error} />}

      {(failedEvent || report.error) && (
        <Alert
          className="live-error"
          type="error"
          showIcon
          message={failedEvent ? `第 ${failedEvent.step} 步执行失败：${failedEvent.action}` : 'UI 自动化执行失败'}
          description={failedEvent?.error || report.error}
        />
      )}

      {report.failure_advice?.length > 0 && (
        <section className="live-diagnosis">
          <h2>失败定位建议</h2>
          <ul>{report.failure_advice.map((item) => <li key={item}>{item}</li>)}</ul>
        </section>
      )}

      <section className="live-stage">
        <div className="browser-chrome">
          <span></span><span></span><span></span>
          <strong>{events[events.length - 1]?.url || 'about:blank'}</strong>
        </div>
        <div className="browser-screen">
          {report.latest_screenshot ? (
            <img src={report.latest_screenshot} alt="UI 自动化当前页面" />
          ) : (
            <div className="live-empty">
              <ThunderboltOutlined />
              <strong>{isRunning ? '浏览器正在启动，等待第一张画面...' : '暂无页面画面'}</strong>
            </div>
          )}
          {isRunning && <div className="live-running">正在执行</div>}
        </div>
      </section>

      <section className="live-steps">
        <h2>执行过程</h2>
        <div className="step-strip">
          {events.length === 0 && <span className="hint">等待 worker 开始执行步骤...</span>}
          {events.map((event) => (
            <div className={`step-pill step-pill-${event.status || 'running'}`} key={`${event.step}-${event.action}`}>
              <strong>
                {event.step}. {event.action}
                <Tag color={event.status === 'failed' ? 'error' : 'success'}>{event.status === 'failed' ? '失败' : '通过'}</Tag>
              </strong>
              <span>{formatDuration(event.elapsed_ms)} · {event.target || event.title || event.url || '-'}</span>
              {event.error && <em>{event.error}</em>}
            </div>
          ))}
        </div>
        {run?.error && <Alert className="live-error" type="error" showIcon message={run.error} />}
      </section>

      {(report.recording_url || report.recording_error || recordingAttachments.length > 0) && (
        <section className="live-recording">
          <h2>执行录屏</h2>
          {report.recording_url ? (
            <video controls preload="metadata" src={report.recording_url}>
              当前浏览器不支持播放 UI 自动化录屏。
            </video>
          ) : report.recording_error ? (
            <Alert type="warning" showIcon message={report.recording_error} />
          ) : null}
          {recordingAttachments.length > 0 && (
            <div className="recording-attachments">
              <Space direction="vertical" size={8}>
                {recordingAttachments.map((item) => (
                  <Button key={item.id} icon={<PaperClipOutlined />} onClick={() => handleDownload(item)}>
                    下载录屏附件：{item.original_name}（{formatBytes(item.size_bytes)}）
                    <DownloadOutlined />
                  </Button>
                ))}
              </Space>
            </div>
          )}
        </section>
      )}

      {(report.dom_snapshot || report.dom_snapshot_error) && (
        <section className="live-diagnosis">
          <h2>DOM 快照</h2>
          {report.dom_snapshot ? (
            <Collapse
              items={[{ key: 'dom', label: '查看失败时页面 HTML', children: <pre className="dom-snapshot">{report.dom_snapshot}</pre> }]}
            />
          ) : (
            <Alert type="warning" showIcon message={report.dom_snapshot_error} />
          )}
        </section>
      )}
    </main>
  );
}

// Live run module: shows UI automation progress in a separate execution window.
