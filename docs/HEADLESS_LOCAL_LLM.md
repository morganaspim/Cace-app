# Headless local CACE + LLM

This integration gives Expert Robot a local-only, headless CACE research surface.

## Processes

- CACE deterministic API: `http://127.0.0.1:8765`
- pinned llama.cpp OpenAI-compatible API: `http://127.0.0.1:8080/v1`
- model role: untrusted informal reasoner
- CACE tools/verifiers remain authoritative only according to their existing qualification contracts

The launcher does not download models or runtimes. Provision the pinned files separately, then set:

```sh
export CACE_MODEL_GGUF=/absolute/path/to/qwen3.5-4b-q4_k_m.gguf
export CACE_LLAMA_SERVER_BIN=/absolute/path/to/pinned/llama-server
scripts/run_cace_headless_local.sh
```

The model is pinned logically to:

- `Qwen/Qwen3.5-4B`
- revision `a7b0d22b993d71000cf2eadfb37222a67cee521e`
- quantization `Q4_K_M`

The llama.cpp runtime is pinned logically to:

- tag `v0.4.1`
- commit `b29c606e28a01b1bc8c1351026a0fa6e616bf6c4`

The actual local GGUF SHA-256 is written to `runtime/headless/model.sha256` at launch so evidence can bind the concrete file.

## Trust boundary

The LLM may:

- converse;
- propose experiments;
- explain available CACE modules;
- suggest typed tool calls;
- help interpret untrusted/informal results.

The LLM may not:

- set PASS/VERIFIED/FORMAL;
- promote a claim;
- mutate proof-ledger truth;
- merge or promote code;
- expand its own authority.

Expert Robot calls the local CACE API separately from the local LLM. This separation is intentional: model text cannot masquerade as deterministic or formal evidence.

## Network boundary

Both listeners bind to `127.0.0.1`. CACE's existing local provider also rejects non-loopback endpoints, ignores proxy environment variables, and refuses HTTP redirects.

Do not change either listener to `0.0.0.0` for the RSI path. If remote operator access is later required, add a separately authenticated relay rather than widening these listeners.

## Expert Robot

Expert Robot uses `python/cace_headless.py` with `config/cace_headless_local.json`:

```sh
python3 python/cace_headless.py health
python3 python/cace_headless.py chat "What can CACE help us verify?"
python3 python/cace_headless.py modules
python3 python/cace_headless.py claims
python3 python/cace_headless.py research-turn "Propose the next exact geometry experiment."
```

`research-turn` supplies high-level CACE context to the LLM but does not execute any proposed action automatically.
