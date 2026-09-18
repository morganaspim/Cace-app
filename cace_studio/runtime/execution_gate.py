from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import time
from typing import Iterable

from .entitlement import EntitlementExpired, EntitlementService
from .sandbox import GrowthSandbox, SandboxPolicy, SandboxResult


class EntitledSandboxExecutor:
    """Server-authoritative bridge between resource entitlement and strict sandbox.

    Browser/localStorage state is never consulted. The server determines remaining
    execution time, caps sandbox wall time, measures actual elapsed monotonic time,
    and charges the authoritative entitlement ledger afterward.
    """

    def __init__(self, entitlements: EntitlementService, policy: SandboxPolicy | None = None) -> None:
        self.entitlements = entitlements
        self.policy = policy or SandboxPolicy()

    def run(
        self,
        *,
        subject: str,
        image: str,
        argv: Iterable[str],
        input_dir: str | Path,
        output_dir: str | Path,
        runtime: str | None = None,
    ) -> SandboxResult:
        status = self.entitlements.status(subject)
        if not status.allowed:
            raise EntitlementExpired("execution time exhausted")
        if status.unlimited:
            allowed = self.policy.wall_seconds
        else:
            allowed = min(self.policy.wall_seconds, max(1, int(status.remaining_seconds)))
        bounded_policy = replace(self.policy, wall_seconds=allowed)
        sandbox = GrowthSandbox(bounded_policy, runtime=runtime)
        started = time.monotonic()
        result = sandbox.run(
            image=image,
            argv=argv,
            input_dir=input_dir,
            output_dir=output_dir,
        )
        elapsed = min(time.monotonic() - started, float(allowed))
        # Charge measured executor time, never a client-supplied number.
        self.entitlements.store.charge(
            subject,
            max(elapsed, 1e-6),
            daily_free_seconds=self.entitlements.daily_free_seconds,
        )
        return result
