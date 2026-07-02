// File purpose: Shared status tag component for run and report states.
// How to change: edit UI text/layout in this file; move reusable logic into shared helpers or the module feature file.

import React from 'react';
import { Tag } from 'antd';
import { statusColor } from './formatters';

// 执行状态标签。执行记录、测试报告、实时窗口共用同一套颜色规则。
// Shared helper block: exported helpers below are reused by multiple modules.
export function StatusTag({ status }) {
  return <Tag color={statusColor(status)}>{status || 'queued'}</Tag>;
}
