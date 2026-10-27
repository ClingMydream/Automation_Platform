// File purpose: Login page. Collect credentials, request a token, and notify the app after login.
// How to change: edit UI text/layout in this file; move reusable logic into shared helpers or the module feature file.

import React, { useState } from 'react';
import { Alert, App as AntApp, Button, Card, Form, Input, Space, Typography } from 'antd';
import { apiClient } from '../../shared/apiClient';
import { BrandMark, OrbitArtwork } from '../../shared/WorkspaceIdentity.jsx';
import { ArrowRight } from 'lucide-react';

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
    <main className="login-screen atelier-login">
      <section className="atelier-login-story" aria-labelledby="login-story-title">
        <div className="atelier-login-wordmark"><BrandMark/><strong>cling<span>✦</span></strong></div>
        <div className="atelier-login-narrative"><span className="atelier-eyebrow">A LITTLE ORDER. A LITTLE WONDER.</span><h1 id="login-story-title">做好工作，<br/>也留一点空间<br/>给<span>自己。</span></h1><p>让测试更有把握，让成长慢慢发生。<br/>你的日常工作，可以轻盈一点。</p></div>
        <OrbitArtwork/>
        <div className="atelier-login-story-foot"><span>测试 · 成长 · 效率</span><span>YOUR EVERYDAY WORKSPACE</span></div>
      </section>
      <section className="atelier-login-entry" aria-labelledby="login-form-title">
      <div className="atelier-login-entry-label">CLING / PERSONAL WORKSPACE</div>
      <Card className="login-card">
        <Space orientation="vertical" size={24} className="full-width">
          <div className="login-brand">
            <div>
              <span className="atelier-eyebrow">WELCOME BACK</span>
              <Title level={2} id="login-form-title">欢迎回到你的工作空间</Title>
              <Text type="secondary">使用平台账号登录，继续今天的好工作。</Text>
            </div>
          </div>
          {notice && <Alert type="warning" showIcon title={notice} />}
          <Form layout="vertical" initialValues={{ username: 'admin', password: '' }} onFinish={submit}>
            <Form.Item label="登录账号" name="username" rules={[{ required: true, message: '请输入账号' }]}>
              <Input size="large" autoComplete="username" />
            </Form.Item>
            <Form.Item label="登录密码" name="password" rules={[{ required: true, message: '请输入密码' }]}>
              <Input.Password size="large" autoFocus autoComplete="current-password" />
            </Form.Item>
            <Button type="primary" size="large" htmlType="submit" loading={loading} block icon={<ArrowRight size={17}/>}>进入自动化平台</Button>
          </Form>
        </Space>
      </Card>
      <p className="atelier-login-entry-foot">一点秩序，一点灵感。<span>让每一次打开，都离目标更近一点。</span></p>
      </section>
    </main>
  );
}

// Auth module: owns the login screen and token handoff after successful login.
