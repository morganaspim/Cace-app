"""Headless, versioned JSON interface for local tools and AI agents."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

from .app import build_registry
from .core.executor import GraphExecutor
from .core.report import run_report
from .core.serialization import load_experiment


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("registry", help="List module contracts; metadata is not executed evidence")
    run = sub.add_parser("run", help="Execute a .cace experiment and emit its evidence report")
    run.add_argument("experiment", type=Path)
    run.add_argument("--seed", type=int, default=0)
    run.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        registry = build_registry()
        if args.command == "registry":
            payload = {
                "cli_schema": 1,
                "metadata_is_verification_evidence": False,
                "modules": [
                    {
                        "metadata": asdict(cls.metadata),
                        "inputs": [asdict(p) for p in cls.inputs],
                        "outputs": [asdict(p) for p in cls.outputs],
                        "parameters": [asdict(p) for p in cls.parameters],
                        "declared_proof_status": cls.proof_status.to_dict(),
                    }
                    for cls in sorted(registry.classes(), key=lambda cls: cls.metadata.module_id)
                ],
            }
            status = 0
        else:
            experiment = load_experiment(args.experiment)
            result = GraphExecutor(registry).run(experiment, seed=args.seed)
            payload = run_report(result, experiment.name)
            payload["cli_schema"] = 1
            payload["seed"] = args.seed
            # A successful computation with absent/skipped verification is not verified.
            states = [record.state.value for records in result.verification.values() for record in records]
            status = 1 if "fail" in states else (0 if result.all_verifiers_passed else 3)
            payload["cli_exit_code"] = status
        rendered = json.dumps(payload, indent=2, sort_keys=True, default=repr, allow_nan=False) + "\n"
        if args.command == "run" and args.output:
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
        return status
    except Exception as exc:
        sys.stderr.write(json.dumps({"cli_schema": 1, "error": str(exc), "error_type": type(exc).__name__}) + "\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
