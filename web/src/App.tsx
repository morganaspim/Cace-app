import React, { useEffect, useMemo, useState } from 'react';
import QRCode from 'qrcode';
import { GraphCanvas } from './components/GraphCanvas';
import { NodePropertiesPanel } from './components/NodePropertiesPanel';
import { PRESET_GEOMETRIC_EXPERIMENTS } from './data/geometryPresets';
import { CaceExperiment, NodeExecutionResult } from './types';

const API = (import.meta as any).env?.VITE_CACE_API_URL || 'http://127.0.0.1:8000';

type HeartbeatSummary = {
  graph_hash: string;
  cell_count: number;
  edge_count: number;
  hash_algorithm: string;
  evidence_effect: 'NONE';
};

type RuntimeStatus = {
  allowed: boolean;
  unlimited: boolean;
  remaining_seconds: number | null;
  free_remaining_seconds: number;
  payment_network: string;
  evidence_effect: 'NONE';
};

type Tier = { id: string; name: string; amount_xmr: string; duration_seconds: number | null };
type PaymentConfig = { network: string; mainnet_primary_address: string; min_confirmations: number; tiers: Tier[] };
type Invoice = {
  invoice_id: string;
  network: string;
  tier_id: string;
  amount_xmr: string;
  address: string;
  uri: string;
  status: string;
  txid?: string | null;
  confirmations: number;
  entitlement_granted?: boolean;
};

function formatSeconds(value: number | null, unlimited: boolean) {
  if (unlimited) return 'Unlimited';
  if (value == null) return 'Unknown';
  const total = Math.max(0, Math.floor(value));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return `${h}h ${m}m ${s}s`;
}

const PaymentPanel: React.FC<{ onClose: () => void; onUnlocked: () => void }> = ({ onClose, onUnlocked }) => {
  const [config, setConfig] = useState<PaymentConfig | null>(null);
  const [tierId, setTierId] = useState('pass_30d');
  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [qr, setQr] = useState<string>('');
  const [error, setError] = useState<string>('');

  useEffect(() => {
    fetch(`${API}/api/payments/monero/config`)
      .then(async r => { if (!r.ok) throw new Error((await r.json()).detail || r.statusText); return r.json(); })
      .then(setConfig)
      .catch(e => setError(String(e)));
  }, []);

  useEffect(() => {
    if (!invoice?.uri) { setQr(''); return; }
    QRCode.toDataURL(invoice.uri, { width: 300, margin: 2 }).then(setQr).catch(e => setError(String(e)));
  }, [invoice?.uri]);

  useEffect(() => {
    if (!invoice || invoice.entitlement_granted) return;
    const timer = window.setInterval(async () => {
      try {
        const response = await fetch(`${API}/api/payments/monero/invoices/${invoice.invoice_id}`);
        if (!response.ok) throw new Error((await response.json()).detail || response.statusText);
        const next: Invoice = await response.json();
        setInvoice(next);
        if (next.entitlement_granted) onUnlocked();
      } catch (e) {
        setError(String(e));
      }
    }, 10000);
    return () => window.clearInterval(timer);
  }, [invoice?.invoice_id, invoice?.entitlement_granted, onUnlocked]);

  const createInvoice = async () => {
    setError('');
    try {
      const response = await fetch(`${API}/api/payments/monero/invoices`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ tier_id: tierId })
      });
      if (!response.ok) throw new Error((await response.json()).detail || response.statusText);
      setInvoice(await response.json());
    } catch (e) { setError(String(e)); }
  };

  return (
    <div className="fixed inset-0 z-[100] bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="w-full max-w-xl rounded-2xl border border-neutral-700 bg-neutral-900 p-5 shadow-2xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold">CACE compute time</h2>
            <p className="text-xs text-neutral-400 mt-1">Payments extend runtime resources only. They never change proof or evidence status.</p>
          </div>
          <button onClick={onClose} className="text-neutral-400 hover:text-white">Close</button>
        </div>
        {config && <div className="mt-4 text-xs font-mono text-neutral-400">Network: {config.network} · required confirmations: {config.min_confirmations}</div>}
        {!invoice && config && (
          <div className="mt-4 space-y-3">
            {config.tiers.map(tier => (
              <label key={tier.id} className="flex items-center justify-between rounded-lg border border-neutral-800 p-3 cursor-pointer">
                <span><input type="radio" checked={tierId === tier.id} onChange={() => setTierId(tier.id)} className="mr-2" />{tier.name}</span>
                <span className="font-mono text-amber-300">{tier.amount_xmr} XMR</span>
              </label>
            ))}
            <button onClick={createInvoice} className="w-full rounded-lg bg-amber-400 text-neutral-950 font-bold py-2">Create wallet-verified invoice</button>
          </div>
        )}
        {invoice && (
          <div className="mt-5 text-center space-y-3">
            <div className="text-sm font-semibold">Send exactly {invoice.amount_xmr} XMR</div>
            {qr && <img src={qr} alt="Monero invoice QR code" className="mx-auto rounded-lg bg-white p-2 w-[300px] h-[300px]" />}
            <div className="text-[10px] break-all rounded bg-neutral-950 border border-neutral-800 p-2 font-mono select-all">{invoice.address}</div>
            <div className="text-xs text-neutral-400">Invoice {invoice.status} · {invoice.confirmations} confirmations</div>
            {invoice.entitlement_granted && <div className="rounded-lg bg-emerald-950 border border-emerald-700 p-3 text-emerald-300 font-semibold">Confirmed by wallet RPC. Compute entitlement unlocked.</div>}
            <p className="text-[11px] text-neutral-500">The app does not trust a pasted transaction hash. Unlock occurs only after the server wallet observes the payment to this invoice subaddress.</p>
          </div>
        )}
        {error && <div className="mt-4 rounded bg-rose-950 border border-rose-800 p-2 text-xs text-rose-300">{error}</div>}
      </div>
    </div>
  );
};

export const App: React.FC = () => {
  const [experiment, setExperiment] = useState<CaceExperiment>(() => PRESET_GEOMETRIC_EXPERIMENTS.protein_fold_domain);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [nodeResults] = useState<Record<string, NodeExecutionResult>>({});
  const [status, setStatus] = useState<RuntimeStatus | null>(null);
  const [runtimeError, setRuntimeError] = useState('');
  const [paymentOpen, setPaymentOpen] = useState(false);
  const [heartbeat, setHeartbeat] = useState<HeartbeatSummary | null>(null);
  const [heartbeatError, setHeartbeatError] = useState('');

  const refreshStatus = async () => {
    try {
      const response = await fetch(`${API}/api/runtime/status`);
      if (!response.ok) throw new Error((await response.json()).detail || response.statusText);
      const next: RuntimeStatus = await response.json();
      setStatus(next);
      setRuntimeError('');
      if (!next.allowed) setPaymentOpen(true);
    } catch (e) {
      setRuntimeError(String(e));
      setStatus(null);
    }
  };

  useEffect(() => {
    refreshStatus();
    const timer = window.setInterval(refreshStatus, 15000);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      try {
        const response = await fetch(`${API}/api/runtime/heartbeat/graph`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ experiment }),
          signal: controller.signal,
        });
        if (!response.ok) throw new Error((await response.json()).detail || response.statusText);
        setHeartbeat(await response.json());
        setHeartbeatError('');
      } catch (e) {
        if ((e as any)?.name === 'AbortError') return;
        setHeartbeat(null);
        setHeartbeatError(String(e));
      }
    }, 300);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [experiment]);

  const entitlementLabel = useMemo(() => {
    if (runtimeError) return 'Runtime gate offline';
    if (!status) return 'Checking entitlement…';
    if (!status.allowed) return 'Compute locked';
    return `Compute: ${formatSeconds(status.remaining_seconds, status.unlimited)}`;
  }, [runtimeError, status]);

  return (
    <div className="h-screen min-h-[720px] bg-neutral-950 text-neutral-100 flex flex-col overflow-hidden">
      <header className="h-16 shrink-0 border-b border-neutral-800 px-4 flex items-center justify-between bg-neutral-950">
        <div>
          <div className="font-bold tracking-tight">CACE Studio · Coordinateless Canvas</div>
          <div className="text-[11px] text-neutral-500">MathObject identity is coordinate-free; Cartesian / honeycomb / Eisenstein / 3-D controls are view projections only.</div>
        </div>
        <div className="flex items-center gap-2">
          <span
            className={`text-xs font-mono px-2 py-1 rounded border ${heartbeat && !heartbeatError ? 'border-indigo-800 text-indigo-300' : 'border-rose-800 text-rose-300'}`}
            title={heartbeat ? `Semantic graph ${heartbeat.graph_hash} · ${heartbeat.hash_algorithm}` : heartbeatError || 'Compiling heartbeat graph…'}
          >
            {heartbeat ? `Heartbeat ${heartbeat.cell_count}c/${heartbeat.edge_count}e · ${heartbeat.graph_hash.slice(0, 10)}` : 'Heartbeat compiling…'}
          </span>
          <span className={`text-xs font-mono px-2 py-1 rounded border ${status?.allowed ? 'border-emerald-800 text-emerald-300' : 'border-rose-800 text-rose-300'}`}>{entitlementLabel}</span>
          <button onClick={() => setPaymentOpen(true)} className="text-xs rounded bg-neutral-800 hover:bg-neutral-700 px-3 py-1.5">Add compute time</button>
        </div>
      </header>
      {runtimeError && <div className="px-4 py-2 text-xs bg-rose-950 border-b border-rose-900 text-rose-300">Fail-closed runtime gate: {runtimeError}</div>}
      {heartbeatError && <div className="px-4 py-2 text-xs bg-rose-950 border-b border-rose-900 text-rose-300">Heartbeat graph rejected: {heartbeatError}</div>}
      <main className="flex-1 flex min-h-0">
        <GraphCanvas
          experiment={experiment}
          onUpdateExperiment={setExperiment}
          nodeResults={nodeResults}
          selectedNodeId={selectedNodeId}
          onSelectNode={setSelectedNodeId}
          onViewReport={() => undefined}
        />
        {selectedNodeId && (
          <NodePropertiesPanel
            selectedNodeId={selectedNodeId}
            experiment={experiment}
            onUpdateExperiment={setExperiment}
            nodeResult={nodeResults[selectedNodeId]}
            onClose={() => setSelectedNodeId(null)}
          />
        )}
      </main>
      {paymentOpen && <PaymentPanel onClose={() => setPaymentOpen(false)} onUnlocked={() => { refreshStatus(); }} />}
    </div>
  );
};
