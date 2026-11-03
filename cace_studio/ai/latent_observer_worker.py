from __future__ import annotations

import json
import os
from pathlib import Path
import time

import numpy as np

from .latent_observer import MatrixObserverArchive


def main() -> int:
    input_dir = Path(os.environ.get("CACE_OBSERVER_INPUT", "/input"))
    archive_dir = Path(os.environ.get("CACE_OBSERVER_ARCHIVE", "/archive"))
    replica_id = os.environ.get("CACE_OBSERVER_ID", "observer")
    archive = MatrixObserverArchive(archive_dir, replica_id=replica_id)
    seen: set[str] = set()
    while True:
        for meta_path in sorted(input_dir.glob("*.json")):
            key = meta_path.name
            if key in seen:
                continue
            try:
                payload = json.loads(meta_path.read_text(encoding="utf-8"))
                matrix_path = input_dir / str(payload["matrix_file"])
                if not matrix_path.is_file():
                    continue
                matrix = np.load(matrix_path, allow_pickle=False)
                archive.observe(
                    run_id=str(payload["run_id"]),
                    model_digest=str(payload["model_digest"]),
                    layer_name=str(payload.get("layer_name", "")),
                    layer_index=int(payload["layer_index"]),
                    step_index=int(payload["step_index"]),
                    matrix=matrix,
                    capture_mode=str(payload.get("capture_mode", "hash-only")),
                    max_full_bytes=int(payload.get("max_full_bytes", 64 * 1024 * 1024)),
                )
                seen.add(key)
            except Exception:
                seen.add(key)
        time.sleep(0.25)


if __name__ == "__main__":
    raise SystemExit(main())
