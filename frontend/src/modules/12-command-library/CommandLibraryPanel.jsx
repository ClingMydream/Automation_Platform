import React, { useEffect, useMemo, useState } from 'react';
import { App as AntApp, Button, Card, Col, Empty, Form, Input, Modal, Popconfirm, Row, Segmented, Space, Tag, Typography } from 'antd';
import { CopyOutlined, DeleteOutlined, EditOutlined, PlusOutlined, StarFilled, StarOutlined } from '@ant-design/icons';
import './command-library.css';

const { Paragraph, Text, Title } = Typography;
const API = '/v1/command-library';
const CATEGORIES = ['全部', 'MySQL', 'Linux', 'Redis', 'Docker', '收藏'];
const COLORS = { MySQL: 'blue', Linux: 'green', Redis: 'red', Docker: 'cyan' };

export function CommandLibraryPanel({ client }) {
  const [rows, setRows] = useState([]);
  const [category, setCategory] = useState('全部');
  const [query, setQuery] = useState('');
  const [editing, setEditing] = useState(null);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();
  const { message } = AntApp.useApp();

  async function load() {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (query) params.set('q', query);
      if (!['全部', '收藏'].includes(category)) params.set('category', category);
      if (category === '收藏') params.set('favorite', 'true');
      setRows(await client.get(`${API}?${params}`));
    } catch (error) { message.error(error.message); }
    finally { setLoading(false); }
  }
  useEffect(() => { load(); }, [category, query]);

  function openEditor(item = null) {
    setEditing(item || {});
    form.setFieldsValue(item ? { ...item, tags: (item.tags || []).join(',') } : { category: 'Linux', tags: '' });
  }
  async function save() {
    const values = await form.validateFields();
    const payload = { ...values, tags: values.tags ? values.tags.split(',').map((value) => value.trim()).filter(Boolean) : [], is_favorite: editing?.is_favorite || false };
    editing?.id ? await client.put(`${API}/${editing.id}`, payload) : await client.post(API, payload);
    message.success(editing?.id ? '命令已更新' : '命令已添加'); setEditing(null); form.resetFields(); await load();
  }
  async function copy(command) { await navigator.clipboard.writeText(command); message.success('命令已复制，请确认环境和参数后再执行'); }
  async function favorite(item) { await client.put(`${API}/${item.id}/favorite`, {}); await load(); }
  async function remove(id) { await client.delete(`${API}/${id}`); message.success('命令已删除'); await load(); }

  const countText = useMemo(() => `${rows.length} 条命令`, [rows]);
  return <div className="command-library">
    <div className="command-heading"><div><Text>工作速查 · 面试复习</Text><Title level={2}>⌨️ 命令手册</Title><Paragraph type="secondary">记录 MySQL、Linux、Redis、Docker 常用命令。这里只展示和复制，不会在服务器上执行。</Paragraph></div><Button type="primary" icon={<PlusOutlined />} onClick={() => openEditor()}>记录命令</Button></div>
    <Card className="command-toolbar"><Row gutter={[12, 12]} align="middle"><Col xs={24} lg={16}><Segmented block options={CATEGORIES} value={category} onChange={setCategory} /></Col><Col xs={24} lg={8}><Input.Search allowClear placeholder="搜索命令、说明或面试要点" onSearch={setQuery} /></Col></Row><Text type="secondary">{loading ? '加载中…' : countText}</Text></Card>
    {rows.length ? <Row gutter={[14, 14]} className="command-grid">{rows.map((item) => <Col xs={24} lg={12} key={item.id}><Card className="command-card" title={<Space><Tag color={COLORS[item.category] || 'purple'}>{item.category}</Tag><b>{item.title}</b>{item.is_builtin && <Tag>内置</Tag>}</Space>} extra={<Button type="text" aria-label="收藏" icon={item.is_favorite ? <StarFilled className="favorite-star" /> : <StarOutlined />} onClick={() => favorite(item)} />}>
      <pre><code>{item.command}</code></pre><div className="command-section"><b>使用说明</b><Paragraph>{item.description || '暂无说明'}</Paragraph></div>{item.usage_example && <div className="command-section example"><b>使用示例</b><pre><code>{item.usage_example}</code></pre></div>}{item.interview_note && <div className="command-section interview"><b>💡 面试要点</b><Paragraph>{item.interview_note}</Paragraph></div>}<Space wrap className="command-actions"><Button type="primary" ghost icon={<CopyOutlined />} onClick={() => copy(item.command)}>复制命令</Button><Button icon={<EditOutlined />} onClick={() => openEditor(item)}>编辑</Button>{!item.is_builtin && <Popconfirm title="删除这条命令？" onConfirm={() => remove(item.id)}><Button danger icon={<DeleteOutlined />}>删除</Button></Popconfirm>}</Space>
    </Card></Col>)}</Row> : <Empty description="没有找到匹配的命令" />}
    <Modal open={Boolean(editing)} title={editing?.id ? '编辑命令' : '记录新命令'} width={720} okText="保存" cancelText="取消" onOk={save} onCancel={() => { setEditing(null); form.resetFields(); }}><Form form={form} layout="vertical"><Row gutter={12}><Col span={8}><Form.Item name="category" label="分类" rules={[{ required: true }]}><Input placeholder="例如 Linux" /></Form.Item></Col><Col span={16}><Form.Item name="title" label="命令名称" rules={[{ required: true }]}><Input placeholder="例如：查看实时日志" /></Form.Item></Col></Row><Form.Item name="command" label="命令" rules={[{ required: true }]}><Input.TextArea rows={4} placeholder="tail -f app.log" /></Form.Item><Form.Item name="description" label="使用说明"><Input.TextArea rows={3} placeholder="说明这个命令解决什么问题、参数如何替换" /></Form.Item><Form.Item name="usage_example" label="使用示例"><Input.TextArea rows={3} /></Form.Item><Form.Item name="interview_note" label="面试要点"><Input.TextArea rows={3} /></Form.Item><Form.Item name="tags" label="标签（逗号分隔）"><Input placeholder="日志, 排查, 常用" /></Form.Item></Form></Modal>
  </div>;
}
