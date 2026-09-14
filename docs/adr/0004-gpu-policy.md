# ADR-0004 — GPU acceleration is optional and provenance-tracked

**Status:** Accepted

GPU acceleration is a performance policy, not a correctness or proof requirement. The UI provides an independent GPU ON/OFF control. GPU-capable modules may use CuPy/CUDA when enabled and available. If GPU is requested but unavailable, execution falls back to CPU and the certificate records requested device, actual device, backend, and fallback behavior.

Scientific verification must remain meaningful regardless of accelerator choice.
