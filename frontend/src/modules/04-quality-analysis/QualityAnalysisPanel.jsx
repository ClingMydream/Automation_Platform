// File purpose: Quality analysis page. Show release risk, stability, failure distribution, and recent trends.

import React from 'react';
import { Card, Col, Empty, List, Row, Space, Statistic, Table, Tag, Typography } from 'antd';
import { AlertOutlined, CheckCircleOutlined, ClockCircleOutlined, LineChartOutlined } from '@ant-design/icons';
import { formatDuration, formatTime } from '../../shared/formatters.js';
import { counterRows, riskMeta } from './qualityAnalysisFeature.js';

const { Text } = Typography;

// Quality analysis page: turns collected result evidence into release-readiness signals.
export function QualityAnalysisPanel({ qualitySummary, qualityTrend }) {
  const summary = qualitySummary || {};
  const risk = riskMeta(summary.release_risk);
  const distributionColumns = [
    { title: '名称', dataIndex: 'name', ellipsis: true },
    { title: '数量', dataIndex: 'count', width: 80 },
  ];

  // Render block: JSX below describes the quality dashboard visible to the user.
  return (
    <Space direction="vertical" size={16} className="full-width">
      <Row gutter={[16, 16]}>
        <Col xs={12} lg={6}>
          <Card>
            <Statistic title="通过率" value={summary.pass_rate || 0} suffix="%" prefix={<CheckCircleOutlined />} valueStyle={{ color: '#13a56b' }} />
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card>
            <Statistic title="稳定性评分" value={summary.stability_score ?? 100} suffix="/100" prefix={<LineChartOutlined />} />
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card>
            <Statistic title="失败率" value={summary.fail_rate || 0} suffix="%" prefix={<AlertOutlined />} valueStyle={{ color: summary.failed ? '#d92d20' : '#13a56b' }} />
          </Card>
        </Col>
        <Col xs={12} lg={6}>
          <Card>
            <Statistic title="P95 耗时" value={summary.p95_duration_ms == null ? '-' : formatDuration(summary.p95_duration_ms)} prefix={<ClockCircleOutlined />} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={8}>
          <Card title="发布风险">
            <Space direction="vertical" size={12} className="full-width">
              <Tag color={risk.color}>{risk.label}</Tag>
              <List
                size="small"
                dataSource={summary.release_risk_reasons || []}
                locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无风险说明" /> }}
                renderItem={(item) => <List.Item><Text>{item}</Text></List.Item>}
              />
              <div className="tool-summary">
                <Text type="secondary">总结果 {summary.total || 0}，通过 {summary.passed || 0}，失败 {summary.failed || 0}，跳过 {summary.skipped || 0}</Text>
              </div>
            </Space>
          </Card>
        </Col>
        <Col xs={24} xl={8}>
          <Card title="失败原因分布">
            <Table
              rowKey="key"
              size="small"
              dataSource={counterRows(summary.failure_category_items)}
              columns={distributionColumns}
              pagination={false}
              locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无失败" /> }}
            />
          </Card>
        </Col>
        <Col xs={24} xl={8}>
          <Card title="高频失败用例">
            <Table
              rowKey="key"
              size="small"
              dataSource={counterRows(summary.top_failed_cases)}
              columns={distributionColumns}
              pagination={false}
              locale={{ emptyText: <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无高频失败" /> }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={8}>
          <Card title="结果类型分布">
            <Table
              rowKey="key"
              size="small"
              dataSource={counterRows(summary.result_type_items)}
              columns={distributionColumns}
              pagination={false}
            />
          </Card>
        </Col>
        <Col xs={24} xl={8}>
          <Card title="状态分布">
            <Table
              rowKey="key"
              size="small"
              dataSource={counterRows(summary.status_items)}
              columns={distributionColumns}
              pagination={false}
            />
          </Card>
        </Col>
        <Col xs={24} xl={8}>
          <Card title="环境分布">
            <Table
              rowKey="key"
              size="small"
              dataSource={counterRows(summary.environment_items)}
              columns={distributionColumns}
              pagination={false}
            />
          </Card>
        </Col>
      </Row>

      <Card title="最近执行批次趋势">
        <Table
          rowKey="batch_no"
          dataSource={qualityTrend}
          pagination={{ pageSize: 10 }}
          scroll={{ x: 980 }}
          columns={[
            { title: '批次号', dataIndex: 'batch_no', width: 210, ellipsis: true },
            { title: '状态', dataIndex: 'status', width: 100, render: (value) => <Tag>{value}</Tag> },
            { title: '风险', dataIndex: 'release_risk', width: 100, render: (value) => <Tag color={riskMeta(value).color}>{riskMeta(value).label}</Tag> },
            { title: '总数', dataIndex: 'total', width: 80 },
            { title: '通过', dataIndex: 'passed', width: 80 },
            { title: '失败', dataIndex: 'failed', width: 80 },
            { title: '通过率', dataIndex: 'pass_rate', width: 100, render: (value) => `${value || 0}%` },
            { title: '失败率', dataIndex: 'fail_rate', width: 100, render: (value) => `${value || 0}%` },
            { title: '耗时', dataIndex: 'duration_ms', width: 110, render: formatDuration },
            { title: '创建时间', dataIndex: 'created_at', width: 180, render: formatTime },
          ]}
        />
      </Card>
    </Space>
  );
}

// Quality-analysis module: converts result-center data into release risk and stability views.
