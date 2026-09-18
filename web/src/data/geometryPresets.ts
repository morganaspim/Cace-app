import { GeometricMetadata, GraphNode, GraphEdge, CaceExperiment } from '../types';
import { ALPHAFOLD_PROTEINS, createAlphaFoldGeometricMetadata } from './alphafoldProteins';

export const GEOMETRIC_CATALOG: Record<string, GeometricMetadata> = {
  // AlphaFold DB Protein Mathematical Objects (CC-BY 4.0 EMBL-EBI / DeepMind)
  'alphafold.P0CG48': createAlphaFoldGeometricMetadata(ALPHAFOLD_PROTEINS['alphafold.P0CG48']),
  'alphafold.P83577': createAlphaFoldGeometricMetadata(ALPHAFOLD_PROTEINS['alphafold.P83577']),
  'alphafold.P01542': createAlphaFoldGeometricMetadata(ALPHAFOLD_PROTEINS['alphafold.P01542']),

  // Atoms
  'atom.C': {
    kind: 'atom',
    subType: 'C',
    color: '#0284c7', // Cyan/Carbon
    radius: 22,
    valency: 4,
    description: 'Carbon (tetrahedral/planar sp³ valence)',
    sites: [
      { id: 'v1', label: '1', angle_deg: 0, kind: 'valence' },
      { id: 'v2', label: '2', angle_deg: 90, kind: 'valence' },
      { id: 'v3', label: '3', angle_deg: 180, kind: 'valence' },
      { id: 'v4', label: '4', angle_deg: 270, kind: 'valence' }
    ],
    properties: { atomic_mass: 12.011, electronegativity: 2.55 }
  },
  'atom.H': {
    kind: 'atom',
    subType: 'H',
    color: '#e2e8f0', // White/Light slate
    radius: 16,
    valency: 1,
    description: 'Hydrogen (1s¹ valence)',
    sites: [
      { id: 'v1', label: '1', angle_deg: 0, kind: 'valence' }
    ],
    properties: { atomic_mass: 1.008, electronegativity: 2.20 }
  },
  'atom.O': {
    kind: 'atom',
    subType: 'O',
    color: '#ef4444', // Red
    radius: 20,
    valency: 2,
    description: 'Oxygen (bent 104.5° valence)',
    sites: [
      { id: 'v1', label: '1', angle_deg: 35, kind: 'valence' },
      { id: 'v2', label: '2', angle_deg: 145, kind: 'valence' }
    ],
    properties: { atomic_mass: 15.999, electronegativity: 3.44 }
  },
  'atom.N': {
    kind: 'atom',
    subType: 'N',
    color: '#6366f1', // Indigo/Blue
    radius: 21,
    valency: 3,
    description: 'Nitrogen (trigonal pyramidal valence)',
    sites: [
      { id: 'v1', label: '1', angle_deg: 30, kind: 'valence' },
      { id: 'v2', label: '2', angle_deg: 150, kind: 'valence' },
      { id: 'v3', label: '3', angle_deg: 270, kind: 'valence' }
    ],
    properties: { atomic_mass: 14.007, electronegativity: 3.04 }
  },
  'atom.S': {
    kind: 'atom',
    subType: 'S',
    color: '#eab308', // Amber/Yellow
    radius: 24,
    valency: 2,
    description: 'Sulfur (forms covalent disulfide bridges)',
    sites: [
      { id: 'v1', label: '1', angle_deg: 45, kind: 'valence' },
      { id: 'v2', label: '2', angle_deg: 225, kind: 'valence' }
    ],
    properties: { atomic_mass: 32.06, electronegativity: 2.58 }
  },

  // Molecules
  'molecule.H2O': {
    kind: 'molecule',
    subType: 'H2O',
    color: '#06b6d4', // Cyan
    radius: 28,
    description: 'Water dipole molecule with 2 H-donors and 2 lone pair acceptors',
    sites: [
      { id: 'h1', label: 'H-don1', angle_deg: 40, kind: 'hydrogen_donor' },
      { id: 'h2', label: 'H-don2', angle_deg: 140, kind: 'hydrogen_donor' },
      { id: 'lp1', label: 'LP-acc1', angle_deg: 220, kind: 'hydrogen_acceptor' },
      { id: 'lp2', label: 'LP-acc2', angle_deg: 320, kind: 'hydrogen_acceptor' }
    ],
    properties: { dipole_debye: 1.85, bond_angle_deg: 104.5 }
  },
  'molecule.Benzene': {
    kind: 'molecule',
    subType: 'C6H6',
    color: '#8b5cf6', // Violet
    radius: 34,
    description: 'Benzene Aromatic ring with delocalized π-orbital hexagonal symmetry',
    sites: [
      { id: 'c1', label: 'C1', angle_deg: 0, kind: 'valence' },
      { id: 'c2', label: 'C2', angle_deg: 60, kind: 'valence' },
      { id: 'c3', label: 'C3', angle_deg: 120, kind: 'valence' },
      { id: 'c4', label: 'C4', angle_deg: 180, kind: 'valence' },
      { id: 'c5', label: 'C5', angle_deg: 240, kind: 'valence' },
      { id: 'c6', label: 'C6', angle_deg: 300, kind: 'valence' }
    ],
    properties: { resonance_energy_kcal: 36, aromatic: true }
  },

  // Protein Fold Secondary Structures
  'fold.AlphaHelix': {
    kind: 'protein_fold',
    subType: 'α-Helix',
    color: '#10b981', // Emerald
    radius: 36,
    description: 'Right-handed α-helix motif (3.6 residues/turn, 1.5 Å rise, i→i+4 H-bonding)',
    sites: [
      { id: 'n_term', label: 'N-Term', angle_deg: 180, kind: 'n_term' },
      { id: 'c_term', label: 'C-Term', angle_deg: 0, kind: 'c_term' },
      { id: 'h_bond_1', label: 'H-i+4', angle_deg: 90, kind: 'hydrogen_donor' },
      { id: 'h_bond_2', label: 'H-i', angle_deg: 270, kind: 'hydrogen_acceptor' }
    ],
    properties: { phi_deg: -57, psi_deg: -47, pitch_angstrom: 5.4 }
  },
  'fold.BetaStrand': {
    kind: 'protein_fold',
    subType: 'β-Strand',
    color: '#f97316', // Orange
    radius: 32,
    description: 'Extended β-sheet strand with alternating inter-chain hydrogen bond latches',
    sites: [
      { id: 'n_term', label: 'N-Term', angle_deg: 180, kind: 'n_term' },
      { id: 'c_term', label: 'C-Term', angle_deg: 0, kind: 'c_term' },
      { id: 'lateral_up', label: 'H-Up', angle_deg: 90, kind: 'hydrogen_donor' },
      { id: 'lateral_dn', label: 'H-Down', angle_deg: 270, kind: 'hydrogen_acceptor' }
    ],
    properties: { phi_deg: -139, psi_deg: 135, pleat_angstrom: 7.0 }
  },
  'fold.BetaLoop': {
    kind: 'protein_fold',
    subType: 'β-Turn',
    color: '#ec4899', // Pink
    radius: 28,
    description: 'Tight 4-residue hairpin loop reversing chain direction (Type I / Type II)',
    sites: [
      { id: 'in', label: 'In', angle_deg: 225, kind: 'n_term' },
      { id: 'out', label: 'Out', angle_deg: 315, kind: 'c_term' },
      { id: 'turn_h', label: 'Turn-H', angle_deg: 90, kind: 'hydrogen_acceptor' }
    ],
    properties: { turn_type: 'Hairpin Type I', length_residues: 4 }
  },

  // Geometric Simplices & Manifolds
  'manifold.Simplex2D': {
    kind: 'simplex',
    subType: '2-Simplex (△)',
    color: '#a855f7', // Purple
    radius: 30,
    description: 'Conformal triangular 2-simplex with 3 vertex boundary faces',
    sites: [
      { id: 'v0', label: 'v₀', angle_deg: 90, kind: 'vertex' },
      { id: 'v1', label: 'v₁', angle_deg: 210, kind: 'vertex' },
      { id: 'v2', label: 'v₂', angle_deg: 330, kind: 'vertex' }
    ],
    properties: { euler_characteristic: 1, metric_dimension: 2 }
  },
  'manifold.BlochSpinor': {
    kind: 'manifold',
    subType: 'Bloch Sphere S²',
    color: '#06b6d4', // Cyan
    radius: 32,
    description: 'Quantum 2-level state space manifold S² = CP¹ with SU(2) double cover',
    sites: [
      { id: 'pole_north', label: '|0⟩', angle_deg: 90, kind: 'vertex' },
      { id: 'pole_south', label: '|1⟩', angle_deg: 270, kind: 'vertex' },
      { id: 'equator_x', label: '|+⟩', angle_deg: 0, kind: 'vertex' },
      { id: 'equator_y', label: '|i⟩', angle_deg: 180, kind: 'vertex' }
    ],
    properties: { manifold: 'S^2', metric: 'Fubini-Study' }
  }
};

/**
 * Helper to instantiate a geometric node from the catalog
 */
export function createGeometricNode(key: string, id: string, position: [number, number]): GraphNode {
  const meta = GEOMETRIC_CATALOG[key];
  if (!meta) throw new Error(`Unknown geometric entity: ${key}`);

  return {
    id,
    module_id: key,
    label: `${meta.subType} (${id.slice(-4)})`,
    position,
    params: { ...meta.properties },
    geometric: meta
  };
}

/**
 * Pre-constructed Geometric Experiments
 */
export const PRESET_GEOMETRIC_EXPERIMENTS: Record<string, CaceExperiment> = {
  protein_fold_domain: {
    schema_version: 1,
    name: "Protein Fold Secondary Architecture (α/β Hairpin Domain)",
    tiling_mode: 'hexagonal_honeycomb',
    rotation_3d: { x: 22, y: -25, z: 0 },
    metadata: {
      purpose: "Secondary structure folding topology connecting Alpha-Helix to Beta-Strands via peptide backbone and hydrogen bonds",
      author: "CACE Geometric Biochemistry Lab",
      created_at: "2026-09-16"
    },
    nodes: [
      {
        id: "geo_helix_1",
        module_id: "fold.AlphaHelix",
        label: "α-Helix Core (Res 1-12)",
        position: [120, 180],
        params: { length: 12 },
        geometric: GEOMETRIC_CATALOG['fold.AlphaHelix']
      },
      {
        id: "geo_loop_1",
        module_id: "fold.BetaLoop",
        label: "Hairpin Loop I",
        position: [290, 120],
        params: { type: 'Type I' },
        geometric: GEOMETRIC_CATALOG['fold.BetaLoop']
      },
      {
        id: "geo_strand_1",
        module_id: "fold.BetaStrand",
        label: "β-Strand A (Res 16-22)",
        position: [440, 180],
        params: { direction: 'parallel' },
        geometric: GEOMETRIC_CATALOG['fold.BetaStrand']
      },
      {
        id: "geo_strand_2",
        module_id: "fold.BetaStrand",
        label: "β-Strand B (Res 26-32)",
        position: [440, 310],
        params: { direction: 'anti-parallel' },
        geometric: GEOMETRIC_CATALOG['fold.BetaStrand']
      },
      {
        id: "geo_cys_bridge",
        module_id: "atom.S",
        label: "Cys Disulfide Crosslink",
        position: [280, 270],
        params: { bond: 'S-S' },
        geometric: GEOMETRIC_CATALOG['atom.S']
      }
    ],
    edges: [
      {
        source_node: "geo_helix_1",
        source_port: "c_term",
        target_node: "geo_loop_1",
        target_port: "in",
        bond_type: "peptide_backbone"
      },
      {
        source_node: "geo_loop_1",
        source_port: "out",
        target_node: "geo_strand_1",
        target_port: "n_term",
        bond_type: "peptide_backbone"
      },
      {
        source_node: "geo_strand_1",
        source_port: "lateral_dn",
        target_node: "geo_strand_2",
        target_port: "lateral_up",
        bond_type: "hydrogen_bond"
      },
      {
        source_node: "geo_helix_1",
        source_port: "h_bond_2",
        target_node: "geo_cys_bridge",
        target_port: "v1",
        bond_type: "covalent_single"
      },
      {
        source_node: "geo_cys_bridge",
        source_port: "v2",
        target_node: "geo_strand_2",
        target_port: "lateral_up",
        bond_type: "covalent_single"
      }
    ]
  },

  water_hydrogen_lattice: {
    schema_version: 1,
    name: "Tetrahedral Water Hydrogen-Bonding Cluster (H₂O)₄",
    tiling_mode: 'eisenstein_omega',
    rotation_3d: { x: 30, y: 35, z: -5 },
    metadata: {
      purpose: "Eisenstein fractal coordinate mapping of tetrahedral hydrogen bonding network in liquid water",
      author: "CACE Molecular Topology",
      created_at: "2026-09-16"
    },
    nodes: [
      {
        id: "h2o_center",
        module_id: "molecule.H2O",
        label: "H₂O Center Dipole",
        position: [300, 240],
        params: {},
        geometric: GEOMETRIC_CATALOG['molecule.H2O']
      },
      {
        id: "h2o_donor_a",
        module_id: "molecule.H2O",
        label: "H₂O Ligand A (Acceptor)",
        position: [180, 140],
        params: {},
        geometric: GEOMETRIC_CATALOG['molecule.H2O']
      },
      {
        id: "h2o_donor_b",
        module_id: "molecule.H2O",
        label: "H₂O Ligand B (Acceptor)",
        position: [420, 140],
        params: {},
        geometric: GEOMETRIC_CATALOG['molecule.H2O']
      },
      {
        id: "h2o_acc_c",
        module_id: "molecule.H2O",
        label: "H₂O Ligand C (Donor)",
        position: [200, 360],
        params: {},
        geometric: GEOMETRIC_CATALOG['molecule.H2O']
      },
      {
        id: "h2o_acc_d",
        module_id: "molecule.H2O",
        label: "H₂O Ligand D (Donor)",
        position: [410, 360],
        params: {},
        geometric: GEOMETRIC_CATALOG['molecule.H2O']
      }
    ],
    edges: [
      {
        source_node: "h2o_center",
        source_port: "h1",
        target_node: "h2o_donor_a",
        target_port: "lp1",
        bond_type: "hydrogen_bond"
      },
      {
        source_node: "h2o_center",
        source_port: "h2",
        target_node: "h2o_donor_b",
        target_port: "lp2",
        bond_type: "hydrogen_bond"
      },
      {
        source_node: "h2o_acc_c",
        source_port: "h1",
        target_node: "h2o_center",
        target_port: "lp1",
        bond_type: "hydrogen_bond"
      },
      {
        source_node: "h2o_acc_d",
        source_port: "h2",
        target_node: "h2o_center",
        target_port: "lp2",
        bond_type: "hydrogen_bond"
      }
    ]
  },

  benzene_aromatic_ring: {
    schema_version: 1,
    name: "Benzene Aromatic Molecule (C₆H₆ Hexagonal Tiling)",
    tiling_mode: 'hexagonal_honeycomb',
    rotation_3d: { x: 15, y: -20, z: 0 },
    metadata: {
      purpose: "Hexagonal honeycomb coordination of 6 Carbon atoms and 6 Hydrogen atoms with delocalized aromatic bonds",
      author: "CACE Organic Geometry",
      created_at: "2026-09-16"
    },
    nodes: [
      {
        id: "c1",
        module_id: "atom.C",
        label: "C₁",
        position: [260, 160],
        params: {},
        geometric: GEOMETRIC_CATALOG['atom.C']
      },
      {
        id: "c2",
        module_id: "atom.C",
        label: "C₂",
        position: [350, 160],
        params: {},
        geometric: GEOMETRIC_CATALOG['atom.C']
      },
      {
        id: "c3",
        module_id: "atom.C",
        label: "C₃",
        position: [400, 240],
        params: {},
        geometric: GEOMETRIC_CATALOG['atom.C']
      },
      {
        id: "c4",
        module_id: "atom.C",
        label: "C₄",
        position: [350, 320],
        params: {},
        geometric: GEOMETRIC_CATALOG['atom.C']
      },
      {
        id: "c5",
        module_id: "atom.C",
        label: "C₅",
        position: [260, 320],
        params: {},
        geometric: GEOMETRIC_CATALOG['atom.C']
      },
      {
        id: "c6",
        module_id: "atom.C",
        label: "C₆",
        position: [210, 240],
        params: {},
        geometric: GEOMETRIC_CATALOG['atom.C']
      },
      {
        id: "h1",
        module_id: "atom.H",
        label: "H₁",
        position: [230, 90],
        params: {},
        geometric: GEOMETRIC_CATALOG['atom.H']
      },
      {
        id: "h2",
        module_id: "atom.H",
        label: "H₂",
        position: [380, 90],
        params: {},
        geometric: GEOMETRIC_CATALOG['atom.H']
      },
      {
        id: "h3",
        module_id: "atom.H",
        label: "H₃",
        position: [480, 240],
        params: {},
        geometric: GEOMETRIC_CATALOG['atom.H']
      },
      {
        id: "h4",
        module_id: "atom.H",
        label: "H₄",
        position: [380, 390],
        params: {},
        geometric: GEOMETRIC_CATALOG['atom.H']
      },
      {
        id: "h5",
        module_id: "atom.H",
        label: "H₅",
        position: [230, 390],
        params: {},
        geometric: GEOMETRIC_CATALOG['atom.H']
      },
      {
        id: "h6",
        module_id: "atom.H",
        label: "H₆",
        position: [130, 240],
        params: {},
        geometric: GEOMETRIC_CATALOG['atom.H']
      }
    ],
    edges: [
      { source_node: "c1", source_port: "v1", target_node: "c2", target_port: "v3", bond_type: "covalent_double" },
      { source_node: "c2", source_port: "v2", target_node: "c3", target_port: "v4", bond_type: "covalent_single" },
      { source_node: "c3", source_port: "v1", target_node: "c4", target_port: "v3", bond_type: "covalent_double" },
      { source_node: "c4", source_port: "v2", target_node: "c5", target_port: "v4", bond_type: "covalent_single" },
      { source_node: "c5", source_port: "v1", target_node: "c6", target_port: "v3", bond_type: "covalent_double" },
      { source_node: "c6", source_port: "v2", target_node: "c1", target_port: "v4", bond_type: "covalent_single" },
      { source_node: "c1", source_port: "v2", target_node: "h1", target_port: "v1", bond_type: "covalent_single" },
      { source_node: "c2", source_port: "v1", target_node: "h2", target_port: "v1", bond_type: "covalent_single" },
      { source_node: "c3", source_port: "v2", target_node: "h3", target_port: "v1", bond_type: "covalent_single" },
      { source_node: "c4", source_port: "v1", target_node: "h4", target_port: "v1", bond_type: "covalent_single" },
      { source_node: "c5", source_port: "v2", target_node: "h5", target_port: "v1", bond_type: "covalent_single" },
      { source_node: "c6", source_port: "v1", target_node: "h6", target_port: "v1", bond_type: "covalent_single" }
    ]
  },
  alphafold_differential_topography: {
    schema_version: 1,
    name: "AlphaFold Differential Space Curves & Topological Linking",
    tiling_mode: 'cartesian_square',
    rotation_3d: { x: 30, y: -35, z: 0 },
    metadata: {
      purpose: "AlphaFold DB structural coordinates analyzed as discrete 3D Frenet-Serret space curves, Călugăreanu-White invariants (Lk = Tw + Wr), and contact graph Laplacians",
      author: "CACE Geometric Biochemistry Lab",
      created_at: "2026-09-16"
    },
    nodes: [
      {
        id: "af_ubiquitin",
        module_id: "alphafold.P0CG48",
        label: "Ubiquitin (AF-P0CG48)",
        position: [120, 180],
        params: { ...GEOMETRIC_CATALOG['alphafold.P0CG48'].properties },
        geometric: GEOMETRIC_CATALOG['alphafold.P0CG48']
      },
      {
        id: "af_trpcage",
        module_id: "alphafold.P83577",
        label: "TRP-Cage (AF-P83577)",
        position: [480, 150],
        params: { ...GEOMETRIC_CATALOG['alphafold.P83577'].properties },
        geometric: GEOMETRIC_CATALOG['alphafold.P83577']
      },
      {
        id: "af_crambin",
        module_id: "alphafold.P01542",
        label: "Crambin Thionin (AF-P01542)",
        position: [300, 360],
        params: { ...GEOMETRIC_CATALOG['alphafold.P01542'].properties },
        geometric: GEOMETRIC_CATALOG['alphafold.P01542']
      }
    ],
    edges: [
      {
        source_node: "af_ubiquitin",
        source_port: "c_term",
        target_node: "af_trpcage",
        target_port: "n_term",
        bond_type: "peptide_backbone"
      },
      {
        source_node: "af_trpcage",
        source_port: "contact_1",
        target_node: "af_crambin",
        target_port: "contact_2",
        bond_type: "hydrogen_bond"
      }
    ]
  }
};
