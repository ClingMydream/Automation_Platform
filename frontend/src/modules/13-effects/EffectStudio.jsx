import React, { useEffect, useRef } from 'react';
import { Button, Card, Space, Typography, message } from 'antd';
import { CopyOutlined, ExportOutlined } from '@ant-design/icons';
import './effects.css';

const { Paragraph, Title } = Typography;
export const HAPPY_ZHAO_PATH = '/effect/xiaozhao-happy';

export function PublicEffectPage() {
  const ref = useRef(null);
  useEffect(() => { const canvas = ref.current; const ctx = canvas.getContext('2d'); let frame; const dots = Array.from({ length: 2600 }, (_, i) => { const t = Math.random() * Math.PI * 2; const r = Math.sqrt(Math.random()); const x = 16 * Math.sin(t) ** 3; const y = -(13 * Math.cos(t) - 5 * Math.cos(2 * t) - 2 * Math.cos(3 * t) - Math.cos(4 * t)); return { x, y, sx:(Math.random()-.5)*1500, sy:(Math.random()-.5)*900, c:i%6 ? '#ffc1d5' : '#fff5ed', z:r }; }); const draw = (now) => { const w = canvas.width = innerWidth * devicePixelRatio, h = canvas.height = innerHeight * devicePixelRatio, scale = Math.min(w,h)/38; ctx.fillStyle='rgba(11,12,16,.20)'; ctx.fillRect(0,0,w,h); const breathe=1+Math.sin(now/900)*.035; dots.forEach((p,i)=>{ const arrive=Math.min(1,now/2400); const ease=1-(1-arrive)**3; const x=(p.sx+(p.x*scale*breathe-p.sx)*ease)+w/2; const y=(p.sy+(p.y*scale*breathe-p.sy)*ease)+h/2; ctx.globalAlpha=.24+p.z*.76; ctx.fillStyle=p.c; ctx.fillRect(x,y,2+3*p.z,2+3*p.z); }); frame=requestAnimationFrame(draw); }; frame=requestAnimationFrame(draw); return()=>cancelAnimationFrame(frame); }, []);
  return <main className="particle-effect"><canvas ref={ref} /><div className="code-wall">def create_heart_particles():<br />&nbsp;&nbsp;target = love_forever<br />&nbsp;&nbsp;particles.gather(target)</div><div className="wireframe" /><div className="particle-message">小赵<br /><strong>天天开心</strong></div></main>;
}

export function EffectStudio() {
  const url = `${window.location.origin}${HAPPY_ZHAO_PATH}`;
  const copy = async () => { await navigator.clipboard.writeText(url); message.success('公开链接已复制'); };
  return <div className="effect-studio"><section className="effect-studio__hero"><div><span>临时创作 · 仅链接可见</span><Title level={2}>🎀 临时效果</Title><Paragraph>制作一句话、一张祝福或一个小动画；分享出去的人只会看到效果页。</Paragraph></div><div>✨</div></section><Card title="已生成效果" className="effect-studio__card"><div className="effect-row"><div><b>小赵天天开心</b><p>第一份可分享的祝福效果</p><code>{url}</code></div><Space wrap><Button icon={<CopyOutlined />} onClick={copy}>复制链接</Button><Button type="primary" icon={<ExportOutlined />} onClick={() => window.open(HAPPY_ZHAO_PATH, '_blank', 'noopener,noreferrer')}>预览效果</Button></Space></div></Card></div>;
}
