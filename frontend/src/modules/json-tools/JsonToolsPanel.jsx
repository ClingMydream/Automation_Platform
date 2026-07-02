// File purpose: JSON tools page. Format, minify, copy, and compare JSON locally.
// How to change: edit UI text/layout in this file; move reusable logic into shared helpers or the module feature file.

import React, { useState } from 'react';
import { Alert, App as AntApp, Button, Card, Col, Input, Row, Space, Table, Tag } from 'antd';
import { CodeOutlined, CopyOutlined } from '@ant-design/icons';
import { compareJsonValues, parseJsonInput, stableStringifyJson } from '../../shared/jsonTools';

const { TextArea } = Input;

// JSON tool page: formats, minifies, and compares JSON locally in the browser.
export function JsonToolsPanel() {
  // State block: values here control loading, selection, form state, and visible page data.
  const [leftJson, setLeftJson] = useState('{\n  "name": "demo",\n  "enabled": true\n}');
  const [rightJson, setRightJson] = useState('{\n  "name": "demo",\n  "enabled": false,\n  "version": 1\n}');
  const [diffs, setDiffs] = useState([]);
  const [summary, setSummary] = useState('');
  const { message } = AntApp.useApp();

  // Format one side of the JSON editor.
  function formatSide(side) {
    try {
      const value = parseJsonInput(side === 'left' ? leftJson : rightJson);
      const formatted = stableStringifyJson(value);
      if (side === 'left') setLeftJson(formatted);
      else setRightJson(formatted);
      message.success('JSON 已格式化');
    } catch (err) {
      message.error(`JSON 格式错误：${err.message}`);
    }
  }

  // Minify one side of the JSON editor.
  function minifySide(side) {
    try {
      const value = parseJsonInput(side === 'left' ? leftJson : rightJson);
      const formatted = stableStringifyJson(value, true);
      if (side === 'left') setLeftJson(formatted);
      else setRightJson(formatted);
      message.success('JSON 已压缩');
    } catch (err) {
      message.error(`JSON 格式错误：${err.message}`);
    }
  }

  // Compare the left and right JSON values and update the diff table.
  function compare() {
    try {
      const left = parseJsonInput(leftJson);
      const right = parseJsonInput(rightJson);
      const result = compareJsonValues(left, right);
      setDiffs(result);
      setSummary(result.length === 0 ? '两段 JSON 完全一致' : `发现 ${result.length} 处差异`);
      message.success(result.length === 0 ? '两段 JSON 一致' : `发现 ${result.length} 处差异`);
    } catch (err) {
      message.error(`JSON 格式错误：${err.message}`);
    }
  }

  // Copy text to the clipboard and show feedback.
  function copy(text) {
    navigator.clipboard.writeText(text).then(() => message.success('已复制')).catch(() => message.warning('复制失败，请手动复制'));
  }

  // Render block: JSX below describes what the user sees on this page.
  return (
    <Space direction="vertical" size={16} className="full-width">
      <Alert type="info" showIcon message="JSON 内容只在当前浏览器处理，不会上传到服务器。对比会按字段路径递归检查对象、数组和值。" />
      <Row gutter={[16, 16]}>
        <Col xs={24} xl={12}>
          <Card title="左侧 JSON" extra={<Space><Button onClick={() => formatSide('left')}>格式化</Button><Button onClick={() => minifySide('left')}>压缩</Button><Button icon={<CopyOutlined />} onClick={() => copy(leftJson)}>复制</Button></Space>}>
            <TextArea rows={18} className="code-input" value={leftJson} onChange={(event) => setLeftJson(event.target.value)} />
          </Card>
        </Col>
        <Col xs={24} xl={12}>
          <Card title="右侧 JSON" extra={<Space><Button onClick={() => formatSide('right')}>格式化</Button><Button onClick={() => minifySide('right')}>压缩</Button><Button icon={<CopyOutlined />} onClick={() => copy(rightJson)}>复制</Button></Space>}>
            <TextArea rows={18} className="code-input" value={rightJson} onChange={(event) => setRightJson(event.target.value)} />
          </Card>
        </Col>
      </Row>
      <Card title="对比结果" extra={<Button type="primary" icon={<CodeOutlined />} onClick={compare}>开始对比</Button>}>
        {summary && <Alert className="tool-summary" type={diffs.length === 0 ? 'success' : 'warning'} showIcon message={summary} />}
        <Table
          rowKey={(record) => `${record.path}-${record.type}`}
          dataSource={diffs}
          pagination={{ pageSize: 10 }}
          scroll={{ x: 900 }}
          columns={[
            { title: '路径', dataIndex: 'path', width: 260 },
            { title: '差异类型', dataIndex: 'type', width: 120, render: (value) => <Tag color={value === '值不同' ? 'volcano' : 'blue'}>{value}</Tag> },
            { title: '左侧值', dataIndex: 'left', render: (value) => <pre className="inline-code">{value}</pre> },
            { title: '右侧值', dataIndex: 'right', render: (value) => <pre className="inline-code">{value}</pre> },
          ]}
        />
      </Card>
    </Space>
  );
}

// 转码工具模块：纯浏览器本地处理，适合处理接口参数和日志片段。

