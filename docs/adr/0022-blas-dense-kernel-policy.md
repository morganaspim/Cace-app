# ADR 0022 — Dense kernel policy

v0.21 adds a BLAS-backed NumPy dense-matrix benchmark as a performance/reference kernel. It does not relabel the C++ hand-written supernodal loops as BLAS. Exact-rational sparse structure remains authoritative for correctness.
