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

// 常改位置：轮询间隔、截图区域、步骤条展示、错误提示。
export function LiveRunWindow({ token, runId }) {
  const client = useMemo(() => apiClient(token), [token]);
  const [run, setRun] = useState(null);
  const [error, setError] = useState('');

  async function loadRun() {
    try {
      const data = await client.get(`/runs/${runId}`);
      setRun(data);
      setError('');
    } catch (err) {
      setError(err.message || '读取执行状态失败');
    }
  }

  useEffect(() => {
    loadRun();
    const timer = window.setInterval(loadRun, 800);
    return () => window.clearInterval(timer);
  }, [runId, token]);

  const report = run?.report || {};
  const events = report.events || [];
  const current = report.current_step && report.total_steps ? `${report.current_step}/${report.total_steps}` : '-';
  const isRunning = run && ['queued', 'running'].includes(run.status);

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
            <div className="step-pill" key={`${event.step}-${event.action}`}>
              <strong>{event.step}. {event.action}</strong>
              <span>{formatDuration(event.elapsed_ms)} · {event.title || event.url || '-'}</span>
            </div>
          ))}
        </div>
        {run?.error && <Alert className="live-error" type="error" showIcon message={run.error} />}
      </section>
    </main>
  );
}

// 应用总入口：负责登录态、权限菜单、全局数据加载和模块切换。

