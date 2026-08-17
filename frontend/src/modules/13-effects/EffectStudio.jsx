import React, { useEffect, useRef } from 'react';
import { Button, Card, Space, Typography, message } from 'antd';
import { CopyOutlined, ExportOutlined } from '@ant-design/icons';
import './effects.css';

const { Paragraph, Title } = Typography;
export const HAPPY_ZHAO_PATH = '/effect/xiaozhao-happy';

function createRoseParticles(width, height) {
  const points = [];
  const scale = Math.min(width, height) / 720;
  const roseCenters = [
    [-150, -122, 1.03], [-45, -160, 1.12], [72, -148, 1.02], [165, -94, .88],
    [-105, -42, 1.08], [15, -58, 1.22], [125, -18, 1.02], [-35, 28, .92], [76, 35, .88],
  ];
  const add = (x, y, color, size = 1, depth = 1) => points.push({
    tx: width / 2 + x * scale,
    ty: height / 2 + y * scale,
    x: Math.random() * width,
    y: Math.random() * height,
    vx: 0,
    vy: 0,
    color,
    size: size * scale,
    depth,
    seed: Math.random() * Math.PI * 2,
  });

  roseCenters.forEach(([cx, cy, roseScale], roseIndex) => {
    for (let i = 0; i < 390; i += 1) {
      const layer = Math.random();
      const angle = Math.random() * Math.PI * 2 + layer * 4.8 + roseIndex * .37;
      const radius = (13 + layer * 58) * roseScale;
      const petalWave = 1 + .24 * Math.sin(angle * 5 + layer * 7);
      const x = cx + Math.cos(angle) * radius * petalWave;
      const y = cy + Math.sin(angle) * radius * .63 * petalWave + layer * 7;
      const palette = layer < .3 ? ['#d94171', '#ef638c'] : ['#ff8fae', '#ffc1d1', '#ffe0e7'];
      add(x, y, palette[Math.floor(Math.random() * palette.length)], .65 + Math.random() * 1.55, 1.15 - layer * .25);
    }
  });

  for (let i = 0; i < 1050; i += 1) {
    const angle = Math.random() * Math.PI * 2;
    const radius = Math.sqrt(Math.random());
    const x = Math.cos(angle) * (238 * radius);
    const y = -36 + Math.sin(angle) * (154 * radius);
    if (Math.random() > .43) add(x, y, Math.random() > .42 ? '#fff1eb' : '#e7dfcf', .55 + Math.random() * 1.25, .75);
  }

  for (let i = 0; i < 700; i += 1) {
    const side = Math.random() > .5 ? 1 : -1;
    const progress = Math.random();
    const x = side * (18 + progress * 105) + (Math.random() - .5) * 36;
    const y = 80 + progress * 185 + (Math.random() - .5) * 28;
    const color = progress < .43 ? (Math.random() > .4 ? '#f4e8de' : '#d6cab9') : (Math.random() > .5 ? '#7e263d' : '#b94862');
    add(x, y, color, .6 + Math.random() * 1.25, .7);
  }
  return points;
}

function RoseBouquetCanvas() {
  const canvasRef = useRef(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas.getContext('2d');
    let particles = [];
    let animationFrame;
    let startedAt = performance.now();
    const resize = () => {
      const ratio = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.round(window.innerWidth * ratio);
      canvas.height = Math.round(window.innerHeight * ratio);
      canvas.style.width = `${window.innerWidth}px`;
      canvas.style.height = `${window.innerHeight}px`;
      particles = createRoseParticles(canvas.width, canvas.height);
      startedAt = performance.now();
    };
    resize();
    window.addEventListener('resize', resize);
    const draw = (time) => {
      context.fillStyle = 'rgba(7, 8, 12, .17)';
      context.fillRect(0, 0, canvas.width, canvas.height);
      const progress = Math.min(1, (time - startedAt) / 3200);
      const pull = .018 + progress * .055;
      const breathe = 1 + Math.sin(time / 850) * .018;
      particles.forEach((particle) => {
        const centerX = canvas.width / 2;
        const centerY = canvas.height / 2;
        const targetX = centerX + (particle.tx - centerX) * breathe + Math.sin(time / 1100 + particle.seed) * 2.2;
        const targetY = centerY + (particle.ty - centerY) * breathe + Math.cos(time / 1250 + particle.seed) * 1.8;
        particle.vx = (particle.vx + (targetX - particle.x) * pull) * .82;
        particle.vy = (particle.vy + (targetY - particle.y) * pull) * .82;
        particle.x += particle.vx;
        particle.y += particle.vy;
        context.globalAlpha = .35 + particle.depth * .5;
        context.fillStyle = particle.color;
        context.beginPath();
        context.arc(particle.x, particle.y, particle.size * particle.depth, 0, Math.PI * 2);
        context.fill();
      });
      context.globalAlpha = 1;
      animationFrame = requestAnimationFrame(draw);
    };
    animationFrame = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(animationFrame);
      window.removeEventListener('resize', resize);
    };
  }, []);
  return <canvas ref={canvasRef} className="bouquet-canvas" aria-label="粉白粒子玫瑰花束动画" />;
}

export function PublicEffectPage() {
  return <main className="particle-effect">
    <div className="code-wall" aria-hidden="true"><span>def rose_particles(target, scale):</span><br />&nbsp;&nbsp;petals = create_roses(count=9)<br />&nbsp;&nbsp;bouquet.gather(petals)<br /><br />while running:<br />&nbsp;&nbsp;update_particles()<br />&nbsp;&nbsp;render_trails()</div>
    <div className="wireframe" aria-hidden="true"><i /><i /><i /><i /></div>
    <RoseBouquetCanvas />
    <div className="particle-message"><span>FOR YOU</span><strong>小赵天天开心</strong></div>
  </main>;
}

export function EffectStudio() {
  const url = `${window.location.origin}${HAPPY_ZHAO_PATH}`;
  const copy = async () => { await navigator.clipboard.writeText(url); message.success('公开链接已复制'); };
  return <div className="effect-studio">
    <section className="effect-studio__hero"><div><span>临时创作 · 仅链接可见</span><Title level={2}>🎀 临时效果</Title><Paragraph>生成可独立分享的效果页面，访问者不会看到私人空间和其他内容。</Paragraph></div><div>✨</div></section>
    <Card title="已生成效果" className="effect-studio__card"><div className="effect-row"><div><b>粒子玫瑰 · 小赵天天开心</b><p>粉白玫瑰花束粒子汇聚动画</p><code>{url}</code></div><Space wrap><Button icon={<CopyOutlined />} onClick={copy}>复制链接</Button><Button type="primary" icon={<ExportOutlined />} onClick={() => window.open(HAPPY_ZHAO_PATH, '_blank', 'noopener,noreferrer')}>预览效果</Button></Space></div></Card>
  </div>;
}
