import React from 'react';
import { Trash2, AlertTriangle, X, RefreshCw, Dna } from 'lucide-react';
import { PRESET_GEOMETRIC_EXPERIMENTS } from '../data/geometryPresets';
import { CaceExperiment } from '../types';

interface ClearCanvasModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirmClear: () => void;
  onLoadTemplate: (exp: CaceExperiment) => void;
}

export const ClearCanvasModal: React.FC<ClearCanvasModalProps> = ({
  isOpen,
  onClose,
  onConfirmClear,
  onLoadTemplate
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div
        id="modal-clear-canvas"
        className="w-full max-w-md bg-neutral-900 border border-neutral-800 rounded-xl shadow-2xl p-5 flex flex-col gap-4 text-neutral-200"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between pb-3 border-b border-neutral-800">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-rose-950/80 border border-rose-800/80 text-rose-400">
              <Trash2 className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white">Clear Canvas</h3>
              <p className="text-[11px] text-neutral-400">Remove all current modules, geometric objects, and edges</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded text-neutral-400 hover:text-white hover:bg-neutral-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="p-3 bg-neutral-950/60 rounded-lg border border-neutral-800/80 flex items-start gap-2.5 text-xs text-neutral-300">
          <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
          <p>
            This action will clear all nodes, geometric objects, and connection edges from the active workspace.
          </p>
        </div>

        {/* Quick starter alternatives */}
        <div className="flex flex-col gap-1.5 text-xs">
          <span className="text-[10px] font-mono uppercase text-neutral-400 font-semibold">
            Or replace with starter architecture:
          </span>
          <button
            type="button"
            onClick={() => {
              onLoadTemplate(PRESET_GEOMETRIC_EXPERIMENTS.protein_fold_domain);
              onClose();
            }}
            className="p-2 rounded-lg bg-neutral-950 border border-neutral-800 hover:border-emerald-700/80 hover:bg-emerald-950/30 text-left transition-colors flex items-center justify-between"
          >
            <div className="flex items-center gap-2">
              <Dna className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-xs font-medium text-white">Protein Fold α/β Domain</span>
            </div>
            <span className="text-[10px] font-mono text-neutral-400">5 nodes, 5 bonds</span>
          </button>
        </div>

        <div className="flex items-center justify-end gap-2 pt-2 border-t border-neutral-800">
          <button
            type="button"
            onClick={onClose}
            className="px-3 py-1.5 rounded-lg border border-neutral-700 text-xs text-neutral-400 hover:text-white hover:bg-neutral-800 transition-colors"
          >
            Cancel
          </button>
          <button
            id="btn-confirm-clear-canvas"
            type="button"
            onClick={() => {
              onConfirmClear();
              onClose();
            }}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-xs font-semibold text-white shadow-md transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Clear Canvas Now</span>
          </button>
        </div>
      </div>
    </div>
  );
};
