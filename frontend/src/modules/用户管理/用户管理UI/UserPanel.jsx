import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Alert,
  App as AntApp,
  Button,
  Card,
  Checkbox,
  Col,
  Descriptions,
  Drawer,
  Empty,
  Form,
  Input,
  Modal,
  QRCode,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
  Upload,
} from 'antd';
import {
  ApiOutlined,
  BugOutlined,
  CloudUploadOutlined,
  CopyOutlined,
  ClockCircleOutlined,
  CloseOutlined,
  CodeOutlined,
  DeleteOutlined,
  DownloadOutlined,
  EditOutlined,
  EyeOutlined,
  FileDoneOutlined,
  FolderOutlined,
  InboxOutlined,
  LogoutOutlined,
  PictureOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
  RocketOutlined,
  SafetyCertificateOutlined,
  SwapOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { apiClient } from '../../../shared/apiClient';
import { runCodec } from '../../../shared/codec';
import { API_BASE, API_JSON_EXAMPLE, DEFAULT_UI_STEPS, UI_STEPS_EXAMPLE } from '../../../shared/constants';
import { downloadBlob, transferKind, transferKindLabel, TransferPreview } from '../../../shared/fileTransfer.jsx';
import { formatBytes, formatDuration, formatTime } from '../../../shared/formatters';
import { compareJsonValues, parseJsonInput, stableStringifyJson } from '../../../shared/jsonTools';
import { downloadReportHtml } from '../../../shared/reportExport';
import { JsonHelpCard } from '../../../shared/JsonHelpCard.jsx';
import { StatusTag } from '../../../shared/StatusTag.jsx';

const { Text, Title, Paragraph } = Typography;
const { TextArea } = Input;
const { Dragger } = Upload;

// 常改位置：菜单权限选项、用户表格字段、普通用户限制规则。
export function UserPanel({ client }) {
  const [form] = Form.useForm();
  const [users, setUsers] = useState([]);
  const [menuOptions, setMenuOptions] = useState([]);
  const [editingId, setEditingId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const { message, modal } = AntApp.useApp();

  async function loadUsers() {
    setLoading(true);
    try {
      const [userRows, menus] = await Promise.all([
        client.get('/users'),
        client.get('/menu-options'),
      ]);
      setUsers(userRows);
      setMenuOptions(menus.map((item) => ({ label: item.label, value: item.key })));
    } catch (err) {
      if (!err.authExpired) message.error(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadUsers();
  }, []);

  function resetForm() {
    setEditingId(null);
    form.resetFields();
    form.setFieldsValue({ is_active: true, menu_permissions: [] });
  }

  function startEdit(user) {
    setEditingId(user.id);
    form.setFieldsValue({
      username: user.username,
      display_name: user.display_name || '',
      password: '',
      is_active: user.is_active,
      menu_permissions: user.is_admin ? menuOptions.map((item) => item.value) : user.menu_permissions || [],
    });
  }

  async function submit(values) {
    setSaving(true);
    try {
      const payload = {
        display_name: values.display_name || null,
        is_active: values.is_active !== false,
        menu_permissions: values.menu_permissions || [],
      };
      if (values.password) payload.password = values.password;
      if (editingId) {
        await client.put(`/users/${editingId}`, payload);
        message.success('用户已更新');
      } else {
        await client.post('/users', { ...payload, username: values.username, password: values.password });
        message.success('用户已创建');
      }
      resetForm();
      await loadUsers();
    } catch (err) {
      message.error(err.message);
    } finally {
      setSaving(false);
    }
  }

  function remove(user) {
    modal.confirm({
      title: `删除用户「${user.username}」？`,
      content: '删除后该用户将无法继续登录平台。',
      okText: '删除',
      okButtonProps: { danger: true },
      cancelText: '取消',
      onOk: async () => {
        await client.delete(`/users/${user.id}`);
        message.success('用户已删除');
        if (editingId === user.id) resetForm();
        await loadUsers();
      },
    });
  }

  const editingUser = users.find((user) => user.id === editingId);

  return (
    <Row gutter={[16, 16]}>
      <Col xs={24} xl={9}>
        <Card title={editingId ? '修改登录人员' : '新增登录人员'} extra={editingId && <Button onClick={resetForm}>取消编辑</Button>}>
          <Form form={form} layout="vertical" onFinish={submit} initialValues={{ is_active: true, menu_permissions: [] }}>
            <Form.Item label="登录账号" name="username" rules={[{ required: !editingId, message: '请输入登录账号' }]}>
              <Input disabled={Boolean(editingId)} placeholder="例如：tester01" />
            </Form.Item>
            <Form.Item label="姓名 / 备注" name="display_name">
              <Input placeholder="例如：测试同事 A" />
            </Form.Item>
            <Form.Item label={editingId ? '新密码' : '登录密码'} name="password" rules={[{ required: !editingId, message: '请输入登录密码' }]}>
              <Input.Password placeholder={editingId ? '不填则不修改密码' : '至少 6 位'} />
            </Form.Item>
            <Form.Item label="账号状态" name="is_active" valuePropName="checked">
              <Checkbox disabled={editingUser?.is_admin}>启用该账号</Checkbox>
            </Form.Item>
            <Form.Item label="可操作菜单" name="menu_permissions" rules={[{ required: !editingUser?.is_admin, message: '请选择至少一个菜单' }]}>
              <Checkbox.Group className="permission-checks" options={menuOptions} disabled={editingUser?.is_admin} />
            </Form.Item>
            {editingUser?.is_admin && <Alert type="info" showIcon message="系统管理员默认拥有全部菜单权限，不能在这里禁用或删除。" />}
            <Button className="form-submit" type="primary" htmlType="submit" loading={saving} icon={<PlusOutlined />}>{editingId ? '更新用户' : '创建用户'}</Button>
          </Form>
        </Card>
      </Col>
      <Col xs={24} xl={15}>
        <Card title="登录人员列表" extra={<Button icon={<ReloadOutlined />} loading={loading} onClick={loadUsers}>刷新</Button>}>
          <Table
            rowKey="id"
            dataSource={users}
            loading={loading}
            pagination={{ pageSize: 8 }}
            scroll={{ x: 920 }}
            columns={[
              { title: '账号', dataIndex: 'username', width: 130 },
              { title: '姓名 / 备注', dataIndex: 'display_name', render: (value) => value || '-' },
              { title: '角色', dataIndex: 'is_admin', width: 100, render: (value) => value ? <Tag color="gold">管理员</Tag> : <Tag>普通用户</Tag> },
              { title: '状态', dataIndex: 'is_active', width: 90, render: (value) => value ? <Tag color="success">启用</Tag> : <Tag color="error">禁用</Tag> },
              {
                title: '菜单权限',
                dataIndex: 'menu_permissions',
                render: (value) => (
                  <Space size={4} wrap>
                    {(value || []).map((key) => <Tag key={key}>{menuOptions.find((item) => item.value === key)?.label || key}</Tag>)}
                  </Space>
                ),
              },
              {
                title: '操作',
                width: 150,
                fixed: 'right',
                render: (_, record) => (
                  <Space className="table-actions" size={6} wrap>
                    <Button icon={<EditOutlined />} onClick={() => startEdit(record)}>修改</Button>
                    <Button danger icon={<DeleteOutlined />} disabled={record.is_admin} onClick={() => remove(record)}>删除</Button>
                  </Space>
                ),
              },
            ]}
          />
        </Card>
      </Col>
    </Row>
  );
}

// 文件快传模块：电脑端上传临时文件，手机扫码下载或回传文件。

