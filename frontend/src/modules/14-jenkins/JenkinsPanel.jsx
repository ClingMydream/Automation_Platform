import React, { useEffect, useState } from 'react';
import { Alert, Button, Card, Col, List, Row, Space, Tag, Typography, message } from 'antd';
import { CopyOutlined, ExportOutlined, ReloadOutlined } from '@ant-design/icons';
import './jenkins.css';

const { Paragraph, Text, Title } = Typography;
const JENKINS_URL = '/jenkins/';

const PIPELINE = `pipeline {
  agent any
  parameters {
    string(name: 'BRANCH', defaultValue: 'dev-20260811-1.9.1-test', description: '要构建的分支')
  }
  stages {
    stage('只读拉取') {
      steps {
        git branch: params.BRANCH,
            credentialsId: 'codeup-readonly',
            url: 'https://codeup.aliyun.com/6523ca864bb5eb36db2f603e/emote-app2.git'
      }
    }
    stage('安装依赖') { steps { sh 'npm ci' } }
    stage('生产构建') { steps { sh 'npm run build' } }
    stage('归档产物') { steps { archiveArtifacts artifacts: 'dist/**', fingerprint: true } }
  }
  post { always { cleanWs() } }
}`;

export function JenkinsPanel() {
  const [status, setStatus] = useState('checking');

  async function check() {
    setStatus('checking');
    try {
      const response = await fetch(`${JENKINS_URL}login`, { redirect: 'manual' });
      setStatus(response.ok || response.type === 'opaqueredirect' ? 'online' : 'offline');
    } catch {
      setStatus('offline');
    }
  }

  useEffect(() => { check(); }, []);

  async function copyPipeline() {
    await navigator.clipboard.writeText(PIPELINE);
    message.success('安全流水线模板已复制');
  }

  return <div className="jenkins-panel">
    <Card className="jenkins-hero">
      <div><Text>独立构建服务</Text><Title level={2}>🧱 Jenkins 持续集成</Title><Paragraph>用于选择分支、拉取代码、执行检查和构建、保存构建产物。流水线不包含提交、合并或推送代码操作。</Paragraph></div>
      <Space direction="vertical" align="end"><Tag color={status === 'online' ? 'green' : status === 'checking' ? 'blue' : 'red'}>{status === 'online' ? '服务正常' : status === 'checking' ? '检查中' : '服务异常'}</Tag><Space><Button icon={<ReloadOutlined />} onClick={check}>检查状态</Button><Button type="primary" icon={<ExportOutlined />} onClick={() => window.open(JENKINS_URL, 'cling-jenkins', 'noopener,noreferrer')}>打开 Jenkins</Button></Space></Space>
    </Card>
    <Alert type="warning" showIcon title="代码安全边界" description="Jenkins 只配置 Codeup 读取凭据。流水线不得出现 git commit、git merge、git rebase 或 git push；构建产物只保存在 Jenkins。" />
    <Row gutter={[16,16]} className="jenkins-grid">
      <Col xs={24} lg={12}><Card title="首次配置"><List dataSource={['打开 Jenkins，使用服务器生成的初始管理员密码完成初始化','在凭据管理中新增只读 Codeup 凭据，ID 固定为 codeup-readonly','新建 Pipeline 任务，例如 emote-frontend-ci','粘贴右侧流水线；构建时在 BRANCH 中填写或选择目标分支']} renderItem={(item,index)=><List.Item><span className="jenkins-step">{index+1}</span>{item}</List.Item>}/></Card></Col>
      <Col xs={24} lg={12}><Card title="安全流水线模板" extra={<Button icon={<CopyOutlined />} onClick={copyPipeline}>复制</Button>}><pre className="jenkins-code"><code>{PIPELINE}</code></pre></Card></Col>
    </Row>
  </div>;
}
