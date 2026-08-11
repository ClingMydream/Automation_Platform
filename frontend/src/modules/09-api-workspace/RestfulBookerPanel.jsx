import React, { useEffect, useState } from 'react';
import { Alert, Button, Card, Col, DatePicker, Form, Input, Modal, Row, Space, Table, Tabs, Tag, Typography, message } from 'antd';
import { BookOutlined, CopyOutlined, HomeOutlined, ReloadOutlined, SettingOutlined } from '@ant-design/icons';
import './api-workspace.css';
import './hotel-project.css';

const { Paragraph, Text, Title } = Typography;
const API = '/v1/hotel-practice';
const API_DOCS = 'https://restful-booker.herokuapp.com/apidoc/index.html';

export function RestfulBookerPanel({ client }) {
  const [rooms, setRooms] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [bookingRoom, setBookingRoom] = useState(null);
  const [loading, setLoading] = useState(true);
  const [form] = Form.useForm();

  async function load() {
    setLoading(true);
    try {
      const [roomRows, bookingRows] = await Promise.all([client.get(`${API}/rooms`), client.get(`${API}/bookings`)]);
      setRooms(roomRows);
      setBookings(bookingRows);
    } catch (error) {
      message.error(error.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function copyDocs() {
    await navigator.clipboard.writeText(API_DOCS);
    message.success('接口文档地址已复制');
  }

  async function submitBooking() {
    const values = await form.validateFields();
    try {
      await client.post(`${API}/bookings`, {
        room_id: bookingRoom.id,
        guest: values.guest,
        phone: values.phone,
        checkin: values.dates[0].format('YYYY-MM-DD'),
        checkout: values.dates[1].format('YYYY-MM-DD'),
      });
      setBookingRoom(null);
      form.resetFields();
      message.success('预约成功：已发送 POST 请求，可在 Network 中查看');
      await load();
    } catch (error) {
      message.error(error.message);
    }
  }

  async function removeBooking(id) {
    try {
      await client.delete(`${API}/bookings/${id}`);
      message.success('预约已取消：已发送 DELETE 请求');
      await load();
    } catch (error) { message.error(error.message); }
  }

  async function toggleRoom(room) {
    const status = room.status === '可预订' ? '维护中' : '可预订';
    try {
      await client.put(`${API}/rooms/${room.id}/status`, { status });
      message.success(`房态已更新为“${status}”：已发送 PUT 请求`);
      await load();
    } catch (error) { message.error(error.message); }
  }

  const frontDesk = <div className="hotel-demo">
    <Alert type="info" showIcon title="这是真实接口练习项目" description="打开浏览器 F12 → Network → Fetch/XHR。首次进入会看到 GET 请求；提交预约会看到 POST 请求。" />
    <div className="hotel-hero"><div><Text>欢迎来到</Text><Title level={2}>cling 小旅馆</Title><Paragraph>选择房间并完成一次中文预约流程。</Paragraph></div><span>🏨</span></div>
    <Row gutter={[16, 16]}>{rooms.map((room) => <Col xs={24} md={8} key={room.id}>
      <Card className="hotel-room-card" title={<Space><HomeOutlined /><b>{room.number} 房间</b></Space>}>
        <Paragraph>{room.room_type}</Paragraph><Title level={3}>¥{room.price}<small> / 晚</small></Title>
        <Tag color={room.status === '可预订' ? 'green' : 'default'}>{room.status}</Tag>
        <Button type="primary" block disabled={room.status !== '可预订'} onClick={() => setBookingRoom(room)}>立即预订</Button>
      </Card>
    </Col>)}</Row>
  </div>;

  const admin = <div className="hotel-admin">
    <Alert type="success" showIcon title="中文管理后台" description="前台预约会通过接口保存；刷新页面后记录仍会保留。" />
    <Card title="预约记录" className="record-card" extra={<Button icon={<ReloadOutlined />} onClick={load}>刷新数据</Button>}>
      <Table loading={loading} rowKey="id" dataSource={bookings} locale={{ emptyText: '还没有预约，请先到“预约前台”创建一条记录' }} pagination={false} columns={[
        { title: '房间', dataIndex: 'room_number', render: (value) => `${value} 房间` },
        { title: '住客姓名', dataIndex: 'guest' }, { title: '联系电话', dataIndex: 'phone' },
        { title: '入住日期', dataIndex: 'checkin' }, { title: '离店日期', dataIndex: 'checkout' },
        { title: '状态', dataIndex: 'status', render: (value) => <Tag color="green">{value}</Tag> },
        { title: '操作', render: (_, row) => <Button danger size="small" onClick={() => removeBooking(row.id)}>取消预约</Button> },
      ]} />
    </Card>
    <Card title="房间管理" className="record-card">
      <Table loading={loading} rowKey="id" dataSource={rooms} pagination={false} columns={[
        { title: '房间号', dataIndex: 'number' }, { title: '房型', dataIndex: 'room_type' },
        { title: '价格', dataIndex: 'price', render: (value) => `¥${value}` },
        { title: '状态', dataIndex: 'status', render: (value) => <Tag color={value === '可预订' ? 'green' : 'default'}>{value}</Tag> },
        { title: '操作', render: (_, row) => <Button size="small" onClick={() => toggleRoom(row)}>切换状态</Button> },
      ]} />
    </Card>
  </div>;

  const docs = <Card title="Restful Booker 接口文档">
    <Paragraph>这里是 cling 的中文练习接口；Restful Booker 原始公开文档可用于继续练习请求方法、参数和响应。</Paragraph>
    <div className="quick-url">{API_DOCS}</div>
    <Space><Button icon={<CopyOutlined />} onClick={copyDocs}>复制地址</Button><Button type="primary" href={API_DOCS} target="_blank">打开接口文档</Button></Space>
  </Card>;

  return <div className="api-workspace">
    <div className="api-heading"><div><Text>全中文、真实请求</Text><Title level={2}>🏨 酒店练习项目</Title><Paragraph type="secondary">前台与后台都会调用接口，适合在浏览器 Network 中练习查看 GET、POST、PUT、DELETE。</Paragraph></div></div>
    <Tabs items={[
      { key: 'front', label: <span><BookOutlined /> 预约前台</span>, children: frontDesk },
      { key: 'admin', label: <span><SettingOutlined /> 管理后台</span>, children: admin },
      { key: 'docs', label: <span><CopyOutlined /> 接口文档</span>, children: docs },
    ]} />
    <Modal open={Boolean(bookingRoom)} title={bookingRoom ? `预订 ${bookingRoom.number} · ${bookingRoom.room_type}` : '预订房间'} okText="确认预约" cancelText="取消" onOk={submitBooking} onCancel={() => { setBookingRoom(null); form.resetFields(); }}>
      <Form form={form} layout="vertical"><Form.Item name="guest" label="住客姓名" rules={[{ required: true, message: '请输入住客姓名' }]}><Input placeholder="例如：张三" /></Form.Item><Form.Item name="phone" label="联系电话" rules={[{ required: true, message: '请输入联系电话' }]}><Input placeholder="用于练习，可填写测试号码" /></Form.Item><Form.Item name="dates" label="入住和离店日期" rules={[{ required: true, message: '请选择入住和离店日期' }]}><DatePicker.RangePicker className="full-width" /></Form.Item></Form>
    </Modal>
  </div>;
}
