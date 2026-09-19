# CACE Multi-Window Spatial Routing and Non-Cartesian Workspaces

Status: design architecture for implementation after the current regression repair branch is clean.

## Core decision

CACE should support multiple independent windows and multiple monitors, but use a **two-layer coordinate model**.

### Layer 1 — physical screen space

The operating system/browser owns real windows. These remain ordinary rectangular regions on one or more physical screens.

### Layer 2 — CACE semantic space

CACE assigns every window/view a semantic position that may use:

- Cartesian coordinates;
- hexagonal axial/cube coordinates;
- polar/radial coordinates;
- hyperbolic coordinates;
- Voronoi/power cells;
- Hilbert/Morton addresses;
- simplex/barycentric coordinates;
- complex Gaussian/Eisenstein lattices;
- recursive/fractal addresses;
- optional 3D/spherical coordinates.

The semantic position is then projected into normal rectangular physical window bounds.

This preserves normal OS/browser behavior while letting CACE use geometry that matches the scientific problem.

## Recommended routing sequence

When a user opens a new view/window:

1. identify its **WindowIntent**:
   - experiment;
   - source node(s);
   - view role;
   - data type;
   - evidence/proof role;
   - heartbeat/attention priority;
   - user pin;
   - preferred monitor/workspace;
2. honor any user pin/lock first;
3. choose the workspace geometry;
4. place the window at a semantic coordinate relative to its scientific/contextual neighbors;
5. select a monitor;
6. project the semantic coordinate into physical screen bounds;
7. resolve overlap/occlusion;
8. minimize movement of existing windows;
9. animate the transition;
10. persist semantic layout independently from scientific state.

## Ranked geometry ideas

### 1. Hybrid semantic atlas — default

Best overall design.

Each CACE workspace can select a geometry while real OS windows remain rectangular.

Benefits:

- supports all later coordinate systems;
- avoids coupling science to display pixels;
- handles multi-monitor changes cleanly;
- lets one experiment use hex while another uses hyperbolic or radial layout;
- keeps saved scientific experiments independent of display arrangement.

### 2. Hexagonal axial/cube routing

Use a six-neighbor semantic lattice.

Good for:

- module neighborhoods;
- mesh/cell-oriented work;
- heartbeat propagation;
- clustering tools around a selected node;
- Eisenstein/omega-based coordinate views.

Example:

- selected PDE canvas at hex cell (0,0);
- residual inspector at one neighbor;
- error estimator at another;
- proof/evidence panel at another;
- AI/help windows on more distant rings.

### 3. Radial / polar orbit routing

Put the current scientific focus at the origin.

Possible rings:

- ring 0: active canvas/result;
- ring 1: immediate inspectors;
- ring 2: proof/evidence/provenance;
- ring 3: help/AI/research notes;
- outer region: logs/background jobs.

This is intuitive for a focused experiment and naturally expresses distance from the active task.

### 4. Hyperbolic focus+context routing

Use for deep dependency/proof/research hierarchies.

The active object expands near the center while distant branches remain visible toward the boundary.

Strong use cases:

- proof trees;
- dependency graphs;
- large Research Idea trees;
- hundreds of windows/views without losing overall context.

CACE should add breadcrumbs, a visible home anchor, smooth focus animation and a mini-map to avoid disorientation.

### 5. Voronoi / weighted power layout

Give each semantic region an area based on something meaningful:

- attention priority;
- heartbeat;
- compute load;
- active errors;
- user importance;
- experiment family.

This could be especially useful for the heartbeat economic city.

Use hysteresis: regions should not constantly resize when metrics change, because preserving human spatial memory is more valuable than perfectly tracking every small numerical update.

### 6. Hilbert/Morton locality-preserving addressing

This is less about appearance and more about routing thousands of objects.

Map a high-dimensional CACE address to a deterministic one-dimensional ordering, then tile that ordering across workspaces/monitors.

Good for:

- huge experiment collections;
- distributed instances;
- deterministic restore;
- cache/data-locality visualization;
- fractal coordinate research.

Human-facing labels/breadcrumbs remain necessary.

### 7. Simplex / barycentric workspace

Useful when a scientific object is naturally described by relative weights.

Examples:

- strength / cost / weight material trade-off;
- three model hypotheses;
- composition fractions;
- multi-objective optimization.

Views move within the simplex according to their visible scientific criteria.

### 8. Complex lattice coordinates

Use Gaussian integers for square-like complex lattices or Eisenstein/omega coordinates for hexagonal/triangular lattices.

This fits CACE's existing interest in alternative complex bases and novel coordinate systems.

Important invariant:

**complex coordinates used for window layout are visualization/addressing only.**

They do not alter the actual science unless the experiment contains an explicit mathematical transform module.

Always provide an optional Cartesian projection/reference view.

### 9. Recursive/fractal workspace

A project can be a tile containing sub-experiments, each containing smaller workspaces.

Zooming changes level rather than merely enlarging pixels.

Strong fit for:

- multi-scale experiments;
- Cantor/Hilbert addressing;
- very large research notebooks;
- nested simulations.

### 10. Spherical / 3D shell windows

Useful as an optional 3D/XR mode.

Keep the active object near the center and arrange related views on a surrounding shell.

Good for demonstrations and spatial science, but not the normal desktop default because ordinary monitors make depth and occlusion harder to manage.

## Routing objectives

The layout engine should optimize for user experience, not simply fill empty pixels.

Priority order:

1. preserve user pins;
2. preserve established spatial memory;
3. keep contextual windows near their source;
4. avoid covering the source;
5. minimize overlap;
6. minimize important connector crossings;
7. keep proof/evidence close to the result it explains;
8. favor the active/focused scientific task;
9. move background windows toward peripheral regions;
10. avoid monitor hopping unless there is a meaningful benefit.

## Window roles

Suggested semantic roles:

- Canvas;
- Inspector;
- Plot/Data View;
- 2D/3D Visualization;
- Proof/Evidence;
- Provenance;
- Research Idea;
- Open Problem;
- Protein Playground;
- Local AI;
- Heartbeat/Economy;
- Help;
- Logs/Console;
- Progress/Error.

The router uses the role plus scientific ancestry to determine where the view belongs.

## Multi-monitor default

When several screens are available:

- primary: active canvas/focus;
- secondary: proof/evidence/inspectors;
- tertiary+: visualization, research dashboard, heartbeat/economy, logs according to user preference.

These are defaults, never hard constraints. User pinning overrides them.

If a monitor disappears, CACE keeps semantic coordinates and remaps only the physical projection.

## Persistence

Save separately:

- semantic workspace geometry;
- semantic coordinates;
- role;
- pin/lock;
- monitor preference;
- physical bounds as a restore hint;
- focus/history.

Do **not** mix those values into scientific hashes, proof state or computation caches.

## Implementation order

1. typed WindowIntent + WindowPlacement state;
2. native rectangular multi-window/multi-monitor support;
3. stable Cartesian auto-router;
4. hex axial semantic router;
5. radial router;
6. routing persistence + monitor-remap tests;
7. hyperbolic focus/context;
8. Voronoi weighted dashboard;
9. Hilbert/Morton large-workspace addressing;
10. simplex/complex/fractal/3D experimental coordinate plugins.

This order gives CACE a usable production multi-window system early while keeping the novel geometries modular.
