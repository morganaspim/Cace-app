import React, { useState } from 'react';
import { Grid, Sparkles, ChevronDown, Network } from 'lucide-react';
import { TilingBasis } from '../types';
import { LATTICE_CONFIGS } from '../engine/geometricLattice';

interface TilingSelectorProps {
  currentBasis: TilingBasis;
  onChangeBasis: (basis: TilingBasis) => void;
  onRelaxGraph: () => void;
}

export const TilingSelector: React.FC<TilingSelectorProps> = ({
  currentBasis,
  onChangeBasis,
  onRelaxGraph
}) => {
  const [showDropdown, setShowDropdown] = useState(false);
  const currentConfig = LATTICE_CONFIGS[currentBasis];

  return (
    <div className="flex items-center gap-1.5 bg-neutral-900/90 border border-neutral-800 rounded-lg p-1 shadow-lg backdrop-blur-md text-xs">
      {/* Tiling Basis Picker */}
      <div className="relative">
        <button
          id="btn-tiling-basis-menu"
          type="button"
          onClick={() => setShowDropdown(!showDropdown)}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-neutral-300 hover:text-white hover:bg-neutral-800 transition-colors"
          title={`Active Tiling: ${currentConfig.name} - ${currentConfig.description}`}
        >
          <Grid className="w-3.5 h-3.5 text-indigo-400" />
          <span className="font-medium text-white">{currentConfig.symbol} {currentConfig.name.split(' ')[0]}</span>
          <ChevronDown className="w-2.5 h-2.5 text-neutral-500" />
        </button>

        {showDropdown && (
          <div
            className="absolute top-full mt-2 left-0 w-72 bg-neutral-900 border border-neutral-800 rounded-lg shadow-2xl p-2 z-40 space-y-1"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="text-[10px] uppercase font-mono text-neutral-400 font-semibold px-2 py-1 border-b border-neutral-800">
              Coordinateless Tiling Projections
            </div>

            {(Object.keys(LATTICE_CONFIGS) as TilingBasis[]).map((key) => {
              const cfg = LATTICE_CONFIGS[key];
              const isSelected = key === currentBasis;
              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => {
                    onChangeBasis(key);
                    setShowDropdown(false);
                  }}
                  className={`w-full text-left p-2 rounded-lg transition-colors flex flex-col gap-0.5 ${
                    isSelected
                      ? 'bg-indigo-950/80 border border-indigo-700/80 text-white'
                      : 'hover:bg-neutral-800/80 text-neutral-300'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold flex items-center gap-1.5">
                      <span className="text-sm">{cfg.symbol}</span>
                      {cfg.name}
                    </span>
                    <span className="text-[9px] font-mono text-indigo-400 bg-neutral-950 px-1.5 py-0.5 rounded border border-neutral-800">
                      {cfg.basisFormula}
                    </span>
                  </div>
                  <p className="text-[10px] text-neutral-400 leading-snug">
                    {cfg.description}
                  </p>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Auto-Map Relational Graph Button */}
      <button
        id="btn-auto-map-lattice"
        type="button"
        onClick={onRelaxGraph}
        className="flex items-center gap-1 px-2.5 py-1.5 rounded-md bg-indigo-950/70 hover:bg-indigo-900/80 border border-indigo-800/70 text-indigo-300 text-xs font-medium transition-colors"
        title="Coordinateless layout: Map interacting modules and geometries dynamically by graph topology and snap to the active tiling"
      >
        <Network className="w-3.5 h-3.5 text-indigo-400" />
        <span className="hidden sm:inline">Auto-Map to Lattice</span>
        <Sparkles className="w-3 h-3 text-indigo-400" />
      </button>
    </div>
  );
};
