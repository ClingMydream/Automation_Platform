// File purpose: Test reports page. Filter reports, view details, and export HTML reports.
// How to change: edit UI text/layout in this file; move reusable logic into shared helpers or the module feature file.

import React, { useState } from 'react';
import { Button, Card, Col, Row, Select, Space, Statistic, Table, Tag } from 'antd';
import { ClockCircleOutlined, DownloadOutlined, EyeOutlined, ReloadOutlined } from '@ant-design/icons';
import { formatDuration, formatTime } from '../../shared/formatters';
import { downloadReportHtml } from '../../shared/reportExport';
import { StatusTag } from '../../shared/StatusTag.jsx';
import { RunDetail } from '../run-history/RunDetail.jsx';
import { buildReportSummary, filterReports, findReportById } from './testReportFeature.js';

// Reports page: shows report statistics, filters, details, and export action.
export function ReportsPanel({ reports, reload, refreshing }) {
  // State block: values here control loading, selection, form state, and visible page data.
  const [typeFilter, setTypeFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedReportId, setSelectedReportId] = useState(null);
  const filtered = filterReports(reports, { typeFilter, statusFilter });
  const summary = buildReportSummary(reports);
  const selectedReport = findReportById(reports, selectedReportId);

  // Render block: JSX below describes what the user sees on this page.
  return (
    <Space direction="vertical" size={16} className="full-width">
      <Row gutter={[16, 16]}>
        <Col xs={12} lg={6}><Card><Statistic title="报告总数" value={summary.total} prefix={<ClockCircleOutlined />} /></Card></Col>
        <Col xs={12} lg={6}><Card><Statistic title="通过" value={summary.passed} valueStyle={{ color: '#16a34a' }} /></Card></Col>
        <Col xs={12} lg={6}><Card><Statistic title="失败" value={summary.failed} valueStyle={{ color: '#dc2626' }} /></Card></Col>
        <Col xs={12} lg={6}><Card><Statistic title="平均耗时" value={summary.avgDuration === null ? '-' : formatDuration(summary.avgDuration)} /></Card></Col>
      </Row>
      <Card
        title="测试报告列表"
        extra={(
          <Space wrap>
            <Select
              value={typeFilter}
              onChange={setTypeFilter}
              style={{ width: 130 }}
              options={[
                { value: 'all', label: '全部类型' },
                { value: 'api', label: '接口测试' },
                { value: 'ui', label: 'UI 测试' },
              ]}
            />
            <Select
              value={statusFilter}
              onChange={setStatusFilter}
              style={{ width: 130 }}
              options={[
                { value: 'all', label: '全部状态' },
                { value: 'passed', label: '通过' },
                { value: 'failed', label: '失败' },
                { value: 'running', label: '运行中' },
                { value: 'queued', label: '排队中' },
              ]}
            />
            <Button icon={<ReloadOutlined />} loading={refreshing} onClick={reload}>刷新</Button>
          </Space>
        )}
      >
        <Table
          rowKey="id"
          dataSource={filtered}
          pagination={{ pageSize: 10 }}
          scroll={{ x: 1180 }}
          columns={[
            { title: '报告 ID', dataIndex: 'id', width: 90 },
            { title: '类型', dataIndex: 'case_type', width: 100, render: (value) => <Tag>{value === 'api' ? '接口' : 'UI'}</Tag> },
            { title: '用例名称', dataIndex: 'case_name', ellipsis: true },
            { title: '状态', dataIndex: 'status', width: 110, render: (value) => <StatusTag status={value} /> },
            { title: '耗时', dataIndex: 'duration_ms', width: 110, render: formatDuration },
            { title: '断言', dataIndex: 'check_count', width: 90, render: (value) => value || 0 },
            { title: '步骤', dataIndex: 'event_count', width: 90, render: (value) => value || 0 },
            { title: '截图', dataIndex: 'screenshot_count', width: 90, render: (value) => value || 0 },
            { title: '完成时间', dataIndex: 'updated_at', width: 180, render: formatTime },
            { title: '错误', dataIndex: 'error', ellipsis: true, render: (value) => value || '-' },
            {
              title: '操作',
              width: 190,
              fixed: 'right',
              render: (_, record) => (
                <Space className="table-actions" size={6} wrap>
                  <Button icon={<EyeOutlined />} onClick={() => setSelectedReportId(record.id)}>详情</Button>
                  <Button icon={<DownloadOutlined />} onClick={() => downloadReportHtml(record)}>导出</Button>
                </Space>
              ),
            },
          ]}
        />
      </Card>
      <RunDetail run={selectedReport} open={Boolean(selectedReportId)} onClose={() => setSelectedReportId(null)} onRefresh={reload} refreshing={refreshing} />
    </Space>
  );
}

// JSON 工具模块：纯浏览器本地处理，不向服务器上传内容。

