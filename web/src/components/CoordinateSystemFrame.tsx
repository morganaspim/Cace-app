import React from 'react';
import { Rotation3D } from '../types';

interface CoordinateSystemFrameProps {
  rotation3D?: Rotation3D;
  visible?: boolean;
}

export const CoordinateSystemFrame: React.FC<CoordinateSystemFrameProps> = ({
  rotation3D = { x: 0, y: 0, z: 0 },
  visible = true
}) => {
  if (!visible) return null;

  const is3D = rotation3D.x !== 0 || rotation3D.y !== 0 || rotation3D.z !== 0;

  // Numerical coordinate tick values along axes (-600 to +1800)
  const ticks = [-600, -400, -200, 200, 400, 600, 800, 1000, 1200, 1400, 1600, 1800];

  return (
    <g id="coordinate-system-frame" className="pointer-events-none select-none">
      <defs>
        {/* Markers for Axis Arrows */}
        <marker id="axis-arrow-x" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 1 L 10 5 L 0 9 z" fill="#f43f5e" />
        </marker>
        <marker id="axis-arrow-y" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 1 L 10 5 L 0 9 z" fill="#10b981" />
        </marker>
        <marker id="axis-arrow-z" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M 0 1 L 10 5 L 0 9 z" fill="#818cf8" />
        </marker>
      </defs>

      {/* Coordinate System Origin Plane Guide Lines */}
      <rect
        x="-800"
        y="-800"
        width="2800"
        height="2400"
        fill="none"
        stroke="rgba(99, 102, 241, 0.12)"
        strokeWidth="1.5"
        strokeDasharray="6,4"
      />

      {/* Primary X-Axis (Coral Red, #f43f5e) */}
      <line
        x1="-800"
        y1="0"
        x2="2000"
        y2="0"
        stroke="#f43f5e"
        strokeWidth="2.5"
        strokeLinecap="round"
        markerEnd="url(#axis-arrow-x)"
        className="drop-shadow-[0_0_8px_rgba(244,63,94,0.4)]"
      />
      {/* Primary Y-Axis (Emerald Green, #10b981) */}
      <line
        x1="0"
        y1="-800"
        x2="0"
        y2="1800"
        stroke="#10b981"
        strokeWidth="2.5"
        strokeLinecap="round"
        markerEnd="url(#axis-arrow-y)"
        className="drop-shadow-[0_0_8px_rgba(16,185,129,0.4)]"
      />

      {/* Axis Ticks and Coordinates along X */}
      {ticks.map((t) => (
        <g key={`tick-x-${t}`}>
          <line
            x1={t}
            y1="-6"
            x2={t}
            y2="6"
            stroke="#f43f5e"
            strokeWidth="1.8"
            strokeOpacity="0.8"
          />
          <text
            x={t}
            y="-10"
            textAnchor="middle"
            fill="#fda4af"
            fontSize="10"
            fontFamily="monospace"
            fontWeight="bold"
            className="drop-shadow-[0_1px_2px_rgba(0,0,0,0.8)]"
          >
            {t > 0 ? `+${t}` : t}
          </text>
        </g>
      ))}

      {/* Axis Ticks and Coordinates along Y */}
      {ticks.map((t) => (
        <g key={`tick-y-${t}`}>
          <line
            x1="-6"
            y1={t}
            x2="6"
            y2={t}
            stroke="#10b981"
            strokeWidth="1.8"
            strokeOpacity="0.8"
          />
          <text
            x="-12"
            y={t + 3.5}
            textAnchor="end"
            fill="#a7f3d0"
            fontSize="10"
            fontFamily="monospace"
            fontWeight="bold"
            className="drop-shadow-[0_1px_2px_rgba(0,0,0,0.8)]"
          >
            {t > 0 ? `+${t}` : t}
          </text>
        </g>
      ))}

      {/* Defined Axis Badges */}
      <g transform="translate(2020, 0)">
        <rect x="0" y="-12" width="68" height="24" rx="6" fill="#18181b" stroke="#f43f5e" strokeWidth="1.5" />
        <text x="34" y="4" textAnchor="middle" fill="#fda4af" fontSize="11" fontFamily="monospace" fontWeight="bold">
          +X Axis
        </text>
      </g>

      <g transform="translate(0, 1820)">
        <rect x="-34" y="0" width="68" height="24" rx="6" fill="#18181b" stroke="#10b981" strokeWidth="1.5" />
        <text x="0" y="16" textAnchor="middle" fill="#a7f3d0" fontSize="11" fontFamily="monospace" fontWeight="bold">
          +Y Axis
        </text>
      </g>

      {/* In 3D mode, render 3D +Z normal axis vector and perspective indicator */}
      {is3D && (
        <g id="axis-z-3d">
          <line
            x1="0"
            y1="0"
            x2="0"
            y2="0"
            stroke="#818cf8"
            strokeWidth="3"
            style={{ transform: 'translateZ(250px)' }}
          />
          <circle
            cx="0"
            cy="0"
            r="6"
            fill="#818cf8"
            className="drop-shadow-[0_0_12px_rgba(129,140,248,0.8)]"
            style={{ transform: 'translateZ(250px)' }}
          />
          <text
            x="12"
            y="4"
            fill="#c7d2fe"
            fontSize="11"
            fontFamily="monospace"
            fontWeight="bold"
            style={{ transform: 'translateZ(250px)' }}
          >
            +Z (Normal)
          </text>
        </g>
      )}

      {/* Prominent High-Contrast Origin (0, 0, 0) Bullseye */}
      <g id="origin-point-marker">
        {/* Outer Pulsing Glow Ring */}
        <circle
          cx="0"
          cy="0"
          r="14"
          fill="none"
          stroke="#818cf8"
          strokeWidth="2"
          strokeDasharray="4,2"
          className="animate-[spin_10s_linear_infinite]"
        />
        {/* Inner Solid Target Ring */}
        <circle
          cx="0"
          cy="0"
          r="6"
          fill="#312e81"
          stroke="#c7d2fe"
          strokeWidth="2"
        />
        {/* Center Point */}
        <circle
          cx="0"
          cy="0"
          r="2.5"
          fill="#ffffff"
        />
        {/* Origin Label Tag */}
        <g transform="translate(18, 20)">
          <rect
            x="-4"
            y="-14"
            width="88"
            height="20"
            rx="4"
            fill="#09090b"
            stroke="#818cf8"
            strokeWidth="1.2"
          />
          <text
            x="40"
            y="0"
            textAnchor="middle"
            fill="#e0e7ff"
            fontSize="10"
            fontFamily="monospace"
            fontWeight="bold"
          >
            Origin (0,0,0)
          </text>
        </g>
      </g>
    </g>
  );
};
