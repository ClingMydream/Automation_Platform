import React, { useEffect, useState } from 'react';
import { Alert, Card, Select, Switch, Table, Typography, message } from 'antd';

export function OaManagementPanel({ client }) {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(false);
  async function load() { setLoading(true); try { const data = await client.get('/oa/admin/accounts'); setAccounts(data.accounts || []); } catch (error) { message.error(error.message); } finally { setLoading(false); } }
  useEffect(() => { load(); }, []);
  async function save(record, patch) { try { await client.put(`/oa/admin/accounts/${record.id}`, { is_enabled: record.is_enabled, ...patch }); message.success('已保存'); load(); } catch (error) { message.error(error.message); } }
  return <Card title="🌸 小程序 OA 管理"><Alert type="info" showIcon message="请在每位人员的“审核人”列中，选择可处理其申请的小程序用户；可选择多人。" style={{ marginBottom: 16 }} /><Table rowKey="id" loading={loading} dataSource={accounts} pagination={false} columns={[{ title: '小程序账号', dataIndex: 'name' }, { title: '登录方式', dataIndex: 'login_method' }, { title: '审核人', render: (_, r) => <Select mode="multiple" placeholder="选择审核人" value={r.approver_account_ids || []} onChange={(approver_account_ids) => save(r, { approver_account_ids })} style={{ minWidth: 260 }} options={accounts.filter((item) => item.is_enabled && item.id !== r.id).map((item) => ({ value: item.id, label: `${item.name}（${item.login_method}）` }))} /> }, { title: '状态', render: (_, r) => <Switch checked={r.is_enabled} checkedChildren="启用" unCheckedChildren="停用" onChange={(is_enabled) => save(r, { is_enabled, approver_account_ids: r.approver_account_ids || [] })} /> }, { title: '首次登录', dataIndex: 'created_at', render: (v) => new Date(v).toLocaleString() }]} /><Typography.Paragraph type="secondary" style={{ marginTop: 16 }}>例如：可为 A 选择 B、C 作为审核人；也可为 B 单独选择 A、C。</Typography.Paragraph></Card>;
}
