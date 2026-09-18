import React, { useState, useRef, useEffect } from 'react';
import { 
  CaceExperiment, 
  GraphNode, 
  GraphEdge, 
  GraphGroup,
  NodeExecutionResult, 
  ModuleDefinition,
  PortDataType,
  TilingBasis,
  Rotation3D,
  GeometricSite,
  BondType,
  AlphaFoldProteinData
} from '../types';
import { CACE_MODULES } from '../data/caceData';
import { GEOMETRIC_CATALOG, createGeometricNode, PRESET_GEOMETRIC_EXPERIMENTS } from '../data/geometryPresets';
import { snapToLattice, relaxCoordinatelessGraph } from '../engine/geometricLattice';
import { Canvas3DControls } from './Canvas3DControls';
import { TilingSelector } from './TilingSelector';
import { GeometryPalette } from './GeometryPalette';
import { ClearCanvasModal } from './ClearCanvasModal';
import { CanvasTilingBackground } from './CanvasTilingBackground';
import { CoordinateSystemFrame } from './CoordinateSystemFrame';
import { AlphaFoldProteinModal } from './AlphaFoldProteinModal';
import { 
  CheckCircle2, 
  XCircle, 
  Plus, 
  Trash2, 
  Maximize2, 
  ZoomIn, 
  ZoomOut,
  Info,
  Map as MapIcon,
  ChevronDown,
  ChevronUp,
  Layers,
  Unlink,
  X,
  Eraser,
  Dna,
  Atom,
  Shapes,
  Sparkles,
  Link2,
  Crosshair,
  Compass,
  Activity
} from 'lucide-react';

interface GraphCanvasProps {
  experiment: CaceExperiment;
  onUpdateExperiment: (exp: CaceExperiment) => void;
  nodeResults: Record<string, NodeExecutionResult>;
  selectedNodeId: string | null;
  onSelectNode: (nodeId: string | null) => void;
  onViewReport: () => void;
}

export const GraphCanvas: React.FC<GraphCanvasProps> = ({
  experiment,
  onUpdateExperiment,
  nodeResults,
  selectedNodeId,
  onSelectNode,
  onViewReport
}) => {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 40, y: 40 });
  const [isPanning, setIsPanning] = useState(false);
  const [panStart, setPanStart] = useState({ x: 0, y: 0 });

  // 3D Canvas Spatial Rotation state
  const [rotation3D, setRotation3D] = useState<Rotation3D>(
    experiment.rotation_3d || { x: 0, y: 0, z: 0 }
  );
  const [isOrbitMode, setIsOrbitMode] = useState(false);
  const [isOrbitDragging, setIsOrbitDragging] = useState(false);
  const [orbitStart, setOrbitStart] = useState({ x: 0, y: 0 });
  const [orbitStartRot, setOrbitStartRot] = useState<Rotation3D>({ x: 0, y: 0, z: 0 });

  // Coordinateless Tiling Basis state
  const [tilingBasis, setTilingBasis] = useState<TilingBasis>(
    experiment.tiling_mode || 'cartesian_square'
  );

  // Clear Canvas modal state
  const [isClearModalOpen, setIsClearModalOpen] = useState(false);

  // Coordinate System Frame & Defined Line Visibility
  const [showCoordinateAxes, setShowCoordinateAxes] = useState(true);
  const [highContrastGrid, setHighContrastGrid] = useState(true);

  // AlphaFold Protein Mathematical Inspector Modal
  const [inspectingAlphaFoldData, setInspectingAlphaFoldData] = useState<AlphaFoldProteinData | null>(null);

  // Dragging node state
  const [draggingNodeId, setDraggingNodeId] = useState<string | null>(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });

  // Standard module Port connecting state
  const [connectingSource, setConnectingSource] = useState<{ nodeId: string; port: string; type: PortDataType } | null>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  // Geometric "Click-to-Connect" state
  const [isClickToConnectActive, setIsClickToConnectActive] = useState(false);
  const [connectingGeoNode, setConnectingGeoNode] = useState<GraphNode | null>(null);
  const [connectingGeoSite, setConnectingGeoSite] = useState<GeometricSite | null>(null);

  // Add node dropdown state
  const [showAddMenu, setShowAddMenu] = useState(false);

  // Minimap state
  const [showMinimap, setShowMinimap] = useState(true);

  // Group modal / management state
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [groupModalTitle, setGroupModalTitle] = useState('');
  const [groupModalColor, setGroupModalColor] = useState<'indigo' | 'emerald' | 'amber' | 'rose' | 'cyan' | 'purple'>('indigo');
  const [groupModalDesc, setGroupModalDesc] = useState('');

  // Pinch-to-zoom touch state
  const touchStateRef = useRef<{
    initialDist: number;
    initialZoom: number;
    initialCenter: { x: number; y: number };
    initialPan: { x: number; y: number };
  } | null>(null);

  const containerRef = useRef<HTMLDivElement>(null);
  const modulesById = new Map(CACE_MODULES.map((m) => [m.module_id, m]));

  // Sync experiment rotation and tiling mode if experiment changes externally
  useEffect(() => {
    if (experiment.tiling_mode && experiment.tiling_mode !== tilingBasis) {
      setTilingBasis(experiment.tiling_mode);
    }
    if (experiment.rotation_3d) {
      setRotation3D(experiment.rotation_3d);
    }
  }, [experiment.tiling_mode, experiment.rotation_3d]);

  const getGroupColorStyles = (color?: string) => {
    switch (color) {
      case 'emerald':
        return {
          border: 'border-emerald-500/40 hover:border-emerald-500/60',
          bg: 'bg-emerald-950/20',
          header: 'bg-emerald-950/80 border-emerald-800/80 text-emerald-300',
          pill: 'bg-emerald-900/60 text-emerald-300 border-emerald-700/60',
          minimap: 'bg-emerald-800/40 border-emerald-500/50'
        };
      case 'cyan':
        return {
          border: 'border-cyan-500/40 hover:border-cyan-500/60',
          bg: 'bg-cyan-950/20',
          header: 'bg-cyan-950/80 border-cyan-800/80 text-cyan-300',
          pill: 'bg-cyan-900/60 text-cyan-300 border-cyan-700/60',
          minimap: 'bg-cyan-800/40 border-cyan-500/50'
        };
      case 'purple':
        return {
          border: 'border-purple-500/40 hover:border-purple-500/60',
          bg: 'bg-purple-950/20',
          header: 'bg-purple-950/80 border-purple-800/80 text-purple-300',
          pill: 'bg-purple-900/60 text-purple-300 border-purple-700/60',
          minimap: 'bg-purple-800/40 border-purple-500/50'
        };
      case 'amber':
        return {
          border: 'border-amber-500/40 hover:border-amber-500/60',
          bg: 'bg-amber-950/20',
          header: 'bg-amber-950/80 border-amber-800/80 text-amber-300',
          pill: 'bg-amber-900/60 text-amber-300 border-amber-700/60',
          minimap: 'bg-amber-800/40 border-amber-500/50'
        };
      case 'rose':
        return {
          border: 'border-rose-500/40 hover:border-rose-500/60',
          bg: 'bg-rose-950/20',
          header: 'bg-rose-950/80 border-rose-800/80 text-rose-300',
          pill: 'bg-rose-900/60 text-rose-300 border-rose-700/60',
          minimap: 'bg-rose-800/40 border-rose-500/50'
        };
      case 'indigo':
      default:
        return {
          border: 'border-indigo-500/40 hover:border-indigo-500/60',
          bg: 'bg-indigo-950/20',
          header: 'bg-indigo-950/80 border-indigo-800/80 text-indigo-300',
          pill: 'bg-indigo-900/60 text-indigo-300 border-indigo-700/60',
          minimap: 'bg-indigo-800/40 border-indigo-500/50'
        };
    }
  };

  const handleCreateOrUpdateGroup = () => {
    if (!selectedNodeId) return;
    const newGroupId = `grp_${Date.now()}`;
    const newGroup: GraphGroup = {
      id: newGroupId,
      title: groupModalTitle.trim() || `Cluster ${((experiment.groups?.length || 0) + 1)}`,
      color: groupModalColor,
      description: groupModalDesc.trim() || undefined,
      node_ids: [selectedNodeId]
    };

    const updatedNodes = experiment.nodes.map(n => 
      n.id === selectedNodeId ? { ...n, group_id: newGroupId } : n
    );
    const updatedGroups = [...(experiment.groups || []), newGroup];

    onUpdateExperiment({
      ...experiment,
      nodes: updatedNodes,
      groups: updatedGroups
    });

    setShowGroupModal(false);
    setGroupModalTitle('');
    setGroupModalDesc('');
  };

  const handleDissolveGroup = (groupId: string) => {
    const updatedNodes = experiment.nodes.map(n => 
      n.group_id === groupId ? { ...n, group_id: undefined } : n
    );
    const updatedGroups = (experiment.groups || []).filter(g => g.id !== groupId);

    onUpdateExperiment({
      ...experiment,
      nodes: updatedNodes,
      groups: updatedGroups
    });
  };

  const handleRemoveNodeFromGroup = (nodeId: string) => {
    const node = experiment.nodes.find(n => n.id === nodeId);
    if (!node || !node.group_id) return;
    const oldGroupId = node.group_id;

    const updatedNodes = experiment.nodes.map(n => 
      n.id === nodeId ? { ...n, group_id: undefined } : n
    );
    
    // Prune empty groups
    const remainingInGroup = updatedNodes.filter(n => n.group_id === oldGroupId);
    const updatedGroups = (experiment.groups || []).filter(g => 
      g.id !== oldGroupId || remainingInGroup.length > 0
    );

    onUpdateExperiment({
      ...experiment,
      nodes: updatedNodes,
      groups: updatedGroups
    });
  };

  const getPortColor = (type: PortDataType) => {
    switch (type) {
      case 'number': return 'bg-cyan-500 border-cyan-400';
      case 'array': return 'bg-emerald-500 border-emerald-400';
      case 'interval': return 'bg-amber-500 border-amber-400';
      case 'bool': return 'bg-purple-500 border-purple-400';
      default: return 'bg-indigo-500 border-indigo-400';
    }
  };

  // Node dimensions & layout constants
  const NODE_WIDTH = 220;
  const HEADER_HEIGHT = 44;
  const PORT_HEIGHT = 24;

  const getNodeHeight = (node: GraphNode) => {
    if (node.geometric) {
      const radius = node.geometric.radius || 28;
      return radius * 2 + 36;
    }
    const mod = modulesById.get(node.module_id);
    if (!mod) return 120;
    const maxPorts = Math.max(mod.inputs.length, mod.outputs.length);
    return Math.max(HEADER_HEIGHT + maxPorts * PORT_HEIGHT + 48, 120);
  };

  const getNodeWidth = (node: GraphNode) => {
    if (node.geometric) {
      const radius = node.geometric.radius || 28;
      return radius * 2 + 56;
    }
    return NODE_WIDTH;
  };

  const getPortCoords = (nodeId: string, portName: string, isOutput: boolean) => {
    const node = experiment.nodes.find((n) => n.id === nodeId);
    if (!node) return { x: 0, y: 0 };

    if (node.geometric) {
      const radius = node.geometric.radius || 28;
      const width = getNodeWidth(node);
      const height = getNodeHeight(node);
      const centerX = node.position[0] + width / 2;
      const centerY = node.position[1] + height / 2;

      const site = node.geometric.sites.find(s => s.id === portName);
      if (site && site.angle_deg !== undefined) {
        const rad = (site.angle_deg * Math.PI) / 180;
        return {
          x: centerX + (radius + 12) * Math.cos(rad),
          y: centerY + (radius + 12) * Math.sin(rad)
        };
      }
      return { x: centerX, y: centerY };
    }

    const mod = modulesById.get(node.module_id);
    if (!mod) return { x: node.position[0], y: node.position[1] };

    const ports = isOutput ? mod.outputs : mod.inputs;
    const index = ports.findIndex((p) => p.name === portName);
    const yOffset = HEADER_HEIGHT + (index >= 0 ? index : 0) * PORT_HEIGHT + 14;

    return {
      x: isOutput ? node.position[0] + NODE_WIDTH : node.position[0],
      y: node.position[1] + yOffset
    };
  };

  // Node drag handlers
  const handleNodeMouseDown = (e: React.MouseEvent, node: GraphNode) => {
    e.stopPropagation();
    onSelectNode(node.id);

    // If click-to-connect mode is active or user is in bonding state
    if (isClickToConnectActive || connectingGeoNode) {
      handleGeometricClickToConnect(node);
      return;
    }

    setDraggingNodeId(node.id);
    setDragOffset({
      x: e.clientX - node.position[0] * zoom - pan.x,
      y: e.clientY - node.position[1] * zoom - pan.y
    });
  };

  // Geometric Click-to-Connect Engine
  const handleGeometricClickToConnect = (targetNode: GraphNode, targetSite?: GeometricSite) => {
    if (!connectingGeoNode) {
      // Set source node
      setConnectingGeoNode(targetNode);
      if (targetSite) setConnectingGeoSite(targetSite);
      return;
    }

    if (connectingGeoNode.id === targetNode.id) {
      // Cancel if clicked same node
      setConnectingGeoNode(null);
      setConnectingGeoSite(null);
      return;
    }

    // Connect source to target!
    const sourceNode = connectingGeoNode;
    const srcSiteId = connectingGeoSite?.id || sourceNode.geometric?.sites[0]?.id || 'v1';
    const tgtSiteId = targetSite?.id || targetNode.geometric?.sites[0]?.id || 'v1';

    // Auto-deduce bond type based on object classes
    let bondType: BondType = 'covalent_single';
    if (sourceNode.geometric?.kind === 'protein_fold' || targetNode.geometric?.kind === 'protein_fold') {
      if ((srcSiteId.includes('term') && tgtSiteId.includes('term')) || (srcSiteId === 'in' || srcSiteId === 'out')) {
        bondType = 'peptide_backbone';
      } else {
        bondType = 'hydrogen_bond';
      }
    } else if (sourceNode.geometric?.subType === 'H2O' || targetNode.geometric?.subType === 'H2O') {
      bondType = 'hydrogen_bond';
    } else if (sourceNode.geometric?.subType === 'C' && targetNode.geometric?.subType === 'C') {
      bondType = 'covalent_double';
    } else if (sourceNode.geometric?.kind === 'simplex' || targetNode.geometric?.kind === 'simplex') {
      bondType = 'simplex_facet';
    }

    const newEdge: GraphEdge = {
      source_node: sourceNode.id,
      source_port: srcSiteId,
      target_node: targetNode.id,
      target_port: tgtSiteId,
      bond_type: bondType
    };

    onUpdateExperiment({
      ...experiment,
      edges: [...experiment.edges, newEdge]
    });

    setConnectingGeoNode(null);
    setConnectingGeoSite(null);
  };

  // Canvas Mouse Down: handles panning or 3D Orbiting
  const handleCanvasMouseDown = (e: React.MouseEvent) => {
    // 3D Orbit trigger: right-click, Alt key, or when isOrbitMode is active
    if (e.button === 2 || e.altKey || isOrbitMode) {
      e.preventDefault();
      setIsOrbitDragging(true);
      setOrbitStart({ x: e.clientX, y: e.clientY });
      setOrbitStartRot({ ...rotation3D });
      return;
    }

    if (e.target === containerRef.current || (e.target as HTMLElement).tagName === 'svg' || (e.target as HTMLElement).tagName === 'rect') {
      setIsPanning(true);
      setPanStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
      onSelectNode(null);
      setConnectingSource(null);
      setConnectingGeoNode(null);
      setConnectingGeoSite(null);
    }
  };

  // Mouse Move: handles panning, node dragging, 3D orbit, and wiring preview
  const handleMouseMove = (e: React.MouseEvent) => {
    if (isOrbitDragging) {
      const dx = e.clientX - orbitStart.x;
      const dy = e.clientY - orbitStart.y;
      const newPitch = Math.max(-85, Math.min(85, orbitStartRot.x - dy * 0.45));
      const newYaw = (orbitStartRot.y + dx * 0.45) % 360;
      setRotation3D({ x: Math.round(newPitch), y: Math.round(newYaw), z: 0 });
      return;
    }

    if (isPanning) {
      setPan({
        x: e.clientX - panStart.x,
        y: e.clientY - panStart.y
      });
    } else if (draggingNodeId) {
      const rawX = Math.round((e.clientX - dragOffset.x - pan.x) / zoom);
      const rawY = Math.round((e.clientY - dragOffset.y - pan.y) / zoom);
      
      const updatedNodes = experiment.nodes.map((node) =>
        node.id === draggingNodeId ? { ...node, position: [rawX, rawY] as [number, number] } : node
      );
      onUpdateExperiment({ ...experiment, nodes: updatedNodes });
    }

    if (connectingSource && containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      setMousePos({
        x: (e.clientX - rect.left - pan.x) / zoom,
        y: (e.clientY - rect.top - pan.y) / zoom
      });
    }
  };

  const handleMouseUp = () => {
    if (isOrbitDragging) {
      setIsOrbitDragging(false);
      onUpdateExperiment({ ...experiment, rotation_3d: rotation3D });
    }

    // Snap released node to active tiling lattice
    if (draggingNodeId) {
      const node = experiment.nodes.find(n => n.id === draggingNodeId);
      if (node) {
        const [snappedX, snappedY] = snapToLattice(node.position[0], node.position[1], tilingBasis);
        const updatedNodes = experiment.nodes.map(n =>
          n.id === draggingNodeId ? { ...n, position: [snappedX, snappedY] as [number, number] } : node
        );
        onUpdateExperiment({ ...experiment, nodes: updatedNodes });
      }
    }

    setIsPanning(false);
    setDraggingNodeId(null);
  };

  // Wheel zoom with cursor focal point preservation
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const container = containerRef.current;
    if (!container) return;

    const rect = container.getBoundingClientRect();
    const cursorX = e.clientX - rect.left;
    const cursorY = e.clientY - rect.top;

    // Zoom delta: smoothly scale by 1.1x / 0.9x
    const zoomMultiplier = e.deltaY < 0 ? 1.12 : 0.89;
    const newZoom = Math.min(3.0, Math.max(0.2, zoom * zoomMultiplier));

    // Maintain focal point at cursor position
    const newPanX = cursorX - (cursorX - pan.x) * (newZoom / zoom);
    const newPanY = cursorY - (cursorY - pan.y) * (newZoom / zoom);

    setZoom(newZoom);
    setPan({ x: Math.round(newPanX), y: Math.round(newPanY) });
  };

  // Touch Pinch-to-Zoom handlers
  const handleTouchStart = (e: React.TouchEvent) => {
    if (e.touches.length === 2) {
      const t1 = e.touches[0];
      const t2 = e.touches[1];
      const dist = Math.hypot(t2.clientX - t1.clientX, t2.clientY - t1.clientY);
      const center = {
        x: (t1.clientX + t2.clientX) / 2,
        y: (t1.clientY + t2.clientY) / 2
      };
      touchStateRef.current = {
        initialDist: dist,
        initialZoom: zoom,
        initialCenter: center,
        initialPan: { ...pan }
      };
    } else if (e.touches.length === 1) {
      const t = e.touches[0];
      setIsPanning(true);
      setPanStart({ x: t.clientX - pan.x, y: t.clientY - pan.y });
    }
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    if (e.touches.length === 2 && touchStateRef.current) {
      e.preventDefault();
      const t1 = e.touches[0];
      const t2 = e.touches[1];
      const currentDist = Math.hypot(t2.clientX - t1.clientX, t2.clientY - t1.clientY);
      const scale = currentDist / touchStateRef.current.initialDist;
      const newZoom = Math.min(3.0, Math.max(0.2, touchStateRef.current.initialZoom * scale));

      const container = containerRef.current;
      if (container) {
        const rect = container.getBoundingClientRect();
        const focalX = touchStateRef.current.initialCenter.x - rect.left;
        const focalY = touchStateRef.current.initialCenter.y - rect.top;

        const newPanX = focalX - (focalX - touchStateRef.current.initialPan.x) * (newZoom / touchStateRef.current.initialZoom);
        const newPanY = focalY - (focalY - touchStateRef.current.initialPan.y) * (newZoom / touchStateRef.current.initialZoom);

        setZoom(newZoom);
        setPan({ x: Math.round(newPanX), y: Math.round(newPanY) });
      }
    } else if (e.touches.length === 1 && isPanning) {
      const t = e.touches[0];
      setPan({
        x: t.clientX - panStart.x,
        y: t.clientY - panStart.y
      });
    }
  };

  const handleTouchEnd = () => {
    touchStateRef.current = null;
    setIsPanning(false);
  };

  // Add standard CACE scientific module
  const handleAddNode = (moduleId: string) => {
    const mod = modulesById.get(moduleId);
    if (!mod) return;
    const newId = `${mod.module_id.split('.').pop()}_${Math.random().toString(36).substring(2, 6)}`;
    const defaultParams: Record<string, any> = {};
    mod.parameters.forEach((p) => {
      defaultParams[p.name] = p.default;
    });

    const [snapX, snapY] = snapToLattice(
      Math.round((-pan.x + 300) / zoom),
      Math.round((-pan.y + 200) / zoom),
      tilingBasis
    );

    const newNode: GraphNode = {
      id: newId,
      module_id: mod.module_id,
      label: mod.name,
      params: defaultParams,
      position: [snapX, snapY]
    };

    onUpdateExperiment({
      ...experiment,
      nodes: [...experiment.nodes, newNode]
    });
    onSelectNode(newId);
    setShowAddMenu(false);
  };

  // Add Geometric Object (Atom, Molecule, Protein Fold, Simplex)
  const handleAddGeometricNode = (catalogKey: string) => {
    const newId = `geo_${catalogKey.replace('.', '_')}_${Math.random().toString(36).substring(2, 6)}`;
    const [snapX, snapY] = snapToLattice(
      Math.round((-pan.x + 320) / zoom),
      Math.round((-pan.y + 220) / zoom),
      tilingBasis
    );

    const newNode = createGeometricNode(catalogKey, newId, [snapX, snapY]);
    onUpdateExperiment({
      ...experiment,
      nodes: [...experiment.nodes, newNode]
    });
    onSelectNode(newId);
  };

  // Delete selected node
  const handleDeleteSelected = () => {
    if (!selectedNodeId) return;
    const remainingNodes = experiment.nodes.filter((n) => n.id !== selectedNodeId);
    const remainingEdges = experiment.edges.filter(
      (e) => e.source_node !== selectedNodeId && e.target_node !== selectedNodeId
    );
    onUpdateExperiment({
      ...experiment,
      nodes: remainingNodes,
      edges: remainingEdges
    });
    onSelectNode(null);
  };

  // Clear Canvas handler
  const handleClearCanvas = () => {
    onUpdateExperiment({
      ...experiment,
      nodes: [],
      edges: [],
      groups: []
    });
    onSelectNode(null);
    setConnectingSource(null);
    setConnectingGeoNode(null);
  };

  // Auto-Map Coordinateless Interaction Graph to Lattice
  const handleAutoMapToLattice = () => {
    const relaxed = relaxCoordinatelessGraph(
      experiment.nodes,
      experiment.edges,
      tilingBasis
    );
    onUpdateExperiment({
      ...experiment,
      nodes: relaxed,
      tiling_mode: tilingBasis
    });
  };

  // Standard module Port click handler
  const handlePortClick = (e: React.MouseEvent, nodeId: string, portName: string, isOutput: boolean, type: PortDataType) => {
    e.stopPropagation();
    if (isOutput) {
      setConnectingSource({ nodeId, port: portName, type });
    } else if (connectingSource) {
      if (connectingSource.nodeId === nodeId) {
        setConnectingSource(null);
        return;
      }
      const existingFiltered = experiment.edges.filter(
        (e) => !(e.target_node === nodeId && e.target_port === portName)
      );
      const newEdge: GraphEdge = {
        source_node: connectingSource.nodeId,
        source_port: connectingSource.port,
        target_node: nodeId,
        target_port: portName,
        bond_type: 'data_flow'
      };
      onUpdateExperiment({
        ...experiment,
        edges: [...existingFiltered, newEdge]
      });
      setConnectingSource(null);
    }
  };

  const handleDeleteEdge = (e: React.MouseEvent, edgeIndex: number) => {
    e.stopPropagation();
    const updated = experiment.edges.filter((_, i) => i !== edgeIndex);
    onUpdateExperiment({ ...experiment, edges: updated });
  };

  return (
    <div 
      id="cace-graph-editor" 
      ref={containerRef}
      onMouseDown={handleCanvasMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onWheel={handleWheel}
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
      onContextMenu={(e) => {
        if (isOrbitMode || e.altKey) e.preventDefault();
      }}
      className={`relative w-full h-[calc(100vh-4rem)] bg-neutral-950 overflow-hidden select-none ${
        isOrbitDragging || isOrbitMode ? 'cursor-grab active:cursor-grabbing' : isPanning ? 'cursor-grabbing' : 'cursor-default'
      }`}
      style={{
        perspective: '1200px',
        perspectiveOrigin: '50% 50%'
      }}
    >
      {/* Background Tiling Lattice (Coordinateless Translation Base: Square, Hex, Eisenstein ω, Dragon) */}
      <CanvasTilingBackground
        basis={tilingBasis}
        zoom={zoom}
        pan={pan}
        highContrast={highContrastGrid}
      />

      {/* Top Floating Main Toolbar */}
      <div className="absolute top-4 left-4 z-20 flex flex-wrap items-center gap-2">
        {/* Module & Node Action Group */}
        <div className="bg-neutral-900/90 border border-neutral-800 rounded-lg p-1.5 flex items-center gap-1 shadow-lg backdrop-blur-md">
          {/* Add Module Button */}
          <div className="relative">
            <button
              id="btn-add-node-menu"
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setShowAddMenu(!showAddMenu);
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-xs transition-colors"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Add Module</span>
            </button>

            {showAddMenu && (
              <div 
                id="add-module-dropdown"
                className="absolute top-full mt-2 left-0 w-64 bg-neutral-900 border border-neutral-800 rounded-lg shadow-2xl p-2 z-40 max-h-80 overflow-y-auto"
                onClick={(e) => e.stopPropagation()}
              >
                <div className="text-[10px] uppercase font-mono text-neutral-400 font-semibold px-2 py-1">Available CACE Modules</div>
                {CACE_MODULES.map((mod) => (
                  <button
                    key={mod.module_id}
                    type="button"
                    onClick={() => handleAddNode(mod.module_id)}
                    className="w-full text-left p-2 rounded hover:bg-neutral-800/80 transition-colors flex flex-col gap-0.5"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-medium text-white">{mod.name}</span>
                      <span className="text-[9px] font-mono px-1 rounded bg-neutral-800 text-neutral-400 border border-neutral-700">
                        {mod.category}
                      </span>
                    </div>
                    <span className="text-[10px] text-neutral-400 font-mono truncate">{mod.module_id}</span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Delete Selected Node */}
          {selectedNodeId && (
            <button
              id="btn-delete-node"
              type="button"
              onClick={handleDeleteSelected}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-md bg-rose-950/60 border border-rose-800/60 hover:bg-rose-900/60 text-rose-300 text-xs font-medium transition-colors"
              title="Delete selected item"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Delete</span>
            </button>
          )}

          {/* Group / Cluster Controls */}
          {selectedNodeId && (
            (() => {
              const selectedNode = experiment.nodes.find(n => n.id === selectedNodeId);
              const inGroup = selectedNode?.group_id ? experiment.groups?.find(g => g.id === selectedNode.group_id) : null;
              
              if (inGroup) {
                return (
                  <button
                    id="btn-remove-from-group"
                    type="button"
                    onClick={() => handleRemoveNodeFromGroup(selectedNodeId)}
                    className="flex items-center gap-1 px-2.5 py-1.5 rounded-md bg-amber-950/60 border border-amber-800/60 hover:bg-amber-900/60 text-amber-300 text-xs font-medium transition-colors"
                    title={`Remove from cluster "${inGroup.title}"`}
                  >
                    <Unlink className="w-3.5 h-3.5" />
                    <span>Leave Cluster</span>
                  </button>
                );
              }

              return (
                <button
                  id="btn-open-create-group"
                  type="button"
                  onClick={() => setShowGroupModal(true)}
                  className="flex items-center gap-1 px-2.5 py-1.5 rounded-md bg-indigo-950/70 border border-indigo-800/70 hover:bg-indigo-900/70 text-indigo-300 text-xs font-medium transition-colors"
                  title="Group selected node into a cluster"
                >
                  <Layers className="w-3.5 h-3.5" />
                  <span>Cluster Node</span>
                </button>
              );
            })()
          )}

          <div className="h-4 w-px bg-neutral-800 mx-1" />

          {/* Clear Canvas Button */}
          <button
            id="btn-clear-canvas"
            type="button"
            onClick={() => setIsClearModalOpen(true)}
            className="flex items-center gap-1 px-2 py-1.5 rounded-md text-neutral-400 hover:text-rose-300 hover:bg-rose-950/30 transition-colors"
            title="Clear canvas (remove all nodes and edges)"
          >
            <Eraser className="w-3.5 h-3.5 text-rose-400" />
            <span className="text-xs">Clear Canvas</span>
          </button>

          <div className="h-4 w-px bg-neutral-800 mx-1" />

          {/* Zoom controls */}
          <button
            type="button"
            onClick={() => setZoom((z) => Math.min(3, z + 0.15))}
            className="p-1.5 rounded text-neutral-400 hover:text-white hover:bg-neutral-800 transition-colors"
            title="Zoom In (or scroll up / pinch)"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <span className="text-[11px] font-mono text-neutral-400 w-10 text-center">
            {Math.round(zoom * 100)}%
          </span>
          <button
            type="button"
            onClick={() => setZoom((z) => Math.max(0.2, z - 0.15))}
            className="p-1.5 rounded text-neutral-400 hover:text-white hover:bg-neutral-800 transition-colors"
            title="Zoom Out (or scroll down / pinch)"
          >
            <ZoomOut className="w-4 h-4" />
          </button>
          <button
            type="button"
            onClick={() => { setZoom(1); setPan({ x: 40, y: 40 }); }}
            className="p-1.5 rounded text-neutral-400 hover:text-white hover:bg-neutral-800 transition-colors"
            title="Reset Pan & Zoom"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
        </div>

        {/* 3D Canvas Spatial Rotation Controls */}
        <Canvas3DControls
          rotation={rotation3D}
          onChangeRotation={(rot) => {
            setRotation3D(rot);
            onUpdateExperiment({ ...experiment, rotation_3d: rot });
          }}
          isOrbitMode={isOrbitMode}
          onToggleOrbitMode={() => setIsOrbitMode(!isOrbitMode)}
        />

        {/* Coordinateless Tiling Basis Selector */}
        <TilingSelector
          currentBasis={tilingBasis}
          onChangeBasis={(b) => {
            setTilingBasis(b);
            onUpdateExperiment({ ...experiment, tiling_mode: b });
          }}
          onRelaxGraph={handleAutoMapToLattice}
        />

        {/* Mathematical & Molecular Geometries Palette */}
        <GeometryPalette
          onAddGeometricNode={handleAddGeometricNode}
          onLoadPreset={(preset) => {
            onUpdateExperiment(preset);
            onSelectNode(null);
          }}
          isClickToConnectActive={isClickToConnectActive}
          onToggleClickToConnect={() => {
            setIsClickToConnectActive(!isClickToConnectActive);
            setConnectingGeoNode(null);
            setConnectingGeoSite(null);
          }}
          connectingSourceNode={connectingGeoNode}
          onCancelConnection={() => {
            setConnectingGeoNode(null);
            setConnectingGeoSite(null);
          }}
        />

        {/* Defined Coordinate System Controls */}
        <div className="bg-neutral-900/90 border border-neutral-800 rounded-lg p-1 flex items-center gap-1 shadow-lg backdrop-blur-md text-xs">
          <button
            id="btn-toggle-coordinate-axes"
            type="button"
            onClick={() => setShowCoordinateAxes(!showCoordinateAxes)}
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md font-medium text-xs transition-colors ${
              showCoordinateAxes
                ? 'bg-rose-950/80 border border-rose-700/80 text-rose-300 font-semibold'
                : 'text-neutral-400 hover:text-white hover:bg-neutral-800'
            }`}
            title="Toggle high-definition coordinate axes (+X, +Y, +Z) and Origin (0,0,0)"
          >
            <Crosshair className={`w-3.5 h-3.5 ${showCoordinateAxes ? 'text-rose-400' : 'text-neutral-400'}`} />
            <span>{showCoordinateAxes ? 'Axes: ON' : 'Axes: OFF'}</span>
          </button>

          <button
            id="btn-toggle-high-contrast-grid"
            type="button"
            onClick={() => setHighContrastGrid(!highContrastGrid)}
            className={`flex items-center gap-1 px-2 py-1.5 rounded-md font-medium text-[11px] transition-colors ${
              highContrastGrid
                ? 'bg-indigo-950/80 border border-indigo-700/80 text-indigo-300'
                : 'text-neutral-400 hover:text-white hover:bg-neutral-800'
            }`}
            title="Toggle High-Contrast Defined Grid Lines"
          >
            <span>{highContrastGrid ? 'High-Def Grid' : 'Subtle Grid'}</span>
          </button>
        </div>

        {/* Experiment info pill */}
        <div className="bg-neutral-900/90 border border-neutral-800 rounded-lg px-3 py-1.5 flex items-center gap-2 shadow-lg backdrop-blur-md">
          <span className="text-xs font-semibold text-neutral-200">{experiment.name}</span>
          <span className="text-[10px] font-mono text-neutral-500">
            ({experiment.nodes.length} nodes, {experiment.edges.length} edges)
          </span>
        </div>
      </div>

      {/* 3D Spatial Canvas Layer: transformed via 3D Perspective + Scale + Pan + Rotation */}
      <div
        id="cace-canvas-3d-stage"
        className="absolute inset-0 w-full h-full pointer-events-none"
        style={{
          transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom}) rotateX(${rotation3D.x}deg) rotateY(${rotation3D.y}deg) rotateZ(${rotation3D.z}deg)`,
          transformOrigin: '0 0',
          transformStyle: 'preserve-3d',
          transition: isOrbitDragging ? 'none' : 'transform 0.15s cubic-bezier(0.2, 0, 0, 1)'
        }}
      >
        {/* SVG Canvas for Connections / Chemical Bonds */}
        <svg 
          className="absolute inset-0 pointer-events-none overflow-visible w-full h-full"
          style={{ transformStyle: 'preserve-3d' }}
        >
          <defs>
            <marker id="edge-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M 0 1 L 10 5 L 0 9 z" fill="#6366f1" />
            </marker>
            <filter id="glow-cyan" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* Defined Coordinate System Frame (Origin, +X, +Y, +Z, Ticks & Coordinates) */}
          <CoordinateSystemFrame
            rotation3D={rotation3D}
            visible={showCoordinateAxes}
          />

          {/* Existing Edges & Chemical Bonds */}
          {experiment.edges.map((edge, idx) => {
            const p1 = getPortCoords(edge.source_node, edge.source_port, true);
            const p2 = getPortCoords(edge.target_node, edge.target_port, false);
            const bondType = edge.bond_type || 'data_flow';

            // Double Covalent Bond (parallel lines)
            if (bondType === 'covalent_double') {
              const dx = p2.x - p1.x;
              const dy = p2.y - p1.y;
              const len = Math.sqrt(dx * dx + dy * dy) || 1;
              const nx = (-dy / len) * 4;
              const ny = (dx / len) * 4;

              return (
                <g key={`${edge.source_node}-${edge.target_node}-${idx}`} className="pointer-events-auto group">
                  <line
                    x1={p1.x + nx}
                    y1={p1.y + ny}
                    x2={p2.x + nx}
                    y2={p2.y + ny}
                    stroke="#38bdf8"
                    strokeWidth="3"
                    strokeLinecap="round"
                    className="transition-colors group-hover:stroke-cyan-300"
                  />
                  <line
                    x1={p1.x - nx}
                    y1={p1.y - ny}
                    x2={p2.x - nx}
                    y2={p2.y - ny}
                    stroke="#38bdf8"
                    strokeWidth="3"
                    strokeLinecap="round"
                    className="transition-colors group-hover:stroke-cyan-300"
                  />
                  {/* Delete trigger */}
                  <circle
                    cx={(p1.x + p2.x) / 2}
                    cy={(p1.y + p2.y) / 2}
                    r="8"
                    fill="#18181b"
                    stroke="#ef4444"
                    strokeWidth="1.5"
                    className="opacity-0 group-hover:opacity-100 cursor-pointer transition-opacity"
                    onClick={(e) => handleDeleteEdge(e, idx)}
                  />
                </g>
              );
            }

            // Hydrogen Bond (cyan dashed with glowing pulses)
            if (bondType === 'hydrogen_bond') {
              return (
                <g key={`${edge.source_node}-${edge.target_node}-${idx}`} className="pointer-events-auto group">
                  <line
                    x1={p1.x}
                    y1={p1.y}
                    x2={p2.x}
                    y2={p2.y}
                    stroke="#06b6d4"
                    strokeWidth="2.5"
                    strokeDasharray="5,5"
                    className="animate-pulse group-hover:stroke-cyan-300 transition-colors"
                  />
                  <circle
                    cx={(p1.x + p2.x) / 2}
                    cy={(p1.y + p2.y) / 2}
                    r="7"
                    fill="#083344"
                    stroke="#06b6d4"
                    strokeWidth="1"
                    className="opacity-0 group-hover:opacity-100 cursor-pointer transition-opacity"
                    onClick={(e) => handleDeleteEdge(e, idx)}
                  />
                </g>
              );
            }

            // Peptide Backbone Ribbon
            if (bondType === 'peptide_backbone') {
              const midX = (p1.x + p2.x) / 2;
              const midY = (p1.y + p2.y) / 2;
              const pathD = `M ${p1.x} ${p1.y} Q ${midX + 15} ${midY - 15}, ${p2.x} ${p2.y}`;

              return (
                <g key={`${edge.source_node}-${edge.target_node}-${idx}`} className="pointer-events-auto group">
                  <path
                    d={pathD}
                    fill="none"
                    stroke="#a855f7"
                    strokeWidth="5"
                    strokeLinecap="round"
                    className="group-hover:stroke-purple-400 transition-colors"
                  />
                  <circle
                    cx={midX}
                    cy={midY}
                    r="8"
                    fill="#3b0764"
                    stroke="#a855f7"
                    strokeWidth="1.5"
                    className="opacity-0 group-hover:opacity-100 cursor-pointer transition-opacity"
                    onClick={(e) => handleDeleteEdge(e, idx)}
                  />
                </g>
              );
            }

            // Simplex facet / single covalent bond
            if (bondType === 'covalent_single' || bondType === 'simplex_facet') {
              const strokeColor = bondType === 'simplex_facet' ? '#f59e0b' : '#38bdf8';
              return (
                <g key={`${edge.source_node}-${edge.target_node}-${idx}`} className="pointer-events-auto group">
                  <line
                    x1={p1.x}
                    y1={p1.y}
                    x2={p2.x}
                    y2={p2.y}
                    stroke={strokeColor}
                    strokeWidth="3.5"
                    strokeLinecap="round"
                    className="group-hover:opacity-80 transition-opacity"
                  />
                  <circle
                    cx={(p1.x + p2.x) / 2}
                    cy={(p1.y + p2.y) / 2}
                    r="7"
                    fill="#18181b"
                    stroke="#ef4444"
                    strokeWidth="1.5"
                    className="opacity-0 group-hover:opacity-100 cursor-pointer transition-opacity"
                    onClick={(e) => handleDeleteEdge(e, idx)}
                  />
                </g>
              );
            }

            // Standard CACE module data-flow edge (cubic bezier)
            const dx = Math.abs(p2.x - p1.x) * 0.5;
            const pathD = `M ${p1.x} ${p1.y} C ${p1.x + dx} ${p1.y}, ${p2.x - dx} ${p2.y}, ${p2.x} ${p2.y}`;

            return (
              <g key={`${edge.source_node}-${edge.target_node}-${idx}`} className="pointer-events-auto group">
                <path
                  d={pathD}
                  fill="none"
                  stroke="#6366f1"
                  strokeWidth="2.5"
                  markerEnd="url(#edge-arrow)"
                  className="transition-colors group-hover:stroke-indigo-400"
                />
                <circle
                  cx={(p1.x + p2.x) / 2}
                  cy={(p1.y + p2.y) / 2}
                  r="7"
                  fill="#18181b"
                  stroke="#ef4444"
                  strokeWidth="1.5"
                  className="opacity-0 group-hover:opacity-100 cursor-pointer transition-opacity"
                  onClick={(e) => handleDeleteEdge(e, idx)}
                />
              </g>
            );
          })}

          {/* Active Standard Port Drag Line */}
          {connectingSource && (
            <line
              x1={getPortCoords(connectingSource.nodeId, connectingSource.port, true).x}
              y1={getPortCoords(connectingSource.nodeId, connectingSource.port, true).y}
              x2={mousePos.x}
              y2={mousePos.y}
              stroke="#818cf8"
              strokeWidth="2"
              strokeDasharray="4 4"
            />
          )}

          {/* Active Geometric Click-to-Connect Preview */}
          {connectingGeoNode && (
            <circle
              cx={connectingGeoNode.position[0] + getNodeWidth(connectingGeoNode) / 2}
              cy={connectingGeoNode.position[1] + getNodeHeight(connectingGeoNode) / 2}
              r={(connectingGeoNode.geometric?.radius || 28) + 18}
              fill="none"
              stroke="#f59e0b"
              strokeWidth="2"
              strokeDasharray="4 4"
              className="animate-spin"
            />
          )}
        </svg>

        {/* Subgraph Clusters Containers */}
        {(experiment.groups || []).map((grp) => {
          const groupNodes = experiment.nodes.filter(n => grp.node_ids.includes(n.id));
          if (groupNodes.length === 0) return null;

          const minX = Math.min(...groupNodes.map(n => n.position[0])) - 18;
          const maxX = Math.max(...groupNodes.map(n => n.position[0] + getNodeWidth(n))) + 18;
          const minY = Math.min(...groupNodes.map(n => n.position[1])) - 38;
          const maxY = Math.max(...groupNodes.map(n => n.position[1] + getNodeHeight(n))) + 18;
          const width = maxX - minX;
          const height = maxY - minY;

          const styles = getGroupColorStyles(grp.color);

          return (
            <div
              key={grp.id}
              id={`group-${grp.id}`}
              className={`absolute rounded-2xl border-2 border-dashed ${styles.border} ${styles.bg} transition-all pointer-events-auto shadow-sm`}
              style={{
                left: `${minX}px`,
                top: `${minY}px`,
                width: `${width}px`,
                height: `${height}px`,
                transform: 'translateZ(5px)'
              }}
            >
              {/* Group Header Badge */}
              <div className="absolute -top-3.5 left-4 flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-neutral-900 border border-neutral-700/80 shadow-md">
                <Layers className="w-3 h-3 text-indigo-400" />
                <span className="text-[11px] font-bold text-neutral-200 tracking-wide">{grp.title}</span>
                <span className={`text-[9px] font-mono px-1.5 py-0.2 rounded font-semibold ${styles.pill}`}>
                  {groupNodes.length} nodes
                </span>
                {grp.description && (
                  <span className="text-[10px] text-neutral-400 max-w-[200px] truncate border-l border-neutral-700 pl-1.5 ml-0.5">
                    {grp.description}
                  </span>
                )}
                <button
                  type="button"
                  onClick={() => handleDissolveGroup(grp.id)}
                  className="ml-1 p-0.5 text-neutral-500 hover:text-rose-400 rounded transition-colors"
                  title="Dissolve cluster group"
                >
                  <Trash2 className="w-2.5 h-2.5" />
                </button>
              </div>
            </div>
          );
        })}

        {/* Graph Nodes (Both Standard CACE Modules and Geometric Objects) */}
        {experiment.nodes.map((node) => {
          const isSelected = selectedNodeId === node.id;
          const isConnectingSource = connectingGeoNode?.id === node.id;

          // RENDER GEOMETRIC / MATHEMATICAL OBJECT (Atom, Molecule, Protein Fold, Simplex)
          if (node.geometric) {
            const meta = node.geometric;
            const radius = meta.radius || 28;
            const width = getNodeWidth(node);
            const height = getNodeHeight(node);
            const centerX = width / 2;
            const centerY = height / 2;

            return (
              <div
                key={node.id}
                id={`geo-node-${node.id}`}
                onMouseDown={(e) => handleNodeMouseDown(e, node)}
                className={`absolute pointer-events-auto select-none cursor-move transition-transform ${
                  isSelected ? 'z-30 scale-105' : 'z-20'
                }`}
                style={{
                  left: `${node.position[0]}px`,
                  top: `${node.position[1]}px`,
                  width: `${width}px`,
                  height: `${height}px`,
                  transform: 'translateZ(20px)'
                }}
              >
                {/* Central Orb / Shape */}
                <div
                  className={`w-full h-full rounded-2xl flex flex-col items-center justify-center p-2 border transition-all backdrop-blur-md relative ${
                    isSelected
                      ? 'ring-2 ring-emerald-400 shadow-xl'
                      : isConnectingSource
                      ? 'ring-2 ring-amber-400 animate-pulse'
                      : 'border-neutral-800 hover:border-neutral-600'
                  }`}
                  style={{
                    backgroundColor: `${meta.color}15`,
                    borderColor: isSelected ? meta.color : undefined
                  }}
                >
                  {/* Central Symbol */}
                  <div
                    className="w-12 h-12 rounded-full flex items-center justify-center font-black font-mono text-sm shadow-md border-2"
                    style={{
                      backgroundColor: `${meta.color}30`,
                      borderColor: meta.color,
                      color: meta.color
                    }}
                  >
                    {meta.kind === 'atom' ? (
                      <span className="text-base">{meta.subType}</span>
                    ) : meta.kind === 'protein_fold' ? (
                      <Dna className="w-5 h-5" />
                    ) : meta.kind === 'alphafold_protein' ? (
                      <div className="flex flex-col items-center justify-center leading-none">
                        <Dna className="w-5 h-5 text-cyan-400 animate-pulse" />
                        <span className="text-[7px] font-black text-cyan-300 uppercase mt-0.5">AFDB</span>
                      </div>
                    ) : meta.kind === 'simplex' ? (
                      <Shapes className="w-5 h-5" />
                    ) : (
                      <span className="text-xs">{meta.subType}</span>
                    )}
                  </div>

                  {/* Title Label */}
                  <span className="text-[10px] font-bold text-neutral-200 mt-1 truncate max-w-full text-center">
                    {node.label || meta.subType}
                  </span>

                  {/* AlphaFold Differential Math / Topological Metrics Inspector Trigger */}
                  {meta.alphafold && (
                    <div className="flex flex-col items-center gap-0.5 mt-0.5 w-full">
                      <div className="flex items-center gap-1">
                        <span className="px-1.5 py-0.2 rounded text-[8px] font-mono font-bold bg-cyan-950/90 text-cyan-300 border border-cyan-800/80">
                          {meta.alphafold.mean_plddt.toFixed(0)}% pLDDT
                        </span>
                        <span className="px-1 py-0.2 rounded text-[8px] font-mono text-neutral-400 bg-neutral-900 border border-neutral-800">
                          {meta.alphafold.residue_count}aa
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setInspectingAlphaFoldData(meta.alphafold || null);
                        }}
                        className="px-2 py-0.5 rounded bg-cyan-600 hover:bg-cyan-500 text-[8px] font-bold uppercase tracking-wider text-white shadow-xs transition-colors flex items-center gap-1 pointer-events-auto mt-0.5"
                        title="Open Differential Space Curve & Topological Invariants Viewer"
                      >
                        <Activity className="w-2.5 h-2.5" />
                        <span>3D Math</span>
                      </button>
                    </div>
                  )}

                  {/* Bonding / Interaction Valence Sites orbiting around the object */}
                  {meta.sites.map((site) => {
                    const angleDeg = site.angle_deg ?? 0;
                    const rad = (angleDeg * Math.PI) / 180;
                    const siteX = centerX + (radius + 12) * Math.cos(rad);
                    const siteY = centerY + (radius + 12) * Math.sin(rad);

                    return (
                      <div
                        key={site.id}
                        id={`site-${node.id}-${site.id}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleGeometricClickToConnect(node, site);
                        }}
                        className={`absolute w-5 h-5 -ml-2.5 -mt-2.5 rounded-full flex items-center justify-center text-[8px] font-mono font-bold cursor-pointer transition-transform hover:scale-130 shadow-md ${
                          site.kind === 'hydrogen_donor' || site.kind === 'hydrogen_acceptor'
                            ? 'bg-cyan-600 text-cyan-100 border border-cyan-400'
                            : site.kind === 'n_term' || site.kind === 'c_term'
                            ? 'bg-purple-600 text-purple-100 border border-purple-400'
                            : 'bg-emerald-600 text-emerald-100 border border-emerald-400'
                        }`}
                        style={{
                          left: `${siteX}px`,
                          top: `${siteY}px`
                        }}
                        title={`Site: ${site.label} (${site.kind}) - Click to connect`}
                      >
                        {site.label.slice(0, 2)}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          }

          // RENDER STANDARD CACE COMPUTATIONAL MODULE NODE
          const mod = modulesById.get(node.module_id);
          const result = nodeResults[node.id];
          const height = getNodeHeight(node);

          return (
            <div
              key={node.id}
              id={`node-${node.id}`}
              onMouseDown={(e) => handleNodeMouseDown(e, node)}
              className={`absolute pointer-events-auto rounded-xl border bg-neutral-900/95 shadow-xl transition-shadow select-none cursor-move ${
                isSelected
                  ? 'border-indigo-500 ring-2 ring-indigo-500/30 shadow-indigo-500/20 z-30'
                  : 'border-neutral-800 hover:border-neutral-700 z-10'
              }`}
              style={{
                left: `${node.position[0]}px`,
                top: `${node.position[1]}px`,
                width: `${NODE_WIDTH}px`,
                height: `${height}px`,
                transform: 'translateZ(15px)'
              }}
            >
              {/* Node Header */}
              <div className="h-11 px-3 border-b border-neutral-800/80 flex items-center justify-between rounded-t-xl bg-neutral-950/60">
                <div className="flex flex-col">
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs font-bold text-neutral-100 truncate max-w-[120px]">
                      {node.label || mod?.name || node.id}
                    </span>
                    {node.group_id && (() => {
                      const grp = experiment.groups?.find(g => g.id === node.group_id);
                      if (!grp) return null;
                      const styles = getGroupColorStyles(grp.color);
                      return (
                        <span className={`text-[8px] font-mono px-1 py-0.2 rounded border font-semibold truncate max-w-[65px] ${styles.pill}`} title={`Cluster: ${grp.title}`}>
                          {grp.title}
                        </span>
                      );
                    })()}
                  </div>
                  <span className="text-[9px] font-mono text-neutral-500 truncate max-w-[130px]">
                    {node.module_id}
                  </span>
                </div>

                {/* Status Indicator */}
                {result ? (
                  <div className="flex items-center gap-1">
                    {result.state === 'SUCCESS' && (
                      <span className="flex items-center gap-0.5 text-[9px] font-mono px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800/60">
                        <CheckCircle2 className="w-2.5 h-2.5" />
                        <span>{result.execution_time_ms}ms</span>
                      </span>
                    )}
                    {result.state === 'FAIL' && (
                      <span className="flex items-center gap-0.5 text-[9px] font-mono px-1.5 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800/60" title={result.error}>
                        <XCircle className="w-2.5 h-2.5" />
                        <span>ERR</span>
                      </span>
                    )}
                  </div>
                ) : (
                  <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-neutral-800 text-neutral-400 border border-neutral-700">
                    IDLE
                  </span>
                )}
              </div>

              {/* Ports Area */}
              <div className="p-2 relative flex justify-between gap-2 text-[10px]">
                {/* Inputs Column */}
                <div className="flex flex-col gap-1.5 flex-1">
                  {mod?.inputs.map((port) => (
                    <div 
                      key={port.name}
                      onClick={(e) => handlePortClick(e, node.id, port.name, false, port.type)}
                      className="flex items-center gap-1.5 group cursor-pointer"
                    >
                      <div className={`w-2.5 h-2.5 rounded-full border ${getPortColor(port.type)} transition-transform group-hover:scale-125`} />
                      <span className="font-mono text-neutral-300 group-hover:text-white transition-colors">
                        {port.name}
                      </span>
                    </div>
                  ))}
                </div>

                {/* Outputs Column */}
                <div className="flex flex-col gap-1.5 flex-1 items-end">
                  {mod?.outputs.map((port) => (
                    <div 
                      key={port.name}
                      onClick={(e) => handlePortClick(e, node.id, port.name, true, port.type)}
                      className="flex items-center gap-1.5 group cursor-pointer"
                    >
                      <span className="font-mono text-neutral-300 group-hover:text-white transition-colors">
                        {port.name}
                      </span>
                      <div className={`w-2.5 h-2.5 rounded-full border ${getPortColor(port.type)} transition-transform group-hover:scale-125`} />
                    </div>
                  ))}
                </div>
              </div>

              {/* Bottom Quick Output Preview */}
              {result && result.state === 'SUCCESS' && Object.keys(result.outputs).length > 0 && (
                <div className="absolute bottom-2 left-2 right-2 px-2 py-1 rounded bg-neutral-950/80 border border-neutral-800/80 text-[9px] font-mono text-neutral-400 truncate">
                  {Object.entries(result.outputs).map(([k, v]) => (
                    <span key={k}>
                      {k}: <strong className="text-neutral-200">{Array.isArray(v) ? `[${v.length} pts]` : typeof v === 'number' ? v.toFixed(3) : String(v)}</strong>
                    </span>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Floating Instructions Banner at bottom */}
      <div className="absolute bottom-4 left-4 z-10 bg-neutral-900/90 border border-neutral-800 rounded-lg px-3 py-2 text-[11px] text-neutral-400 flex flex-wrap items-center gap-3 shadow-lg backdrop-blur-md">
        <div className="flex items-center gap-1.5">
          <Info className="w-3.5 h-3.5 text-cyan-400" />
          <span>
            <strong>Scroll / Pinch</strong> to zoom. <strong>Hold Alt or Right-Click</strong> to 3D Orbit. <strong>Click-to-Connect</strong> atoms, molecules & protein folds.
          </span>
        </div>
        <div className="flex items-center gap-2 border-l border-neutral-800 pl-2">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-cyan-500" /> Covalent</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-teal-400" /> H-Bond</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-purple-500" /> Peptide</span>
        </div>
      </div>

      {/* Floating Interactive Minimap at bottom right */}
      <div className="absolute bottom-4 right-4 z-10 flex flex-col items-end">
        {showMinimap ? (
          <div
            id="cace-minimap-container"
            className="bg-neutral-900/95 border border-neutral-800 rounded-xl p-2.5 shadow-2xl backdrop-blur-md flex flex-col"
          >
            <div className="flex items-center justify-between pb-1.5 mb-1.5 border-b border-neutral-800/80">
              <div className="flex items-center gap-1.5">
                <MapIcon className="w-3.5 h-3.5 text-indigo-400" />
                <span className="text-[11px] font-bold text-neutral-300 uppercase tracking-wider font-mono">
                  Minimap
                </span>
              </div>
              <button
                type="button"
                onClick={() => setShowMinimap(false)}
                className="p-0.5 rounded text-neutral-500 hover:text-neutral-300 transition-colors"
                title="Collapse Minimap"
              >
                <ChevronDown className="w-3 h-3" />
              </button>
            </div>

            {(() => {
              const MAP_W = 160;
              const MAP_H = 110;

              const xs = experiment.nodes.map(n => n.position[0]);
              const ys = experiment.nodes.map(n => n.position[1]);

              const minGraphX = xs.length ? Math.min(...xs, 0) : 0;
              const maxGraphX = xs.length ? Math.max(...xs, 800) + NODE_WIDTH : 1000;
              const minGraphY = ys.length ? Math.min(...ys, 0) : 0;
              const maxGraphY = ys.length ? Math.max(...ys, 600) + 150 : 800;

              const spanX = Math.max(maxGraphX - minGraphX, 600);
              const spanY = Math.max(maxGraphY - minGraphY, 400);

              const scaleX = MAP_W / spanX;
              const scaleY = MAP_H / spanY;
              const scale = Math.min(scaleX, scaleY);

              const offsetX = (MAP_W - spanX * scale) / 2;
              const offsetY = (MAP_H - spanY * scale) / 2;

              const toMinimapX = (worldX: number) => (worldX - minGraphX) * scale + offsetX;
              const toMinimapY = (worldY: number) => (worldY - minGraphY) * scale + offsetY;

              const viewW = containerRef.current?.clientWidth || 1000;
              const viewH = containerRef.current?.clientHeight || 700;

              const vpWorldLeft = -pan.x / zoom;
              const vpWorldTop = -pan.y / zoom;
              const vpWorldRight = (-pan.x + viewW) / zoom;
              const vpWorldBottom = (-pan.y + viewH) / zoom;

              const vpLeft = Math.max(0, Math.min(MAP_W, toMinimapX(vpWorldLeft)));
              const vpTop = Math.max(0, Math.min(MAP_H, toMinimapY(vpWorldTop)));
              const vpRight = Math.max(0, Math.min(MAP_W, toMinimapX(vpWorldRight)));
              const vpBottom = Math.max(0, Math.min(MAP_H, toMinimapY(vpWorldBottom)));

              const vpWidth = Math.max(10, vpRight - vpLeft);
              const vpHeight = Math.max(10, vpBottom - vpTop);

              const handleMinimapClick = (e: React.MouseEvent<HTMLDivElement>) => {
                const rect = e.currentTarget.getBoundingClientRect();
                const clickMx = e.clientX - rect.left - offsetX;
                const clickMy = e.clientY - rect.top - offsetY;

                const targetWorldX = clickMx / scale + minGraphX;
                const targetWorldY = clickMy / scale + minGraphY;

                setPan({
                  x: Math.round(-(targetWorldX * zoom - viewW / 2)),
                  y: Math.round(-(targetWorldY * zoom - viewH / 2))
                });
              };

              return (
                <div
                  className="relative bg-neutral-950 border border-neutral-800/80 rounded-lg overflow-hidden cursor-crosshair"
                  style={{ width: `${MAP_W}px`, height: `${MAP_H}px` }}
                  onClick={handleMinimapClick}
                >
                  {/* Nodes in Minimap */}
                  {experiment.nodes.map((node) => {
                    const nx = toMinimapX(node.position[0]);
                    const ny = toMinimapY(node.position[1]);
                    const nw = Math.max(4, getNodeWidth(node) * scale);
                    const nh = Math.max(3, getNodeHeight(node) * scale);
                    const isSelected = node.id === selectedNodeId;

                    return (
                      <div
                        key={node.id}
                        className={`absolute rounded-xs transition-colors ${
                          isSelected 
                            ? 'bg-indigo-400 border border-white z-10' 
                            : node.geometric
                            ? 'bg-emerald-500/80'
                            : 'bg-neutral-600/80 hover:bg-neutral-400'
                        }`}
                        style={{
                          left: `${nx}px`,
                          top: `${ny}px`,
                          width: `${nw}px`,
                          height: `${nh}px`
                        }}
                      />
                    );
                  })}

                  {/* Viewport Indicator Rectangle */}
                  <div
                    className="absolute border border-indigo-500/80 bg-indigo-500/15 pointer-events-none rounded-xs"
                    style={{
                      left: `${vpLeft}px`,
                      top: `${vpTop}px`,
                      width: `${vpWidth}px`,
                      height: `${vpHeight}px`
                    }}
                  />
                </div>
              );
            })()}

            <div className="flex items-center justify-between text-[9px] font-mono text-neutral-500 mt-1.5 px-0.5">
              <span>Zoom: {Math.round(zoom * 100)}%</span>
              <span className="text-neutral-400">Click to center</span>
            </div>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setShowMinimap(true)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-neutral-900/90 border border-neutral-800 text-xs font-mono text-neutral-300 hover:text-white shadow-lg backdrop-blur-md transition-colors"
            title="Open Minimap"
          >
            <MapIcon className="w-3.5 h-3.5 text-indigo-400" />
            <span>Minimap</span>
            <ChevronUp className="w-3 h-3 text-neutral-400" />
          </button>
        )}
      </div>

      {/* Clear Canvas Modal */}
      <ClearCanvasModal
        isOpen={isClearModalOpen}
        onClose={() => setIsClearModalOpen(false)}
        onConfirmClear={handleClearCanvas}
        onLoadTemplate={(exp) => {
          onUpdateExperiment(exp);
          onSelectNode(null);
        }}
      />

      {/* Group Creation / Clustering Modal */}
      {showGroupModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div 
            id="cace-cluster-modal" 
            className="w-full max-w-md bg-neutral-900 border border-neutral-800 rounded-xl shadow-2xl p-5 flex flex-col gap-4 text-neutral-200"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between pb-3 border-b border-neutral-800">
              <div className="flex items-center gap-2">
                <div className="p-2 rounded-lg bg-indigo-950/80 border border-indigo-800 text-indigo-400">
                  <Layers className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-white">Create Subgraph Cluster</h3>
                  <p className="text-[11px] text-neutral-400">Organize selected node into a named visual group</p>
                </div>
              </div>
              <button 
                type="button"
                onClick={() => setShowGroupModal(false)}
                className="p-1 rounded text-neutral-400 hover:text-white hover:bg-neutral-800 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex flex-col gap-3 text-xs">
              <div className="flex flex-col gap-1">
                <label className="text-[11px] font-mono text-neutral-400">Cluster Title</label>
                <input
                  type="text"
                  placeholder="e.g., FEM Discretization Pipeline"
                  value={groupModalTitle}
                  onChange={(e) => setGroupModalTitle(e.target.value)}
                  className="px-3 py-2 bg-neutral-950 border border-neutral-800 rounded-lg text-white font-medium focus:outline-hidden focus:border-indigo-500"
                />
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[11px] font-mono text-neutral-400">Color Theme</label>
                <div className="flex items-center gap-2">
                  {(['indigo', 'emerald', 'cyan', 'purple', 'amber', 'rose'] as const).map((c) => (
                    <button
                      key={c}
                      type="button"
                      onClick={() => setGroupModalColor(c)}
                      className={`w-7 h-7 rounded-md border flex items-center justify-center transition-all ${
                        groupModalColor === c 
                          ? 'ring-2 ring-white scale-110' 
                          : 'opacity-70 hover:opacity-100'
                      } ${
                        c === 'indigo' ? 'bg-indigo-600 border-indigo-400' :
                        c === 'emerald' ? 'bg-emerald-600 border-emerald-400' :
                        c === 'cyan' ? 'bg-cyan-600 border-cyan-400' :
                        c === 'purple' ? 'bg-purple-600 border-purple-400' :
                        c === 'amber' ? 'bg-amber-600 border-amber-400' :
                        'bg-rose-600 border-rose-400'
                      }`}
                    />
                  ))}
                </div>
              </div>

              <div className="flex flex-col gap-1">
                <label className="text-[11px] font-mono text-neutral-400">Description (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g., Piecewise linear Galerkin formulation & residual gate"
                  value={groupModalDesc}
                  onChange={(e) => setGroupModalDesc(e.target.value)}
                  className="px-3 py-2 bg-neutral-950 border border-neutral-800 rounded-lg text-white font-medium focus:outline-hidden focus:border-indigo-500"
                />
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-neutral-800">
              <button
                type="button"
                onClick={() => setShowGroupModal(false)}
                className="px-3 py-1.5 rounded-lg border border-neutral-700 text-xs text-neutral-400 hover:text-white hover:bg-neutral-800 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleCreateOrUpdateGroup}
                className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white shadow-md transition-colors"
              >
                Create Cluster
              </button>
            </div>
          </div>
        </div>
      )}

      {/* AlphaFold Protein Mathematical Invariants & 3D Viewer Modal */}
      {inspectingAlphaFoldData && (
        <AlphaFoldProteinModal
          data={inspectingAlphaFoldData}
          onClose={() => setInspectingAlphaFoldData(null)}
        />
      )}
    </div>
  );
};
