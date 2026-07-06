// File purpose: Problem diagnosis page. Convert failed results into trackable findings.
// How to change: keep API calls here, and put pure label/default helpers in problemDiagnosisFeature.js.

import React, { useState } from 'react';
import { Button, Card, Col, Descriptions, Form, Input, Modal, Row, Select, Space, Table, Tag, Typography } from 'antd';
import { PlusOutlined, SearchOutlined } from '@ant-design/icons';
import { formatDuration, formatTime } from '../../shared/formatters.js';
import {
  findingStatusOptions,
  severityColor,
  severityOptions,
  statusColor,
  toFindingPayload,
} from './problemDiagnosisFeature.js';

const { Paragraph } = Typography;

// Render one page that links failed result evidence with human-readable investigation records.
export function ProblemDiagnosisPanel({ client, results, findings, reload }) {
  const [selectedFinding, setSelectedFinding] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  // Only failed or errored results can become diagnosis records automatically.
  const failedResults = (results || []).filter((item) => ['failed', 'error'].includes(item.status));

  // Open the manual create/edit modal and preload fields when editing.
  function openModal(record = null) {
    setSelectedFinding(record);
    form.setFieldsValue(record || { severity: 'medium', status: 'open', source: 'manual' });
    setModalOpen(true);
  }

  // Save the modal form through create or update APIs.
  async function saveFinding() {
    const values = await form.validateFields();
    setSaving(true);
    try {
      const payload = toFindingPayload({ ...values, evidence: selectedFinding?.evidence || values.evidence });
      if (selectedFinding?.id) {
        await client.put(`/v1/problem-findings/${selectedFinding.id}`, payload);
      } else {
        await client.post('/v1/problem-findings', payload);
      }
      setModalOpen(false);
      setSelectedFinding(null);
      await reload();
    } finally {
      setSaving(false);
    }
  }

  // Ask the backend to infer category, severity, evidence, and suggested reproduction steps.
  async function generateFromResult(resultId) {
    await client.post(`/v1/problem-findings/from-result/${resultId}`, {});
    await reload();
  }

  // Remove one diagnosis record while keeping original result evidence intact.
  async function deleteFinding(findingId) {
    await client.delete(`/v1/problem-findings/${findingId}`);
    if (selectedFinding?.id === findingId) setSelectedFinding(null);
    await reload();
  }

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={10}>
        <Card title="失败结果">
          <Table
            rowKey="id"
            dataSource={failedResults}
            pagination={{ pageSize: 8 }}
            scroll={{ x: 760 }}
            columns={[
              { title: 'ID', dataIndex: 'id', width: 70 },
              { title: '类型', dataIndex: 'result_type', width: 100, render: (value) => <Tag>{value}</Tag> },
              { title: '状态', dataIndex: 'status', width: 100, render: (value) => <Tag color="red">{value}</Tag> },
              { title: '耗时', dataIndex: 'duration_ms', width: 100, render: formatDuration },
              { title: '时间', dataIndex: 'created_at', width: 160, render: formatTime },
              {
                title: '操作',
                fixed: 'right',
                width: 130,
                render: (_, record) => (
                  <Button size="small" icon={<SearchOutlined />} onClick={() => generateFromResult(record.id)}>
                    生成定位
                  </Button>
                ),
              },
            ]}
          />
        </Card>
      </Col>
      <Col xs={24} xl={14}>
        <Card
          title="问题定位"
          extra={<Button type="primary" icon={<PlusOutlined />} onClick={() => openModal()}>手工新增</Button>}
        >
          <Table
            rowKey="id"
            dataSource={findings || []}
            pagination={{ pageSize: 8 }}
            scroll={{ x: 980 }}
            onRow={(record) => ({ onClick: () => setSelectedFinding(record) })}
            columns={[
              { title: '标题', dataIndex: 'title', width: 220 },
              { title: '严重级别', dataIndex: 'severity', width: 100, render: (value) => <Tag color={severityColor(value)}>{value}</Tag> },
              { title: '状态', dataIndex: 'status', width: 110, render: (value) => <Tag color={statusColor(value)}>{value}</Tag> },
              { title: '分类', dataIndex: 'failure_category', width: 120, render: (value) => value || '-' },
              { title: '责任人', dataIndex: 'owner', width: 120, render: (value) => value || '-' },
              { title: '时间', dataIndex: 'created_at', width: 160, render: formatTime },
              {
                title: '操作',
                fixed: 'right',
                width: 150,
                render: (_, record) => (
                  <Space>
                    <Button size="small" onClick={(event) => { event.stopPropagation(); openModal(record); }}>修改</Button>
                    <Button size="small" danger onClick={(event) => { event.stopPropagation(); deleteFinding(record.id); }}>删除</Button>
                  </Space>
                ),
              },
            ]}
          />
        </Card>
        {selectedFinding && (
          <Card title={`定位详情 #${selectedFinding.id}`} style={{ marginTop: 16 }}>
            <Descriptions column={1} size="small">
              <Descriptions.Item label="根因分析"><Paragraph copyable>{selectedFinding.root_cause || '-'}</Paragraph></Descriptions.Item>
              <Descriptions.Item label="复现步骤"><Paragraph copyable>{selectedFinding.reproduce_steps || '-'}</Paragraph></Descriptions.Item>
              <Descriptions.Item label="处理建议"><Paragraph copyable>{selectedFinding.suggestion || '-'}</Paragraph></Descriptions.Item>
              <Descriptions.Item label="证据 JSON"><pre>{JSON.stringify(selectedFinding.evidence || {}, null, 2)}</pre></Descriptions.Item>
            </Descriptions>
          </Card>
        )}
      </Col>
      <Modal
        title={selectedFinding?.id ? '修改问题定位' : '新增问题定位'}
        open={modalOpen}
        onOk={saveFinding}
        onCancel={() => setModalOpen(false)}
        confirmLoading={saving}
        width={760}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="source" hidden><Input /></Form.Item>
          <Form.Item name="title" label="标题" rules={[{ required: true, message: '请填写标题' }]}>
            <Input placeholder="例如：登录接口响应断言失败" />
          </Form.Item>
          <Row gutter={12}>
            <Col span={8}>
              <Form.Item name="severity" label="严重级别"><Select options={severityOptions} /></Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="status" label="状态"><Select options={findingStatusOptions} /></Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="owner" label="责任人"><Input placeholder="可选" /></Form.Item>
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={8}><Form.Item name="result_id" label="结果 ID"><Input type="number" /></Form.Item></Col>
            <Col span={8}><Form.Item name="batch_id" label="批次 ID"><Input type="number" /></Form.Item></Col>
            <Col span={8}><Form.Item name="test_object_id" label="测试对象 ID"><Input type="number" /></Form.Item></Col>
          </Row>
          <Form.Item name="failure_category" label="失败分类"><Input placeholder="assertion / timeout / network / ui_element" /></Form.Item>
          <Form.Item name="root_cause" label="根因分析"><Input.TextArea rows={3} /></Form.Item>
          <Form.Item name="reproduce_steps" label="复现步骤"><Input.TextArea rows={3} /></Form.Item>
          <Form.Item name="suggestion" label="处理建议"><Input.TextArea rows={3} /></Form.Item>
        </Form>
      </Modal>
    </Row>
  );
}
