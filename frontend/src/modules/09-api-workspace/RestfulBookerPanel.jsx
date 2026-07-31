import React from 'react';
import { Button, Card, Col, Row, Space, Tag, Typography, message } from 'antd';
import { CopyOutlined, ExportOutlined } from '@ant-design/icons';
import './api-workspace.css';

const { Paragraph, Text, Title } = Typography;
const ENDPOINTS = [
  { name: '酒店预约前台', method: '页面', url: 'https://automationintesting.online/', note: '浏览房间并完成一次预约。' },
  { name: '酒店管理后台', method: '后台', url: 'https://automationintesting.online/#/admin', note: '查看和管理房间、预约与消息。' },
  { name: '接口说明文档', method: '文档', url: 'https://restful-booker.herokuapp.com/apidoc/index.html', note: '查看接口地址、参数和返回结果。' },
];

export function RestfulBookerPanel() {
  async function copy(url) {
    await navigator.clipboard.writeText(url);
    message.success('地址已复制');
  }

  return <div className="api-workspace">
    <div className="api-heading"><div><Text>简单、可直接使用的练习项目</Text><Title level={2}>🏨 酒店练习项目</Title><Paragraph type="secondary">先从预约前台了解业务，再根据学习任务使用后台或接口文档。</Paragraph></div></div>
    <Row gutter={[14, 14]} className="quick-grid">{ENDPOINTS.map((item) => <Col xs={24} md={8} key={`${item.method}-${item.name}`}>
      <Card className="quick-api" title={<Space><Tag color={item.method === 'GET' ? 'green' : item.method === 'POST' ? 'blue' : 'purple'}>{item.method}</Tag><b>{item.name}</b></Space>}>
        <Paragraph>{item.note}</Paragraph><div className="quick-url">{item.url}</div>
        <Space><Button icon={<CopyOutlined />} onClick={() => copy(item.url)}>复制</Button><Button type="primary" icon={<ExportOutlined />} onClick={() => window.open(item.url, '_blank', 'noopener,noreferrer')}>打开</Button></Space>
      </Card>
    </Col>)}</Row>
  </div>;
}
