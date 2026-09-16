import React, { useEffect, useState } from 'react';
import { Alert, Card, Select, Switch, Table, Typography, message } from 'antd';

export function OaManagementPanel({ client }) {
  const [accounts, setAccounts] = useState([]);
  const [reviewerId, setReviewerId] = useState(null);
  const [loading, setLoading] = useState(false);
  async function load() { setLoading(true); try { const data = await client.get('/oa/admin/accounts'); setAccounts(data.accounts || []); setReviewerId(data.reviewer_account_id || null); } catch (error) { message.error(error.message); } finally { setLoading(false); } }
  useEffect(() => { load(); }, []);
  async function save(record, patch) { try { await client.put(`/oa/admin/accounts/${record.id}`, { is_enabled: record.is_enabled, ...patch }); message.success('已保存'); load(); } catch (error) { message.error(error.message); } }
  async function setReviewer(accountId) { try { await client.put('/oa/admin/reviewer', { account_id: accountId || null }); message.success('审核人已更新'); load(); } catch (error) { message.error(error.message); } }
  return <Card title="🌸 小程序 OA 管理" extra="登录后自动建立小程序账号"><Alert type="info" showIcon message="账号登录和微信一键登录都会建立人员档案。请选择一位已启用的小程序用户作为审核人。" style={{ marginBottom: 16 }} /><Typography.Text strong>指定审核人：</Typography.Text><Select allowClear placeholder="从小程序用户中选择审核人" value={reviewerId} onChange={setReviewer} style={{ minWidth: 280, margin: '0 0 16px 12px' }} options={accounts.filter((item) => item.is_enabled).map((item) => ({ value: item.id, label: `${item.name}（${item.login_method}）` }))} /><Table rowKey="id" loading={loading} dataSource={accounts} pagination={false} columns={[{ title: '小程序账号', dataIndex: 'name' }, { title: '登录方式', dataIndex: 'login_method' }, { title: '状态', render: (_, r) => <Switch checked={r.is_enabled} checkedChildren="启用" unCheckedChildren="停用" onChange={(is_enabled) => save(r, { is_enabled })} /> }, { title: '首次登录', dataIndex: 'created_at', render: (v) => new Date(v).toLocaleString() }]} /><Typography.Paragraph type="secondary" style={{ marginTop: 16 }}>人员可使用平台账号密码或微信一键登录。首次成功登录后会自动出现在上方列表，随后即可在下拉框中指定审核人。</Typography.Paragraph></Card>;
}
