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
import { apiClient } from '../../shared/apiClient';
import { runCodec } from '../../shared/codec';
import { API_BASE, API_JSON_EXAMPLE, DEFAULT_UI_STEPS, UI_STEPS_EXAMPLE } from '../../shared/constants';
import { downloadBlob, transferKind, transferKindLabel, TransferPreview } from '../../shared/fileTransfer.jsx';
import { formatBytes, formatDuration, formatTime } from '../../shared/formatters';
import { compareJsonValues, parseJsonInput, stableStringifyJson } from '../../shared/jsonTools';
import { downloadReportHtml } from '../../shared/reportExport';
import { JsonHelpCard } from '../../shared/JsonHelpCard.jsx';
import { StatusTag } from '../../shared/StatusTag.jsx';

const { Text, Title, Paragraph } = Typography;
const { TextArea } = Input;
const { Dragger } = Upload;

// 常改位置：详情抽屉布局、刷新按钮、截图展示、报告字段。
export function RunDetail({ run, open, onClose, onRefresh, refreshing }) {
  const report = run?.report || {};
  const events = report.events || [];
  const checks = report.checks || [];
  const screenshots = report.screenshots || [];
  return (
    <Drawer title={run ? `执行详情 #${run.id}` : '执行详情'} width={720} open={open} onClose={onClose} extra={<Button icon={<ReloadOutlined />} onClick={onRefresh} loading={refreshing}>刷新</Button>}>
      {!run ? <Empty description="请选择一条执行记录" /> : (
        <Space direction="vertical" size={18} className="full-width">
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label="类型">{run.case_type}</Descriptions.Item>
            <Descriptions.Item label="用例 ID">{run.case_id}</Descriptions.Item>
            <Descriptions.Item label="状态"><StatusTag status={run.status} /></Descriptions.Item>
            <Descriptions.Item label="耗时">{formatDuration(run.duration_ms)}</Descriptions.Item>
            <Descriptions.Item label="创建时间">{formatTime(run.created_at)}</Descriptions.Item>
            <Descriptions.Item label="更新时间">{formatTime(run.updated_at)}</Descriptions.Item>
          </Descriptions>
          {run.logs && <Alert type="info" showIcon message={run.logs} />}
          {run.error && <Alert type="error" showIcon message={run.error} />}
          {report.latest_screenshot && (
            <Card title="当前页面截图" size="small">
              <img className="report-image" src={report.latest_screenshot} alt={`run-${run.id}-latest`} />
            </Card>
          )}
          {events.length > 0 && (
            <Card title="UI 步骤" size="small">
              <Table
                rowKey={(event) => `${event.step}-${event.action}`}
                size="small"
                pagination={false}
                dataSource={events}
                columns={[
                  { title: '步骤', dataIndex: 'step', width: 70 },
                  { title: '动作', dataIndex: 'action', width: 110 },
                  { title: '目标', dataIndex: 'target', ellipsis: true, render: (value) => value || '-' },
                  { title: '值', dataIndex: 'value', ellipsis: true, render: (value) => value || '-' },
                  { title: '耗时', dataIndex: 'elapsed_ms', width: 100, render: formatDuration },
                ]}
              />
            </Card>
          )}
          {checks.length > 0 && (
            <Card title="接口断言" size="small">
              <Table
                rowKey="name"
                size="small"
                pagination={false}
                dataSource={checks}
                columns={[
                  { title: '名称', dataIndex: 'name' },
                  { title: '结果', dataIndex: 'passed', render: (value) => value ? <Tag color="success">通过</Tag> : <Tag color="error">失败</Tag> },
                  { title: '期望', dataIndex: 'expected', render: (value) => String(value ?? '-') },
                  { title: '实际', dataIndex: 'actual', render: (value) => String(value ?? '-') },
                ]}
              />
            </Card>
          )}
          {report.response && (
            <Card title="接口响应" size="small">
              <pre className="json-report">{JSON.stringify(report.response, null, 2)}</pre>
            </Card>
          )}
          {screenshots.length > 0 && (
            <Card title="截图清单" size="small">
              <div className="thumb-grid">{screenshots.map((item) => <img key={`${item.step}-${item.title}`} src={item.image} alt={item.title} />)}</div>
            </Card>
          )}
        </Space>
      )}
    </Drawer>
  );
}

// 执行记录模块：展示历史执行任务，并打开详情抽屉。

