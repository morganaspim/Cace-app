#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
from pathlib import Path
import tarfile
import tempfile

EXPECTED_SHA256 = "1999b810a8c2a8d86013a8c311a9d66de36fe98ff292b6ddf43e156145478d99"
EXPECTED_FILES = {
    "src/components/AlphaFoldProteinModal.tsx",
    "src/components/Canvas3DControls.tsx",
    "src/components/CanvasTilingBackground.tsx",
    "src/components/ClearCanvasModal.tsx",
    "src/components/CoordinateSystemFrame.tsx",
    "src/components/GeometryPalette.tsx",
    "src/components/GraphCanvas.tsx",
    "src/components/NodePropertiesPanel.tsx",
    "src/components/TilingSelector.tsx",
    "src/data/alphafoldProteins.ts",
    "src/data/caceData.ts",
    "src/data/geometryPresets.ts",
    "src/engine/geometricLattice.ts",
    "src/types.ts",
}


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parts = sorted((root / "vendor").glob("cmb64_*"))
    if not parts:
        raise SystemExit("missing content-addressed canvas source bundle parts")
    encoded = b"".join(part.read_bytes() for part in parts)
    archive = base64.b64decode(encoded, validate=True)
    digest = hashlib.sha256(archive).hexdigest()
    if digest != EXPECTED_SHA256:
        raise SystemExit(f"canvas source bundle SHA-256 mismatch: {digest}")

    with tempfile.NamedTemporaryFile(suffix=".tar.gz") as tmp:
        tmp.write(archive)
        tmp.flush()
        with tarfile.open(tmp.name, "r:gz") as tf:
            members = tf.getmembers()
            names = {m.name for m in members if m.isfile()}
            if names != EXPECTED_FILES:
                raise SystemExit("canvas source bundle file manifest mismatch")
            for member in members:
                target = (root / member.name).resolve()
                if root not in target.parents and target != root:
                    raise SystemExit(f"unsafe archive path: {member.name}")
                if member.issym() or member.islnk():
                    raise SystemExit(f"links forbidden in canvas source bundle: {member.name}")
            tf.extractall(root, filter="data")
    print(f"materialized {len(EXPECTED_FILES)} exact canvas modules sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
