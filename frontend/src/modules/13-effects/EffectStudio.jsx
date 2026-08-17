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

const ROSE_TONES = {
  pink: { hue: 344, saturation: 76, lightness: 39 },
  blush: { hue: 350, saturation: 58, lightness: 48 },
  ivory: { hue: 12, saturation: 42, lightness: 63 },
  ruby: { hue: 347, saturation: 72, lightness: 32 },
};

const ROSE_HEADS = [
  [-136, -102, -12, .94, 'pink', -.42, -.04],
  [-70, -154, 28, 1.05, 'blush', -.24, -.1],
  [12, -166, -12, 1.16, 'pink', .02, -.13],
  [103, -136, 24, 1, 'ivory', .3, -.08],
  [158, -76, -20, .84, 'pink', .48, 0],
  [-158, -43, 28, .82, 'ivory', -.52, .02],
  [-82, -46, 86, 1.06, 'pink', -.2, 0],
  [14, -61, 102, 1.14, 'blush', .02, .02],
  [105, -35, 74, 1.01, 'pink', .28, .01],
  [-119, 24, 8, .84, 'ruby', -.42, .08],
  [-27, 19, 66, .97, 'ivory', -.1, .05],
  [69, 24, 34, .92, 'blush', .16, .05],
];

function particleColor(toneName, exposure, variation = 0) {
  const tone = ROSE_TONES[toneName];
  const hue = tone.hue + variation * 7;
  const saturation = Math.max(28, tone.saturation - exposure * 9 + variation * 4);
  const lightness = Math.min(94, tone.lightness + exposure * 43 + variation * 5);
  return `hsl(${hue} ${saturation}% ${lightness}%)`;
}

function rotateRosePoint(x, y, z, yaw, pitch) {
  const yawCosine = Math.cos(yaw);
  const yawSine = Math.sin(yaw);
  const pitchedX = x * yawCosine + z * yawSine;
  const yawedZ = -x * yawSine + z * yawCosine;
  const pitchCosine = Math.cos(pitch);
  const pitchSine = Math.sin(pitch);
  return [
    pitchedX,
    y * pitchCosine - yawedZ * pitchSine,
    y * pitchSine + yawedZ * pitchCosine,
  ];
}

function createParametricBouquet(density = 1) {
  const particles = [];
  const addParticle = (x, y, z, color, size = 1, alpha = .9, glow = 0) => {
    particles.push({
      x,
      y,
      z,
      color,
      size,
      alpha,
      glow,
      seed: Math.random() * Math.PI * 2,
      startAngle: Math.random() * Math.PI * 2,
      startRadius: 300 + Math.random() * 560,
      delay: Math.random() * .3,
    });
  };

  // 先生成花束下方的包装和粗实花柄，让侧面旋转时仍保持完整体积。
  const wrapperCount = Math.round(1450 * density);
  for (let index = 0; index < wrapperCount; index += 1) {
    const progress = Math.random();
    const y = 68 + progress * 198;
    const halfWidth = 67 - progress * 27;
    const x = (Math.random() * 2 - 1) * halfWidth;
    const z = (Math.random() * 2 - 1) * (31 - progress * 7);
    const isHighlight = Math.random() > .76;
    addParticle(
      x,
      y,
      z,
      isHighlight ? particleColor('blush', .56, Math.random() - .5) : particleColor('ruby', .12 + progress * .18, Math.random() - .5),
      .7 + Math.random() * 1.2,
      .76 + Math.random() * .2,
    );
  }

  const ribbonCount = Math.round(430 * density);
  for (let index = 0; index < ribbonCount; index += 1) {
    const side = Math.random() > .5 ? 1 : -1;
    const distance = Math.pow(Math.random(), .7) * 85;
    const x = side * distance;
    const y = 142 + (Math.random() * 2 - 1) * (17 + distance * .08);
    const z = 28 + (Math.random() * 2 - 1) * 10;
    addParticle(x, y, z, particleColor('ivory', .58 + Math.random() * .24, Math.random() - .5), .75 + Math.random(), .9, .16);
  }

  // 每支花都拥有独立的三维花茎和叶片，旋转后不会退化成一条平面细线。
  ROSE_HEADS.forEach(([centerX, centerY, centerZ], roseIndex) => {
    const stemCount = Math.round(155 * density);
    for (let index = 0; index < stemCount; index += 1) {
      const progress = Math.random();
      const easedProgress = progress * progress * (3 - 2 * progress);
      const stemX = centerX * .08 + (centerX * .82 - centerX * .08) * easedProgress + Math.sin(progress * Math.PI) * (roseIndex % 2 ? 8 : -8);
      const stemY = 230 + (centerY + 31 - 230) * progress;
      const stemZ = centerZ * .1 + (centerZ - 7 - centerZ * .1) * progress;
      const tubeAngle = Math.random() * Math.PI * 2;
      const radius = 2.4 + (1 - progress) * 2.8;
      addParticle(
        stemX + Math.cos(tubeAngle) * radius,
        stemY + (Math.random() - .5) * 2.8,
        stemZ + Math.sin(tubeAngle) * radius,
        `hsl(${342 + Math.random() * 14} ${26 + Math.random() * 20}% ${24 + Math.random() * 24}%)`,
        .65 + Math.random() * .9,
        .72 + Math.random() * .2,
      );
    }

    if (roseIndex % 2 === 0) {
      const leafProgress = .42 + Math.random() * .25;
      const anchorX = centerX * (.08 + .74 * leafProgress);
      const anchorY = 230 + (centerY + 31 - 230) * leafProgress;
      const anchorZ = centerZ * (.1 + .82 * leafProgress);
      const leafSide = roseIndex % 4 === 0 ? -1 : 1;
      const leafCount = Math.round(150 * density);
      for (let index = 0; index < leafCount; index += 1) {
        const progress = Math.random();
        const width = (Math.random() * 2 - 1) * Math.sin(progress * Math.PI) * 18;
        addParticle(
          anchorX + leafSide * progress * 62 + width * .2,
          anchorY - progress * 38 + width * .52,
          anchorZ + width,
          `hsl(${346 + Math.random() * 12} ${22 + Math.random() * 17}% ${26 + Math.random() * 24}%)`,
          .65 + Math.random() * 1.05,
          .68 + Math.random() * .22,
        );
      }
    }
  });

  // 四层花瓣由参数曲面生成：内层收紧、外层展开，并通过弯曲高度形成玫瑰的螺旋层次。
  const petalRings = [
    { count: 3, base: 1, length: 16, spread: .75, curl: 11, samples: 72 },
    { count: 5, base: 7, length: 22, spread: .54, curl: 14, samples: 62 },
    { count: 8, base: 16, length: 27, spread: .4, curl: 16, samples: 52 },
    { count: 12, base: 27, length: 31, spread: .3, curl: 13, samples: 44 },
  ];

  ROSE_HEADS.forEach(([centerX, centerY, centerZ, roseScale, toneName, yaw, pitch], roseIndex) => {
    petalRings.forEach((ring, ringIndex) => {
      for (let petalIndex = 0; petalIndex < ring.count; petalIndex += 1) {
        const baseAngle = petalIndex / ring.count * Math.PI * 2 + ringIndex * 1.11 + roseIndex * .19;
        const sampleCount = Math.round(ring.samples * density);
        for (let sampleIndex = 0; sampleIndex < sampleCount; sampleIndex += 1) {
          const progress = Math.pow(Math.random(), .82);
          const crossPosition = Math.random() * 2 - 1;
          const petalWidth = Math.pow(Math.sin(progress * Math.PI), .56);
          const angle = baseAngle + crossPosition * ring.spread * petalWidth;
          const radius = ring.base + ring.length * progress;
          const localX = Math.cos(angle) * radius * roseScale;
          const localY = Math.sin(angle) * radius * .86 * roseScale;
          const localZ = (
            29 - ringIndex * 6.2
            + ring.curl * Math.sin(progress * Math.PI)
            - Math.abs(crossPosition) * 5
            + (Math.random() - .5) * 2.4
          ) * roseScale;
          const [orientedX, orientedY, orientedZ] = rotateRosePoint(localX, localY, localZ, yaw, pitch);
          const exposure = .16 + progress * .48 + Math.abs(crossPosition) * .22 + ringIndex * .025;
          addParticle(
            centerX + orientedX,
            centerY + orientedY,
            centerZ + orientedZ,
            particleColor(toneName, exposure, Math.random() - .5),
            .7 + Math.random() * 1.18 + (1 - ringIndex / 4) * .22,
            .78 + Math.random() * .2,
            Math.random() > .9 ? .2 : 0,
          );
        }

        const edgeSampleCount = Math.max(5, Math.round((ringIndex < 2 ? 11 : 8) * density));
        [-1, 1].forEach((edgeSide) => {
          for (let edgeIndex = 1; edgeIndex <= edgeSampleCount; edgeIndex += 1) {
            const progress = edgeIndex / (edgeSampleCount + 1);
            const petalWidth = Math.pow(Math.sin(progress * Math.PI), .56);
            const angle = baseAngle + edgeSide * ring.spread * petalWidth * .94;
            const radius = ring.base + ring.length * progress;
            const localX = Math.cos(angle) * radius * roseScale;
            const localY = Math.sin(angle) * radius * .86 * roseScale;
            const localZ = (
              29 - ringIndex * 6.2
              + ring.curl * Math.sin(progress * Math.PI)
              - 4.7
            ) * roseScale;
            const [orientedX, orientedY, orientedZ] = rotateRosePoint(localX, localY, localZ, yaw, pitch);
            addParticle(
              centerX + orientedX,
              centerY + orientedY,
              centerZ + orientedZ,
              particleColor(toneName, .62 + progress * .18, edgeSide * .12),
              1 + Math.random() * .7,
              .94,
              .16,
            );
          }
        });
      }
    });

    const centerCount = Math.round(270 * density);
    for (let index = 0; index < centerCount; index += 1) {
      const spiralProgress = index / centerCount;
      const angle = index * 2.39996 + roseIndex * .37 + (Math.random() - .5) * .18;
      const radius = Math.sqrt(spiralProgress) * 17 * roseScale;
      const [orientedX, orientedY, orientedZ] = rotateRosePoint(
        Math.cos(angle) * radius,
        Math.sin(angle) * radius * .8,
        (39 - radius * .5 + Math.sin(angle * .5) * 1.8) * roseScale,
        yaw,
        pitch,
      );
      addParticle(
        centerX + orientedX,
        centerY + orientedY,
        centerZ + orientedZ,
        particleColor(toneName, .22 + spiralProgress * .3, Math.random() - .5),
        .82 + Math.random() * 1.2,
        .94,
        .22,
      );
    }
  });

  const dustCount = Math.round(540 * density);
  for (let index = 0; index < dustCount; index += 1) {
    const angle = Math.random() * Math.PI * 2;
    const radius = 180 + Math.random() * 155;
    addParticle(
      Math.cos(angle) * radius,
      -58 + Math.sin(angle) * radius * .62,
      (Math.random() * 2 - 1) * 145,
      Math.random() > .36 ? '#f8c7d3' : '#fff1e7',
      .45 + Math.random() * .95,
      .18 + Math.random() * .36,
      .3,
    );
  }
  return particles;
}

function CodeRoseBouquetCanvas() {
  const canvasRef = useRef(null);
  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas.getContext('2d', { alpha: true });
    let particles = [];
    let animationFrame = 0;
    let viewportWidth = window.innerWidth;
    let viewportHeight = window.innerHeight;
    let startedAt = performance.now();

    const resize = () => {
      const pixelRatio = Math.min(window.devicePixelRatio || 1, 1.75);
      viewportWidth = window.innerWidth;
      viewportHeight = window.innerHeight;
      canvas.width = Math.round(viewportWidth * pixelRatio);
      canvas.height = Math.round(viewportHeight * pixelRatio);
      canvas.style.width = `${viewportWidth}px`;
      canvas.style.height = `${viewportHeight}px`;
      context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
      particles = createParametricBouquet(viewportWidth <= 650 ? .78 : 1);
      startedAt = performance.now();
    };

    const draw = (time) => {
      const elapsed = time - startedAt;
      const introduction = Math.min(1, elapsed / 3300);
      const easedIntroduction = 1 - Math.pow(1 - introduction, 3);
      const rotation = Math.max(0, elapsed - 2200) / 22000 * Math.PI * 2;
      const rotationCosine = Math.cos(rotation);
      const rotationSine = Math.sin(rotation);
      const tilt = -.055 + Math.sin(elapsed / 4200) * .025;
      const tiltCosine = Math.cos(tilt);
      const tiltSine = Math.sin(tilt);
      const sceneScale = Math.min(viewportWidth / 760, viewportHeight / 760) * (viewportWidth <= 650 ? 1.1 : 1.04);
      const centerX = viewportWidth / 2;
      const centerY = viewportHeight * (viewportWidth <= 650 ? .43 : .47);
      const cameraDistance = 930;

      context.fillStyle = 'rgba(5, 4, 8, .36)';
      context.fillRect(0, 0, viewportWidth, viewportHeight);
      context.globalCompositeOperation = 'screen';

      particles.forEach((particle) => {
        const breathedX = particle.x * (1 + Math.sin(elapsed / 1200 + particle.seed) * .005);
        const rotatedX = breathedX * rotationCosine + particle.z * rotationSine;
        const rotatedZ = -breathedX * rotationSine + particle.z * rotationCosine;
        const tiltedY = particle.y * tiltCosine - rotatedZ * tiltSine;
        const tiltedZ = particle.y * tiltSine + rotatedZ * tiltCosine;
        const perspective = cameraDistance / (cameraDistance + tiltedZ * sceneScale);
        const targetX = centerX + rotatedX * sceneScale * perspective;
        const targetY = centerY + tiltedY * sceneScale * perspective;
        const particleProgress = Math.max(0, Math.min(1, (easedIntroduction - particle.delay) / (1 - particle.delay)));
        const startX = centerX + Math.cos(particle.startAngle) * particle.startRadius;
        const startY = centerY + Math.sin(particle.startAngle) * particle.startRadius * .72;
        const drift = Math.sin(elapsed / 820 + particle.seed) * (1.2 + particle.glow * 2.5);
        const screenX = startX + (targetX - startX) * particleProgress + drift;
        const screenY = startY + (targetY - startY) * particleProgress + Math.cos(elapsed / 930 + particle.seed) * .8;
        const pointSize = Math.max(.55, particle.size * sceneScale * perspective);
        const twinkle = particle.glow ? .78 + Math.sin(elapsed / 360 + particle.seed) * .22 : 1;

        context.globalAlpha = particle.alpha * particleProgress * twinkle * Math.max(.48, Math.min(1.08, perspective));
        context.fillStyle = particle.color;
        context.fillRect(screenX, screenY, pointSize, pointSize);
        if (particle.glow > .12 && pointSize > .7) {
          context.globalAlpha *= .16;
          context.fillRect(screenX - pointSize, screenY - pointSize, pointSize * 3, pointSize * 3);
        }
      });

      context.globalCompositeOperation = 'source-over';
      context.globalAlpha = 1;
      animationFrame = requestAnimationFrame(draw);
    };

    resize();
    window.addEventListener('resize', resize);
    animationFrame = requestAnimationFrame(draw);
    return () => {
      cancelAnimationFrame(animationFrame);
      window.removeEventListener('resize', resize);
    };
  }, []);
  return <canvas ref={canvasRef} className="bouquet-canvas code-rose-canvas" role="img" aria-label="代码生成的三维粒子玫瑰花束动画" />;
}

export function PublicEffectPage() {
  return <main className="particle-effect code-rose-effect">
    <div className="rose-aurora" aria-hidden="true" />
    <RoseBouquetCanvas />
    <div className="rose-gesture-hint" aria-hidden="true"><span>↔</span> 左右滑动旋转</div>
    <div className="particle-message"><i /><strong>小赵天天开心</strong><i /></div>
  </main>;
}

export function EffectStudio() {
  const url = `${window.location.origin}${HAPPY_ZHAO_PATH}`;
  const copy = async () => { await navigator.clipboard.writeText(url); message.success('公开链接已复制'); };
  return <div className="effect-studio">
    <section className="effect-studio__hero"><div><span>临时创作 · 仅链接可见</span><Title level={2}>🎀 临时效果</Title><Paragraph>生成可独立分享的效果页面，访问者不会看到私人空间和其他内容。</Paragraph></div><div>✨</div></section>
    <Card title="已生成效果" className="effect-studio__card"><div className="effect-row"><div><b>可交互粒子玫瑰 · 小赵天天开心</b><p>约 28000 粒子、12 秒 360° 自动旋转；每个角度保持正面饱满轮廓，支持手指滑动、鼠标拖动和惯性</p><code>{url}</code></div><Space wrap><Button icon={<CopyOutlined />} onClick={copy}>复制链接</Button><Button type="primary" icon={<ExportOutlined />} onClick={() => window.open(HAPPY_ZHAO_PATH, '_blank', 'noopener,noreferrer')}>预览效果</Button></Space></div></Card>
  </div>;
}
