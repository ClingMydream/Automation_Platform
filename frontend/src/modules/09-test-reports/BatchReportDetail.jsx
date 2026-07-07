// File purpose: Batch report drawer. It displays execution-batch statistics and result evidence.
// How to change: keep batch-report UI here; keep filtering and export logic in testReportFeature/reportExport.

import React from 'react';
import { Card, Descriptions, Drawer, Empty, Space, Table, Tag } from 'antd';
import { formatDuration, formatTime } from '../../shared/formatters';
import { StatusTag } from '../../shared/StatusTag.jsx';

// Batch report drawer: summarizes one execution batch and lists all collected result rows.
export function BatchReportDetail({ report, open, onClose }) {
  // Derived data keeps rendering safe for old reports that do not contain batch fields.
  const detail = report?.report || {};
  const batch = detail.batch || {};
  const stats = detail.stats || {};
  const results = detail.results || [];

  // Render block: JSX below describes the batch report evidence view.
  return (
    <Drawer title={report ? `批次报告 ${batch.batch_no || `#${report.id}`}` : '批次报告'} width={860} open={open} onClose={onClose}>
      {!report ? <Empty description="请选择一份批次报告" /> : (
        <Space direction="vertical" size={16} className="full-width">
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label="批次号">{batch.batch_no || '-'}</Descriptions.Item>
            <Descriptions.Item label="状态"><StatusTag status={report.status} /></Descriptions.Item>
            <Descriptions.Item label="触发方式">{batch.trigger_type || '-'}</Descriptions.Item>
            <Descriptions.Item label="环境 ID">{batch.environment_id || '-'}</Descriptions.Item>
            <Descriptions.Item label="创建时间">{formatTime(report.created_at)}</Descriptions.Item>
            <Descriptions.Item label="更新时间">{formatTime(report.updated_at)}</Descriptions.Item>
            <Descriptions.Item label="总耗时">{formatDuration(report.duration_ms)}</Descriptions.Item>
            <Descriptions.Item label="任务 ID">{batch.task_id || '-'}</Descriptions.Item>
          </Descriptions>
          <Card title="执行统计" size="small">
            <Descriptions bordered column={4} size="small">
              <Descriptions.Item label="总数">{stats.total ?? 0}</Descriptions.Item>
              <Descriptions.Item label="通过">{stats.passed ?? 0}</Descriptions.Item>
              <Descriptions.Item label="失败">{stats.failed ?? 0}</Descriptions.Item>
              <Descriptions.Item label="跳过">{stats.skipped ?? 0}</Descriptions.Item>
            </Descriptions>
          </Card>
          <Card title="结果明细" size="small">
            <Table
              rowKey="id"
              size="small"
              pagination={{ pageSize: 8 }}
              dataSource={results}
              scroll={{ x: 980 }}
              columns={[
                { title: 'ID', dataIndex: 'id', width: 70 },
                { title: '类型', dataIndex: 'result_type', width: 90, render: (value) => <Tag>{value}</Tag> },
                { title: '用例', dataIndex: 'case_id', width: 90 },
                { title: '状态', dataIndex: 'status', width: 100, render: (value) => <StatusTag status={value} /> },
                { title: '耗时', dataIndex: 'duration_ms', width: 100, render: formatDuration },
                { title: '失败分类', dataIndex: 'failure_category', width: 120, render: (value) => value || '-' },
                { title: '错误', dataIndex: 'error', ellipsis: true, render: (value) => value || '-' },
              ]}
              expandable={{
                expandedRowRender: (record) => (
                  <Space direction="vertical" size={12} className="full-width">
                    <pre className="json-report">{JSON.stringify({
                      request: record.request_data,
                      response: record.response_data,
                      assertions: record.assertions,
                      metrics: record.metrics,
                    }, null, 2)}</pre>
                  </Space>
                ),
              }}
            />
          </Card>
        </Space>
      )}
    </Drawer>
  );
}

// Test reports module: this file only owns batch report detail rendering.
