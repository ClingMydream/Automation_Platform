import React, { useEffect, useState } from 'react';
import { Alert, Button, Card, Col, DatePicker, Form, Input, Modal, Row, Space, Table, Tabs, Tag, Typography, message } from 'antd';
import { BookOutlined, CopyOutlined, HomeOutlined, ReloadOutlined, SettingOutlined } from '@ant-design/icons';
import './api-workspace.css';
import './hotel-project.css';

const { Paragraph, Text, Title } = Typography;
const API = '/v1/hotel-practice';
const BOOKER_BASE_URL = `${window.location.origin}/booker`;
const API_DOCS = `${BOOKER_BASE_URL}/apidoc/index.html`;

async function bookerRequest(path, options = {}) {
  const response = await fetch(`${BOOKER_BASE_URL}${path}`, {
    ...options,
    headers: { Accept: 'application/json', ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...(options.headers || {}) },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.message || `自建 Restful Booker 返回 HTTP ${response.status}`);
  return body;
}

function toBookingRow(bookingid, booking) {
  return {
    id: bookingid,
    room: booking.additionalneeds?.match(/房间[：:](\S+)/)?.[1] || '练习预约',
    guest: `${booking.firstname || ''} ${booking.lastname || ''}`.trim(),
    phone: booking.additionalneeds?.match(/电话[：:]([^;；]+)/)?.[1] || '未填写',
    checkin: booking.bookingdates?.checkin,
    checkout: booking.bookingdates?.checkout,
    status: booking.depositpaid ? '已确认' : '待确认',
  };
}

export function RestfulBookerPanel({ client }) {
  const [rooms, setRooms] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [bookingRoom, setBookingRoom] = useState(null);
  const [loading, setLoading] = useState(true);
  const [apiResponse, setApiResponse] = useState(null);
  const [bookingToken, setBookingToken] = useState('');
  const [form] = Form.useForm();

  async function load() {
    setLoading(true);
    try {
      const [roomRows, bookingIds] = await Promise.all([client.get(`${API}/rooms`), bookerRequest('/booking')]);
      const bookingRows = await Promise.all(bookingIds.map(async ({ bookingid }) => toBookingRow(bookingid, await bookerRequest(`/booking/${bookingid}`))));
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

  async function runBookingExample(url, label) {
    setApiResponse({ label, loading: true });
    try {
      const response = await fetch(url);
      const body = await response.json();
      setApiResponse({ label, status: response.status, body });
    } catch (error) {
      setApiResponse({ label, error: '请求失败：' + error.message });
    }
  }

  async function submitBooking() {
    const values = await form.validateFields();
    try {
      const [firstname, ...lastNameParts] = values.guest.trim().split(/\s+/);
      await bookerRequest('/booking', {
        method: 'POST',
        body: JSON.stringify({
          firstname,
          lastname: lastNameParts.join(' ') || '测试',
          totalprice: bookingRoom.price,
          depositpaid: true,
          bookingdates: { checkin: values.dates[0].format('YYYY-MM-DD'), checkout: values.dates[1].format('YYYY-MM-DD') },
          additionalneeds: `房间：${bookingRoom.number}; 电话：${values.phone}`,
        }),
      });
      setBookingRoom(null);
      form.resetFields();
      message.success('预约成功：已写入自建 Restful Booker，可在 /booker/booking 查看');
      await load();
    } catch (error) {
      message.error(error.message);
    }
  }

  async function removeBooking(id) {
    try {
      if (!bookingToken.trim()) throw new Error('请先粘贴通过 POST /booker/auth 获取的 token');
      await bookerRequest(`/booking/${id}`, { method: 'DELETE', headers: { Cookie: `token=${bookingToken.trim()}` } });
      message.success('预约已取消：已从自建 Restful Booker 删除');
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
      <Alert type="info" showIcon message="这里的数据与 /booker/booking 完全相同" description="创建预约后会立即同步。若要取消预约，请先在 Postman 调用 POST /booker/auth，并把返回的 token 临时粘贴到下方；token 不会保存。" style={{ marginBottom: 16 }} />
      <Input.Password value={bookingToken} onChange={event => setBookingToken(event.target.value)} placeholder="取消预约用的 token（仅当前页面临时使用）" style={{ maxWidth: 440, marginBottom: 16 }} />
      <Table loading={loading} rowKey="id" dataSource={bookings} locale={{ emptyText: '还没有预约，请先到“预约前台”创建一条记录' }} pagination={false} columns={[
        { title: '房间', dataIndex: 'room_number', render: (value) => `${value} 房间` },
        { title: '住客姓名', dataIndex: 'guest' }, { title: '联系电话', dataIndex: 'phone' },
        { title: '入住日期', dataIndex: 'checkin' }, { title: '离店日期', dataIndex: 'checkout' },
        { title: '状态', dataIndex: 'status', render: (value) => <Tag color="green">{value}</Tag> },
        { title: '操作', render: (_, row) => <Button danger size="small" disabled={!bookingToken.trim()} onClick={() => removeBooking(row.id)}>取消预约</Button> },
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

  const docs = <div className="hotel-api-guide">
    <Alert type="info" showIcon title="中文接口引导 + 真实响应" description="下面的按钮会直接请求 Restful Booker 公共接口。按 F12 → Network 可同时观察请求和响应。" />
    <Card title="1. 先认识 Booking 接口" className="record-card">
      <Table pagination={false} rowKey="url" columns={[{ title: '你要做什么', dataIndex: 'purpose' }, { title: '方法', dataIndex: 'method', render: value => <Tag color="blue">{value}</Tag> }, { title: '地址', dataIndex: 'url', render: value => <code>{value}</code> }, { title: '响应怎么看', dataIndex: 'response' }, { title: '练习', render: (_, row) => <Button onClick={() => runBookingExample(row.url, row.purpose)}>发送请求</Button> }]} dataSource={[
        { purpose: '查询所有预约编号', method: 'GET', url: `${BOOKER_BASE_URL}/booking`, response: '200 表示成功；数组中每一项的 bookingid 是预约编号。' },
        { purpose: '查询一条预约详情', method: 'GET', url: `${BOOKER_BASE_URL}/booking/1`, response: '200 表示找到数据；404 表示该编号不存在，可先从上一条响应中复制编号。' },
      ]} />
    </Card>
    <Card title="2. 看懂一次响应" className="record-card">
      {!apiResponse && <Paragraph type="secondary">点击上面的“发送请求”，这里会显示真实响应。重点先看状态码，再看 JSON 中的字段。</Paragraph>}
      {apiResponse?.loading && <Paragraph>正在发送 {apiResponse.label}…</Paragraph>}
      {apiResponse?.error && <Alert type="error" showIcon title={apiResponse.error} />}
      {apiResponse?.status && <><Space><b>{apiResponse.label}</b><Tag color={apiResponse.status >= 200 && apiResponse.status < 300 ? 'green' : 'red'}>HTTP {apiResponse.status}</Tag></Space><pre className="guide-code"><code>{JSON.stringify(apiResponse.body, null, 2)}</code></pre><Paragraph><b>小白解读：</b>状态码 200 表示服务器成功返回；方括号 <code>[]</code> 是列表，花括号 <code>{'{}'}</code> 是一条对象数据。先找 <code>bookingid</code>，它就是后续查询、修改、删除时会用到的编号。</Paragraph></>}
    </Card>
    <Card title="3. 后续怎么练习" className="record-card">
      <Paragraph>先用 GET 取得一个 bookingid；再到 Postman 用这个编号查询详情。创建、修改、删除会改变公开练习站的数据，建议先在 cling 中文酒店项目中练习完整 CRUD，再阅读官方原始文档对照参数。</Paragraph>
      <div className="quick-url">{API_DOCS}</div>
      <Space><Button icon={<CopyOutlined />} onClick={copyDocs}>复制官方文档地址</Button><Button type="primary" href={API_DOCS} target="_blank">打开官方英文文档</Button></Space>
    </Card>
  </div>;

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
