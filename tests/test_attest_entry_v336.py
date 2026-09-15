from __future__ import annotations

import json

from cace_studio.attest_entry import main


def test_keygen_rejects_same_private_and_public_path_before_writing(tmp_path, capsys):
    target = tmp_path / "same.pem"
    code = main(
        [
            "keygen",
            "--private-key",
            str(target),
            "--public-key",
            str(target),
        ]
    )
    assert code == 2
    assert not target.exists()
    payload = json.loads(capsys.readouterr().err)
    assert payload["error_type"] == "ValueError"


def test_keygen_preflights_both_existing_outputs_before_partial_write(tmp_path, capsys):
    private_key = tmp_path / "new-private.pem"
    public_key = tmp_path / "existing-public.pem"
    public_key.write_text("existing", encoding="utf-8")

    code = main(
        [
            "keygen",
            "--private-key",
            str(private_key),
            "--public-key",
            str(public_key),
        ]
    )
    assert code == 2
    assert not private_key.exists()
    assert public_key.read_text(encoding="utf-8") == "existing"
    payload = json.loads(capsys.readouterr().err)
    assert payload["error_type"] == "FileExistsError"
