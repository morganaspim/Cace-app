import React from 'react';
import { GraphNode, NodeExecutionResult, CaceExperiment, ModuleDefinition } from '../types';
import { CACE_MODULES } from '../data/caceData';
import { X, CheckCircle2, AlertTriangle, ShieldCheck, Activity, Sliders, ArrowRight, ArrowLeft } from 'lucide-react';

interface NodePropertiesPanelProps {
  selectedNodeId: string | null;
  experiment: CaceExperiment;
  onUpdateExperiment: (exp: CaceExperiment) => void;
  nodeResult?: NodeExecutionResult;
  onClose: () => void;
}

export const NodePropertiesPanel: React.FC<NodePropertiesPanelProps> = ({
  selectedNodeId,
  experiment,
  onUpdateExperiment,
  nodeResult,
  onClose
}) => {
  if (!selectedNodeId) return null;

  const node = experiment.nodes.find((n) => n.id === selectedNodeId);
  if (!node) return null;

  const mod = CACE_MODULES.find((m) => m.module_id === node.module_id);

  const handleParamChange = (paramName: string, value: any) => {
    const updatedNodes = experiment.nodes.map((n) =>
      n.id === selectedNodeId
        ? {
            ...n,
            params: {
              ...n.params,
              [paramName]: value
            }
          }
        : n
    );
    onUpdateExperiment({ ...experiment, nodes: updatedNodes });
  };

  const handleLabelChange = (newLabel: string) => {
    const updatedNodes = experiment.nodes.map((n) =>
      n.id === selectedNodeId ? { ...n, label: newLabel } : n
    );
    onUpdateExperiment({ ...experiment, nodes: updatedNodes });
  };

  // Incoming and outgoing edges for this node
  const incomingEdges = experiment.edges.filter((e) => e.target_node === selectedNodeId);
  const outgoingEdges = experiment.edges.filter((e) => e.source_node === selectedNodeId);

  return (
    <aside 
      id="node-properties-panel"
      className="w-80 border-l border-neutral-800 bg-neutral-900/95 backdrop-blur-md h-[calc(100vh-4rem)] overflow-y-auto flex flex-col z-10"
    >
      {/* Panel Header */}
      <div className="p-4 border-b border-neutral-800 flex items-center justify-between sticky top-0 bg-neutral-900 z-10">
        <div className="flex items-center gap-2">
          <Sliders className="w-4 h-4 text-indigo-400" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-neutral-200">Node Properties</h2>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded hover:bg-neutral-800 text-neutral-400 hover:text-white transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="p-4 space-y-5 text-xs flex-1">
        {/* Node Identity */}
        <div>
          <label className="text-[10px] font-mono uppercase text-neutral-400 font-semibold block mb-1">
            Display Label
          </label>
          <input
            type="text"
            value={node.label || ''}
            onChange={(e) => handleLabelChange(e.target.value)}
            placeholder={mod?.name || node.id}
            className="w-full bg-neutral-950 border border-neutral-800 rounded px-2.5 py-1.5 text-neutral-100 font-medium focus:outline-none focus:border-indigo-500"
          />
          <div className="flex items-center justify-between mt-1 text-[10px] font-mono text-neutral-500">
            <span>ID: {node.id}</span>
            <span>{node.module_id}</span>
          </div>
        </div>

        {/* Module Description or Geometric Properties */}
        {node.geometric ? (
          <div className="bg-neutral-950/60 border border-neutral-800/80 rounded-lg p-2.5 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-white flex items-center gap-1.5">
                <span
                  className="w-2.5 h-2.5 rounded-full inline-block"
                  style={{ backgroundColor: node.geometric.color }}
                />
                {node.geometric.subType}
              </span>
              <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800/50 uppercase">
                {node.geometric.kind}
              </span>
            </div>
            <p className="text-[11px] text-neutral-400 leading-relaxed">
              {node.geometric.description}
            </p>
            {node.geometric.sites && (
              <div className="pt-1 border-t border-neutral-800/60 space-y-1">
                <span className="text-[10px] font-mono text-neutral-400 font-semibold uppercase block">
                  Interaction / Valence Sites ({node.geometric.sites.length}):
                </span>
                <div className="flex flex-wrap gap-1">
                  {node.geometric.sites.map(s => (
                    <span
                      key={s.id}
                      className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-neutral-900 border border-neutral-800 text-neutral-300"
                    >
                      {s.label} ({s.kind}) @ {s.angle_deg}°
                    </span>
                  ))}
                </div>
              </div>
            )}
            {node.geometric.properties && (
              <div className="pt-1 border-t border-neutral-800/60 space-y-1">
                <span className="text-[10px] font-mono text-neutral-400 font-semibold uppercase block">
                  Physical / Topological Invariants:
                </span>
                <div className="space-y-0.5">
                  {Object.entries(node.geometric.properties).map(([k, v]) => (
                    <div key={k} className="flex items-center justify-between text-[10px] font-mono">
                      <span className="text-neutral-500">{k}:</span>
                      <span className="text-neutral-300 font-semibold">{String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : mod ? (
          <div className="bg-neutral-950/60 border border-neutral-800/80 rounded-lg p-2.5 space-y-1.5">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-neutral-300">{mod.name}</span>
              <span className="text-[9px] font-mono px-1 rounded bg-neutral-800 text-neutral-400">
                v{mod.version}
              </span>
            </div>
            <p className="text-[11px] text-neutral-400 leading-relaxed">{mod.description}</p>
            {mod.assumptions && mod.assumptions.length > 0 && (
              <div className="pt-1 text-[10px] text-amber-400/90 font-mono">
                <span className="font-semibold">Assumptions: </span>
                {mod.assumptions.join('; ')}
              </div>
            )}
          </div>
        ) : null}

        {/* Parameters Form */}
        <div>
          <div className="flex items-center gap-1.5 mb-2">
            <Sliders className="w-3.5 h-3.5 text-neutral-400" />
            <h3 className="text-[11px] font-bold uppercase tracking-wider text-neutral-300">Parameters</h3>
          </div>

          {mod?.parameters.length === 0 ? (
            <div className="text-[11px] text-neutral-500 italic p-2 bg-neutral-950/40 rounded border border-neutral-800/40">
              No configurable parameters for this module.
            </div>
          ) : (
            <div className="space-y-2.5">
              {mod?.parameters.map((p) => {
                const currentVal = node.params[p.name] ?? p.default;

                return (
                  <div key={p.name} className="space-y-1">
                    <div className="flex items-center justify-between">
                      <label className="text-[11px] font-mono text-neutral-300">{p.name}</label>
                      <span className="text-[9px] font-mono text-neutral-500">{p.type}</span>
                    </div>
                    {p.description && (
                      <p className="text-[10px] text-neutral-500 leading-tight">{p.description}</p>
                    )}
                    <input
                      type={p.type === 'integer' || p.type === 'number' ? 'number' : 'text'}
                      value={currentVal}
                      step={p.type === 'integer' ? '1' : 'any'}
                      onChange={(e) => {
                        const val = p.type === 'integer' 
                          ? (isNaN(parseInt(e.target.value, 10)) ? 0 : parseInt(e.target.value, 10))
                          : p.type === 'number' 
                          ? (isNaN(parseFloat(e.target.value)) ? 0 : parseFloat(e.target.value))
                          : e.target.value;
                        handleParamChange(p.name, val);
                      }}
                      className="w-full bg-neutral-950 border border-neutral-800 rounded px-2.5 py-1 text-neutral-100 font-mono focus:outline-none focus:border-indigo-500 text-xs"
                    />
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Execution Results & Verification */}
        {nodeResult && (
          <div className="pt-2 border-t border-neutral-800 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <Activity className="w-3.5 h-3.5 text-neutral-400" />
                <h3 className="text-[11px] font-bold uppercase tracking-wider text-neutral-300">Run State</h3>
              </div>
              <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded font-bold ${
                nodeResult.state === 'SUCCESS' ? 'bg-emerald-950 text-emerald-300 border border-emerald-800/60' : 'bg-rose-950 text-rose-300 border border-rose-800/60'
              }`}>
                {nodeResult.state} ({nodeResult.execution_time_ms}ms)
              </span>
            </div>

            {nodeResult.error && (
              <div className="p-2 rounded bg-rose-950/50 border border-rose-800/60 text-rose-300 text-[11px]">
                {nodeResult.error}
              </div>
            )}

            {/* Output Values Inspector */}
            {Object.keys(nodeResult.outputs).length > 0 && (
              <div className="space-y-1.5">
                <span className="text-[10px] font-mono text-neutral-400 font-semibold uppercase">Outputs</span>
                <div className="space-y-1">
                  {Object.entries(nodeResult.outputs).map(([k, v]) => (
                    <div key={k} className="p-2 rounded bg-neutral-950 border border-neutral-800 font-mono text-[10px] space-y-1">
                      <div className="flex items-center justify-between text-indigo-400 font-semibold">
                        <span>{k}</span>
                        <span className="text-neutral-500">
                          {Array.isArray(v) ? `Array(${v.length})` : typeof v}
                        </span>
                      </div>
                      <div className="text-neutral-300 max-h-24 overflow-y-auto break-all">
                        {Array.isArray(v) ? (
                          v.length > 8 ? `[${v.slice(0, 4).map(n => Number(n).toFixed(3)).join(', ')}, ... ${v.length - 8} more ..., ${v.slice(-4).map(n => Number(n).toFixed(3)).join(', ')}]` : JSON.stringify(v)
                        ) : typeof v === 'object' ? JSON.stringify(v) : String(v)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Verification Records */}
            {nodeResult.verifications.length > 0 && (
              <div className="space-y-2">
                <span className="text-[10px] font-mono text-neutral-400 font-semibold uppercase flex items-center gap-1">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                  Verification Records ({nodeResult.verifications.length})
                </span>
                <div className="space-y-1.5">
                  {nodeResult.verifications.map((v) => (
                    <div 
                      key={v.check_id}
                      className={`p-2 rounded border text-[10px] space-y-1 ${
                        v.state === 'PASS' 
                          ? 'bg-emerald-950/30 border-emerald-800/40 text-neutral-200' 
                          : 'bg-rose-950/30 border-rose-800/40 text-neutral-200'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono font-bold">{v.check_id}</span>
                        <span className={`px-1 rounded text-[9px] font-mono font-bold ${
                          v.state === 'PASS' ? 'text-emerald-400' : 'text-rose-400'
                        }`}>
                          {v.state}
                        </span>
                      </div>
                      <p className="text-[10px] text-neutral-400">{v.claim}</p>
                      <div className="flex items-center justify-between text-[9px] text-neutral-500 font-mono pt-1">
                        <span>Kind: {v.evidence_kind}</span>
                        <span>{v.method}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Port Wiring Summary */}
        <div className="pt-2 border-t border-neutral-800 space-y-2 text-[10px] font-mono">
          <span className="text-neutral-400 uppercase font-semibold block">Wiring Connections</span>
          
          <div className="space-y-1">
            <span className="text-neutral-500 flex items-center gap-1">
              <ArrowLeft className="w-3 h-3 text-cyan-400" /> Incoming ({incomingEdges.length})
            </span>
            {incomingEdges.map((e, i) => (
              <div key={i} className="pl-3 text-neutral-400">
                {e.source_node}.{e.source_port} → {e.target_port}
              </div>
            ))}
          </div>

          <div className="space-y-1">
            <span className="text-neutral-500 flex items-center gap-1">
              <ArrowRight className="w-3 h-3 text-emerald-400" /> Outgoing ({outgoingEdges.length})
            </span>
            {outgoingEdges.map((e, i) => (
              <div key={i} className="pl-3 text-neutral-400">
                {e.source_port} → {e.target_node}.{e.target_port}
              </div>
            ))}
          </div>
        </div>
      </div>
    </aside>
  );
};
