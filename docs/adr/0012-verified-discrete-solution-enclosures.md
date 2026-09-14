# ADR 0012 — Verified discrete solution enclosures

CACE v0.10 treats the stored binary64 CSR matrix and right-hand side as the exact discrete problem for the linear-algebra certificate.

A floating-point inverse `R` is **not** trusted as an inverse. It is only a preconditioner candidate. CACE evaluates `E = I - R A` with outward-rounded interval arithmetic. If a certified infinity-norm bound `q = ||E||_inf < 1`, then `A` is nonsingular. For the floating-point candidate `xhat` and interval residual `r = b - A xhat`, CACE evaluates `y = R r` with intervals and derives

`||x* - xhat||_inf <= ||y||_inf / (1-q)`.

It then verifies the corresponding Krawczyk/fixed-point box maps into itself before issuing a coefficient enclosure. If `q >= 1`, if the inverse candidate cannot be formed, or if inclusion cannot be shown, certification is `NOT_RUN`.

This certifies only the exact solution of the stored discrete binary64 system. Continuum FEM discretization error remains a separate certificate.
