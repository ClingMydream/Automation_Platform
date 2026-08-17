import React from 'react';
import { Button, Card, Space, Typography, message } from 'antd';
import { CopyOutlined, ExportOutlined } from '@ant-design/icons';
import './effects.css';

const { Paragraph, Title } = Typography;
export const HAPPY_ZHAO_PATH = '/effect/xiaozhao-happy';

export function PublicEffectPage() {
  return <main className="particle-effect"><div className="code-wall">def make_love():<br />&nbsp;&nbsp;particles = create_heart(5000)<br />&nbsp;&nbsp;return happiness_forever</div><div className="wireframe" /><div className="particle-heart">{Array.from({ length: 86 }, (_, index) => <i key={index} style={{ '--i': index }} />)}<div className="particle-message">小赵<br /><strong>天天开心</strong></div></div></main>;
}

export function EffectStudio() {
  const url = `${window.location.origin}${HAPPY_ZHAO_PATH}`;
  const copy = async () => { await navigator.clipboard.writeText(url); message.success('公开链接已复制'); };
  return <div className="effect-studio"><section className="effect-studio__hero"><div><span>临时创作 · 仅链接可见</span><Title level={2}>🎀 临时效果</Title><Paragraph>制作一句话、一张祝福或一个小动画；分享出去的人只会看到效果页。</Paragraph></div><div>✨</div></section><Card title="已生成效果" className="effect-studio__card"><div className="effect-row"><div><b>小赵天天开心</b><p>第一份可分享的祝福效果</p><code>{url}</code></div><Space wrap><Button icon={<CopyOutlined />} onClick={copy}>复制链接</Button><Button type="primary" icon={<ExportOutlined />} onClick={() => window.open(HAPPY_ZHAO_PATH, '_blank', 'noopener,noreferrer')}>预览效果</Button></Space></div></Card></div>;
}
