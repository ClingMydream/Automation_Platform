import React from 'react';
import { Tag } from 'antd';
import { statusColor } from './formatters';

// 执行状态标签。执行记录、测试报告、实时窗口共用同一套颜色规则。
export function StatusTag({ status }) {
  return <Tag color={statusColor(status)}>{status || 'queued'}</Tag>;
}
