"""Hardened console entry point for optional CACE Ed25519 attestations."""
from __future__ import annotations

import json
from pathlib import Path
import sys

from .attest_cli import main as _attest_main


def _option_value(argv: list[str], name: str) -> str | None:
    try:
        index = argv.index(name)
    except ValueError:
        return None
    if index + 1 >= len(argv):
        return None
    return argv[index + 1]


def _error(message: str, error_type: str) -> int:
    sys.stderr.write(
        json.dumps(
            {
                "cli_schema": 1,
                "error": message,
                "error_type": error_type,
            },
            sort_keys=True,
        )
        + "\n"
    )
    return 2


def _preflight_keygen(argv: list[str]) -> int | None:
    private_text = _option_value(argv, "--private-key")
    public_text = _option_value(argv, "--public-key")
    if private_text is None or public_text is None:
        return None  # argparse in the underlying CLI owns missing-argument errors.
    private_path = Path(private_text).expanduser()
    public_path = Path(public_text).expanduser()
    try:
        same_target = private_path.resolve(strict=False) == public_path.resolve(strict=False)
    except OSError:
        same_target = private_path.absolute() == public_path.absolute()
    if same_target:
        return _error(
            "private and public key output paths must be different",
            "ValueError",
        )
    if "--force" not in argv:
        existing = [str(path) for path in (private_path, public_path) if path.exists()]
        if existing:
            return _error(
                "refusing to create a partial keypair because output path(s) already exist: "
                + ", ".join(existing),
                "FileExistsError",
            )
    return None


def _preflight_crypto() -> int | None:
    try:
        import cryptography  # noqa: F401
    except ImportError:
        return _error(
            "Ed25519 attestations require the optional 'attest' dependency: "
            "pip install 'cace-studio[attest]'",
            "AttestationUnavailableError",
        )
    return None


def _preflight_pqc() -> int | None:
    try:
        import oqs  # noqa: F401
    except ImportError:
        return _error(
            "ML-DSA attestations require the optional pinned liboqs-python provider",
            "PQCProviderUnavailable",
        )
    return None


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in {"-h", "--help"}:
        return _attest_main(args)
    command = args[0]
    if command == "keygen":
        blocked = _preflight_keygen(args)
        if blocked is not None:
            return blocked
        blocked = _preflight_crypto()
        if blocked is not None:
            return blocked
    elif command == "sign":
        blocked = _preflight_crypto()
        if blocked is not None:
            return blocked
    elif command.startswith("pqc-"):
        blocked = _preflight_pqc()
        if blocked is not None:
            return blocked
    return _attest_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
