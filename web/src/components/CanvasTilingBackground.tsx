import React from 'react';
import { TilingBasis } from '../types';

interface CanvasTilingBackgroundProps {
  basis: TilingBasis;
  zoom: number;
  pan: { x: number; y: number };
  highContrast?: boolean;
}

export const CanvasTilingBackground: React.FC<CanvasTilingBackgroundProps> = ({
  basis,
  zoom,
  pan,
  highContrast = true
}) => {
  const scaledZoom = Math.max(0.2, zoom);

  // Cartesian Square: Defined Major (100px) & Minor (20px) Grid Hierarchy
  if (basis === 'cartesian_square') {
    const majorSize = 100 * scaledZoom;
    const minorSize = majorSize / 5;

    const strokeMajor = highContrast ? 'rgba(129, 140, 248, 0.52)' : 'rgba(99, 102, 241, 0.35)';
    const strokeMinor = highContrast ? 'rgba(99, 102, 241, 0.25)' : 'rgba(99, 102, 241, 0.15)';
    const dotColor = highContrast ? 'rgba(165, 180, 252, 0.85)' : 'rgba(129, 140, 248, 0.6)';

    return (
      <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-85">
        <defs>
          {/* Minor Grid Subdivisions (20px) */}
          <pattern
            id="tiling-square-minor"
            width={minorSize}
            height={minorSize}
            patternUnits="userSpaceOnUse"
          >
            <path
              d={`M ${minorSize} 0 L 0 0 0 ${minorSize}`}
              fill="none"
              stroke={strokeMinor}
              strokeWidth="1"
            />
          </pattern>

          {/* Major Grid Lines (100px) with Crosshair Anchors */}
          <pattern
            id="tiling-square-major"
            width={majorSize}
            height={majorSize}
            patternUnits="userSpaceOnUse"
            patternTransform={`translate(${pan.x}, ${pan.y})`}
          >
            {/* Embed minor grid */}
            <rect width={majorSize} height={majorSize} fill="url(#tiling-square-minor)" />

            {/* Major boundary lines */}
            <path
              d={`M ${majorSize} 0 L 0 0 0 ${majorSize}`}
              fill="none"
              stroke={strokeMajor}
              strokeWidth="1.5"
            />

            {/* Crosshair intersection anchor at (0,0) */}
            <path
              d={`M -4 0 L 4 0 M 0 -4 L 0 4`}
              stroke={dotColor}
              strokeWidth="1.5"
            />
            <circle cx="0" cy="0" r="2" fill={dotColor} />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#tiling-square-major)" />
      </svg>
    );
  }

  // Hexagonal Honeycomb (Graphene / Coordination Basis)
  if (basis === 'hexagonal_honeycomb') {
    const r = 45 * scaledZoom;
    const w = Math.sqrt(3) * r;
    const h = 3 * r;

    // Hexagon vertices
    const hx = (angleDeg: number) => (w / 2) + r * Math.sin((angleDeg * Math.PI) / 180);
    const hy = (angleDeg: number) => r + r * Math.cos((angleDeg * Math.PI) / 180);

    const hexPath = `M ${hx(0)} ${hy(0)} L ${hx(60)} ${hy(60)} L ${hx(120)} ${hy(120)} L ${hx(180)} ${hy(180)} L ${hx(240)} ${hy(240)} L ${hx(300)} ${hy(300)} Z`;

    const strokeHex = highContrast ? 'rgba(16, 185, 129, 0.55)' : 'rgba(16, 185, 129, 0.35)';
    const strokeSub = highContrast ? 'rgba(16, 185, 129, 0.28)' : 'rgba(16, 185, 129, 0.18)';
    const centerColor = highContrast ? 'rgba(52, 211, 153, 0.85)' : 'rgba(52, 211, 153, 0.6)';

    return (
      <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-85">
        <defs>
          <pattern
            id="tiling-hex"
            width={w}
            height={h}
            patternUnits="userSpaceOnUse"
            patternTransform={`translate(${pan.x}, ${pan.y})`}
          >
            {/* Defined Hexagon Perimeter */}
            <path
              d={hexPath}
              fill="none"
              stroke={strokeHex}
              strokeWidth="1.5"
            />
            {/* Defined Honeycomb Bisectors */}
            <path
              d={`M ${w/2} 0 L ${w/2} ${r/2} M 0 ${r*1.5} L ${w/2} ${r*1.5} M ${w} ${r*1.5} L ${w/2} ${r*1.5}`}
              fill="none"
              stroke={strokeSub}
              strokeWidth="1.2"
              strokeDasharray="4,2"
            />
            {/* Defined Vertex & Center Points */}
            <circle cx={w/2} cy={r} r="2.2" fill={centerColor} />
            <circle cx={hx(0)} cy={hy(0)} r="1.8" fill={centerColor} />
            <circle cx={hx(120)} cy={hy(120)} r="1.8" fill={centerColor} />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#tiling-hex)" />
      </svg>
    );
  }

  // Eisenstein Omega (Trigonal Triangular Basis)
  if (basis === 'eisenstein_omega') {
    const s = 70 * scaledZoom;
    const h = (s * Math.sqrt(3)) / 2;

    const strokeEisen = highContrast ? 'rgba(6, 182, 212, 0.55)' : 'rgba(6, 182, 212, 0.35)';
    const strokeMed = highContrast ? 'rgba(6, 182, 212, 0.30)' : 'rgba(6, 182, 212, 0.18)';
    const vertexColor = highContrast ? 'rgba(34, 211, 238, 0.85)' : 'rgba(34, 211, 238, 0.6)';

    return (
      <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-85">
        <defs>
          <pattern
            id="tiling-eisenstein"
            width={s}
            height={h * 2}
            patternUnits="userSpaceOnUse"
            patternTransform={`translate(${pan.x}, ${pan.y})`}
          >
            {/* Defined Triangular & snowflake sub-division grid */}
            <path
              d={`M 0 0 L ${s} 0 L ${s/2} ${h} Z M ${s/2} ${h} L 0 ${2*h} L ${s} ${2*h} Z`}
              fill="none"
              stroke={strokeEisen}
              strokeWidth="1.5"
            />
            {/* Defined Fractal median lines */}
            <path
              d={`M ${s/4} ${h/2} L ${3*s/4} ${h/2} M ${s/2} 0 L ${s/2} ${h}`}
              fill="none"
              stroke={strokeMed}
              strokeWidth="1.2"
              strokeDasharray="4,3"
            />
            <circle cx={s/2} cy={h} r="2.5" fill={vertexColor} />
            <circle cx="0" cy="0" r="2" fill={vertexColor} />
            <circle cx={s} cy="0" r="2" fill={vertexColor} />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#tiling-eisenstein)" />
      </svg>
    );
  }

  // Gaussian Dragon (1+i Fractal Basis)
  const ds = 75 * scaledZoom;
  const strokeDragon = highContrast ? 'rgba(192, 132, 252, 0.55)' : 'rgba(168, 85, 247, 0.35)';
  const strokeFold = highContrast ? 'rgba(192, 132, 252, 0.32)' : 'rgba(168, 85, 247, 0.18)';
  const nodeColor = highContrast ? 'rgba(216, 180, 254, 0.85)' : 'rgba(192, 132, 252, 0.6)';

  return (
    <svg className="absolute inset-0 w-full h-full pointer-events-none opacity-85">
      <defs>
        <pattern
          id="tiling-dragon"
          width={ds}
          height={ds}
          patternUnits="userSpaceOnUse"
          patternTransform={`translate(${pan.x}, ${pan.y}) rotate(45)`}
        >
          <rect
            x="0"
            y="0"
            width={ds}
            height={ds}
            fill="none"
            stroke={strokeDragon}
            strokeWidth="1.5"
          />
          {/* Defined Dragon recursion diagonal folds */}
          <path
            d={`M 0 0 L ${ds} ${ds} M ${ds} 0 L ${ds/2} ${ds/2} M 0 ${ds} L ${ds/2} ${ds/2}`}
            fill="none"
            stroke={strokeFold}
            strokeWidth="1.2"
            strokeDasharray="4,2"
          />
          <circle cx={ds/2} cy={ds/2} r="2.5" fill={nodeColor} />
          <circle cx="0" cy="0" r="2" fill={nodeColor} />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill="url(#tiling-dragon)" />
    </svg>
  );
};
