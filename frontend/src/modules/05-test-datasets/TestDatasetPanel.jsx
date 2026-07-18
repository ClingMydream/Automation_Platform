// File purpose: Test dataset page. Maintain variables, test accounts, and data pools.

import React, { useMemo, useState } from 'react';
import { Alert, App as AntApp, Button, Card, Col, Form, Input, InputNumber, Row, Select, Space, Switch, Table, Tag, Typography } from 'antd';
import { CopyOutlined, DeleteOutlined, EditOutlined, PlusOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { buildDatasetFormValues, DATASET_TYPES, deleteDataset, generateTestData, saveDataset } from './testDatasetFeature.js';

const { TextArea } = Input;
const { Paragraph } = Typography;

export function TestDatasetPanel({ client, projects, datasets, reload }) {
  const [form] = Form.useForm();
  const [generatorForm] = Form.useForm();
  const [editingId, setEditingId] = useState(null);
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [generatorKind, setGeneratorKind] = useState('phone');
  const [generated, setGenerated] = useState({ rows: [], warning: '' });
  const { message, modal } = AntApp.useApp();
  const projectOptions = useMemo(() => projects.map((item) => ({ value: item.id, label: item.name })), [projects]);
  const projectNameById = useMemo(() => new Map(projects.map((item) => [item.id, item.name])), [projects]);

  function resetForm() {
    setEditingId(null);
    form.resetFields();
    form.setFieldsValue({ dataset_type: 'variables', variablesText: '{}', rowsText: '[]', is_active: true });
  }

  function startEdit(item) {
    setEditingId(item.id);
    form.setFieldsValue(buildDatasetFormValues(item));
  }

  async function submit(values) {
    setSaving(true);
    try {
      const result = await saveDataset(client, editingId, values);
      message.success(result === 'updated' ? '测试数据已更新' : '测试数据已创建');
      resetForm();
      await reload();
    } catch (err) {
      message.error(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function runGenerator(values) {
    setGenerating(true);
    try {
      const result = await generateTestData(client, values);
      setGenerated(result);
      message.success(`已生成 ${result.rows.length} 条测试数据`);
    } catch (err) {
      message.error(err.message);
    } finally {
      setGenerating(false);
    }
  }

  async function copyGenerated() {
    await navigator.clipboard.writeText(JSON.stringify(generated.rows, null, 2));
    message.success('生成结果已复制');
  }

  function appendGenerated() {
    let currentRows = [];
    try {
      currentRows = JSON.parse(form.getFieldValue('rowsText') || '[]');
      if (!Array.isArray(currentRows)) throw new Error('not an array');
    } catch {
      message.error('当前“数据行 JSON 数组”格式不正确，请先修正');
      return;
    }
    form.setFieldValue('rowsText', JSON.stringify([...currentRows, ...generated.rows], null, 2));
    message.success('已追加到数据行，可继续保存为数据集');
  }

  function remove(item) {
    modal.confirm({
      title: `删除测试数据「${item.name}」？`,
      okText: '删除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: async () => {
        await deleteDataset(client, item.id);
        message.success('测试数据已删除');
        await reload();
      },
    });
  }

  return (
    <Row gutter={[16, 16]}>
      <Col span={24}>
        <Card title="测试数据生成器">
          <Alert
            type="warning"
            showIcon
            message="格式正确不等于可以收短信"
            description="随机中国手机号仅用于字段校验，可能与真实号码碰撞，禁止拨打或发送。真实短信测试必须选择“自有/已租用接收号码”，并由服务端 TEST_SMS_PHONE_NUMBERS 配置受控号码。"
            style={{ marginBottom: 16 }}
          />
          <Form
            form={generatorForm}
            layout="inline"
            initialValues={{ kind: 'phone', count: 5, phone_mode: 'cn_format', gender: 'any', min_birth_year: 1970, max_birth_year: 2005 }}
            onFinish={runGenerator}
          >
            <Form.Item label="数据类型" name="kind">
              <Select style={{ width: 150 }} onChange={setGeneratorKind} options={[{ value: 'phone', label: '电话号码' }, { value: 'id_card', label: '身份证号码' }]} />
            </Form.Item>
            <Form.Item label="数量" name="count"><InputNumber min={1} max={100} /></Form.Item>
            {generatorKind === 'phone' && (
              <Form.Item label="号码模式" name="phone_mode">
                <Select
                  style={{ width: 230 }}
                  options={[
                    { value: 'cn_format', label: '中国手机号格式（不可收信）' },
                    { value: 'twilio_magic', label: 'Twilio API 模拟（不投递）' },
                    { value: 'configured_receivers', label: '自有/已租用接收号码' },
                  ]}
                />
              </Form.Item>
            )}
            {generatorKind === 'id_card' && (
              <>
                <Form.Item label="性别" name="gender"><Select style={{ width: 110 }} options={[{ value: 'any', label: '不限' }, { value: 'male', label: '男' }, { value: 'female', label: '女' }]} /></Form.Item>
                <Form.Item label="出生年份" name="min_birth_year"><InputNumber min={1900} max={2099} /></Form.Item>
                <Form.Item label="至" name="max_birth_year"><InputNumber min={1900} max={2099} /></Form.Item>
              </>
            )}
            <Form.Item><Button type="primary" htmlType="submit" loading={generating} icon={<ThunderboltOutlined />}>生成</Button></Form.Item>
          </Form>
          {generated.rows.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <Alert type="info" showIcon message={generated.warning} />
              <Paragraph><pre style={{ maxHeight: 260, overflow: 'auto' }}>{JSON.stringify(generated.rows, null, 2)}</pre></Paragraph>
              <Space>
                <Button icon={<CopyOutlined />} onClick={copyGenerated}>复制 JSON</Button>
                <Button onClick={appendGenerated}>追加到下方数据集</Button>
              </Space>
            </div>
          )}
        </Card>
      </Col>
      <Col xs={24} xl={9}>
        <Card title={editingId ? '修改测试数据' : '新建测试数据'} extra={editingId && <Button onClick={resetForm}>取消编辑</Button>}>
          <Form form={form} layout="vertical" initialValues={{ dataset_type: 'variables', variablesText: '{}', rowsText: '[]', is_active: true }} onFinish={submit}>
            <Form.Item label="名称" name="name" rules={[{ required: true, message: '请输入名称' }]}><Input placeholder="测试账号池" /></Form.Item>
            <Form.Item label="所属项目" name="project_id"><Select allowClear options={projectOptions} placeholder="可选" /></Form.Item>
            <Form.Item label="类型" name="dataset_type"><Select options={DATASET_TYPES} /></Form.Item>
            <Form.Item label="变量 JSON" name="variablesText"><TextArea rows={4} placeholder='{"baseUser":"tester"}' /></Form.Item>
            <Form.Item label="数据行 JSON 数组" name="rowsText"><TextArea rows={5} placeholder='[{"username":"u1","password":"p1"}]' /></Form.Item>
            <Form.Item label="启用状态" name="is_active" valuePropName="checked"><Switch checkedChildren="启用" unCheckedChildren="停用" /></Form.Item>
            <Form.Item label="说明" name="description"><TextArea rows={3} /></Form.Item>
            <Button type="primary" htmlType="submit" loading={saving} icon={<PlusOutlined />}>{editingId ? '更新数据' : '保存数据'}</Button>
          </Form>
        </Card>
      </Col>
      <Col xs={24} xl={15}>
        <Card title="测试数据列表">
          <Table
            rowKey="id"
            dataSource={datasets}
            pagination={{ pageSize: 8 }}
            scroll={{ x: 820 }}
            columns={[
              { title: '名称', dataIndex: 'name' },
              { title: '项目', dataIndex: 'project_id', render: (value) => (value ? projectNameById.get(value) || `项目 ${value}` : '-') },
              { title: '类型', dataIndex: 'dataset_type', render: (value) => <Tag>{DATASET_TYPES.find((item) => item.value === value)?.label || value}</Tag> },
              { title: '数据行', dataIndex: 'rows', render: (value = []) => value.length },
              { title: '状态', dataIndex: 'is_active', render: (value) => <Tag color={value ? 'green' : 'default'}>{value ? '启用' : '停用'}</Tag> },
              { title: '操作', width: 170, render: (_, record) => <Space><Button icon={<EditOutlined />} onClick={() => startEdit(record)}>修改</Button><Button danger icon={<DeleteOutlined />} onClick={() => remove(record)}>删除</Button></Space> },
            ]}
          />
        </Card>
      </Col>
    </Row>
  );
}
