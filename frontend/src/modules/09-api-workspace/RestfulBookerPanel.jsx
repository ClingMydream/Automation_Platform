import React, { useState } from 'react';
import { Alert, Button, Card, Col, DatePicker, Form, Input, Modal, Row, Space, Table, Tabs, Tag, Typography, message } from 'antd';
import { BookOutlined, CopyOutlined, HomeOutlined, SettingOutlined } from '@ant-design/icons';
import './api-workspace.css';
import './hotel-project.css';

const { Paragraph, Text, Title } = Typography;
const API_DOCS = 'https://restful-booker.herokuapp.com/apidoc/index.html';
const INITIAL_ROOMS = [
  { id: 1, number: '101', type: '标准大床房', price: 399, status: '可预订' },
  { id: 2, number: '202', type: '舒适双床房', price: 459, status: '可预订' },
  { id: 3, number: '303', type: '景观家庭房', price: 599, status: '维护中' },
];

export function RestfulBookerPanel() {
  const [rooms, setRooms] = useState(INITIAL_ROOMS);
  const [bookings, setBookings] = useState([]);
  const [bookingRoom, setBookingRoom] = useState(null);
  const [form] = Form.useForm();

  async function copyDocs() {
    await navigator.clipboard.writeText(API_DOCS);
    message.success('接口文档地址已复制');
  }

  async function submitBooking() {
    const values = await form.validateFields();
    const dates = values.dates || [];
    const booking = {
      id: Date.now(),
      room: bookingRoom.number,
      guest: values.guest,
      phone: values.phone,
      checkin: dates[0]?.format('YYYY-MM-DD'),
      checkout: dates[1]?.format('YYYY-MM-DD'),
      status: '已确认',
    };
    setBookings((rows) => [booking, ...rows]);
    setBookingRoom(null);
    form.resetFields();
    message.success('预约成功，可以到“管理后台”查看记录');
  }

  function removeBooking(id) {
    setBookings((rows) => rows.filter((row) => row.id !== id));
    message.success('预约已取消');
  }

  const frontDesk = <div className="hotel-demo">
    <Alert type="info" showIcon title="这是 cling 内置的中文练习项目，数据只用于当前页面练习。" />
    <div className="hotel-hero"><div><Text>欢迎来到</Text><Title level={2}>cling 小旅馆</Title><Paragraph>选择房间并完成一次中文预约流程。</Paragraph></div><span>🏨</span></div>
    <Row gutter={[16, 16]}>{rooms.map((room) => <Col xs={24} md={8} key={room.id}>
      <Card className="hotel-room-card" title={<Space><HomeOutlined /><b>{room.number} 房间</b></Space>}>
        <Paragraph>{room.type}</Paragraph><Title level={3}>¥{room.price}<small> / 晚</small></Title>
        <Tag color={room.status === '可预订' ? 'green' : 'default'}>{room.status}</Tag>
        <Button type="primary" block disabled={room.status !== '可预订'} onClick={() => setBookingRoom(room)}>立即预订</Button>
      </Card>
    </Col>)}</Row>
  </div>;

  const admin = <div className="hotel-admin">
    <Alert type="success" showIcon title="中文管理后台" description="前台提交的预约会立即显示在这里，刷新页面后练习数据会清空。" />
    <Card title="预约记录" className="record-card">
      <Table rowKey="id" dataSource={bookings} locale={{ emptyText: '还没有预约，请先到“预约前台”创建一条记录' }} pagination={false} columns={[
        { title: '房间', dataIndex: 'room', render: (value) => `${value} 房间` },
        { title: '住客姓名', dataIndex: 'guest' },
        { title: '联系电话', dataIndex: 'phone' },
        { title: '入住日期', dataIndex: 'checkin' },
        { title: '离店日期', dataIndex: 'checkout' },
        { title: '状态', dataIndex: 'status', render: (value) => <Tag color="green">{value}</Tag> },
        { title: '操作', render: (_, row) => <Button danger size="small" onClick={() => removeBooking(row.id)}>取消预约</Button> },
      ]} />
    </Card>
    <Card title="房间管理" className="record-card">
      <Table rowKey="id" dataSource={rooms} pagination={false} columns={[
        { title: '房间号', dataIndex: 'number' },
        { title: '房型', dataIndex: 'type' },
        { title: '价格', dataIndex: 'price', render: (value) => `¥${value}` },
        { title: '状态', dataIndex: 'status', render: (value) => <Tag color={value === '可预订' ? 'green' : 'default'}>{value}</Tag> },
        { title: '操作', render: (_, row) => <Button size="small" onClick={() => setRooms((items) => items.map((item) => item.id === row.id ? { ...item, status: item.status === '可预订' ? '维护中' : '可预订' } : item))}>切换状态</Button> },
      ]} />
    </Card>
  </div>;

  const docs = <Card title="Restful Booker 接口文档">
    <Paragraph>接口文档仍由原练习站提供，主要用于查询请求地址、方法、请求参数和返回结果。</Paragraph>
    <div className="quick-url">{API_DOCS}</div>
    <Space><Button icon={<CopyOutlined />} onClick={copyDocs}>复制地址</Button><Button type="primary" href={API_DOCS} target="_blank">打开接口文档</Button></Space>
  </Card>;

  return <div className="api-workspace">
    <div className="api-heading"><div><Text>全中文、简单易用</Text><Title level={2}>🏨 酒店练习项目</Title><Paragraph type="secondary">先在预约前台创建订单，再到管理后台查看和取消预约。</Paragraph></div></div>
    <Tabs items={[
      { key: 'front', label: <span><BookOutlined /> 预约前台</span>, children: frontDesk },
      { key: 'admin', label: <span><SettingOutlined /> 管理后台</span>, children: admin },
      { key: 'docs', label: <span><CopyOutlined /> 接口文档</span>, children: docs },
    ]} />
    <Modal open={Boolean(bookingRoom)} title={bookingRoom ? `预订 ${bookingRoom.number} · ${bookingRoom.type}` : '预订房间'} okText="确认预约" cancelText="取消" onOk={submitBooking} onCancel={() => { setBookingRoom(null); form.resetFields(); }}>
      <Form form={form} layout="vertical"><Form.Item name="guest" label="住客姓名" rules={[{ required: true, message: '请输入住客姓名' }]}><Input placeholder="例如：张三" /></Form.Item><Form.Item name="phone" label="联系电话" rules={[{ required: true, message: '请输入联系电话' }]}><Input placeholder="用于练习，可填写测试号码" /></Form.Item><Form.Item name="dates" label="入住和离店日期" rules={[{ required: true, message: '请选择入住和离店日期' }]}><DatePicker.RangePicker className="full-width" /></Form.Item></Form>
    </Modal>
  </div>;
}
