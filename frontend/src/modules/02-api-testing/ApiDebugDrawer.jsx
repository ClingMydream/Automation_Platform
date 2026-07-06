// File purpose: API debug drawer. It displays one API debug run beside the case list.
// How to change: keep visual result rendering here; keep backend calls in apiCaseFeature.js.

import React from 'react';
import { Alert, Button, Card, Descriptions, Drawer, Empty, Space, Spin, Table, Tag } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { formatDuration, formatTime } from '../../shared/formatters';
import { StatusTag } from '../../shared/StatusTag.jsx';

// API debug drawer: shows request, response, assertions, logs, and run timing for one debug execution.
export function ApiDebugDrawer({ run, open, loading, onClose, onRefresh }) {
  // Derived report data keeps JSX readable and makes empty states predictable.
  const report = run?.report || {};
  const checks = report.checks || [];
  const request = report.request || {};
  const response = report.response || {};
  const isWaiting = loading || ['queued', 'running'].includes(run?.status);

  // Render block: JSX below describes the inline debug result view.
  return (
    <Drawer
      title={run ? `接口调试 #${run.id}` : '接口调试'}
      width={760}
      open={open}
      onClose={onClose}
      extra={<Button icon={<ReloadOutlined />} loading={loading} onClick={onRefresh}>刷新</Button>}
    >
      {!run ? (
        <Empty description="请选择一个接口用例并点击调试" />
      ) : (
        <Space direction="vertical" size={16} className="full-width">
          {isWaiting && <Alert type="info" showIcon message="调试任务正在执行，页面会自动刷新结果。" />}
          <Descriptions bordered column={2} size="small">
            <Descriptions.Item label="状态"><StatusTag status={run.status} /></Descriptions.Item>
            <Descriptions.Item label="耗时">{formatDuration(run.duration_ms)}</Descriptions.Item>
            <Descriptions.Item label="创建时间">{formatTime(run.created_at)}</Descriptions.Item>
            <Descriptions.Item label="更新时间">{formatTime(run.updated_at)}</Descriptions.Item>
          </Descriptions>
          {run.logs && <Alert type="info" showIcon message={run.logs} />}
          {run.error && <Alert type="error" showIcon message={run.error} />}
          {report.error && <Alert type="error" showIcon message={report.error} />}
          <Card title="请求信息" size="small">
            <Descriptions bordered column={1} size="small">
              <Descriptions.Item label="方法">{request.method || '-'}</Descriptions.Item>
              <Descriptions.Item label="URL">{request.url || '-'}</Descriptions.Item>
              <Descriptions.Item label="环境 ID">{request.environment_id || '-'}</Descriptions.Item>
            </Descriptions>
          </Card>
          <Card title="响应摘要" size="small">
            {Object.keys(response).length === 0 ? (
              <Spin spinning={isWaiting}><Empty description="等待响应结果" /></Spin>
            ) : (
              <pre className="json-report">{JSON.stringify(response, null, 2)}</pre>
            )}
          </Card>
          <Card title="断言结果" size="small">
            <Table
              rowKey="name"
              size="small"
              pagination={false}
              dataSource={checks}
              locale={{ emptyText: '暂无断言结果' }}
              columns={[
                { title: '名称', dataIndex: 'name' },
                { title: '结果', dataIndex: 'passed', width: 90, render: (value) => value ? <Tag color="success">通过</Tag> : <Tag color="error">失败</Tag> },
                { title: '期望', dataIndex: 'expected', render: (value) => String(value ?? '-') },
                { title: '实际', dataIndex: 'actual', render: (value) => String(value ?? '-') },
              ]}
            />
          </Card>
        </Space>
      )}
    </Drawer>
  );
}

// API testing module: this file only owns the inline debug result UI.
