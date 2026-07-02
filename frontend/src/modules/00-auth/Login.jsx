// File purpose: Login page. Collect credentials, request a token, and notify the app after login.
// How to change: edit UI text/layout in this file; move reusable logic into shared helpers or the module feature file.

import React, { useState } from 'react';
import { Alert, App as AntApp, Button, Card, Form, Input, Space, Typography } from 'antd';
import { SafetyCertificateOutlined } from '@ant-design/icons';
import { apiClient } from '../../shared/apiClient';

const { Text, Title } = Typography;

// Login page: submits credentials and stores the returned token.
export function Login({ onLogin, notice }) {
  // State block: values here control loading, selection, form state, and visible page data.
  const [loading, setLoading] = useState(false);
  const { message } = AntApp.useApp();

  // Submit the current form and refresh the list after saving.
  async function submit(values) {
    setLoading(true);
    try {
      const data = await apiClient().post('/auth/login', values);
      localStorage.setItem('token', data.access_token);
      onLogin(data.access_token);
      message.success('登录成功');
    } catch (err) {
      message.error(err.message);
    } finally {
      setLoading(false);
    }
  }

  // Render block: JSX below describes what the user sees on this page.
  return (
    <main className="login-screen">
      <Card className="login-card">
        <Space direction="vertical" size={24} className="full-width">
          <div className="login-brand">
            <SafetyCertificateOutlined />
            <div>
              <Title level={3}>Automation Platform</Title>
              <Text type="secondary">接口测试与低代码 UI 自动化控制台</Text>
            </div>
          </div>
          {notice && <Alert type="warning" showIcon message={notice} />}
          <Form layout="vertical" initialValues={{ username: 'admin', password: '' }} onFinish={submit}>
            <Form.Item label="管理员账号" name="username" rules={[{ required: true, message: '请输入账号' }]}>
              <Input size="large" />
            </Form.Item>
            <Form.Item label="管理员密码" name="password" rules={[{ required: true, message: '请输入密码' }]}>
              <Input.Password size="large" autoFocus />
            </Form.Item>
            <Button type="primary" size="large" htmlType="submit" loading={loading} block icon={<SafetyCertificateOutlined />}>登录平台</Button>
          </Form>
        </Space>
      </Card>
    </main>
  );
}

// Auth module: owns the login screen and token handoff after successful login.
