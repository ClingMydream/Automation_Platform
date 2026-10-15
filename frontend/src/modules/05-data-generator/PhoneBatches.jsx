import React, { useEffect, useRef, useState } from 'react';
import { App, Button, Card, Input, Modal, Popconfirm, Space, Table, Typography } from 'antd';

const base = '/v1/tools/data-generator/batches';
export function PhoneBatches({ client, rows, onRowsChange }) {
  const { message, modal } = App.useApp();
  const [items, setItems] = useState([]);
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [draft, setDraft] = useState(null);
  const [busy, setBusy] = useState(false);
  const loadSequence = useRef(0);
  const [error, setError] = useState('');
  async function load(search = query, current = page) {
    const sequence = ++loadSequence.current;
    try {
      const data = await client.get(`${base}?q=${encodeURIComponent(search)}&page=${current}`);
      if (sequence !== loadSequence.current) return;
      setItems(data.items); setTotal(data.total); setError('');
    } catch (e) { if (sequence === loadSequence.current) setError(e.message); }
  }
  useEffect(() => { load(); }, [client, page]);
  function changeRow(index, patch) {
    setDraft(d => ({ ...d, rows: d.rows.map((r, i) => i === index ? { ...r, ...patch } : r) }));
  }
  async function save() {
    setBusy(true);
    try {
      const body = { ...draft, rows: draft.rows.map(({ phone, remark }) => ({ phone, remark: remark || '' })) };
      if (draft.id) await client.put(`${base}/${draft.id}`, body);
      else await client.post(base, body);
      message.success('批次已保存'); setDraft(null); await load();
    } catch (e) { message.error(e.message); } finally { setBusy(false); }
  }
  async function open(item) {
    try { const d = await client.get(`${base}/${item.id}`); setDraft({ ...d, rows: d.rows.map(r => ({ ...r, _key: r.phone })) }); } catch (e) { message.error(e.message); }
  }
  function close() {
    modal.confirm({ title: '放弃尚未保存的修改？', onOk: () => setDraft(null), okText: '放弃修改', cancelText: '继续编辑' });
  }
  async function addRow() {
    setBusy(true);
    try {
      const data = await client.post('/v1/tools/data-generator', { kind: 'phone', count: 1, phone_mode: 'synthetic' });
      setDraft(d => ({ ...d, rows: [...d.rows, { phone: data.rows[0].phone, _key: data.rows[0].phone, remark: '' }] }));
    } catch (e) { message.error(e.message); } finally { setBusy(false); }
  }
  return <Card title="已保存的虚拟账号批次" style={{ marginTop: 24 }} extra={<Button disabled={!rows.length} onClick={() => setDraft({ name: `测试账号 ${new Date().toLocaleString()}`, remark: '', rows: rows.map(r => ({ phone: r.phone, _key: r.phone, remark: r.remark || '' })), request_id: crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`, revision: 1 })}>保存当前批次</Button>}>
    <Space wrap style={{ marginBottom: 16 }}><Input.Search aria-label="查询批次" placeholder="搜索名称、号码或备注" value={query} onChange={e => setQuery(e.target.value)} onSearch={() => { setPage(1); load(query, 1); }} enterButton="查询" /><Button onClick={() => load()}>刷新</Button></Space>
    {error && <Typography.Paragraph type="danger">加载失败：{error}，请点击刷新重试。</Typography.Paragraph>}
    <Table rowKey="id" dataSource={items} scroll={{ x: 650 }} pagination={{ current: page, total, pageSize: 10, onChange: setPage }} columns={[
      { title: '批次名称', dataIndex: 'name' }, { title: '数量', render: (_, r) => r.rows.length }, { title: '备注', dataIndex: 'remark', ellipsis: true },
      { title: '操作', render: (_, r) => <Space><Button onClick={() => open(r)}>查看 / 编辑</Button><Button onClick={async () => { try { const d = await client.get(`${base}/${r.id}`); onRowsChange(d.rows); message.success('已载入生成结果'); } catch(e) { message.error(e.message); } }}>载入 / 导出</Button><Popconfirm title="删除整个批次？无法撤销。" onConfirm={async () => { try { await client.delete(`${base}/${r.id}?revision=${r.revision}`); await load(); } catch (e) { message.error(e.message); } }}><Button danger>删除</Button></Popconfirm></Space> },
    ]} />
    <Modal title={draft?.id ? '查看 / 编辑账号批次' : '保存虚拟账号批次'} open={!!draft} onCancel={busy ? undefined : close} onOk={save} confirmLoading={busy} okButtonProps={{ disabled: !draft?.name?.trim() || !draft?.rows.length }} okText="保存" cancelText="取消" width={900} mask={{ closable: false }} styles={{ body: { maxHeight: '65vh', overflowY: 'auto' } }}>
      {draft && <Space orientation="vertical" style={{ width: '100%' }}>
        <Typography.Text>批次名称</Typography.Text><Input aria-label="批次名称" maxLength={120} value={draft.name} onChange={e => setDraft(d => ({ ...d, name: e.target.value }))} />
        <Typography.Text>批次备注（选填）</Typography.Text><Input.TextArea aria-label="批次备注" maxLength={2000} value={draft.remark} onChange={e => setDraft(d => ({ ...d, remark: e.target.value }))} />
        <Button disabled={busy || draft.rows.length >= 100} onClick={addRow}>新增虚拟账号</Button>
        <Table rowKey="_key" dataSource={draft.rows} pagination={{ pageSize: 5 }} scroll={{ x: 650 }} columns={[
          { title: '虚拟手机号', dataIndex: 'phone', render: (v, r, i) => <Input aria-label={`虚拟手机号 ${i + 1}`} value={v} onChange={e => changeRow(draft.rows.indexOf(r), { phone: e.target.value })} /> },
          { title: '备注', dataIndex: 'remark', render: (v, r, i) => <Input aria-label={`账号备注 ${i + 1}`} maxLength={1000} value={v} onChange={e => changeRow(draft.rows.indexOf(r), { remark: e.target.value })} /> },
          { title: '操作', render: (_, r) => <Popconfirm title="移除此账号？保存后生效。" onConfirm={() => setDraft(d => ({ ...d, rows: d.rows.filter(x => x !== r) }))}><Button danger disabled={busy}>移除</Button></Popconfirm> },
        ]} />
        <Typography.Text type="secondary">仅允许 TEST-PHONE- 加 32 位大写十六进制字符。修改后点击保存生效；不接受真实手机号。</Typography.Text>
      </Space>}
    </Modal>
  </Card>;
}

