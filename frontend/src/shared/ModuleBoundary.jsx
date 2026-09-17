import React from 'react';
import { Alert, Button, Spin } from 'antd';
export const ModuleLoading = () => <div className="module-loading" role="status"><Spin /><p>正在加载功能…</p></div>;
export class ModuleBoundary extends React.Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    if (this.state.failed) return <Alert type="error" showIcon title="功能暂时无法显示" description="请重试；如果刚发布了新版本，请刷新页面。刷新前请保存其他页面的输入。" action={<Button onClick={() => this.setState({failed:false})}>重试</Button>} />;
    return this.props.children;
  }
}
