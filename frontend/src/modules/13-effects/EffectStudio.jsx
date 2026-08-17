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
    let bouquetMetrics = null;
    let animationFrame;
    let startedAt = performance.now();
    const bouquet = new Image();
    bouquet.src = '/effects/particle-rose-bouquet-v3-thick-stems.png';
    const buildFromBouquet = () => {
      if (!bouquet.complete || !bouquet.naturalWidth) return;
      const source = document.createElement('canvas');
      const sourceContext = source.getContext('2d', { willReadFrequently: true });
      const maxWidth = Math.min(canvas.width * .72, 1400);
      const maxHeight = Math.min(canvas.height * .86, 1000);
      const ratio = Math.min(maxWidth / bouquet.naturalWidth, maxHeight / bouquet.naturalHeight);
      source.width = Math.max(1, Math.round(bouquet.naturalWidth * ratio));
      source.height = Math.max(1, Math.round(bouquet.naturalHeight * ratio));
      sourceContext.drawImage(bouquet, 0, 0, source.width, source.height);
      const pixels = sourceContext.getImageData(0, 0, source.width, source.height).data;
      const candidates = [];
      for (let y = 0; y < source.height; y += 2) {
        for (let x = 0; x < source.width; x += 2) {
          const offset = (y * source.width + x) * 4;
          const red = pixels[offset];
          const green = pixels[offset + 1];
          const blue = pixels[offset + 2];
          if (red + green + blue > 125) candidates.push([x, y, red, green, blue]);
        }
      }
      for (let index = candidates.length - 1; index > 0; index -= 1) {
        const other = Math.floor(Math.random() * (index + 1));
        [candidates[index], candidates[other]] = [candidates[other], candidates[index]];
      }
      const left = (canvas.width - source.width) / 2;
      const top = (canvas.height - source.height) / 2 - canvas.height * .015;
      bouquetMetrics = { width: source.width, height: source.height, top };
      const particleLimit = window.innerWidth <= 650 ? 18000 : 28000;
      particles = candidates.slice(0, particleLimit).map(([x, y, red, green, blue]) => {
        const verticalPosition = y / source.height;
        const normalizedX = (x - source.width / 2) / (source.width / 2);
        const roundedEdge = Math.sqrt(Math.max(.08, 1 - normalizedX * normalizedX));
        const depthRatio = verticalPosition < .6 ? .38 : verticalPosition < .78 ? .24 : .1;
        return {
        tx: left + x,
        ty: top + y,
        tz: (Math.random() * 2 - 1) * source.width * depthRatio * roundedEdge,
        x: Math.random() > .5 ? -80 : canvas.width + 80,
        y: Math.random() * canvas.height,
        vx: 0,
        vy: 0,
        color: `rgb(${red},${green},${blue})`,
        size: .45 + Math.random() * .85,
        depth: .62 + Math.random() * .55,
        seed: Math.random() * Math.PI * 2,
        };
      });
      startedAt = performance.now();
    };
    const resize = () => {
      const ratio = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = Math.round(window.innerWidth * ratio);
      canvas.height = Math.round(window.innerHeight * ratio);
      canvas.style.width = `${window.innerWidth}px`;
      canvas.style.height = `${window.innerHeight}px`;
      buildFromBouquet();
    };
    resize();
    bouquet.addEventListener('load', buildFromBouquet);
    window.addEventListener('resize', resize);
    const draw = (time) => {
      context.fillStyle = 'rgba(7, 8, 12, .22)';
      context.fillRect(0, 0, canvas.width, canvas.height);
      const progress = Math.min(1, (time - startedAt) / 3600);
      const pull = .012 + progress * .062;
      const breathe = 1 + Math.sin(time / 850) * .012;
      const rotation = Math.max(0, time - startedAt - 3200) / 12000 * Math.PI * 2;
      const cosine = Math.cos(rotation);
      const sine = Math.sin(rotation);
      if (bouquetMetrics && progress > .72) {
        context.save();
        context.globalCompositeOperation = 'screen';
        context.globalAlpha = Math.pow(Math.abs(cosine), 7) * .34 * progress;
        context.translate(canvas.width / 2, 0);
        context.scale(cosine, 1);
        context.drawImage(bouquet, -bouquetMetrics.width / 2, bouquetMetrics.top, bouquetMetrics.width, bouquetMetrics.height);
        context.restore();
      }
      particles.forEach((particle) => {
        const centerX = canvas.width / 2;
        const centerY = canvas.height / 2;
        const localX = (particle.tx - centerX) * breathe;
        const localY = (particle.ty - centerY) * breathe;
        const rotatedX = localX * cosine - particle.tz * sine;
        const rotatedZ = localX * sine + particle.tz * cosine;
        const perspective = 1800 / (1800 + rotatedZ);
        const targetX = centerX + rotatedX * perspective + Math.sin(time / 1100 + particle.seed) * 1.2;
        const targetY = centerY + localY * perspective + Math.cos(time / 1250 + particle.seed) * 1.1;
        particle.vx = (particle.vx + (targetX - particle.x) * pull) * .82;
        particle.vy = (particle.vy + (targetY - particle.y) * pull) * .82;
        particle.x += particle.vx;
        particle.y += particle.vy;
        context.globalAlpha = .42 + particle.depth * .42;
        context.fillStyle = particle.color;
        const pointSize = Math.max(.6, particle.size * particle.depth * perspective);
        context.fillRect(particle.x, particle.y, pointSize, pointSize);
      });
      context.globalAlpha = 1;
      animationFrame = requestAnimationFrame(draw);
    };
    animationFrame = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(animationFrame);
      bouquet.removeEventListener('load', buildFromBouquet);
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
    <div className="particle-message" aria-label="小赵天天开心"><i /><strong>小赵天天开心</strong><i /></div>
  </main>;
}

export function EffectStudio() {
  const url = `${window.location.origin}${HAPPY_ZHAO_PATH}`;
  const copy = async () => { await navigator.clipboard.writeText(url); message.success('公开链接已复制'); };
  return <div className="effect-studio">
    <section className="effect-studio__hero"><div><span>临时创作 · 仅链接可见</span><Title level={2}>🎀 临时效果</Title><Paragraph>生成可独立分享的效果页面，访问者不会看到私人空间和其他内容。</Paragraph></div><div>✨</div></section>
    <Card title="已生成效果" className="effect-studio__card"><div className="effect-row"><div><b>粒子玫瑰 · 小赵天天开心</b><p>粗花把玫瑰花束粒子汇聚与呼吸动画</p><code>{url}</code></div><Space wrap><Button icon={<CopyOutlined />} onClick={copy}>复制链接</Button><Button type="primary" icon={<ExportOutlined />} onClick={() => window.open(HAPPY_ZHAO_PATH, '_blank', 'noopener,noreferrer')}>预览效果</Button></Space></div></Card>
  </div>;
}
