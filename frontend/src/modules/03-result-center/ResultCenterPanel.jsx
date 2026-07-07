// File purpose: Result center page. Review execution batches and collected result evidence.

import React, { useState } from 'react';
import { App as AntApp, Button, Card, Col, Descriptions, Row, Space, Statistic, Table, Tag, Typography } from 'antd';
import { RedoOutlined } from '@ant-design/icons';
import { StatusTag } from '../../shared/StatusTag.jsx';
import { formatDuration, formatTime } from '../../shared/formatters.js';
import { canRetryBatch, formatPerformanceMetric, performanceRiskColor, retryFailedBatch } from './resultCenterFeature.js';

const { Paragraph } = Typography;

export function ResultCenterPanel({ client, batches, results, performanceSummary = {}, reload }) {
  const [selected, setSelected] = useState(null);
  const [retryingId, setRetryingId] = useState(null);
  const { message } = AntApp.useApp();
  const performanceRows = performanceSummary.latest_results || [];

  async function handleRetry(batch) {
    setRetryingId(batch.id);
    try {
      const nextBatch = await retryFailedBatch(client, batch.id);
      message.success(`已创建重试批次：${nextBatch.batch_no}`);
      await reload();
    } catch (err) {
      message.error(err.message);
    } finally {
      setRetryingId(null);
    }
  }

  return (
    <Row gutter={[16, 16]}>
      <Col span={24}>
        <Card
          title="性能结果概览"
          extra={<Tag color={performanceRiskColor(performanceSummary.risk_level)}>{performanceSummary.risk_level || 'no-data'}</Tag>}
        >
          <Row gutter={[16, 16]}>
            <Col xs={12} md={6} xl={3}><Statistic title="性能结果" value={performanceSummary.total || 0} /></Col>
            <Col xs={12} md={6} xl={3}><Statistic title="通过率" value={performanceSummary.pass_rate || 0} suffix="%" precision={2} /></Col>
            <Col xs={12} md={6} xl={3}><Statistic title="平均响应" value={performanceSummary.avg_response_ms || 0} suffix="ms" precision={2} /></Col>
            <Col xs={12} md={6} xl={3}><Statistic title="最大 P95" value={performanceSummary.max_p95_ms || 0} suffix="ms" precision={2} /></Col>
            <Col xs={12} md={6} xl={3}><Statistic title="最大 P99" value={performanceSummary.max_p99_ms || 0} suffix="ms" precision={2} /></Col>
            <Col xs={12} md={6} xl={3}><Statistic title="最大 TPS" value={performanceSummary.max_tps || 0} precision={2} /></Col>
            <Col xs={12} md={6} xl={3}><Statistic title="最高错误率" value={performanceSummary.max_error_rate || 0} suffix="%" precision={2} /></Col>
            <Col xs={12} md={6} xl={3}><Statistic title="样本数" value={performanceSummary.total_samples || 0} /></Col>
          </Row>
          <Paragraph type="secondary" style={{ margin: '12px 0 0' }}>
            {(performanceSummary.risk_reasons || ['暂无性能结果；JMeter 或脚本回传 result_type=performance 后会自动汇总。']).join('；')}
          </Paragraph>
        </Card>
      </Col>
      <Col xs={24} xl={10}>
        <Card title="执行批次">
          <Table
            rowKey="id"
            dataSource={batches}
            pagination={{ pageSize: 8 }}
            scroll={{ x: 760 }}
            columns={[
              { title: '批次号', dataIndex: 'batch_no', width: 190 },
              { title: '状态', dataIndex: 'status', width: 100, render: (value) => <StatusTag status={value} /> },
              { title: '总数', dataIndex: 'total_count', width: 80 },
              { title: '通过', dataIndex: 'passed_count', width: 80 },
              { title: '失败', dataIndex: 'failed_count', width: 80 },
              {
                title: '操作',
                width: 110,
                fixed: 'right',
                render: (_, record) => (
                  <Button
                    icon={<RedoOutlined />}
                    disabled={!canRetryBatch(record)}
                    loading={retryingId === record.id}
                    onClick={() => handleRetry(record)}
                  >
                    重试
                  </Button>
                ),
              },
            ]}
          />
        </Card>
      </Col>
      <Col xs={24} xl={14}>
        <Card title="性能结果" style={{ marginBottom: 16 }}>
          <Table
            rowKey="id"
            dataSource={performanceRows}
            pagination={{ pageSize: 5 }}
            scroll={{ x: 920 }}
            onRow={(record) => ({ onClick: () => setSelected(results.find((item) => item.id === record.id) || record) })}
            columns={[
              { title: 'ID', dataIndex: 'id', width: 80 },
              { title: '状态', dataIndex: 'status', width: 100, render: (value) => <StatusTag status={value} /> },
              { title: '平均', width: 100, render: (_, record) => formatPerformanceMetric(record.normalized_metrics?.avg_ms, ' ms') },
              { title: 'P95', width: 100, render: (_, record) => formatPerformanceMetric(record.normalized_metrics?.p95_ms, ' ms') },
              { title: 'P99', width: 100, render: (_, record) => formatPerformanceMetric(record.normalized_metrics?.p99_ms, ' ms') },
              { title: 'TPS', width: 90, render: (_, record) => formatPerformanceMetric(record.normalized_metrics?.tps) },
              { title: '错误率', width: 100, render: (_, record) => formatPerformanceMetric(record.normalized_metrics?.error_rate, '%') },
              { title: '样本', width: 90, render: (_, record) => formatPerformanceMetric(record.normalized_metrics?.samples) },
              { title: '时间', dataIndex: 'created_at', width: 170, render: formatTime },
            ]}
          />
        </Card>
        <Card title="结果明细">
          <Table
            rowKey="id"
            dataSource={results}
            pagination={{ pageSize: 8 }}
            scroll={{ x: 980 }}
            onRow={(record) => ({ onClick: () => setSelected(record) })}
            columns={[
              { title: 'ID', dataIndex: 'id', width: 80 },
              { title: '类型', dataIndex: 'result_type', width: 110, render: (value) => <Tag>{value}</Tag> },
              { title: '状态', dataIndex: 'status', width: 100, render: (value) => <StatusTag status={value} /> },
              { title: '耗时', dataIndex: 'duration_ms', width: 100, render: formatDuration },
              { title: '失败分类', dataIndex: 'failure_category', width: 130, render: (value) => value || '-' },
              { title: '时间', dataIndex: 'created_at', width: 170, render: formatTime },
            ]}
          />
        </Card>
        {selected && (
          <Card title={`结果详情 #${selected.id}`} style={{ marginTop: 16 }}>
            <Descriptions size="small" column={1}>
              <Descriptions.Item label="日志"><Paragraph copyable>{selected.logs || '-'}</Paragraph></Descriptions.Item>
              <Descriptions.Item label="错误"><Paragraph type="danger" copyable>{selected.error || '-'}</Paragraph></Descriptions.Item>
              <Descriptions.Item label="指标"><pre>{JSON.stringify(selected.metrics || {}, null, 2)}</pre></Descriptions.Item>
              <Descriptions.Item label="断言"><pre>{JSON.stringify(selected.assertions || [], null, 2)}</pre></Descriptions.Item>
            </Descriptions>
          </Card>
        )}
      </Col>
    </Row>
  );
}
