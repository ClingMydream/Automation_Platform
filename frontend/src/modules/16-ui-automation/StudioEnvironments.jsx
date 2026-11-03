import React, { useState } from 'react';
import { Button, Input, Modal, Select, Space, message } from 'antd';
const API = '/v1/ui-automation/environments';

export function StudioEnvironments({ client, items, onChange, onSelect, disabled }) {
  const [open, setOpen] = useState(false), [id, setId] = useState(null);
  const [draft, setDraft] = useState({}), [busy, setBusy] = useState(false), [error, setError] = useState('');
  function edit(value) {
    setId(value);
    setDraft({ ...(items.find((row) => row.id === value) || { name: '', base_url: '', viewport: 'mobile', notes: '' }) });
    setError('');
  }
  async function save() {
    if (busy) return;
    if (!draft.name?.trim()) { setError('请填写环境名称'); return; }
    setBusy(true); setError('');
    try {
      const body = { name: draft.name, base_url: draft.base_url, viewport: draft.viewport, notes: draft.notes };
      const row = id ? await client.put(API + '/' + id, body) : await client.post(API, body);
      onChange(id ? items.map((item) => item.id === id ? row : item) : [...items, row]);
      onSelect(row); setOpen(false); message.success('环境已保存');
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  function remove() {
    Modal.confirm({ title: '删除这个测试环境？', content: '历史执行报告和当时的环境信息会保留。',
      okText: '删除', okButtonProps: { danger: true, 'aria-label': '确认删除环境' },
      onOk: async () => {
        setBusy(true);
        try { await client.delete(API + '/' + id); onChange(items.filter((row) => row.id !== id)); edit(null); message.success('环境已删除'); }
        catch (e) { setError(e.message); throw e; } finally { setBusy(false); }
      } });
  }
  const field = (key, value) => setDraft((row) => ({ ...row, [key]: value }));
  return <>
    <Button disabled={disabled} onClick={() => { edit(null); setOpen(true); }}>管理测试环境</Button>
    <Modal title="测试环境管理" open={open} onCancel={() => !busy && setOpen(false)} footer={<Space wrap>
      {id && <Button danger aria-label="删除环境" disabled={busy} onClick={remove}>删除</Button>}
      <Button disabled={busy} onClick={() => edit(null)}>新增环境</Button>
      <Button type="primary" aria-label="保存环境" loading={busy} onClick={save}>保存环境</Button>
    </Space>}>
      <label className="studio-field">已有环境<Select aria-label="编辑已有环境" allowClear placeholder="选择环境进行修改" value={id || undefined} disabled={busy}
        options={items.map((row) => ({ value: row.id, label: row.name }))} onChange={(value) => edit(value || null)} /></label>
      <label className="studio-field">环境名称<Input aria-label="环境名称" disabled={busy} value={draft.name} onChange={(e) => field('name', e.target.value)} maxLength={120} /></label>
      <label className="studio-field">Base URL<Input aria-label="环境地址" disabled={busy} value={draft.base_url} onChange={(e) => field('base_url', e.target.value)} placeholder="https://example.com/（留空使用平台预览）" maxLength={2048} /></label>
      <label className="studio-field">默认视口<Select aria-label="环境默认视口" disabled={busy} value={draft.viewport} onChange={(value) => field('viewport', value)}
        options={[{ value: 'mobile', label: '移动端 390 × 844' }, { value: 'desktop', label: '桌面端 1440 × 900' }]} /></label>
      <label className="studio-field">备注（选填）<Input.TextArea aria-label="环境备注" disabled={busy} value={draft.notes} onChange={(e) => field('notes', e.target.value)} maxLength={2000} rows={3} /></label>
      <p className="studio-footnote">环境配置保存在服务器。仅填写站点地址，请勿在 URL 或备注中填写密码、Token。</p>
      {error && <p role="alert">{error}</p>}
    </Modal>
  </>;
}
