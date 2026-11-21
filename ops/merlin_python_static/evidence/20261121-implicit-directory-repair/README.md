# Static Python archive layout repair — 2026-11-21

The exact archive retained from native run 44960327067 has 4,949 members and zero explicit directory headers. The original inspector successfully acquired and hash-verified the archive, then failed with `python_root_directory_missing`.

`ops/merlin_python_static/acquire_inspect.py` now derives missing ancestor directories only from validated member paths. It retains separate measured archive records, rejects explicit non-directory ancestors and escaping/dangling links, and bounds the entire logical namespace. `test_acquire_inspect.py` now includes the 12 relevant regressions. No scientific, formal or promotion semantics change.

Validation: all 35 local controls passed. Five targeted positive-layout regressions fail against the exact original inspector. Retained-archive replay reproduced the original error and completed with the repaired parser: 3,900 regular files, 1,049 symlinks, 255 inferred directories, 10 ELF files and 64 notices. Original regular-file, notice and ELF evidence remained byte-identical.

These are local Python3.12.14 results, with Python3.9 grammar checks. They do not establish native interpreter compatibility, installation, model inference or production qualification. No new download, execution of archive members, installation or provider change occurred.

The earlier acquisition workflow remains frozen to its original embedded source identities. Do not submit another acquisition request to use this repair. The separate native repair-validation route runs only fixtures and does not download or execute the archived interpreter. Source and evidence publication does not activate that route or a runtime.

Original operations source commit: `13b9267222c5b3235dfa72f063582ba0dffa832e`.
Repaired controller SHA256: `c3a5bd263d22a50a4872648e1a0934782c5f2cbb87d153b91adf84c67ce25ba2`.
Repaired test SHA256: `30f1a819dbb526622130b14a5579d203ede018300f8ed7d91c552b8df8d1ef3e`.
Full reproducibility checkpoint is preserved separately in the product evidence record; original native artifacts are preserved unchanged.
