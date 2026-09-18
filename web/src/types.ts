export type EvidenceKind = 
  | 'NUMERICAL' 
  | 'INTERVAL' 
  | 'SYMBOLIC' 
  | 'FORMAL' 
  | 'BACKEND_AGREEMENT';

export type Maturity = 'ALPHA' | 'BETA' | 'STABLE' | 'EXPERIMENTAL';

export type PortDataType = 'number' | 'array' | 'interval' | 'bool' | 'matrix' | 'mesh' | 'certificate';

export interface PortSpec {
  name: string;
  type: PortDataType;
  description?: string;
}

export interface ParameterSpec {
  name: string;
  type: 'number' | 'integer' | 'string' | 'bool' | 'float_array';
  default: any;
  description?: string;
  min?: number;
  max?: number;
}

export interface ProofStatus {
  evidence: EvidenceKind[];
  unit_tests: boolean;
  property_tests?: boolean;
  documentation: boolean;
  limitations?: string[];
}

export interface ModuleDefinition {
  module_id: string;
  name: string;
  version: string;
  category: 'Utilities' | 'Data' | 'Analysis' | 'PDE' | 'Verification' | 'FEM';
  description: string;
  maturity: Maturity;
  assumptions?: string[];
  inputs: PortSpec[];
  outputs: PortSpec[];
  parameters: ParameterSpec[];
  proof_status: ProofStatus;
  supports_gpu?: boolean;
  // Execution function
  execute: (inputs: Record<string, any>, params: Record<string, any>) => Record<string, any>;
  verify?: (inputs: Record<string, any>, params: Record<string, any>, outputs: Record<string, any>) => VerificationRecord[];
}

export interface VerificationRecord {
  check_id: string;
  evidence_kind: EvidenceKind;
  claim: string;
  state: 'PASS' | 'FAIL' | 'NOT_RUN';
  method: string;
  diagnostics?: Record<string, any>;
}

export interface GraphGroup {
  id: string;
  title: string;
  color?: 'indigo' | 'emerald' | 'amber' | 'rose' | 'cyan' | 'purple';
  description?: string;
  node_ids: string[];
}

export type TilingBasis = 'cartesian_square' | 'hexagonal_honeycomb' | 'eisenstein_omega' | 'gaussian_dragon';

export interface Rotation3D {
  x: number; // pitch (-90 to 90)
  y: number; // yaw (-180 to 180)
  z: number; // roll (-180 to 180)
}

export type GeometricKind = 'atom' | 'molecule' | 'protein_fold' | 'simplex' | 'manifold' | 'alphafold_protein';

export type BondType = 'data_flow' | 'covalent_single' | 'covalent_double' | 'hydrogen_bond' | 'peptide_backbone' | 'simplex_facet' | 'disulfide_bridge';

export interface GeometricSite {
  id: string;
  label: string;
  angle_deg?: number;
  kind: 'valence' | 'hydrogen_donor' | 'hydrogen_acceptor' | 'n_term' | 'c_term' | 'vertex' | 'disulfide';
}

export interface AlphaFoldProteinData {
  uniprot_id: string;
  alphafold_id: string;
  name: string;
  organism: string;
  mean_plddt: number;
  confidence_class: 'Very High (>90)' | 'Confident (70-90)' | 'Low (50-70)' | 'Very Low (<50)';
  residue_count: number;
  ca_coords: [number, number, number][]; // 3D C-alpha coordinates in Angstroms
  sequence_summary?: string;
  writhe: number; // Călugăreanu-White-Fuller Writhe (Wr)
  twist: number;  // Total Twist (Tw)
  link_number: number; // Lk = Tw + Wr
  mean_curvature: number; // Mean discrete curvature kappa
  mean_torsion: number;   // Mean discrete torsion tau
  laplacian_spectral_gap: number; // Fiedler lambda_2 of contact complex
  secondary_structure_ratio: { alpha: number; beta: number; coil: number };
  license: 'CC-BY-4.0 (EMBL-EBI / DeepMind)';
  source_db: 'AlphaFold Protein Structure Database';
}

export interface GeometricMetadata {
  kind: GeometricKind;
  subType: string;
  color: string;
  radius?: number;
  valency?: number;
  sites: GeometricSite[];
  description?: string;
  properties?: Record<string, any>;
  alphafold?: AlphaFoldProteinData;
}

export interface GraphNode {
  id: string;
  module_id: string;
  params: Record<string, any>;
  position: [number, number];
  label?: string;
  group_id?: string;
  geometric?: GeometricMetadata;
}

export interface GraphEdge {
  source_node: string;
  source_port: string;
  target_node: string;
  target_port: string;
  bond_type?: BondType;
}

export interface CaceExperiment {
  schema_version: number;
  name: string;
  metadata?: {
    purpose?: string;
    author?: string;
    created_at?: string;
  };
  nodes: GraphNode[];
  edges: GraphEdge[];
  groups?: GraphGroup[];
  tiling_mode?: TilingBasis;
  rotation_3d?: Rotation3D;
}

export type ExecutionState = 'NOT_RUN' | 'RUNNING' | 'SUCCESS' | 'FAIL';

export interface NodeExecutionResult {
  node_id: string;
  state: ExecutionState;
  inputs: Record<string, any>;
  params: Record<string, any>;
  outputs: Record<string, any>;
  verifications: VerificationRecord[];
  execution_time_ms: number;
  error?: string;
  diagnostics?: Record<string, any>;
}

export interface RunReport {
  run_id: string;
  experiment_name: string;
  schema_version: number;
  timestamp: string;
  total_duration_ms: number;
  status: 'PASS' | 'FAIL';
  node_results: Record<string, NodeExecutionResult>;
  all_verifications_passed: boolean;
  evidence_summary: {
    total_checks: number;
    passed_checks: number;
    failed_checks: number;
    evidence_breakdown: Record<EvidenceKind, number>;
  };
}

export interface CanonicalClaim {
  claim_id: string;
  statement: string;
  scope: string;
  evidence_ceiling: 'formally-verified' | 'symbolic' | 'interval' | 'numerical';
  module_ids: string[];
  nonclaims: string[];
  proof_contract_id?: string;
  qualification: {
    status: 'QUALIFIED' | 'HISTORICAL_PASS' | 'NOT_RUN' | 'FORMAL_FAIL_CLOSED';
    attested_commit: string | null;
    current_head_qualified: boolean;
    proof_artifact_sha256: string | null;
    reason: string;
  };
}

export interface ProofContract {
  contract_id: string;
  claim_id: string;
  build_target: string;
  dependency_pins: {
    lean_toolchain: string;
    mathlib_commit: string;
  };
  allowed_axioms: string[];
  audited_source_files: string[];
  endpoint_theorems: string[];
}

export interface EvidenceBundleItem {
  id: string;
  data: string;
  role: string;
  sha256: string;
  bytes: number;
}

// Adaptive Scientific Cellular World types
export type HeartbeatMode = 'PERIODIC' | 'EVENT' | 'CONDITIONAL' | 'ON_DEMAND';

export type CellState = 
  | 'READY' 
  | 'RUNNING' 
  | 'PASS' 
  | 'QUALIFIED' 
  | 'STALE' 
  | 'BLOCKED' 
  | 'FAILED' 
  | 'KERNEL_PROVED';

export interface ScientificCell {
  id: string;
  name: string;
  type: 'proof_object' | 'mesh_cell' | 'neural_block' | 'ga_rotor' | 'pde_solver';
  state: CellState;
  heartbeat_mode: HeartbeatMode;
  rate_hz?: number;
  last_tick: number;
  cell_seed: string;
  current_hash: string;
  evidence_level: EvidenceKind;
  neighbors: string[];
  metrics: Record<string, any>;
}

// Growth Loop Control types
export type GrowthLoopMode = 'SUGGESTIONS_ONLY' | 'TEST_IN_ISOLATION' | 'AUTO_IMPLEMENT';

export interface GrowthLoopConfig {
  enabled: boolean;
  mode: GrowthLoopMode;
  rigor_kernel_locked: true; // Constitutional invariant
  cpu_budget_ms: number;
  gpu_budget_ms: number;
  memory_budget_mb: number;
  max_iterations: number;
  current_iterations: number;
  stop_conditions: {
    no_measurable_gain: boolean;
    repeated_failure_fingerprint: boolean;
    evidence_degradation_blocked: boolean;
  };
}

// Directive #16: Representation Translation types
export type RepresentationType = 'Matrix_SO3' | 'Quaternion_H1' | 'GA_Rotor_Cl30' | 'Spinor_Spin3';

export interface RepresentationTranslation {
  id: string;
  source: RepresentationType;
  target: RepresentationType;
  cost_in: number;
  cost_compute: number;
  cost_out: number;
  cost_validation: number;
  total_cost_translated: number;
  total_cost_canonical: number;
  speedup_ratio: number;
  double_cover_handled: boolean; // R ~ -R
  certified_error_bound: number; // e.g. 1e-15
  status: 'RECOMMENDED' | 'EQUIVALENT' | 'SUBOPTIMAL' | 'INVALID';
}

// Rigor Kernel Architecture & IP Hardening Types
export type ThreatVector = 
  | 'CODE_EXTRACTION_ATTEMPT' 
  | 'PROOF_LEDGER_TAMPER' 
  | 'AST_PROTOTYPE_POLLUTION' 
  | 'QUALIFICATION_DRIFT_HIJACK' 
  | 'UNAUTHORIZED_DEBUGGER'
  | 'PARAMETER_FUZZING_EXPLOIT';

export interface SecurityIncident {
  id: string;
  timestamp: string;
  threat_vector: ThreatVector;
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM';
  defense_action: string;
  target_boundary: string;
  blocked: boolean;
  forensic_fingerprint: string;
  payload_summary?: string;
}

export interface HardeningPolicies {
  kernel_enclave_isolation: boolean;       // Proprietary algorithms executed in isolated TCB Layer 0
  anti_extraction_obfuscation: boolean;    // Masks internal AST & prevents source decompilation
  fail_closed_lockdown: boolean;           // Aborts execution immediately upon any verification or drift anomaly
  tamper_guard_watchdog: boolean;          // Active DOM/prototype & memory scraping monitor
  zero_retention_memory_wipe: boolean;     // Purges intermediate mathematical registers post-verification
  certificate_only_export: boolean;        // Prohibits raw kernel source export; allows only verifiable Merkle certificates
  merkle_provenance_enforced: boolean;     // Requires cryptographic Merkle root matching canonical claim ledger
}

export interface RigorKernelEnvelope {
  experiment_digest: string;
  timestamp: string;
  enclave_nonce: string;
  session_watermark: string;
  tcb_layer: 0;
  sanitization_state: 'CLEAN' | 'NEUTRALIZED' | 'REJECTED';
  merkle_root: string;
  signature_verified: boolean;
}

export interface SecurityPerimeterStatus {
  enclave_state: 'ARMORED_ENCLAVE_ACTIVE' | 'ISOLATED' | 'COMPROMISE_BLOCKED';
  anti_extraction_shield: 'MAXIMUM_HARDENING' | 'MONITORING' | 'BREACH_DEFENDED';
  tamper_defense: 'SECURE' | 'TAMPER_DETECTED' | 'LOCKED_DOWN';
  merkle_ledger_integrity: 'CANONICAL_MATCH' | 'DRIFT_DETECTED';
  fail_closed_policy: 'ENFORCED' | 'STANDBY';
  total_threats_neutralized: number;
  active_policies: HardeningPolicies;
  recent_incidents: SecurityIncident[];
}

