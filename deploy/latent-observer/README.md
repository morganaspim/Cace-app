# CACE latent observer container example

This image is for **one-way hidden-layer observation only**. It is not part of
CACE proof/evidence authority.

Run at least two replicas from the same host-brokered read-only input directory.
The inference/model process must not mount either observer archive and the
observers must not expose sockets back to inference.

Example security properties:

- `--network=none`
- `--read-only`
- `--cap-drop=ALL`
- `--security-opt=no-new-privileges`
- input volume mounted `:ro`
- separate writable archive volume per replica
- no Docker socket, credentials, model control socket, or host shell

The trusted host broker writes one immutable `.npy` matrix plus a JSON metadata
file into the input spool for each layer/step. Each observer independently hashes
or archives the same matrix. Ordinary text-only Ollama/OpenAI-compatible HTTP
providers do not expose hidden activations, so this feature is unavailable for
those providers unless the underlying engine adds an explicit instrumentation
adapter.
