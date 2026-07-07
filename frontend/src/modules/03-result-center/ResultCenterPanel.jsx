// File purpose: Result center page. Review execution batches and collected result evidence.

import React, { useState } from 'react';
import { App as AntApp, Button, Card, Col, Descriptions, Row, Space, Table, Tag, Typography } from 'antd';
import { RedoOutlined } from '@ant-design/icons';
import { StatusTag } from '../../shared/StatusTag.jsx';
import { formatDuration, formatTime } from '../../shared/formatters.js';
import { canRetryBatch, retryFailedBatch } from './resultCenterFeature.js';

const { Paragraph } = Typography;

export function ResultCenterPanel({ client, batches, results, reload }) {
  const [selected, setSelected] = useState(null);
  const [retryingId, setRetryingId] = useState(null);
  const { message } = AntApp.useApp();

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
