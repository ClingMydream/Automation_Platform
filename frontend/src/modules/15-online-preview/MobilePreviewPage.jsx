import React, { useRef } from 'react';
import { Button, Space, Typography } from 'antd';
import { ExportOutlined, ReloadOutlined } from '@ant-design/icons';
import './online-preview.css';

const { Text, Title } = Typography;
const PREVIEW_URL = '/emote-preview/';

export function MobilePreviewPage() {
  const screenRef = useRef(null);
  return <main className="emote-mobile-preview-page">
    <header className="emote-mobile-preview-page__header">
      <div><Text>cling · 独立应用窗口</Text><Title level={4}>Emote 手机应用预览</Title></div>
      <Space><Button icon={<ReloadOutlined />} onClick={() => screenRef.current?.contentWindow?.location.reload()}>刷新应用</Button><Button icon={<ExportOutlined />} onClick={() => window.open(PREVIEW_URL, 'cling-emote-preview-web', 'noopener,noreferrer')}>网页调试模式</Button><Button onClick={() => window.close()}>关闭窗口</Button></Space>
    </header>
    <section className="emote-mobile-preview-page__body">
      <div className="emote-mobile-preview__hint">390 × 844 · 独立应用式预览</div>
      <div className="emote-mobile-frame"><div className="emote-mobile-frame__speaker" /><iframe ref={screenRef} title="Emote 手机预览" src={PREVIEW_URL} className="emote-mobile-frame__screen" /></div>
    </section>
  </main>;
}
