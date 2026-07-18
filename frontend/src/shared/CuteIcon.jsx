import React from 'react';

export function CuteIcon({ emoji, tone = 'blue', size = 30, className = '' }) {
  return (
    <span
      aria-hidden="true"
      className={`cute-icon cute-icon-${tone} ${className}`}
      style={{ width: size, height: size, fontSize: Math.round(size * 0.55) }}
    >
      {emoji}
    </span>
  );
}
