import React, { useState } from 'react';
import { Box, RotateCcw, Compass, Eye, ChevronDown } from 'lucide-react';
import { Rotation3D } from '../types';

interface Canvas3DControlsProps {
  rotation: Rotation3D;
  onChangeRotation: (rot: Rotation3D) => void;
  isOrbitMode: boolean;
  onToggleOrbitMode: () => void;
}

export const Canvas3DControls: React.FC<Canvas3DControlsProps> = ({
  rotation,
  onChangeRotation,
  isOrbitMode,
  onToggleOrbitMode
}) => {
  const [showPresetsMenu, setShowPresetsMenu] = useState(false);

  const presets = [
    { label: '2D Orthogonal (0°, 0°)', rot: { x: 0, y: 0, z: 0 } },
    { label: 'Isometric 3D (35°, -45°)', rot: { x: 35, y: -45, z: 0 } },
    { label: 'Oblique Perspective (25°, 25°)', rot: { x: 25, y: 25, z: 0 } },
    { label: 'Deep Tilt (50°, -30°)', rot: { x: 50, y: -30, z: 0 } },
    { label: 'Side Elevation (15°, 75°)', rot: { x: 15, y: 75, z: 0 } }
  ];

  const isFlat2D = rotation.x === 0 && rotation.y === 0 && rotation.z === 0;

  return (
    <div className="relative flex items-center gap-1.5 bg-neutral-900/90 border border-neutral-800 rounded-lg p-1 shadow-lg backdrop-blur-md text-xs">
      {/* 3D Orbit Toggle Button */}
      <button
        id="btn-toggle-3d-orbit"
        type="button"
        onClick={onToggleOrbitMode}
        className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md font-medium transition-all ${
          isOrbitMode
            ? 'bg-cyan-600 text-white shadow-md ring-2 ring-cyan-400/30'
            : !isFlat2D
            ? 'bg-neutral-800 text-cyan-300 border border-cyan-800/40'
            : 'text-neutral-400 hover:text-white hover:bg-neutral-800'
        }`}
        title="Toggle 3D Orbit Mode (or hold Alt / Right-Click to orbit)"
      >
        <Box className={`w-3.5 h-3.5 ${isOrbitMode ? 'animate-pulse text-white' : 'text-cyan-400'}`} />
        <span>3D Orbit</span>
        {!isFlat2D && (
          <span className="text-[10px] font-mono text-cyan-300 ml-0.5">
            {Math.round(rotation.x)}°, {Math.round(rotation.y)}°
          </span>
        )}
      </button>

      {/* Preset Angles Dropdown */}
      <div className="relative">
        <button
          type="button"
          onClick={() => setShowPresetsMenu(!showPresetsMenu)}
          className="p-1.5 rounded-md text-neutral-400 hover:text-white hover:bg-neutral-800 transition-colors flex items-center"
          title="3D Perspective Presets"
        >
          <Compass className="w-3.5 h-3.5" />
          <ChevronDown className="w-2.5 h-2.5 ml-0.5" />
        </button>

        {showPresetsMenu && (
          <div
            className="absolute top-full mt-2 right-0 w-52 bg-neutral-900 border border-neutral-800 rounded-lg shadow-2xl p-1.5 z-40"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="text-[10px] uppercase font-mono text-neutral-400 px-2 py-1 font-semibold border-b border-neutral-800">
              3D Perspective Angles
            </div>
            {presets.map((p, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => {
                  onChangeRotation(p.rot);
                  setShowPresetsMenu(false);
                }}
                className="w-full text-left px-2.5 py-1.5 rounded hover:bg-neutral-800 text-xs text-neutral-200 transition-colors flex items-center justify-between"
              >
                <span>{p.label}</span>
                {rotation.x === p.rot.x && rotation.y === p.rot.y && (
                  <Eye className="w-3 h-3 text-cyan-400" />
                )}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Reset 3D to Flat 2D */}
      {!isFlat2D && (
        <button
          type="button"
          onClick={() => onChangeRotation({ x: 0, y: 0, z: 0 })}
          className="p-1.5 rounded-md text-neutral-400 hover:text-white hover:bg-neutral-800 transition-colors"
          title="Reset to Top-Down 2D"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
};
