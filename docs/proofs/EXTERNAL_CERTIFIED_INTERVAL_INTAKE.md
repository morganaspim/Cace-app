# Compatible external proof intake
Change class E; tracks A/B/I; existing goal G062.
CACE base: 0e7aa229d3bb57174e281b883ee8af5445f15f75.
LeanCert: 8a0104b8a8472e3c4695791c0671d89a37ae404f.
Keep Lean and Mathlib v4.32.1; resolve Mathlib to 520045ab14e26149ee970e2e617ca04b09bde5d6.
First quarantine CACEFormal.CertifiedIntervalBounds, compile it and audit all seven theorem targets.
Reject every axiom except propext, Classical.choice, Quot.sound.
Reject unfinished CACE proof source; test rejection of an invalid upper certificate.
Only after standalone success move the module to the audited root allowlist and compile root and audits.
Runtime source-to-formal object identity remains an explicit theorem hypothesis; arbitrary Python/C++ data is not promoted.
Canonical public claim promotion stays separate and requires the existing qualification gate.
