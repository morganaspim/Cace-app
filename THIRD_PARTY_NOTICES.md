# CACE Studio — Third-Party Notices

Status: source-level dependency and distribution policy summary. The exact
license bundle for a released artifact must be generated from the environment
used to build that artifact. This file is not a substitute for the full license
texts that must accompany redistributed third-party components.

CACE's original materials remain governed by the proprietary repository
`LICENSE`. Nothing in the CACE license changes the license of third-party
software.

## Current direct dependency inventory

| Component | Scope in CACE | Upstream license / licensing model | CACE distribution rule |
|---|---|---|---|
| NumPy | default Python scientific runtime | BSD-3-Clause | Allowed in browser/server profile. Preserve package copyright, conditions, disclaimer, and any bundled-library notices contained in the exact wheel. |
| FastAPI | default API runtime | MIT | Allowed in browser/server profile. Preserve the MIT copyright/license notice and exact transitive-package notices. |
| cryptography | optional attestation/signing support | Apache-2.0 OR BSD-3-Clause | Allowed when included. Preserve the exact package license files/notices from the distributed wheel. |
| Matplotlib | optional desktop GUI / plots; tests | Matplotlib license (PSF/BSD-compatible) plus package third-party notices | Allowed only in profiles that actually ship it. Preserve Matplotlib and package-provided third-party notices. |
| PySide6 / Qt for Python | optional desktop GUI | Qt Commercial OR LGPLv3/GPLv3 community licensing, with Qt/Qt-for-Python third-party components | Excluded from the default browser/server release. Desktop redistribution is blocked until a Qt commercial path or separately reviewed LGPLv3-compliant package is selected. GPL-only Qt modules and Qt WebEngine require explicit additional review. |
| pytest | tests only | MIT | Not part of the normal product artifact. If redistributed, preserve its MIT notice. |
| Hypothesis | tests only | MPL-2.0 | Not part of the normal product artifact. Redistribution or modification requires separate MPL review. |
| Lean 4 | Oracle CI/formal qualification tooling | Apache-2.0 | CI-only under the current architecture. If redistributed, preserve Apache-2.0 license/notice obligations. |
| mathlib | Oracle CI/formal qualification dependency | Apache-2.0 | CI-only under the current architecture. If redistributed, preserve Apache-2.0 license/notice obligations. |
| setuptools / wheel | build tooling | upstream open-source licenses | Build-time only under the normal product profile; if bundled into an artifact, include them in the generated artifact inventory. |

## Release profiles

### Browser/server

The intended normal proprietary product profile contains CACE plus its required
server/scientific runtime dependencies. PySide6 is not part of this profile.

A release must run:

```sh
python scripts/audit_license_compliance.py
python scripts/generate_third_party_notices.py --output-dir <artifact>/licenses
```

The generated inventory and copied package license files must be included with
the artifact.

### Desktop GUI

PySide6 makes desktop redistribution a separate licensing profile. Do not ship a
proprietary desktop bundle merely because the application imports successfully.

Before a desktop release, record one of:

1. the applicable Qt commercial distribution entitlement and use the proper
   commercial packages; or
2. a documented LGPLv3-compliant packaging review for the exact deployment
   method, including all required notices and user rights for the covered Qt
   libraries.

Do not add a GPL-only Qt module or Qt WebEngine to the proprietary distribution
without an explicit review of that exact module and its third-party components.

### Formal/CI tooling

Oracle is used for runner/CI jobs only. Lean, mathlib, Ubuntu packages, GitHub
Actions, and other CI tooling are not automatically part of a customer-facing
CACE artifact. Their licenses become distribution obligations only if CACE
actually redistributes them.

## Bundled assets and datasets

Future externally sourced models, fonts, images/media, datasets, molecule or
protein structures, or native binaries require provenance and license review
before redistribution. Public availability alone is not redistribution
permission.

Generated CACE example plots are first-party output unless their source record
explicitly says otherwise.

## Attribution rule

Third-party attribution is retained when CACE incorporates material whose
license, copyright, contract, or terms require it. General public discussion,
marketing statements, or high-level ideas do not create a software-license
attribution entry by themselves.

## Exact-license rule

Do not copy a license summary from this file into a customer artifact and call
the job complete. The release bundle must contain the exact license/notice files
from the actual package versions and wheels shipped in that artifact.
