// File purpose: Run detail drawer. Display logs, checks, screenshots, errors, and response data.
// How to change: edit UI text/layout in this file; move reusable logic into shared helpers or the module feature file.

import React, { useEffect, useState } from 'react';
import { Alert, App as AntApp, Button, Card, Collapse, Descriptions, Drawer, Empty, Space, Table, Tag, Statistic, Row, Col, Select, Upload } from 'antd';
import { DownloadOutlined, PaperClipOutlined, ReloadOutlined, UploadOutlined } from '@ant-design/icons';
import { formatBytes, formatDuration, formatTime } from '../../shared/formatters';
import { StatusTag } from '../../shared/StatusTag.jsx';
import { attachmentTypeOptions, downloadAttachment, listResultAttachments, uploadResultAttachment } from '../03-result-center/resultCenterFeature.js';

// Run detail drawer: shows logs, assertions, screenshots, errors, and response data.
export function RunDetail({ client, run, open, onClose, onRefresh, refreshing }) {
  const report = run?.report || {};
  const events = report.events || [];
  const checks = report.checks || [];
  const screenshots = report.screenshots || [];
  const metrics = run?.metrics || report.metrics || {};
  const [attachments, setAttachments] = useState([]);
  const [attachmentType, setAttachmentType] = useState('log');
  const [attachmentLoading, setAttachmentLoading] = useState(false);
  const { message } = AntApp.useApp();

  useEffect(() => {
    if (!client || !run?.result_id || !open) {
      setAttachments([]);
      return undefined;
    }
    let ignore = false;
    async function loadAttachments() {
      setAttachmentLoading(true);
      try {
        const rows = await listResultAttachments(client, run.result_id);
        if (!ignore) setAttachments(rows);
      } catch (err) {
        if (!ignore) message.error(err.message);
      } finally {
        if (!ignore) setAttachmentLoading(false);
      }
    }
    loadAttachments();
    return () => { ignore = true; };
  }, [client, run?.result_id, open]);

  async function handleUploadAttachment(file) {
    if (!client || !run?.result_id) {
      message.warning('这条执行记录还没有结果中心记录，暂不能上传附件');
      return false;
    }
    setAttachmentLoading(true);
    try {
      await uploadResultAttachment(client, run.result_id, attachmentType, file);
      message.success('附件已上传');
      setAttachments(await listResultAttachments(client, run.result_id));
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
  // Render block: JSX below describes what the user sees on this page.
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
          {run.result_id && (
            <Card
              title={<Space><PaperClipOutlined />结果附件</Space>}
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
                locale={{ emptyText: '暂无附件，可上传日志、截图、录屏、HAR 或性能报告' }}
                columns={[
                  { title: '类型', dataIndex: 'attachment_type', width: 110, render: (value) => attachmentTypeOptions.find((item) => item.value === value)?.label || value },
                  { title: '文件名', dataIndex: 'original_name', ellipsis: true },
                  { title: '大小', dataIndex: 'size_bytes', width: 90, render: formatBytes },
                  { title: '时间', dataIndex: 'created_at', width: 165, render: formatTime },
                  { title: '操作', width: 82, render: (_, record) => <Button size="small" icon={<DownloadOutlined />} onClick={() => handleDownloadAttachment(record)}>下载</Button> },
                ]}
              />
            </Card>
          )}
          {run.case_type === 'performance' && Object.keys(metrics).length > 0 && (
            <Card title="性能指标" size="small">
              <Row gutter={[12, 12]}>
                <Col xs={12} md={6}><Statistic title="平均响应" value={metrics.avg_ms || 0} suffix="ms" precision={2} /></Col>
                <Col xs={12} md={6}><Statistic title="P95" value={metrics.p95_ms || 0} suffix="ms" precision={2} /></Col>
                <Col xs={12} md={6}><Statistic title="P99" value={metrics.p99_ms || 0} suffix="ms" precision={2} /></Col>
                <Col xs={12} md={6}><Statistic title="TPS" value={metrics.tps || 0} precision={2} /></Col>
                <Col xs={12} md={6}><Statistic title="错误率" value={metrics.error_rate || 0} suffix="%" precision={2} /></Col>
                <Col xs={12} md={6}><Statistic title="样本数" value={metrics.samples || 0} /></Col>
                <Col xs={12} md={6}><Statistic title="并发" value={metrics.concurrency || 0} /></Col>
                <Col xs={12} md={6}><Statistic title="成功数" value={metrics.successes || 0} /></Col>
              </Row>
            </Card>
          )}
          {report.latest_screenshot && (
            <Card title="当前页面截图" size="small">
              <img className="report-image" src={report.latest_screenshot} alt={`run-${run.id}-latest`} />
            </Card>
          )}
          {(report.recording_url || report.recording_error) && (
            <Card title="UI 执行录屏" size="small">
              {report.recording_url ? (
                <video className="report-video" controls preload="metadata" src={report.recording_url}>
                  当前浏览器不支持播放 UI 自动化录屏。
                </video>
              ) : (
                <Alert type="warning" showIcon message={report.recording_error} />
              )}
            </Card>
          )}
          {report.failure_advice?.length > 0 && (
            <Card title="失败定位建议" size="small">
              <ul className="diagnosis-list">{report.failure_advice.map((item) => <li key={item}>{item}</li>)}</ul>
            </Card>
          )}
          {(report.dom_snapshot || report.dom_snapshot_error) && (
            <Card title="DOM 快照" size="small">
              {report.dom_snapshot ? (
                <Collapse
                  items={[{ key: 'dom', label: '查看失败时页面 HTML', children: <pre className="dom-snapshot">{report.dom_snapshot}</pre> }]}
                />
              ) : (
                <Alert type="warning" showIcon message={report.dom_snapshot_error} />
              )}
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
                  { title: '结果', dataIndex: 'status', width: 90, render: (value) => value === 'failed' ? <Tag color="error">失败</Tag> : <Tag color="success">通过</Tag> },
                  { title: '目标', dataIndex: 'target', ellipsis: true, render: (value) => value || '-' },
                  { title: '值', dataIndex: 'value', ellipsis: true, render: (value) => value || '-' },
                  { title: '耗时', dataIndex: 'elapsed_ms', width: 100, render: formatDuration },
                  { title: '错误', dataIndex: 'error', ellipsis: true, render: (value) => value || '-' },
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
