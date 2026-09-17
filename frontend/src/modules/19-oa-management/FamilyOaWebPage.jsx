import React, { useEffect, useMemo, useState } from 'react';
import { Alert, Avatar, Button, Card, DatePicker, Descriptions, Form, Input, List, Select, Space, Spin, Tag, Typography, Upload, message } from 'antd';
import { ArrowLeftOutlined, CheckOutlined, ClockCircleOutlined, CopyOutlined, EditOutlined, FileTextOutlined, HomeOutlined, LogoutOutlined, PlusOutlined, SendOutlined, UploadOutlined, UserOutlined, CloseOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { apiClient } from '../../shared/apiClient.js';
import './family-oa.css';

const { Title, Text } = Typography;
const SESSION_KEY = 'cling-family-oa-session';

const FALLBACK_TEMPLATES = [
  { key: 'leave', name: '游戏 / 出行申请', description: '提交玩游戏或出行的小申请', icon: '🌸', color: '#f69ab7', fields: [{ key: 'plan_type', label: '申请类型', type: 'select', options: ['游戏时间', '约会出行', '旅行计划', '其他'], required: true }, { key: 'game_name', label: '游戏名称', placeholder: '例如：双人成行', type: 'textarea' }, { key: 'start_date', label: '开始日期', type: 'date', required: true }, { key: 'end_date', label: '结束日期', type: 'date', required: true }, { key: 'reason', label: '计划说明', type: 'textarea', required: true }] },
  { key: 'purchase', name: '家庭采购', description: '申请一起添置喜欢的生活小物', icon: '🍓', color: '#f4b455', fields: [{ key: 'item_name', label: '想买的东西', placeholder: '想买的东西', type: 'textarea', required: true }, { key: 'amount', label: '预计金额', placeholder: '预计金额（元）', type: 'textarea', required: true }, { key: 'reason', label: '想买它的理由', type: 'textarea', required: true }] },
];

function statusLabel(status) { return ({ pending: '审批中', approved: '已通过', rejected: '已拒绝' }[status] || status); }
function statusColor(status) { return ({ pending: 'gold', approved: 'green', rejected: 'red' }[status] || 'default'); }
function initialSession() { try { return JSON.parse(sessionStorage.getItem(SESSION_KEY) || 'null'); } catch { return null; } }

export function FamilyOaWebPage({ embedded = false }) {
  const [session, setSession] = useState(initialSession);
  const [profile, setProfile] = useState(null);
  const [templates, setTemplates] = useState(FALLBACK_TEMPLATES);
  const [requests, setRequests] = useState([]);
  const [pending, setPending] = useState([]);
  const [view, setView] = useState('home');
  const [scope, setScope] = useState('mine');
  const [activeTemplate, setActiveTemplate] = useState(null);
  const [activeRequest, setActiveRequest] = useState(null);
  const [loading, setLoading] = useState(false);
  const [loginForm] = Form.useForm();
  const [applyForm] = Form.useForm();
  const [profileForm] = Form.useForm();
  const client = useMemo(() => apiClient(session?.access_token), [session]);

  function forgetSession() { sessionStorage.removeItem(SESSION_KEY); setSession(null); setProfile(null); setRequests([]); setPending([]); setView('home'); }
  async function load() {
    if (!session?.access_token) return;
    setLoading(true);
    try {
      const [remoteTemplates, currentProfile, mine, toReview] = await Promise.all([client.get('/oa/templates'), client.get('/oa/profile'), client.get('/oa/requests?scope=mine'), client.get('/oa/requests?scope=pending')]);
      if (Array.isArray(remoteTemplates) && remoteTemplates.length) setTemplates(remoteTemplates);
      setProfile(currentProfile); profileForm.setFieldsValue({ display_name: currentProfile.name, family_role: currentProfile.family_role });
      setRequests(mine); setPending(toReview);
    } catch (error) {
      if (!error.authExpired) message.error(error.message);
    } finally { setLoading(false); }
  }
  useEffect(() => { load(); }, [session?.access_token]);

  async function login(values) {
    setLoading(true);
    try {
      const data = await apiClient().post('/oa/auth/account-login', values);
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(data));
      setSession(data); message.success('登录成功');
    } catch (error) { message.error(error.message); } finally { setLoading(false); }
  }
  function openTemplate(template) { setActiveTemplate(template); applyForm.resetFields(); setView('apply'); }
  async function submitApplication(values) {
    const formData = Object.fromEntries(Object.entries(values).map(([key, value]) => [key, dayjs.isDayjs(value) ? value.format('YYYY-MM-DD') : value]));
    try { await client.post('/oa/requests', { template_key: activeTemplate.key, form_data: formData }); message.success('申请已提交'); setView('records'); setScope('mine'); load(); } catch (error) { message.error(error.message); }
  }
  function openRequest(item) { setActiveRequest(item); setView('detail'); }
  async function decide(action) {
    try { await client.post(`/oa/requests/${activeRequest.id}/decision`, { action, comment: '' }); message.success(action === 'approved' ? '已同意' : '已拒绝'); setView('records'); setScope('pending'); load(); } catch (error) { message.error(error.message); }
  }
  async function saveProfile(values) {
    try { const data = await client.put('/oa/profile', values); setSession(data); sessionStorage.setItem(SESSION_KEY, JSON.stringify(data)); setProfile(data.user); message.success('个人资料已保存'); } catch (error) { message.error(error.message); }
  }
  async function uploadAvatar({ file, onSuccess, onError }) {
    try { const body = new FormData(); body.append('file', file); const data = await client.post('/oa/profile/avatar', body); setProfile((current) => ({ ...current, avatar_url: data.avatar_url })); onSuccess?.(data); message.success('头像已更新'); } catch (error) { onError?.(error); message.error(error.message); }
  }
  function copyLink() { navigator.clipboard?.writeText(`${window.location.origin}/family-oa`).then(() => message.success('网页链接已复制')).catch(() => message.info('请复制浏览器地址栏中的链接')); }

  if (!session?.access_token) return <main className="family-oa-page family-oa-login"><Card className="family-oa-login-card"><div className="family-oa-brand"><span>♡</span><div><Title level={2}>莓好审批</Title><Text>把每一份小小的心意，轻轻送达。</Text></div></div><Alert type="info" showIcon message="网页版使用账号密码登录；微信一键登录请使用小程序。" style={{ marginBottom: 18 }} /><Form form={loginForm} layout="vertical" onFinish={login}><Form.Item name="username" label="账号" rules={[{ required: true, message: '请输入账号' }]}><Input size="large" placeholder="输入小程序账号" /></Form.Item><Form.Item name="password" label="密码" rules={[{ required: true, message: '请输入密码' }]}><Input.Password size="large" placeholder="输入密码" /></Form.Item><Button htmlType="submit" type="primary" size="large" block loading={loading}>登录莓好审批</Button></Form></Card></main>;

  const recordRows = scope === 'pending' ? pending : requests;
  const body = view === 'home' ? <><section className="family-oa-welcome"><div><Text>早安，{profile?.name || '宝宝'} ♡</Text><Title level={2}>今天也要轻轻松松完成<br />我们的小计划呀</Title></div><Avatar size={58} src={profile?.avatar_url} icon={<UserOutlined />} /></section><button type="button" className="family-oa-status" onClick={() => { setScope('pending'); setView('records'); }}><ClockCircleOutlined /><span><strong>待处理的申请</strong><small>你有 {pending.length} 条申请正在等待处理</small></span><span>›</span></button><section><div className="family-oa-heading"><Title level={4}>发起审批</Title><Button type="link" icon={<CopyOutlined />} onClick={copyLink}>复制网页链接</Button></div><div className="family-oa-template-grid">{templates.map((template) => <button type="button" className="family-oa-template" key={template.key} onClick={() => openTemplate(template)}><span style={{ background: `${template.color}24`, color: template.color }}>{template.icon}</span><strong>{template.name}</strong><small>{template.description}</small></button>)}</div></section></> : view === 'apply' ? <><Button type="text" icon={<ArrowLeftOutlined />} onClick={() => setView('home')}>返回工作台</Button><section className="family-oa-form-hero" style={{ background: activeTemplate?.color }}><span>{activeTemplate?.icon}</span><div><strong>{activeTemplate?.name}</strong><small>{activeTemplate?.description}</small></div></section><Card className="family-oa-form-card"><Form form={applyForm} layout="vertical" onFinish={submitApplication}>{activeTemplate?.fields.map((field) => <Form.Item key={field.key} name={field.key} label={field.label || field.placeholder} rules={field.required ? [{ required: true, message: `请填写${field.label || field.placeholder}` }] : []}>{field.type === 'select' ? <Select placeholder="请选择" options={(field.options || []).map((value) => ({ value, label: value }))} /> : field.type === 'date' ? <DatePicker style={{ width: '100%' }} placeholder="请选择日期" /> : <Input.TextArea autoSize={{ minRows: 2, maxRows: 5 }} placeholder={field.placeholder || '请填写'} />}</Form.Item>)}<Button htmlType="submit" type="primary" size="large" block icon={<SendOutlined />}>提交申请</Button></Form></Card></> : view === 'records' ? <><div className="family-oa-page-head"><Button type="text" icon={<ArrowLeftOutlined />} onClick={() => setView('home')}>工作台</Button><Title level={3}>{scope === 'pending' ? '待我审批' : '我发起的'}</Title></div><div className="family-oa-segment"><button className={scope === 'mine' ? 'active' : ''} onClick={() => setScope('mine')}>我发起的</button><button className={scope === 'pending' ? 'active' : ''} onClick={() => setScope('pending')}>待我审批</button></div><List className="family-oa-list" locale={{ emptyText: '🌷 暂时没有审批记录' }} dataSource={recordRows} renderItem={(item) => <List.Item onClick={() => openRequest(item)}><div><strong>{item.template.icon} {item.title}</strong><small>{item.request_no} · {new Date(item.created_at).toLocaleString()}</small></div><Tag color={statusColor(item.status)}>{statusLabel(item.status)}</Tag></List.Item>} /></> : view === 'detail' ? <><Button type="text" icon={<ArrowLeftOutlined />} onClick={() => setView('records')}>返回记录</Button><Card className="family-oa-detail"><Title level={3}>{activeRequest?.template.icon} {activeRequest?.title}</Title><Text type="secondary">{activeRequest?.request_no}</Text><Descriptions column={1} size="small" style={{ marginTop: 16 }}>{activeRequest?.template.fields.map((field) => <Descriptions.Item key={field.key} label={field.label || field.placeholder}>{activeRequest?.form_data?.[field.key] || '-'}</Descriptions.Item>)}</Descriptions></Card><Title level={4}>审批记录</Title><List className="family-oa-actions" dataSource={activeRequest?.actions || []} renderItem={(action) => <List.Item><div><strong>{action.actor_name} · {action.action === 'submitted' ? '提交申请' : statusLabel(action.action)}</strong><small>{action.comment || '无备注'} · {new Date(action.created_at).toLocaleString()}</small></div></List.Item>} />{scope === 'pending' && activeRequest?.status === 'pending' && <Space className="family-oa-decision" direction="vertical"><Button type="primary" size="large" icon={<CheckOutlined />} onClick={() => decide('approved')}>同意申请</Button><Button danger size="large" icon={<CloseOutlined />} onClick={() => decide('rejected')}>拒绝申请</Button></Space>}</> : <><div className="family-oa-page-head"><Button type="text" icon={<ArrowLeftOutlined />} onClick={() => setView('home')}>工作台</Button><Title level={3}>我的资料</Title></div><Card className="family-oa-profile"><div className="family-oa-avatar"><Upload showUploadList={false} accept="image/jpeg,image/png,image/webp" customRequest={uploadAvatar}><Avatar size={82} src={profile?.avatar_url} icon={<UserOutlined />} /><Button shape="circle" size="small" icon={<UploadOutlined />} /></Upload></div><Form form={profileForm} layout="vertical" onFinish={saveProfile}><Form.Item label="个人昵称" name="display_name" rules={[{ required: true, message: '请输入昵称' }]}><Input /></Form.Item><Form.Item label="家庭角色" name="family_role" rules={[{ required: true, message: '请输入家庭角色' }]}><Input placeholder="例如：宝宝、男朋友、女朋友" /></Form.Item><Button htmlType="submit" type="primary" block icon={<EditOutlined />}>保存资料</Button></Form></Card></>;

  return <main className={`family-oa-page ${embedded ? 'family-oa-embedded' : ''}`}><header className="family-oa-header"><button type="button" onClick={() => setView('home')}><span>♡</span><strong>莓好审批</strong></button><Space><Button type="text" icon={<CopyOutlined />} onClick={copyLink}>链接</Button><Button type="text" icon={<LogoutOutlined />} onClick={forgetSession}>退出</Button></Space></header>{loading && !profile ? <div className="family-oa-loading"><Spin /></div> : <section className="family-oa-shell">{body}</section>}<nav className="family-oa-nav"><button className={view === 'home' || view === 'apply' ? 'active' : ''} onClick={() => setView('home')}><HomeOutlined /><span>首页</span></button><button className={view === 'records' ? 'active' : ''} onClick={() => { setScope('mine'); setView('records'); }}><FileTextOutlined /><span>审批</span></button><button className={view === 'profile' ? 'active' : ''} onClick={() => setView('profile')}><UserOutlined /><span>我的</span></button></nav></main>;
}
