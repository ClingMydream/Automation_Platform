import { copyText } from '../../shared/clipboard.js';
import React, { useEffect, useRef, useState } from 'react';
import { Button, Card, Empty, Modal, Popconfirm, Space, Typography, Upload, message } from 'antd';
import { CopyOutlined, DeleteOutlined, ExportOutlined, ReloadOutlined, UploadOutlined } from '@ant-design/icons';
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
    let lastFrameAt = startedAt;
    let autoRotation = 0;
    let manualRotation = 0;
    let angularVelocity = 0;
    let dragging = false;
    let activePointerId = null;
    let lastPointerX = 0;
    let lastPointerAt = 0;
    const bouquet = new Image();
    bouquet.src = '/effects/particle-rose-bouquet-v3-thick-stems.png';
    const buildFromBouquet = () => {
      if (!bouquet.complete || !bouquet.naturalWidth) return;
      const source = document.createElement('canvas');
      const sourceContext = source.getContext('2d', { willReadFrequently: true });
      const maxWidth = Math.min(canvas.width * (window.innerWidth <= 650 ? .86 : .72), 1400);
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
      lastFrameAt = startedAt;
      autoRotation = 0;
      angularVelocity = 0;
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
    const beginDrag = (event) => {
      dragging = true;
      activePointerId = event.pointerId;
      lastPointerX = event.clientX;
      lastPointerAt = performance.now();
      angularVelocity = 0;
      canvas.classList.add('is-dragging');
      canvas.setPointerCapture?.(event.pointerId);
    };
    const dragBouquet = (event) => {
      if (!dragging || event.pointerId !== activePointerId) return;
      const now = performance.now();
      const distance = event.clientX - lastPointerX;
      const elapsed = Math.max(8, now - lastPointerAt);
      const rotationChange = distance * .0085;
      manualRotation += rotationChange;
      angularVelocity = rotationChange / elapsed;
      lastPointerX = event.clientX;
      lastPointerAt = now;
    };
    const endDrag = (event) => {
      if (!dragging || event.pointerId !== activePointerId) return;
      dragging = false;
      canvas.classList.remove('is-dragging');
      if (canvas.hasPointerCapture?.(event.pointerId)) canvas.releasePointerCapture(event.pointerId);
      activePointerId = null;
    };
    const rotateWithKeyboard = (event) => {
      if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
      event.preventDefault();
      manualRotation += event.key === 'ArrowLeft' ? -.24 : .24;
      angularVelocity = event.key === 'ArrowLeft' ? -.004 : .004;
    };
    canvas.addEventListener('pointerdown', beginDrag);
    canvas.addEventListener('pointermove', dragBouquet);
    canvas.addEventListener('pointerup', endDrag);
    canvas.addEventListener('pointercancel', endDrag);
    canvas.addEventListener('keydown', rotateWithKeyboard);
    const draw = (time) => {
      context.fillStyle = 'rgba(7, 8, 12, .22)';
      context.fillRect(0, 0, canvas.width, canvas.height);
      const progress = Math.min(1, (time - startedAt) / 3600);
      const pull = .012 + progress * .062;
      const breathe = 1 + Math.sin(time / 850) * .012;
      const frameDuration = Math.min(40, Math.max(0, time - lastFrameAt));
      lastFrameAt = time;
      if (time - startedAt > 3200 && !dragging) autoRotation += frameDuration / 12000 * Math.PI * 2;
      if (!dragging) {
        manualRotation += angularVelocity * frameDuration;
        angularVelocity *= Math.pow(.91, frameDuration / 16.67);
      }
      const rotation = autoRotation + manualRotation;
      const cosine = Math.cos(rotation);
      const sine = Math.sin(rotation);
      if (bouquetMetrics && progress > .72) {
        context.save();
        context.globalCompositeOperation = 'screen';
        context.globalAlpha = (.12 + Math.pow(Math.abs(cosine), 7) * .2) * progress;
        context.translate(canvas.width / 2 + sine * bouquetMetrics.width * .012, 0);
        context.drawImage(bouquet, -bouquetMetrics.width / 2, bouquetMetrics.top, bouquetMetrics.width, bouquetMetrics.height);
        context.restore();
      }
      particles.forEach((particle) => {
        const centerX = canvas.width / 2;
        const centerY = canvas.height / 2;
        const localX = (particle.tx - centerX) * breathe;
        const localY = (particle.ty - centerY) * breathe;
        // 保持正面轮廓不被压扁，只让粒子深度产生视差和光影变化。
        const rotatedX = localX - particle.tz * sine * .31;
        const rotatedZ = particle.tz * cosine + localX * sine * .18;
        const perspective = 1800 / (1800 + rotatedZ);
        const targetX = centerX + rotatedX * perspective + Math.sin(time / 1100 + particle.seed) * 1.2;
        const targetY = centerY + (localY + particle.tz * sine * .018) * perspective + Math.cos(time / 1250 + particle.seed) * 1.1;
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
      canvas.removeEventListener('pointerdown', beginDrag);
      canvas.removeEventListener('pointermove', dragBouquet);
      canvas.removeEventListener('pointerup', endDrag);
      canvas.removeEventListener('pointercancel', endDrag);
      canvas.removeEventListener('keydown', rotateWithKeyboard);
    };
  }, []);
  return <canvas ref={canvasRef} className="bouquet-canvas gesture-rose-canvas" role="img" tabIndex={0} aria-label="可左右滑动旋转的粉白粒子玫瑰花束" />;
}

export function PublicEffectPage() {
  return <main className="particle-effect code-rose-effect">
    <div className="rose-aurora" aria-hidden="true" />
    <RoseBouquetCanvas />
    <div className="rose-gesture-hint" aria-hidden="true"><span>↔</span> 左右滑动旋转</div>
    <div className="particle-message"><i /><strong>小赵天天开心</strong><i /></div>
  </main>;
}

export function EffectStudio({ client, isAdmin }) {
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState(null);
  const [previewVersion, setPreviewVersion] = useState(0);
  const [phoneScale, setPhoneScale] = useState(1);
  const [builtinEnabled, setBuiltinEnabled] = useState(false);
  const url = `${window.location.origin}${HAPPY_ZHAO_PATH}`;
  const copy = async () => { if (!(await copyText(url))) { message.warning('复制失败，请手动选择链接'); return; } message.success('公开链接已复制'); };
  const refresh = async () => {
    try { setItems(await client.get('/effects/workspace')); }
    catch (error) { message.error(error.message); }
  };
  useEffect(() => { refresh(); }, [client]);
  useEffect(() => { client.get('/effects/builtin').then((state) => setBuiltinEnabled(state.enabled)).catch((error) => message.error(error.message)); }, [client]);
  useEffect(() => {
    if (!preview) return;
    const resize = () => setPhoneScale(Math.max(0.3, Math.min(1, (window.innerWidth - 64) / 450, (window.innerHeight - 190) / 952)));
    resize();
    window.addEventListener('resize', resize);
    return () => window.removeEventListener('resize', resize);
  }, [preview]);
  const upload = async (file) => {
    setBusy(true);
    try {
      const data = new FormData();
      data.append('file', file);
      await client.post('/effects/workspace', data);
      await refresh();
      message.success('临时效果已上传');
    } catch (error) { message.error(error.message); }
    finally { setBusy(false); }
    return false;
  };
  const clearEffects = async () => {
    setBusy(true);
    try { await client.delete('/effects/workspace'); await refresh(); message.success('临时效果文件已清空'); }
    catch (error) { message.error(error.message); }
    finally { setBusy(false); }
  };
  const remove = async (id) => {
    try { await client.delete(`/effects/workspace/${id}`); await refresh(); message.success('已删除'); }
    catch (error) { message.error(error.message); }
  };
  return <div className="effect-studio">
    <section className="effect-studio__hero"><div><span>独立工作空间 · 随时清空</span><Title level={2}>🎀 临时效果</Title><Paragraph>上传构建后的网页 ZIP，在这里独立预览；清空将删除服务器上的临时文件，不影响其他项目或分支。</Paragraph></div><div>✨</div></section>
    <Card
      title="临时效果工作空间"
      className="effect-studio__card"
      extra={isAdmin && <Space><Upload accept=".zip" showUploadList={false} beforeUpload={upload}><Button loading={busy} icon={<UploadOutlined />}>上传网页 ZIP</Button></Upload><Popconfirm title="确认清空全部临时效果？" description="会永久删除此工作空间内的所有文件，不影响其他项目。" okText="确认清空" cancelText="取消" onConfirm={clearEffects}><Button danger disabled={!items.length} loading={busy} icon={<DeleteOutlined />}>清空</Button></Popconfirm></Space>}
    >
      {!items.length ? <Empty description="还没有上传临时效果" /> : items.map(item => <div className="effect-row" key={item.id}><div><b>{item.name}</b><p>独立临时文件，可随时删除</p><code>{window.location.origin}{item.url}</code></div><Space wrap><Button icon={<CopyOutlined />} onClick={async () => { if (!(await copyText(`${window.location.origin}${item.url}`))) { message.warning('复制失败，请手动选择链接'); return; } message.success('链接已复制'); }}>复制链接</Button><Button type="primary" icon={<ExportOutlined />} onClick={() => setPreview(item)}>平台内预览</Button>{isAdmin && <Popconfirm title="删除这个临时效果？" onConfirm={() => remove(item.id)}><Button danger icon={<DeleteOutlined />}>删除</Button></Popconfirm>}</Space></div>)}
    </Card>
    <Modal title={preview?.name || '临时效果预览'} open={!!preview} onCancel={() => setPreview(null)} footer={<Space><Button icon={<ReloadOutlined />} onClick={() => setPreviewVersion((value) => value + 1)}>刷新预览</Button><Button onClick={() => window.open(preview?.url, '_blank', 'noopener,noreferrer')}>新窗口打开</Button></Space>} width="min(96vw, 620px)" destroyOnHidden>
      <div className="effect-phone-preview">
        <p>430 × 932 · 手机样式预览</p>
        <div className="effect-phone-preview__slot" style={{ width: 450 * phoneScale, height: 952 * phoneScale }}>
          <div className="effect-phone-preview__device" style={{ transform: `scale(${phoneScale})` }}>
            <div className="effect-phone-preview__speaker" />
            <iframe key={`${preview?.id}-${previewVersion}`} className="effect-preview-frame" title={preview?.name || '临时效果'} src={preview?.url} />
          </div>
        </div>
      </div>
    </Modal>
    {builtinEnabled && <Card title="平台自带效果" className="effect-studio__card"><div className="effect-row"><div><b>可交互粒子玫瑰 · 小赵天天开心</b><p>平台内置效果，可由管理员删除。</p><code>{url}</code></div><Space wrap><Button icon={<CopyOutlined />} onClick={copy}>复制链接</Button><Button icon={<ExportOutlined />} onClick={() => setPreview({ id: 'builtin', name: '可交互粒子玫瑰 · 小赵天天开心', url: HAPPY_ZHAO_PATH })}>平台内预览</Button>{isAdmin && <Popconfirm title="删除这个平台自带效果？" description="删除后公开链接也将停止展示。" okText="删除" cancelText="取消" onConfirm={async () => { try { await client.delete('/effects/builtin'); setBuiltinEnabled(false); setPreview(null); message.success('已删除'); } catch (error) { message.error(error.message); } }}><Button danger icon={<DeleteOutlined />}>删除</Button></Popconfirm>}</Space></div></Card>}
  </div>;
}
