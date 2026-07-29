import React from 'react';
import { Button, Card, Col, Row, Space, Tag, Typography, message } from 'antd';
import { CopyOutlined, ExportOutlined } from '@ant-design/icons';
import './api-workspace.css';

const { Paragraph, Text, Title } = Typography;
const ENDPOINTS = [
  { name: '官方 API 文档', method: 'DOCS', url: 'https://restful-booker.herokuapp.com/apidoc/index.html', note: '查看接口参数、请求体和响应示例。' },
  { name: 'Booking 列表', method: 'GET', url: 'https://restful-booker.herokuapp.com/booking', note: '浏览器可直接打开，用于确认服务是否可用。' },
  { name: '获取登录 Token', method: 'POST', url: 'https://restful-booker.herokuapp.com/auth', note: '在 Postman 或 pytest 中练习登录鉴权。' },
  { name: '创建 Booking', method: 'POST', url: 'https://restful-booker.herokuapp.com/booking', note: '练习 JSON 请求体和新增接口断言。' },
];

export function RestfulBookerPanel() {
  async function copy(url) {
    await navigator.clipboard.writeText(url);
    message.success('地址已复制');
  }

  return <div className="api-workspace">
    <div className="api-heading"><div><Text>常驻接口练习环境</Text><Title level={2}>🏨 Restful Booker 调试</Title><Paragraph type="secondary">先打开文档了解接口；GET 地址可以直接打开，POST 请求请使用 Postman 或 pytest。</Paragraph></div></div>
    <Row gutter={[14, 14]} className="quick-grid">{ENDPOINTS.map((item) => <Col xs={24} md={12} key={`${item.method}-${item.name}`}>
      <Card className="quick-api" title={<Space><Tag color={item.method === 'GET' ? 'green' : item.method === 'POST' ? 'blue' : 'purple'}>{item.method}</Tag><b>{item.name}</b></Space>}>
        <Paragraph>{item.note}</Paragraph><div className="quick-url">{item.url}</div>
        <Space><Button icon={<CopyOutlined />} onClick={() => copy(item.url)}>复制地址</Button><Button type="primary" icon={<ExportOutlined />} onClick={() => window.open(item.url, '_blank', 'noopener,noreferrer')}>打开页面</Button></Space>
      </Card>
    </Col>)}</Row>
  </div>;
}
