# ADR 0021 — Dense-block supernodes, reusable workspaces, and fixed thread pool

v0.20 promotes symbolic supernodes from analysis metadata to numeric units. Each native front may eliminate multiple consecutive pivot columns as one dense block, then emit one Schur contribution for the supernode update set. Correctness is checked against the exact-rational sparse LDLT structure and a deterministic known solution.

The runtime uses a fixed C++20 worker pool. Supernodes are scheduled level-by-level from elimination-tree leaves to roots, so tasks at one level are independent. Dense frontal buffers are `thread_local`, grown only when a larger front is encountered, and reused by later tasks on the same worker.

This is a real dense-block supernodal kernel, but it is not yet BLAS-backed and the scheduler is level-synchronous rather than work-stealing. Timing data are benchmark evidence only.
