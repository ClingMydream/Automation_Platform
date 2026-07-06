// File purpose: Quality analysis page. Show pass rate, failure distribution, and recent trend.

import React from 'react';
import { Card, Col, Descriptions, Empty, Row, Table, Tag } from 'antd';

export function QualityAnalysisPanel({ qualitySummary, qualityTrend }) {
  const summary = qualitySummary || {};
  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={8}>
        <Card title="质量总览">
          <Descriptions column={1} size="small">
            <Descriptions.Item label="总结果数">{summary.total || 0}</Descriptions.Item>
            <Descriptions.Item label="通过率">{summary.pass_rate || 0}%</Descriptions.Item>
            <Descriptions.Item label="失败数">{summary.failed || 0}</Descriptions.Item>
            <Descriptions.Item label="平均耗时">{summary.avg_duration_ms || '-'}</Descriptions.Item>
            <Descriptions.Item label="P95">{summary.p95_duration_ms || '-'}</Descriptions.Item>
            <Descriptions.Item label="发布风险"><Tag color={summary.release_risk === 'high' ? 'red' : summary.release_risk === 'medium' ? 'orange' : 'green'}>{summary.release_risk || 'low'}</Tag></Descriptions.Item>
          </Descriptions>
        </Card>
        <Card title="失败原因分布" style={{ marginTop: 16 }}>
          {summary.failure_categories ? Object.entries(summary.failure_categories).map(([key, value]) => <Tag key={key} color="red">{key}: {value}</Tag>) : <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} />}
        </Card>
      </Col>
      <Col xs={24} xl={16}>
        <Card title="最近执行批次趋势">
          <Table
            rowKey="batch_no"
            dataSource={qualityTrend}
            pagination={{ pageSize: 10 }}
            columns={[
              { title: '批次号', dataIndex: 'batch_no' },
              { title: '状态', dataIndex: 'status', width: 100 },
              { title: '总数', dataIndex: 'total', width: 80 },
              { title: '通过', dataIndex: 'passed', width: 80 },
              { title: '失败', dataIndex: 'failed', width: 80 },
              { title: '通过率', dataIndex: 'pass_rate', width: 100, render: (value) => `${value}%` },
            ]}
          />
        </Card>
      </Col>
    </Row>
  );
}
