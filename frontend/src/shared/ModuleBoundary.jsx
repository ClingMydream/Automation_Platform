import React from 'react';
import { Alert, Button, Space, Spin } from 'antd';
export const ModuleLoading = () => <div className="module-loading" role="status"><Spin /><p>正在加载功能…</p></div>;
export class ModuleBoundary extends React.Component {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    if (this.state.failed) return <Alert type="error" showIcon title="功能暂时无法显示" description="请先重试。若仍无法加载，可保存其他页面的输入后刷新加载。" action={<Space wrap><Button onClick={() => this.setState({failed:false})}>重试</Button><Button onClick={() => window.location.reload()}>刷新加载</Button></Space>} />;
    return this.props.children;
  }
}
