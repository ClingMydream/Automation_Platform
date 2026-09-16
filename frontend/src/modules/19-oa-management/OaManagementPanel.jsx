import React, { useEffect, useState } from 'react';
import { Alert, Card, Switch, Table, Typography, message } from 'antd';

export function OaManagementPanel({ client }) {
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(false);
  async function load() { setLoading(true); try { setAccounts(await client.get('/oa/admin/accounts')); } catch (error) { message.error(error.message); } finally { setLoading(false); } }
  useEffect(() => { load(); }, []);
  async function save(record, patch) { try { await client.put(`/oa/admin/accounts/${record.id}`, { is_enabled: record.is_enabled, is_reviewer: record.is_reviewer, ...patch }); message.success('已保存'); load(); } catch (error) { message.error(error.message); } }
  return <Card title="🌸 小程序 OA 管理" extra="小程序用户首次微信登录后会出现在这里"><Alert type="info" showIcon message="被审核人是所有已启用的小程序账号；打开“审核人”后，该账号可处理对方提交的申请。" style={{ marginBottom: 16 }} /><Table rowKey="id" loading={loading} dataSource={accounts} pagination={false} columns={[{ title: '小程序账号', dataIndex: 'name' }, { title: '状态', render: (_, r) => <Switch checked={r.is_enabled} checkedChildren="启用" unCheckedChildren="停用" onChange={(is_enabled) => save(r, { is_enabled })} /> }, { title: '审核人', render: (_, r) => <Switch checked={r.is_reviewer} checkedChildren="是" unCheckedChildren="否" onChange={(is_reviewer) => save(r, { is_reviewer })} /> }, { title: '首次登录', dataIndex: 'created_at', render: (v) => new Date(v).toLocaleString() }]} /><Typography.Paragraph type="secondary" style={{ marginTop: 16 }}>请先让对方从小程序完成一次微信授权登录，再回到此页设置其审核权限。</Typography.Paragraph></Card>;
}
