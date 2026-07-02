import React from 'react';
import { Button, Card, Col, Row, Space, Statistic, Table, Tag } from 'antd';
import { ClockCircleOutlined, EyeOutlined, ReloadOutlined } from '@ant-design/icons';
import { formatDuration, formatTime } from '../../../shared/formatters';
import { StatusTag } from '../../../shared/StatusTag.jsx';
import { RunDetail } from './RunDetail.jsx';
import { buildRunSummary, findRunById } from '../feature/runHistoryFeature.js';

export function RunsPanel({ runs, reload, refreshing, selectedRunId, onSelectRun }) {
  const selectedRun = findRunById(runs, selectedRunId);
  const summary = buildRunSummary(runs);
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

