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
import { RunDetail } from './RunDetail.jsx';

const { Text, Title, Paragraph } = Typography;
const { TextArea } = Input;
const { Dragger } = Upload;

// 常改位置：列表列配置、筛选条件、刷新策略、详情入口。
export function RunsPanel({ runs, reload, refreshing, selectedRunId, onSelectRun }) {
  const selectedRun = runs.find((run) => run.id === selectedRunId) || null;
  const summary = {
    total: runs.length,
    running: runs.filter((run) => ['queued', 'running'].includes(run.status)).length,
    passed: runs.filter((run) => run.status === 'passed').length,
    failed: runs.filter((run) => run.status === 'failed').length,
  };
  return (
    <Space direction="vertical" size={16} className="full-width">
      <Row gutter={[16, 16]}>
        <Col xs={12} lg={6}><Card><Statistic title="最近任务" value={summary.total} prefix={<ClockCircleOutlined />} /></Card></Col>
        <Col xs={12} lg={6}><Card><Statistic title="运行中" value={summary.running} valueStyle={{ color: '#1677ff' }} /></Card></Col>
        <Col xs={12} lg={6}><Card><Statistic title="通过" value={summary.passed} valueStyle={{ color: '#16a34a' }} /></Card></Col>
        <Col xs={12} lg={6}><Card><Statistic title="失败" value={summary.failed} valueStyle={{ color: '#dc2626' }} /></Card></Col>
      </Row>
      <Card title="执行记录" extra={<Button icon={<ReloadOutlined />} loading={refreshing} onClick={reload}>刷新</Button>}>
        <Table
          rowKey="id"
          dataSource={runs}
          pagination={{ pageSize: 10 }}
          scroll={{ x: 1180 }}
          columns={[
            { title: 'ID', dataIndex: 'id', width: 80 },
            { title: '类型', dataIndex: 'case_type', width: 90, render: (value) => <Tag>{value}</Tag> },
            { title: '用例', dataIndex: 'case_id', width: 90 },
            { title: '状态', dataIndex: 'status', width: 110, render: (value) => <StatusTag status={value} /> },
            { title: '创建时间', dataIndex: 'created_at', render: formatTime },
            { title: '更新时间', dataIndex: 'updated_at', render: formatTime },
            { title: '耗时', dataIndex: 'duration_ms', width: 110, render: formatDuration },
            { title: '错误', dataIndex: 'error', ellipsis: true, render: (value) => value || '-' },
            { title: '操作', width: 100, render: (_, record) => <Button icon={<EyeOutlined />} onClick={() => onSelectRun(record.id)}>详情</Button> },
          ]}
        />
      </Card>
      <RunDetail run={selectedRun} open={Boolean(selectedRunId)} onClose={() => onSelectRun(null)} onRefresh={reload} refreshing={refreshing} />
    </Space>
  );
}

// 测试报告模块：面向结果复盘，支持查看详情和导出 HTML 报告。

