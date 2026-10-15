import React, { useMemo, useState } from 'react';
import {
  Alert,
  App as AntApp,
  Button,
  Card,
  Col,
  Form,
  InputNumber,
  Input,
  Radio,
  Row,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from 'antd';
import { CopyOutlined, DownloadOutlined } from '@ant-design/icons';
import { PhoneBatches } from './PhoneBatches.jsx';
import { copyText } from '../../shared/clipboard.js';
import { CuteIcon } from '../../shared/CuteIcon.jsx';


const { Text, Title } = Typography;

const PHONE_MODES = [{ value: 'synthetic', label: '手机号格式测试', description: '符合常见手机号正则；可能对应真人，仅限隔离测试，禁止真实拨打或发送短信' }];
const SOURCE_LABELS = { synthetic: '历史测试数据', random_format: '随机格式测试' };

function downloadFile(content, filename, type) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function csvCell(value) {
  const text = String(value ?? '').replaceAll('"', '""');
  return `"${text}"`;
}

export function DataGeneratorPanel({ client }) {
  const [form] = Form.useForm();
  const [kind, setKind] = useState('phone');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState({ rows: [], warning: '' });
  const { message } = AntApp.useApp();

  const columns = useMemo(() => {
    if (kind === 'id_card') {
      return [
        { title: '身份证号码', dataIndex: 'id_card', render: (value) => <Text copyable code>{value}</Text> },
        { title: '出生日期', dataIndex: 'birth_date', width: 140 },
        { title: '性别', dataIndex: 'gender', width: 90, render: (value) => (value === 'male' ? '男' : '女') },
        { title: '属性', width: 100, render: () => <Tag color="blue">合成数据</Tag> },
      ];
    }
    return [
      { title: '电话号码', dataIndex: 'phone', render: (value) => <Text copyable code>{value}</Text> },
      { title: '来源', dataIndex: 'source', width: 140, render: (value) => <Tag>{SOURCE_LABELS[value] || value}</Tag> },
      { title: '本工具发送短信', dataIndex: 'sms_capable', width: 120, render: (value) => <Tag color={value ? 'green' : 'default'}>{value ? '已配置' : '不提供'}</Tag> },
      { title: '备注（选填）', dataIndex: 'remark', render: (value, row) => <Input maxLength={1000} aria-label={`备注 ${row.phone}`} value={value || ''} onChange={e => setResult(current => ({ ...current, rows: current.rows.map(r => r.phone === row.phone ? { ...r, remark: e.target.value } : r) }))} /> },
    ];
  }, [kind]);

  async function generate(values) {
    setLoading(true);
    try {
      const data = await client.post('/v1/tools/data-generator', { ...values, kind });
      setResult(data);
      message.success(`已生成 ${data.rows.length} 条数据`);
    } catch (error) {
      message.error(error.message);
    } finally {
      setLoading(false);
    }
  }

  async function copyAll() {
    const key = kind === 'phone' ? 'phone' : 'id_card';
    const ok = await copyText(result.rows.map((row) => row[key]).join('\n'));
    if (ok) message.success('全部数据已复制'); else message.error('复制失败，请使用导出');
  }

  function exportJson() {
    downloadFile(JSON.stringify(result.rows, null, 2), `cling-${kind}.json`, 'application/json;charset=utf-8');
  }

  function exportCsv() {
    const keys = kind === 'phone' ? ['phone', 'remark'] : ['id_card', 'birth_date', 'gender', 'synthetic'];
    const content = [keys.map(csvCell).join(','), ...result.rows.map((row) => keys.map((key) => csvCell(row[key])).join(','))].join('\n');
    downloadFile(`\uFEFF${content}`, `cling-${kind}.csv`, 'text/csv;charset=utf-8');
  }

  return (
    <div className="generator-page">
      <section className="generator-heading">
        <div>
          <Title level={2}>数据生成器</Title>
          <Text>为表单、接口和演示环境快速准备规则正确、边界清晰的数据。</Text>
        </div>
        <div className="generator-meta">
          <span><i />安全测试模式</span>
          <span>单次最多 100 条</span>
        </div>
      </section>

      <Row gutter={[24, 24]} align="stretch">
        <Col xs={24} xl={9} xxl={8}>
          <Card className="control-card" title="生成设置" extra={<Text type="secondary">填写后立即生成</Text>}>
            <Radio.Group
              className="generator-kind-switch"
              value={kind}
              onChange={(event) => { setKind(event.target.value); setResult({ rows: [], warning: '' }); }}
              optionType="button"
              buttonStyle="solid"
              options={[
                { value: 'phone', label: <><span className="inline-emoji">📱</span> 电话号码</> },
                { value: 'id_card', label: <><span className="inline-emoji">🪪</span> 身份证</> },
              ]}
            />
            <Form
              form={form}
              layout="vertical"
              initialValues={{ count: 10, phone_mode: 'synthetic', gender: 'any', min_birth_year: 1980, max_birth_year: 2005 }}
              onFinish={generate}
            >
              <Form.Item label="生成数量" name="count"><InputNumber min={1} max={100} className="full-width" /></Form.Item>
              {kind === 'phone' ? (
                <Form.Item label="号码模式" name="phone_mode">
                  <Select options={PHONE_MODES.map((item) => ({ value: item.value, label: item.label }))} />
                </Form.Item>
              ) : (
                <>
                  <Form.Item label="性别" name="gender"><Select options={[{ value: 'any', label: '随机' }, { value: 'male', label: '男' }, { value: 'female', label: '女' }]} /></Form.Item>
                  <Row gutter={12}>
                    <Col span={12}><Form.Item label="最早出生年" name="min_birth_year"><InputNumber min={1900} max={2099} className="full-width" /></Form.Item></Col>
                    <Col span={12}><Form.Item label="最晚出生年" name="max_birth_year"><InputNumber min={1900} max={2099} className="full-width" /></Form.Item></Col>
                  </Row>
                </>
              )}
              <Button block type="primary" htmlType="submit" loading={loading} icon={<span className="inline-emoji">✨</span>}>立即生成</Button>
            </Form>
            {kind === 'phone' && (
              <div className="mode-notes">
                {PHONE_MODES.map((item) => <div key={item.value}><strong>{item.label}</strong><span>{item.description}</span></div>)}
              </div>
            )}
          </Card>
        </Col>

        <Col xs={24} xl={15} xxl={16}>
          <Card
            className="result-card"
            title={<Space><span>生成结果</span>{result.rows.length > 0 && <Tag color="blue">{result.rows.length} 条</Tag>}</Space>}
            extra={result.rows.length > 0 && <Space><Button icon={<CopyOutlined />} onClick={copyAll}>复制全部</Button><Button icon={<DownloadOutlined />} onClick={exportCsv}>CSV</Button><Button onClick={exportJson}>JSON</Button></Space>}
          >
            {result.warning && <Alert className="result-warning" type="warning" showIcon title={result.warning} />}
            {result.rows.length > 0 ? (
              <Table rowKey={(row) => row.phone || row.id_card} columns={columns} dataSource={result.rows} pagination={{ pageSize: 10 }} scroll={{ x: 720 }} />
            ) : (
              <div className="empty-result">
                <CuteIcon emoji="🧪" tone="blue" size={48} className="empty-result-icon" />
                <strong>等待生成</strong>
                <span>配置左侧选项后，结果会在这里出现。</span>
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {kind === 'phone' && <PhoneBatches client={client} rows={result.rows} onRowsChange={rows => setResult({ rows: rows.map(r => ({ ...r, source: /^1[3-9][0-9]{9}$/.test(r.phone) ? 'random_format' : 'synthetic', sms_capable: false, synthetic: true })), warning: '已载入保存批次的副本，可导出；修改原批次请使用“查看 / 编辑”。' })} />}
      <div className="generator-footnote">
        <span>身份证号码通过 MOD 11-2 校验</span>
        <span>支持 CSV、JSON 导出</span>
        <span>生成内容仅用于测试</span>
      </div>
    </div>
  );
}
