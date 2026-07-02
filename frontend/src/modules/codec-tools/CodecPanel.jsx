// File purpose: Codec tools page. Convert text locally without sending content to the backend.
// How to change: edit UI text/layout in this file; move reusable logic into shared helpers or the module feature file.

import React, { useState } from 'react';
import { Alert, App as AntApp, Button, Card, Col, Input, Row, Select, Space } from 'antd';
import { CopyOutlined, SwapOutlined } from '@ant-design/icons';
import { runCodec } from '../../shared/codec';

const { TextArea } = Input;

// Codec tool page: runs common encode and decode operations locally.
export function CodecPanel() {
  // State block: values here control loading, selection, form state, and visible page data.
  const [operation, setOperation] = useState('url_encode');
  const [input, setInput] = useState('中文参数 test=123');
  const [output, setOutput] = useState('');
  const { message } = AntApp.useApp();
  const options = [
    { value: 'url_encode', label: 'URL 编码' },
    { value: 'url_decode', label: 'URL 解码' },
    { value: 'base64_encode', label: 'Base64 编码' },
    { value: 'base64_decode', label: 'Base64 解码' },
    { value: 'base64url_encode', label: 'Base64URL 编码' },
    { value: 'base64url_decode', label: 'Base64URL 解码' },
    { value: 'unicode_escape', label: 'Unicode 转义' },
    { value: 'unicode_unescape', label: 'Unicode 反转义' },
    { value: 'html_encode', label: 'HTML 实体编码' },
    { value: 'html_decode', label: 'HTML 实体解码' },
    { value: 'hex_encode', label: 'Hex 编码' },
    { value: 'hex_decode', label: 'Hex 解码' },
    { value: 'json_escape', label: 'JSON 字符串转义' },
    { value: 'json_unescape', label: 'JSON 字符串反转义' },
  ];

  // Run the selected codec operation and write the output.
  function convert() {
    try {
      setOutput(runCodec(operation, input));
      message.success('转码完成');
    } catch (err) {
      message.error(`转码失败：${err.message}`);
    }
  }

  // Copy text to the clipboard and show feedback.
  function copy(text) {
    navigator.clipboard.writeText(text).then(() => message.success('已复制')).catch(() => message.warning('复制失败，请手动复制'));
  }

  // Swap input and output values in the codec tool.
  function swap() {
    setInput(output);
    setOutput(input);
  }

  // Render block: JSX below describes what the user sees on this page.
  return (
    <Space direction="vertical" size={16} className="full-width">
      <Alert type="info" showIcon message="转码内容只在当前浏览器处理，不会上传到服务器。适合处理接口参数、Token 片段、日志文本和配置片段。" />
      <Card title="通用转码">
        <Space direction="vertical" size={14} className="full-width">
          <Row gutter={[12, 12]}>
            <Col xs={24} md={12}>
              <Select className="full-width" value={operation} onChange={setOperation} options={options} />
            </Col>
            <Col xs={24} md={12}>
              <Space wrap>
                <Button type="primary" icon={<SwapOutlined />} onClick={convert}>执行转码</Button>
                <Button icon={<SwapOutlined />} onClick={swap} disabled={!output}>输入/输出互换</Button>
              </Space>
            </Col>
          </Row>
          <Row gutter={[16, 16]}>
            <Col xs={24} xl={12}>
              <Card size="small" title="输入" extra={<Button icon={<CopyOutlined />} onClick={() => copy(input)}>复制</Button>}>
                <TextArea rows={15} className="code-input" value={input} onChange={(event) => setInput(event.target.value)} />
              </Card>
            </Col>
            <Col xs={24} xl={12}>
              <Card size="small" title="输出" extra={<Button icon={<CopyOutlined />} disabled={!output} onClick={() => copy(output)}>复制</Button>}>
                <TextArea rows={15} className="code-input" value={output} onChange={(event) => setOutput(event.target.value)} />
              </Card>
            </Col>
          </Row>
        </Space>
      </Card>
    </Space>
  );
}

// UI 实时执行窗口：新窗口展示 UI 自动化运行过程和最新截图。

