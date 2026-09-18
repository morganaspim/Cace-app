# CACE Studio third-party notices

CACE Studio's original source remains governed by the repository's proprietary `LICENSE`.
Third-party components remain under their own terms. `third_party_policy.json` is the
machine-readable release policy; `scripts/audit_third_party_licenses.py` fails closed when a
declared dependency lacks a reviewed policy entry.

Release packaging must preserve the license/notices supplied by each redistributed component.
In particular:

- Lean 4 and Mathlib4: Apache-2.0 notices must be preserved when redistributed.
- LaTeX itself is LPPL-1.3c; compiling a CACE-authored `.tex` file does not relicense that CACE document.
- TeX Live is an aggregate: if bundled, preserve the individual package licenses/notices.
- PySide6/Qt: proprietary distribution must use a compliant LGPL route (including applicable relinking/replacement rights) or an appropriate Qt commercial license.
- Monero software: preserve its BSD-family notices if CACE redistributes wallet/daemon binaries. RPC interoperability alone does not copy Monero source into CACE.
- CUDA: do not redistribute toolkit components except as permitted by the applicable NVIDIA terms.

The generated `SBOM.spdx.json` and `SBOM.cyclonedx.json` record the dependency inventory used by
the build. Release automation should additionally copy license files from installed Python and JS
packages into the release's `licenses/` directory.
