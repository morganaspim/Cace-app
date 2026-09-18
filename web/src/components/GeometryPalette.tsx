import React, { useState } from 'react';
import { Shapes, Dna, Atom, Plus, Sparkles, X, ChevronRight } from 'lucide-react';
import { GEOMETRIC_CATALOG, PRESET_GEOMETRIC_EXPERIMENTS } from '../data/geometryPresets';
import { CaceExperiment, GraphNode } from '../types';

interface GeometryPaletteProps {
  onAddGeometricNode: (key: string) => void;
  onLoadPreset: (exp: CaceExperiment) => void;
  isClickToConnectActive: boolean;
  onToggleClickToConnect: () => void;
  connectingSourceNode: GraphNode | null;
  onCancelConnection: () => void;
}

export const GeometryPalette: React.FC<GeometryPaletteProps> = ({
  onAddGeometricNode,
  onLoadPreset,
  isClickToConnectActive,
  onToggleClickToConnect,
  connectingSourceNode,
  onCancelConnection
}) => {
  const [showCatalogModal, setShowCatalogModal] = useState(false);
  const [activeCategory, setActiveCategory] = useState<'alphafold_protein' | 'atom' | 'molecule' | 'protein_fold' | 'simplex'>('alphafold_protein');

  const categories = [
    { key: 'alphafold_protein', label: 'AlphaFold DB (Proteins)', icon: Dna },
    { key: 'atom', label: 'Atoms & Elements', icon: Atom },
    { key: 'molecule', label: 'Molecules', icon: Shapes },
    { key: 'protein_fold', label: 'Protein Folds (α/β)', icon: Dna },
    { key: 'simplex', label: 'Simplices & Manifolds', icon: Shapes }
  ] as const;

  const catalogItems = Object.entries(GEOMETRIC_CATALOG).filter(
    ([_, meta]) => meta.kind === activeCategory
  );

  return (
    <>
      <div className="flex items-center gap-1.5 bg-neutral-900/90 border border-neutral-800 rounded-lg p-1 shadow-lg backdrop-blur-md text-xs">
        {/* Add Geometry Button */}
        <button
          id="btn-open-geometry-palette"
          type="button"
          onClick={() => setShowCatalogModal(true)}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-emerald-950/80 hover:bg-emerald-900 border border-emerald-700/70 text-emerald-300 font-semibold shadow-xs transition-colors"
          title="Add Atoms, Molecules, Protein Folds, or Simplicial Geometries"
        >
          <Dna className="w-3.5 h-3.5 text-emerald-400" />
          <span>Add Geometry</span>
          <Plus className="w-3 h-3 text-emerald-400" />
        </button>

        {/* Click to Connect Mode Toggle */}
        <button
          id="btn-toggle-click-to-connect"
          type="button"
          onClick={onToggleClickToConnect}
          className={`flex items-center gap-1 px-2.5 py-1.5 rounded-md font-medium text-xs transition-all ${
            isClickToConnectActive || connectingSourceNode
              ? 'bg-amber-600 text-white shadow-md ring-2 ring-amber-400/30'
              : 'text-neutral-400 hover:text-white hover:bg-neutral-800'
          }`}
          title="Click to Connect: Click any mathematical object or port to bond / link it directly"
        >
          <Sparkles className={`w-3.5 h-3.5 ${isClickToConnectActive ? 'animate-spin text-white' : 'text-amber-400'}`} />
          <span>{connectingSourceNode ? `Click Target to Bond...` : `Click-to-Connect`}</span>
        </button>

        {connectingSourceNode && (
          <button
            type="button"
            onClick={onCancelConnection}
            className="p-1 rounded text-neutral-400 hover:text-rose-400 hover:bg-neutral-800 transition-colors"
            title="Cancel pending geometric connection"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </div>

      {/* Geometry Palette Modal */}
      {showCatalogModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div
            id="modal-geometry-catalog"
            className="w-full max-w-2xl bg-neutral-900 border border-neutral-800 rounded-xl shadow-2xl p-5 flex flex-col gap-4 text-neutral-200"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-center justify-between pb-3 border-b border-neutral-800">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-lg bg-emerald-950/80 border border-emerald-700/80 text-emerald-400">
                  <Dna className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">Mathematical & Molecular Geometries</h3>
                  <p className="text-[11px] text-neutral-400">
                    Click to add atoms, molecules, protein fold motifs, or simplicial manifolds to the canvas
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowCatalogModal(false)}
                className="p-1.5 rounded text-neutral-400 hover:text-white hover:bg-neutral-800 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Category tabs */}
            <div className="flex items-center gap-1 border-b border-neutral-800 pb-2">
              {categories.map((cat) => {
                const Icon = cat.icon;
                const isSelected = activeCategory === cat.key;
                return (
                  <button
                    key={cat.key}
                    type="button"
                    onClick={() => setActiveCategory(cat.key)}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                      isSelected
                        ? 'bg-emerald-600 text-white shadow-xs'
                        : 'text-neutral-400 hover:text-white hover:bg-neutral-800'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5" />
                    <span>{cat.label}</span>
                  </button>
                );
              })}
            </div>

            {/* Catalog Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 max-h-72 overflow-y-auto pr-1">
              {catalogItems.map(([key, meta]) => (
                <button
                  key={key}
                  type="button"
                  onClick={() => {
                    onAddGeometricNode(key);
                    setShowCatalogModal(false);
                  }}
                  className="p-3 bg-neutral-950/80 border border-neutral-800/80 rounded-xl hover:border-emerald-600/80 hover:bg-emerald-950/20 transition-all text-left flex items-start gap-3 group"
                >
                  <div
                    className="w-10 h-10 rounded-full flex items-center justify-center font-bold font-mono text-sm shadow-inner flex-shrink-0"
                    style={{
                      backgroundColor: `${meta.color}22`,
                      borderColor: meta.color,
                      borderWidth: 2,
                      color: meta.color
                    }}
                  >
                    {meta.subType.slice(0, 3)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-white group-hover:text-emerald-300 transition-colors truncate">
                        {meta.subType}
                      </span>
                      <span className="text-[10px] font-mono text-neutral-400">
                        {meta.sites.length} sites
                      </span>
                    </div>
                    <p className="text-[10px] text-neutral-400 leading-snug line-clamp-2 mt-0.5">
                      {meta.description}
                    </p>
                  </div>
                  <ChevronRight className="w-4 h-4 text-neutral-600 group-hover:text-emerald-400 self-center transition-colors flex-shrink-0" />
                </button>
              ))}
            </div>

            {/* Preset Architecture Templates */}
            <div className="pt-3 border-t border-neutral-800 flex flex-col gap-2">
              <span className="text-[10px] font-mono uppercase text-neutral-400 font-semibold">
                Or Load Pre-Constructed Geometric Architecture:
              </span>
              <div className="flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  onClick={() => {
                    onLoadPreset(PRESET_GEOMETRIC_EXPERIMENTS.alphafold_differential_topography);
                    setShowCatalogModal(false);
                  }}
                  className="px-3 py-1.5 rounded-lg bg-cyan-950/80 hover:bg-cyan-900 hover:border-cyan-600 border border-cyan-700/80 text-xs text-cyan-200 transition-colors flex items-center gap-1.5 font-semibold"
                >
                  <Dna className="w-3.5 h-3.5 text-cyan-400" />
                  <span>AlphaFold Space Curves & Topology</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    onLoadPreset(PRESET_GEOMETRIC_EXPERIMENTS.protein_fold_domain);
                    setShowCatalogModal(false);
                  }}
                  className="px-3 py-1.5 rounded-lg bg-neutral-800 hover:bg-emerald-950 hover:border-emerald-700 border border-neutral-700 text-xs text-neutral-200 transition-colors flex items-center gap-1.5"
                >
                  <Dna className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Protein α/β Hairpin Domain</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    onLoadPreset(PRESET_GEOMETRIC_EXPERIMENTS.benzene_aromatic_ring);
                    setShowCatalogModal(false);
                  }}
                  className="px-3 py-1.5 rounded-lg bg-neutral-800 hover:bg-violet-950 hover:border-violet-700 border border-neutral-700 text-xs text-neutral-200 transition-colors flex items-center gap-1.5"
                >
                  <Shapes className="w-3.5 h-3.5 text-violet-400" />
                  <span>Benzene Ring (C₆H₆)</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    onLoadPreset(PRESET_GEOMETRIC_EXPERIMENTS.water_hydrogen_lattice);
                    setShowCatalogModal(false);
                  }}
                  className="px-3 py-1.5 rounded-lg bg-neutral-800 hover:bg-cyan-950 hover:border-cyan-700 border border-neutral-700 text-xs text-neutral-200 transition-colors flex items-center gap-1.5"
                >
                  <Atom className="w-3.5 h-3.5 text-cyan-400" />
                  <span>Water (H₂O)₄ Cluster</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
