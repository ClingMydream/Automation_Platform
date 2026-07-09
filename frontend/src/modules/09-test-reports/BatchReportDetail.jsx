// File purpose: Batch report drawer. It displays execution-batch statistics and result evidence.
// How to change: keep batch-report UI here; keep filtering and export logic in testReportFeature/reportExport.

import React, { useEffect, useState } from 'react';
import { App as AntApp, Button, Card, Descriptions, Drawer, Empty, Space, Statistic, Table, Tag, Row, Col, Select, Upload } from 'antd';
import { DownloadOutlined, PaperClipOutlined, UploadOutlined } from '@ant-design/icons';
import { formatBytes, formatDuration, formatTime } from '../../shared/formatters';
import { StatusTag } from '../../shared/StatusTag.jsx';
import { attachmentTypeOptions, downloadAttachment, listBatchAttachments, uploadBatchAttachment } from '../03-result-center/resultCenterFeature.js';

// Batch report drawer: summarizes one execution batch and lists all collected result rows.
export function BatchReportDetail({ client, report, open, onClose }) {
  // Derived data keeps rendering safe for old reports that do not contain batch fields.
  const detail = report?.report || {};
  const batch = detail.batch || {};
  const stats = detail.stats || {};
  const results = detail.results || [];
  const performance = detail.performance_summary || {};
  const [attachments, setAttachments] = useState([]);
  const [attachmentType, setAttachmentType] = useState('performance_report');
  const [attachmentLoading, setAttachmentLoading] = useState(false);
  const { message } = AntApp.useApp();

  useEffect(() => {
    if (!client || !batch.id || !open) {
      setAttachments([]);
      return undefined;
    }
    let ignore = false;
    async function loadAttachments() {
      setAttachmentLoading(true);
      try {
        const rows = await listBatchAttachments(client, batch.id);
        if (!ignore) setAttachments(rows);
      } catch (err) {
        if (!ignore) message.error(err.message);
      } finally {
        if (!ignore) setAttachmentLoading(false);
      }
    }
    loadAttachments();
    return () => { ignore = true; };
  }, [client, batch.id, open]);

  async function handleUploadAttachment(file) {
    if (!client || !batch.id) {
      message.warning('缺少批次 ID，暂不能上传附件');
      return false;
    }
    setAttachmentLoading(true);
    try {
      await uploadBatchAttachment(client, batch.id, attachmentType, file);
      message.success('批次附件已上传');
      setAttachments(await listBatchAttachments(client, batch.id));
    } catch (err) {
      message.error(err.message);
    } finally {
      setAttachmentLoading(false);
    }
    return false;
  }

  async function handleDownloadAttachment(attachment) {
    try {
      await downloadAttachment(client, attachment);
    } catch (err) {
      message.error(err.message);
    }
  }

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
          {performance.total > 0 && (
            <Card title="性能摘要" size="small">
              <Row gutter={[12, 12]}>
                <Col xs={12} md={4}><Statistic title="性能结果" value={performance.total || 0} /></Col>
                <Col xs={12} md={4}><Statistic title="通过率" value={performance.pass_rate || 0} suffix="%" precision={2} /></Col>
                <Col xs={12} md={4}><Statistic title="平均响应" value={performance.avg_response_ms || 0} suffix="ms" precision={2} /></Col>
                <Col xs={12} md={4}><Statistic title="最大 P95" value={performance.max_p95_ms || 0} suffix="ms" precision={2} /></Col>
                <Col xs={12} md={4}><Statistic title="错误率" value={performance.max_error_rate || 0} suffix="%" precision={2} /></Col>
                <Col xs={12} md={4}><Statistic title="最大 TPS" value={performance.max_tps || 0} precision={2} /></Col>
              </Row>
            </Card>
          )}
          <Card
            title={<Space><PaperClipOutlined />批次附件</Space>}
            size="small"
            extra={(
              <Space wrap>
                <Select size="small" value={attachmentType} options={attachmentTypeOptions} style={{ width: 118 }} onChange={setAttachmentType} />
                <Upload showUploadList={false} beforeUpload={handleUploadAttachment}>
                  <Button size="small" icon={<UploadOutlined />} loading={attachmentLoading}>上传</Button>
                </Upload>
              </Space>
            )}
          >
            <Table
              rowKey="id"
              size="small"
              loading={attachmentLoading}
              dataSource={attachments}
              pagination={false}
              locale={{ emptyText: '暂无批次附件，可上传 JMeter HTML 报告、JTL、日志、HAR 或录屏' }}
              columns={[
                { title: '类型', dataIndex: 'attachment_type', width: 120, render: (value) => attachmentTypeOptions.find((item) => item.value === value)?.label || value },
                { title: '文件名', dataIndex: 'original_name', ellipsis: true },
                { title: '大小', dataIndex: 'size_bytes', width: 100, render: formatBytes },
                { title: '时间', dataIndex: 'created_at', width: 170, render: formatTime },
                { title: '操作', width: 90, render: (_, record) => <Button size="small" icon={<DownloadOutlined />} onClick={() => handleDownloadAttachment(record)}>下载</Button> },
              ]}
            />
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
