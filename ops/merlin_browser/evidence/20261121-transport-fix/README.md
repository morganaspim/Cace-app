# Browser root-payload transport follow-up

## Observed failure

The approved browser continuation [run 44956001171](https://github.com/morganaspim/Cace-app/actions/runs/44956001171) failed before the continuation controller started. Its 33 controller controls and 41 product browser tests passed on the actual `cace-oci-a1` runner using Python 3.9.25. These are executions of existing scoped tests, not additional unique product cases or successful live browser acceptance.

The root journal reports `ValueError: base85 overflow in hunk starting at byte 12805` on the second line of the generated Python program, while decoding the first embedded module. None of the embedded modules had executed. Root retained-state inspection, durable request-marker creation, retained arXiv recovery, new source submissions, pointer changes, supervisor activation, restart readback and rollback were not reached. The transient root launch itself did start and fail.

This run therefore reached zero new public-source submissions. The workflow's plan records two remaining public attempts, but it is not a fresh ledger observation: the actual host ledger, provider, package state and launcher pointer were not read by the root controller. A future authorized continuation must perform all existing preflight and ledger checks. Do not rerun the original request.

The original 239,597-byte artifact has SHA-256 `aa1ae30cd94a72f011ea03ce58560bbd5044c4fce7adf7a77ee1a67c3feab9db`. Its 40 files, archive CRC, eight source pins, 14 runtime payload files and runtime manifest were verified. The exact archive, decoded job log and API metadata are preserved in the neighboring `browser-continuation-44956001171` directory. The decisive journal, original workflow, launch identity and interpretation are copied into this follow-up's `evidence` directory.

## Smallest correction

The corrected workflow changes exactly two lines: standard Base64 replaces Base85 for compressed source capsules, and decoding uses `base64.b64decode(..., validate=True)`. The standard Base64 alphabet excludes both dollar and percent characters.

All controller, runtime, helper, test, action, request, budget, identity, deadline, privilege and service-launch settings remain byte-identical. No new option or dependency on a newer systemd version is introduced. The original frozen source files and publication maps are untouched.

The authoritative [systemd 252 command-line documentation](https://www.freedesktop.org/software/systemd/man/252/systemd.service.html#Command%20lines) specifies braced variable replacement within arguments, substitution of unknown values with empty strings, and doubled-dollar escaping. The [systemd-run documentation](https://www.freedesktop.org/software/systemd/man/latest/systemd-run.html) explains that the service manager applies argument expansion. Its convenience switch to disable expansion was introduced in version 254; this repair does not depend on it.

The preserved original capsule decodes normally to its approved source hash. Applying the relevant documented argument-expansion rules locally produces the exact observed error at byte 12805. This supports the transport diagnosis; it is not a capture of the native process's received argument, and the regression does not claim to reproduce the whole service manager.

## Focused verification

Four offline transport controls pass, with no errors, failures or skips. They verify the exact two-line workflow delta and approved inputs; reproduce the original error at the observed byte offset; recover all five corrected module byte streams under the same expansion model; reject nonalphabet input with strict decoding; and preserve the existing argument bound and service recipe. The module code is decoded and hashed only, never imported or executed.

The corrected root argument is 77,805 bytes for the original run metadata, compared with 73,049 bytes before. Total argv size becomes 78,338 bytes and argument count remains 29. The existing 115,000-byte runtime check remains in place for the next run's actual metadata. These sizes are the exact serialization delta applied to the observed launch identity, not a new native launch measurement.

Reproduce the focused controls from this directory with a fresh output directory:

```sh
python3 -I -B verify_transport.py \
  --artifact ../browser-continuation-44956001171/artifact \
  --output /tmp/merlin-browser-transport-review-new
```

The corrected workflow is 19,929 bytes, SHA-256 `2093b64ad89e68add600d4bbd7b70c933b26276bfd01eec1b19acc31cb55fc3f`. The original is 19,915 bytes, SHA-256 `140122b0082f4e13237a140117a98427cb084498f252dcf8722c7d89e3202f98`.

## Publication and execution boundary

This is a local reviewable follow-up only. It creates no request, dispatch, rerun, package installation, provider call or host change. Publication may replace only the active workflow and add scoped evidence. Any subsequent execution must use a distinct request and retain all original source, ledger, serialization and host preconditions. Native success remains unverified.
