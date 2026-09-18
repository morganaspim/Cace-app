import { TilingBasis, GraphNode, GraphEdge } from '../types';

export interface LatticePoint {
  x: number;
  y: number;
  label?: string;
}

export const LATTICE_CONFIGS: Record<TilingBasis, {
  name: string;
  symbol: string;
  basisFormula: string;
  description: string;
  defaultSpacing: number;
}> = {
  cartesian_square: {
    name: 'Square Lattice (ℤ²)',
    symbol: '⊞',
    basisFormula: 'v = x·e₁ + y·e₂',
    description: 'Standard 4-fold orthogonal Cartesian basis grid',
    defaultSpacing: 60
  },
  hexagonal_honeycomb: {
    name: 'Hexagonal Honeycomb (A₂)',
    symbol: '⬡',
    basisFormula: 'q·e₁ + r·e₂ (60° triangular)',
    description: '6-fold A₂ root lattice ideal for aromatic rings and isotropic packing',
    defaultSpacing: 55
  },
  eisenstein_omega: {
    name: 'Eisenstein ω Fractal (ℤ[ω])',
    symbol: '❄',
    basisFormula: 'z = a + b·e^{2πi/3} (ω³ = 1)',
    description: 'Complex triangular Eisenstein ring producing snowflake fractal domains',
    defaultSpacing: 65
  },
  gaussian_dragon: {
    name: 'Gaussian Base (1+i) Dragon',
    symbol: '🐉',
    basisFormula: 'z = ∑ dₖ·(1+i)ᵏ (b² = 2i)',
    description: 'Binary twindragon fractal tiling coordinate base over ℤ[i]',
    defaultSpacing: 70
  }
};

/**
 * Snap a continuous coordinate (x, y) to the nearest lattice node under the selected tiling basis
 */
export function snapToLattice(x: number, y: number, basis: TilingBasis, spacing = 60): [number, number] {
  switch (basis) {
    case 'cartesian_square': {
      const qx = Math.round(x / spacing) * spacing;
      const qy = Math.round(y / spacing) * spacing;
      return [qx, qy];
    }

    case 'hexagonal_honeycomb': {
      // Axial coordinates (q, r)
      const sqrt3 = Math.sqrt(3);
      const r = (2 / 3 * y) / spacing;
      const q = (sqrt3 / 3 * x - 1 / 3 * y) / spacing;
      // Cube rounding algorithm
      const rx = q;
      const rz = r;
      const ry = -rx - rz;

      let roundX = Math.round(rx);
      let roundY = Math.round(ry);
      let roundZ = Math.round(rz);

      const xDiff = Math.abs(roundX - rx);
      const yDiff = Math.abs(roundY - ry);
      const zDiff = Math.abs(roundZ - rz);

      if (xDiff > yDiff && xDiff > zDiff) {
        roundX = -roundY - roundZ;
      } else if (yDiff > zDiff) {
        roundY = -roundX - roundZ;
      } else {
        roundZ = -roundX - roundY;
      }

      const snapQ = roundX;
      const snapR = roundZ;
      const snappedX = spacing * (sqrt3 * snapQ + sqrt3 / 2 * snapR);
      const snappedY = spacing * (3 / 2 * snapR);
      return [Math.round(snappedX), Math.round(snappedY)];
    }

    case 'eisenstein_omega': {
      // Eisenstein integers ℤ[ω] where ω = -1/2 + i*sqrt(3)/2
      // x = spacing * (a - b/2)
      // y = spacing * (b * sqrt(3)/2)
      const sqrt3 = Math.sqrt(3);
      const bApprox = y / (spacing * sqrt3 / 2);
      const bRound = Math.round(bApprox);
      const aApprox = (x / spacing) + (bRound / 2);
      const aRound = Math.round(aApprox);

      const snappedX = spacing * (aRound - bRound / 2);
      const snappedY = spacing * (bRound * sqrt3 / 2);
      return [Math.round(snappedX), Math.round(snappedY)];
    }

    case 'gaussian_dragon': {
      // Complex integer lattice ℤ[i] with base b = 1 + i
      // Modulo the dragon tile center spacing
      const s = spacing * 0.7071;
      const u = (x + y) / (2 * s);
      const v = (x - y) / (2 * s);
      const uRound = Math.round(u);
      const vRound = Math.round(v);
      const snappedX = (uRound + vRound) * s;
      const snappedY = (uRound - vRound) * s;
      return [Math.round(snappedX), Math.round(snappedY)];
    }

    default:
      return [x, y];
  }
}

/**
 * Coordinateless Relational Relaxer:
 * Calculates positions dynamically from the interaction topology (modules & geometric bonds)
 * rather than hardcoded Cartesian coordinates, then projects and snaps them into the target lattice!
 */
export function relaxCoordinatelessGraph(
  nodes: GraphNode[],
  edges: GraphEdge[],
  basis: TilingBasis,
  iterations = 60
): GraphNode[] {
  if (nodes.length === 0) return [];
  if (nodes.length === 1) {
    return [{ ...nodes[0], position: [120, 120] }];
  }

  // Work on a mutable copy of positions
  const posMap = new Map<string, { x: number; y: number }>();
  
  // Initialize with small topological jitter or preserve center
  nodes.forEach((n, idx) => {
    const angle = (idx / nodes.length) * 2 * Math.PI;
    const initialRadius = 160 + (idx % 3) * 40;
    posMap.set(n.id, {
      x: n.position?.[0] || (300 + initialRadius * Math.cos(angle)),
      y: n.position?.[1] || (240 + initialRadius * Math.sin(angle))
    });
  });

  // Ideal target interaction distance based on connection type
  const getIdealLength = (edge: GraphEdge) => {
    switch (edge.bond_type) {
      case 'covalent_single': return 90;
      case 'covalent_double': return 75;
      case 'hydrogen_bond': return 110;
      case 'peptide_backbone': return 130;
      case 'simplex_facet': return 95;
      default: return 180; // Module data-flow port connection
    }
  };

  const kRepulse = 8000;
  const kSpring = 0.05;

  for (let iter = 0; iter < iterations; iter++) {
    const forces = new Map<string, { fx: number; fy: number }>();
    nodes.forEach(n => forces.set(n.id, { fx: 0, fy: 0 }));

    // Repulsion between all node pairs
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const idA = nodes[i].id;
        const idB = nodes[j].id;
        const pA = posMap.get(idA)!;
        const pB = posMap.get(idB)!;

        let dx = pB.x - pA.x;
        let dy = pB.y - pA.y;
        let dist = Math.sqrt(dx * dx + dy * dy) || 1;

        if (dist < 40) dist = 40;
        const repForce = kRepulse / (dist * dist);
        const fx = (dx / dist) * repForce;
        const fy = (dy / dist) * repForce;

        const fA = forces.get(idA)!;
        const fB = forces.get(idB)!;
        fA.fx -= fx;
        fA.fy -= fy;
        fB.fx += fx;
        fB.fy += fy;
      }
    }

    // Attractive spring force along edges / bonds
    edges.forEach((edge) => {
      const pA = posMap.get(edge.source_node);
      const pB = posMap.get(edge.target_node);
      if (!pA || !pB) return;

      const dx = pB.x - pA.x;
      const dy = pB.y - pA.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const ideal = getIdealLength(edge);
      const delta = dist - ideal;
      const springForce = kSpring * delta;

      const fx = (dx / dist) * springForce;
      const fy = (dy / dist) * springForce;

      const fA = forces.get(edge.source_node)!;
      const fB = forces.get(edge.target_node)!;
      fA.fx += fx;
      fA.fy += fy;
      fB.fx -= fx;
      fB.fy -= fy;
    });

    // Apply forces with damping
    const temp = Math.max(0.1, 1 - iter / iterations);
    nodes.forEach(n => {
      const p = posMap.get(n.id)!;
      const f = forces.get(n.id)!;
      p.x += Math.max(-30, Math.min(30, f.fx * temp));
      p.y += Math.max(-30, Math.min(30, f.fy * temp));
    });
  }

  // Find bounding box and offset so coordinates stay positive with margin
  let minX = Infinity;
  let minY = Infinity;
  nodes.forEach(n => {
    const p = posMap.get(n.id)!;
    if (p.x < minX) minX = p.x;
    if (p.y < minY) minY = p.y;
  });

  const offsetX = 80 - minX;
  const offsetY = 80 - minY;

  // Project and snap to the target lattice
  const spacing = LATTICE_CONFIGS[basis]?.defaultSpacing || 60;
  return nodes.map(n => {
    const p = posMap.get(n.id)!;
    const rawX = p.x + offsetX;
    const rawY = p.y + offsetY;
    const [snappedX, snappedY] = snapToLattice(rawX, rawY, basis, spacing);
    return {
      ...n,
      position: [Math.max(40, snappedX), Math.max(40, snappedY)]
    };
  });
}
