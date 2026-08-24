import React, { useEffect, useState } from 'react';
import { Alert, Button, Card, Col, List, QRCode, Row, Space, Tag, Typography, message } from 'antd';
import { CopyOutlined, ExportOutlined, ReloadOutlined } from '@ant-design/icons';
import './jenkins.css';

const { Paragraph, Text, Title } = Typography;
const JENKINS_URL = '/jenkins/';
const EMOTE_JOB_URL = '/jenkins/job/emote-apk/';
const APK_SHARE_URL = `${window.location.origin}/?testPackage=latest`;

const PIPELINE = `pipeline {
  agent any
  parameters {
    gitParameter(name: 'BRANCH', type: 'PT_BRANCH', branchFilter: 'origin/(.*)',
      sortMode: 'DESCENDING_SMART', quickFilterEnabled: true,
      description: '选择或搜索需要打包的远程分支')
  }
  stages {
    stage('只读拉取') {
      steps {
        git branch: params.BRANCH,
            credentialsId: 'codeup-readonly',
            url: 'https://codeup.aliyun.com/6523ca864bb5eb36db2f603e/emote-app2.git'
      }
    }
    stage('安装依赖') { steps { sh 'pnpm install --frozen-lockfile' } }
    stage('同步工程') { steps { sh 'pnpm build -- --mode production && pnpm exec cap sync android' } }
    stage('构建 APK') { steps { dir('android') { sh './gradlew -Dorg.gradle.java.home="$JAVA_HOME" assembleDebug --no-daemon' } } }
    stage('发布最新版') { steps { archiveArtifacts artifacts: 'android/app/build/outputs/apk/debug/*.apk' } }
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
      <div><Text>Emote Android 自动打包</Text><Title level={2}>🧱 Jenkins 持续集成</Title><Paragraph>从下拉框选择远程分支，一键生成可安装的 Debug APK。成功后自动更新测试包模块，固定二维码不会改变。</Paragraph></div>
      <Space direction="vertical" align="end"><Tag color={status === 'online' ? 'green' : status === 'checking' ? 'blue' : 'red'}>{status === 'online' ? '服务正常' : status === 'checking' ? '检查中' : '服务异常'}</Tag><Space wrap><Button icon={<ReloadOutlined />} onClick={check}>检查状态</Button><Button type="primary" icon={<ExportOutlined />} onClick={() => window.open(EMOTE_JOB_URL, 'cling-emote-apk', 'noopener,noreferrer')}>打开 Emote 打包任务</Button></Space></Space>
    </Card>
    <Alert type="warning" showIcon title="代码安全边界" description="Jenkins 只配置 Codeup 读取凭据。流水线不得出现 git commit、git merge、git rebase 或 git push；构建产物只保存在 Jenkins。" />
    <Row gutter={[16,16]} className="jenkins-grid">
      <Col xs={24} lg={12}><Card title="怎么打包"><List dataSource={['打开 Emote 打包任务并登录 Jenkins','点击左侧 Build with Parameters（使用参数构建）','在 BRANCH 下拉框浏览全部远程分支，也可以输入分支名快速筛选','确认分支后点击 Build，构建标题会记录本次选择','等待所有阶段变绿，再扫描下方固定二维码下载最新 APK']} renderItem={(item,index)=><List.Item><span className="jenkins-step">{index+1}</span>{item}</List.Item>}/><div style={{textAlign:'center', marginTop:16}}><QRCode value={APK_SHARE_URL} size={180}/><Paragraph type="secondary">APK 固定下载二维码</Paragraph><Button onClick={() => window.open(APK_SHARE_URL, '_blank')}>打开下载页</Button></div></Card></Col>
      <Col xs={24} lg={12}><Card title="自动构建流程" extra={<Button icon={<CopyOutlined />} onClick={copyPipeline}>复制示例</Button>}><pre className="jenkins-code"><code>{PIPELINE}</code></pre></Card></Col>
    </Row>
  </div>;
}
