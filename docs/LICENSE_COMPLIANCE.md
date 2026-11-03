# CACE License Compliance and Release Gate

Status: engineering/compliance policy. This is not legal advice and is not a
substitute for counsel reviewing a final commercial distribution.

Canonical machine policy: `ops/license_compliance_policy.json`.

## Current conclusion

The normal browser/server CACE profile can remain proprietary while using the
current permissively licensed runtime dependencies, provided the exact release
artifact preserves the required third-party license/copyright notices.

The optional PySide6 desktop GUI is deliberately separated from that conclusion:
desktop redistribution is blocked until its Qt license path is explicitly
selected and reviewed.

## Source-level controls

CACE requires:

- PEP 639-style first-party package metadata using
  `LicenseRef-CACE-Proprietary`;
- `LICENSE`, `NOTICE`, and `THIRD_PARTY_NOTICES.md` in package legal files;
- every direct Python dependency represented in the machine license policy;
- an audit that rejects unreviewed bundled native libraries, fonts, package
  archives, and common external scientific dataset formats;
- no voluntary company attribution that is not tied to incorporated material or
  an applicable obligation;
- any future frontend dependency tree to receive an exact lockfile/artifact
  license inventory before production release.

Run:

```sh
python scripts/audit_license_compliance.py
```

## Artifact-level controls

Source inspection alone cannot prove a binary/container release is complete,
because wheels can carry transitive dependencies and embedded native libraries.

Build the release in an isolated environment, then run:

```sh
python scripts/generate_third_party_notices.py \
  --output-dir <release-artifact>/licenses
```

The generator walks the installed dependency closure for the requested release
roots, records exact versions/license metadata, and copies license-like files
from each installed distribution. The resulting directory ships with the
artifact.

## PySide6 / Qt rule

Qt for Python is not treated as an ordinary permissive dependency. The default
browser/server profile excludes it.

A proprietary desktop release may proceed only through a recorded:

- Qt commercial distribution path using the appropriate commercial packages; or
- separately reviewed LGPLv3-compliant packaging path for the exact bundler and
  deployment model.

Qt WebEngine is an additional explicit review gate because it includes Chromium
and its license set.

## Development/formal tools

pytest, Hypothesis, Lean, mathlib, GitHub Actions tooling, Ubuntu packages, and
other CI-only dependencies do not automatically belong in the customer product
artifact. If CACE later redistributes any of them, they must appear in the exact
artifact notice bundle.

## Assets and datasets

Externally sourced assets/data are reviewed independently of Python packages.
A file being publicly downloadable does not imply redistribution permission.

For future protein/molecular/material examples, record source, provider,
license/terms, attribution requirements, and content hash.

## Release checklist

A production artifact is ready for license review only when:

1. source audit passes;
2. the build is from the intended exact CACE commit;
3. the artifact-specific dependency inventory has been generated;
4. all copied package license files are included;
5. no dependency is marked review-required without an explicit recorded
   distribution decision;
6. no new bundled binary/font/dataset/model/asset lacks provenance and license;
7. Qt desktop obligations are resolved if PySide6 is included;
8. the notice bundle is physically present in the released artifact.
