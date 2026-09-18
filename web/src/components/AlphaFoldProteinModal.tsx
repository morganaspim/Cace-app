import React, { useState } from 'react';
import { AlphaFoldProteinData } from '../types';
import { X, Dna, ExternalLink, Download, Layers, Compass, CheckCircle2, ShieldCheck, Activity } from 'lucide-react';

interface AlphaFoldProteinModalProps {
  data: AlphaFoldProteinData;
  onClose: () => void;
}

export const AlphaFoldProteinModal: React.FC<AlphaFoldProteinModalProps> = ({
  data,
  onClose
}) => {
  const [activeTab, setActiveTab] = useState<'3d_backbone' | 'differential' | 'topology' | 'license'>('3d_backbone');
  const [rotX, setRotX] = useState(25);
  const [rotY, setRotY] = useState(45);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // Handle 3D rotation dragging for mini viewer
  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX, y: e.clientY });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    const dx = e.clientX - dragStart.x;
    const dy = e.clientY - dragStart.y;
    setRotY((prev) => (prev + dx * 0.8) % 360);
    setRotX((prev) => Math.max(-80, Math.min(80, prev - dy * 0.8)));
    setDragStart({ x: e.clientX, y: e.clientY });
  };

  const handleMouseUp = () => setIsDragging(false);

  // Compute 2D isometric projected points for SVG 3D viewer
  const radX = (rotX * Math.PI) / 180;
  const radY = (rotY * Math.PI) / 180;

  // Center the coordinates
  const meanX = data.ca_coords.reduce((acc, c) => acc + c[0], 0) / (data.ca_coords.length || 1);
  const meanY = data.ca_coords.reduce((acc, c) => acc + c[1], 0) / (data.ca_coords.length || 1);
  const meanZ = data.ca_coords.reduce((acc, c) => acc + c[2], 0) / (data.ca_coords.length || 1);

  const projectedPoints = data.ca_coords.map(([x, y, z], idx) => {
    const cx = x - meanX;
    const cy = y - meanY;
    const cz = z - meanZ;

    // Rotate Y
    const x1 = cx * Math.cos(radY) + cz * Math.sin(radY);
    const z1 = -cx * Math.sin(radY) + cz * Math.cos(radY);

    // Rotate X
    const y2 = cy * Math.cos(radX) - z1 * Math.sin(radX);
    const z2 = cy * Math.sin(radX) + z1 * Math.cos(radX);

    // Scale and shift to canvas center (200, 150)
    const scale = 5.5;
    const px = 200 + x1 * scale;
    const py = 150 + y2 * scale;

    return { px, py, pz: z2, idx, residue: idx + 1 };
  });

  const exportPdb = () => {
    let pdb = `HEADER    ALPHAFOLD DB MODEL ${data.alphafold_id}\n`;
    pdb += `TITLE     ${data.name.toUpperCase()}\n`;
    pdb += `SOURCE    ${data.organism}\n`;
    pdb += `REMARK    CACE COMPUTATIONAL TOPOLOGY OBJECT\n`;
    pdb += `REMARK    WRITHE=${data.writhe} TWIST=${data.twist} LINK=${data.link_number}\n`;

    data.ca_coords.forEach(([x, y, z], i) => {
      const num = (i + 1).toString().padStart(5, ' ');
      const resNum = (i + 1).toString().padStart(4, ' ');
      const xs = x.toFixed(3).padStart(8, ' ');
      const ys = y.toFixed(3).padStart(8, ' ');
      const zs = z.toFixed(3).padStart(8, ' ');
      pdb += `ATOM  ${num}  CA  GLY A${resNum}    ${xs}${ys}${zs}  1.00 ${data.mean_plddt.toFixed(2)}           C\n`;
    });
    pdb += `END\n`;

    const blob = new Blob([pdb], { type: 'chemical/x-pdb' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${data.alphafold_id}_cace_math.pdb`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-md p-4">
      <div
        id="modal-alphafold-inspector"
        className="w-full max-w-4xl bg-neutral-900 border border-neutral-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh] text-neutral-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b border-neutral-800 bg-neutral-950/80 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-cyan-950/80 border border-cyan-700/80 text-cyan-400">
              <Dna className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-white tracking-wide">{data.name}</h2>
                <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-300 border border-cyan-800 font-mono font-semibold">
                  {data.alphafold_id}
                </span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-800 font-mono">
                  pLDDT: {data.mean_plddt}%
                </span>
              </div>
              <p className="text-xs text-neutral-400 font-mono mt-0.5">
                {data.organism} • {data.residue_count} Residues • Discrete 3D Space Curve
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={exportPdb}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-neutral-800 hover:bg-neutral-700 text-neutral-200 text-xs font-medium border border-neutral-700 transition-colors"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export PDB</span>
            </button>
            <a
              href={`https://alphafold.ebi.ac.uk/entry/${data.uniprot_id}`}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-900/60 hover:bg-cyan-800/80 text-cyan-200 text-xs font-medium border border-cyan-700/70 transition-colors"
            >
              <span>AlphaFold DB</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </a>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg text-neutral-400 hover:text-white hover:bg-neutral-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-2 px-6 pt-3 border-b border-neutral-800 bg-neutral-900">
          <button
            type="button"
            onClick={() => setActiveTab('3d_backbone')}
            className={`px-3 py-2 text-xs font-semibold border-b-2 transition-colors flex items-center gap-1.5 ${
              activeTab === '3d_backbone'
                ? 'border-cyan-500 text-cyan-300'
                : 'border-transparent text-neutral-400 hover:text-neutral-200'
            }`}
          >
            <Compass className="w-3.5 h-3.5" />
            <span>3D Differential Curve (Cα Trajectory)</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('topology')}
            className={`px-3 py-2 text-xs font-semibold border-b-2 transition-colors flex items-center gap-1.5 ${
              activeTab === 'topology'
                ? 'border-cyan-500 text-cyan-300'
                : 'border-transparent text-neutral-400 hover:text-neutral-200'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Topological Invariants (Lk = Tw + Wr)</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('differential')}
            className={`px-3 py-2 text-xs font-semibold border-b-2 transition-colors flex items-center gap-1.5 ${
              activeTab === 'differential'
                ? 'border-cyan-500 text-cyan-300'
                : 'border-transparent text-neutral-400 hover:text-neutral-200'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Frenet-Serret Curvature & Torsion</span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('license')}
            className={`px-3 py-2 text-xs font-semibold border-b-2 transition-colors flex items-center gap-1.5 ${
              activeTab === 'license'
                ? 'border-cyan-500 text-cyan-300'
                : 'border-transparent text-neutral-400 hover:text-neutral-200'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Open Licensing (CC-BY 4.0)</span>
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto flex-1">
          {activeTab === '3d_backbone' && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Interactive 3D Orbit View */}
              <div className="md:col-span-2 bg-neutral-950 border border-neutral-800 rounded-xl p-4 flex flex-col">
                <div className="flex items-center justify-between mb-2">
                  <div className="text-xs font-semibold text-neutral-300 flex items-center gap-1.5">
                    <Compass className="w-4 h-4 text-cyan-400" />
                    <span>Interactive 3D Cα Polyline (Drag to Orbit)</span>
                  </div>
                  <span className="text-[10px] font-mono text-neutral-500">
                    Rot: {Math.round(rotX)}°, {Math.round(rotY)}°
                  </span>
                </div>

                <div
                  className="relative w-full h-80 bg-neutral-900/50 rounded-lg overflow-hidden cursor-grab active:cursor-grabbing select-none flex items-center justify-center border border-neutral-800/80"
                  onMouseDown={handleMouseDown}
                  onMouseMove={handleMouseMove}
                  onMouseUp={handleMouseUp}
                  onMouseLeave={handleMouseUp}
                >
                  <svg className="w-full h-full pointer-events-none">
                    <defs>
                      <linearGradient id="backbone-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#38bdf8" />
                        <stop offset="50%" stopColor="#10b981" />
                        <stop offset="100%" stopColor="#f59e0b" />
                      </linearGradient>
                    </defs>

                    {/* Backbone Line Connecting C-alpha atoms */}
                    {projectedPoints.map((pt, i) => {
                      if (i === 0) return null;
                      const prev = projectedPoints[i - 1];
                      return (
                        <line
                          key={`seg-${i}`}
                          x1={prev.px}
                          y1={prev.py}
                          x2={pt.px}
                          y2={pt.py}
                          stroke="url(#backbone-gradient)"
                          strokeWidth="2.5"
                          strokeLinecap="round"
                        />
                      );
                    })}

                    {/* C-alpha atom beads */}
                    {projectedPoints.map((pt) => (
                      <circle
                        key={`ca-${pt.idx}`}
                        cx={pt.px}
                        cy={pt.py}
                        r={pt.idx === 0 || pt.idx === projectedPoints.length - 1 ? 5 : 3}
                        fill={
                          pt.idx === 0
                            ? '#38bdf8' // N-term
                            : pt.idx === projectedPoints.length - 1
                            ? '#f43f5e' // C-term
                            : '#ffffff'
                        }
                        stroke="#0f172a"
                        strokeWidth="1.5"
                      />
                    ))}
                  </svg>

                  {/* View Overlay Indicators */}
                  <div className="absolute bottom-2 left-2 flex items-center gap-2 text-[10px] font-mono text-neutral-400 bg-neutral-900/80 px-2 py-1 rounded border border-neutral-800">
                    <span className="flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-sky-400" /> N-Term
                    </span>
                    <span className="flex items-center gap-1">
                      <span className="w-2 h-2 rounded-full bg-rose-500" /> C-Term
                    </span>
                  </div>
                </div>
              </div>

              {/* Mathematical Summary Card */}
              <div className="space-y-4">
                <div className="bg-neutral-950 border border-neutral-800 rounded-xl p-4">
                  <h4 className="text-xs font-bold text-neutral-200 uppercase font-mono tracking-wider mb-3">
                    Differential Metrics
                  </h4>
                  <div className="space-y-2.5 text-xs">
                    <div className="flex justify-between py-1 border-b border-neutral-800">
                      <span className="text-neutral-400">Backbone Length:</span>
                      <span className="font-mono text-white font-bold">{data.residue_count} Cα nodes</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-neutral-800">
                      <span className="text-neutral-400">Mean Curvature κ:</span>
                      <span className="font-mono text-cyan-300 font-bold">{data.mean_curvature}° / res</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-neutral-800">
                      <span className="text-neutral-400">Mean Torsion τ:</span>
                      <span className="font-mono text-amber-300 font-bold">{data.mean_torsion}° / res</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-neutral-800">
                      <span className="text-neutral-400">Total Writhe (Wr):</span>
                      <span className="font-mono text-emerald-300 font-bold">{data.writhe}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-neutral-800">
                      <span className="text-neutral-400">Total Twist (Tw):</span>
                      <span className="font-mono text-indigo-300 font-bold">{data.twist}</span>
                    </div>
                    <div className="flex justify-between py-1">
                      <span className="text-neutral-400">Link Invariant (Lk):</span>
                      <span className="font-mono text-white font-bold">{data.link_number}</span>
                    </div>
                  </div>
                </div>

                <div className="bg-cyan-950/30 border border-cyan-800/60 rounded-xl p-3.5 text-xs text-neutral-300">
                  <div className="font-bold text-cyan-300 mb-1 flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-cyan-400" />
                    <span>Rigorous Geometric Contract</span>
                  </div>
                  <p className="text-[11px] leading-relaxed text-neutral-400">
                    Extracted from AlphaFold DB. Treated strictly as a discrete differential curve in ℝ³ with explicit Frenet framing, avoiding black-box assertions.
                  </p>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'topology' && (
            <div className="space-y-4">
              <div className="bg-neutral-950 border border-neutral-800 rounded-xl p-5">
                <h3 className="text-sm font-bold text-white mb-2">Călugăreanu-White-Fuller Theorem</h3>
                <p className="text-xs text-neutral-300 leading-relaxed font-mono bg-neutral-900 p-3 rounded-lg border border-neutral-800">
                  Lk = Tw + Wr &nbsp;&nbsp;⟹&nbsp;&nbsp; {data.link_number} = {data.twist} + ({data.writhe})
                </p>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4 text-xs">
                  <div className="p-3 rounded-lg bg-neutral-900 border border-neutral-800">
                    <div className="text-neutral-400">Twist (Tw)</div>
                    <div className="text-lg font-bold font-mono text-cyan-300 mt-1">{data.twist}</div>
                    <div className="text-[10px] text-neutral-500 mt-1">Integral of discrete rotation rate about backbone tangent</div>
                  </div>
                  <div className="p-3 rounded-lg bg-neutral-900 border border-neutral-800">
                    <div className="text-neutral-400">Writhe (Wr)</div>
                    <div className="text-lg font-bold font-mono text-emerald-300 mt-1">{data.writhe}</div>
                    <div className="text-[10px] text-neutral-500 mt-1">Gauss linking double-integral over the 3D space curve</div>
                  </div>
                  <div className="p-3 rounded-lg bg-neutral-900 border border-neutral-800">
                    <div className="text-neutral-400">Algebraic Connectivity (λ₂)</div>
                    <div className="text-lg font-bold font-mono text-purple-300 mt-1">{data.laplacian_spectral_gap}</div>
                    <div className="text-[10px] text-neutral-500 mt-1">Fiedler eigenvalue of the 8.0Å contact graph Laplacian</div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'differential' && (
            <div className="space-y-4">
              <div className="bg-neutral-950 border border-neutral-800 rounded-xl p-5">
                <h3 className="text-sm font-bold text-white mb-2">Discrete Frenet-Serret Equations</h3>
                <p className="text-xs text-neutral-300 leading-relaxed mb-4">
                  For each residue node $i$, the discrete curve has tangent $T_i = (r_{'{i+1}'} - r_i)/||r_{'{i+1}'} - r_i||$, curvature $\kappa_i = \arccos(T_i \cdot T_{'{i+1}'})$, and binormal $B_i = T_i \times T_{'{i+1}'}$.
                </p>
                <div className="bg-neutral-900 p-4 rounded-lg border border-neutral-800 font-mono text-xs text-neutral-300 space-y-2">
                  <div>dT/ds = κ N</div>
                  <div>dN/ds = -κ T + τ B</div>
                  <div>dB/ds = -τ N</div>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'license' && (
            <div className="space-y-4">
              <div className="bg-neutral-950 border border-neutral-800 rounded-xl p-5">
                <div className="flex items-center gap-2 mb-3">
                  <ShieldCheck className="w-5 h-5 text-emerald-400" />
                  <h3 className="text-sm font-bold text-white">AlphaFold Database Licensing & IP Terms</h3>
                </div>
                <div className="text-xs text-neutral-300 leading-relaxed space-y-3">
                  <p>
                    <strong>Open Access License:</strong> All structural predictions in the AlphaFold Protein Structure Database are provided under the <strong>Creative Commons Attribution 4.0 International (CC-BY 4.0)</strong> license.
                  </p>
                  <p>
                    <strong>Permitted Uses:</strong> You are free to share, copy, redistribute, and adapt the data for any purpose, including commercial applications, academic research, and computational mathematics, provided proper attribution is maintained.
                  </p>
                  <div className="p-3 bg-neutral-900 rounded-lg border border-neutral-800 font-mono text-[11px] text-neutral-400">
                    Source: AlphaFold Protein Structure Database (EMBL-EBI / DeepMind).<br />
                    Citation: Jumper, J. et al. Highly accurate protein structure prediction with AlphaFold. Nature 596, 583–589 (2021).<br />
                    License: CC-BY 4.0 International.
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-neutral-800 bg-neutral-950/80 flex items-center justify-between text-xs text-neutral-400">
          <span className="font-mono">CACE Studio Scientific Geometry Engine</span>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-neutral-800 hover:bg-neutral-700 text-white font-medium transition-colors"
          >
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  );
};
