# ADR 0013 — Native runtime and backend equivalence (v0.12)

## Decision
CACE keeps Python/NumPy as a reference implementation while introducing C++20 kernels behind two optional bindings: pybind11 and a minimal C ABI loadable with `ctypes`. Accelerated execution never creates proof evidence by itself.

The first native kernels are CSR matrix-vector multiplication, CSR infinity residual, and deterministic Dörfler marking. Dörfler ties are resolved by descending squared indicator followed by ascending cell index, making adaptive histories reproducible across backends.

## Equivalence evidence
A C++ backend receives numerical equivalence evidence only after it is run on the identical stored binary64 input and compared with the Python reference output within an explicit tolerance. GPU/CUDA follows the same rule. An unavailable backend is `NOT_RUN`, never PASS and never failure.

## Scope
The C++20 sparse kernels and Dörfler selector are native in v0.12. Full sparse factorization, element assembly, red/green topology refinement, and verified interval arithmetic remain Python/reference paths and are future native-runtime work.

## Trust boundary
Native numerical equivalence is not interval or formal proof of implementation correctness. Existing interval certificates remain authoritative for exact-discrete-solution enclosures.
