# ADR-0001: Stable orchestration core, extensible scientific modules

Status: Accepted — 2026-09-13

CACE Studio's core owns graph semantics, module contracts, serialization, provenance and plugin loading. Domain mathematics lives in modules. This prevents scientific experiments from changing application architecture and lets verification obligations remain local to each module.
