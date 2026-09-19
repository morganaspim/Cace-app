from __future__ import annotations

import numpy as np

from cace_studio.ai.latent_observer import MatrixObserverArchive, MultiObserverBroker


def test_two_observers_receive_identical_matrix_digest(tmp_path):
    a = MatrixObserverArchive(tmp_path / "a", replica_id="a")
    b = MatrixObserverArchive(tmp_path / "b", replica_id="b")
    broker = MultiObserverBroker((a, b))
    matrix = np.arange(24, dtype=np.float32).reshape(3, 8)
    result = broker.fanout(
        run_id="run1",
        model_digest="model123",
        layer_name="block.2",
        layer_index=2,
        step_index=4,
        matrix=matrix,
        capture_mode="hash-only",
    )
    assert result.digests_match is True
    assert len({item.replica_id for item in result.observations}) == 2


def test_full_capture_is_content_addressed(tmp_path):
    archive = MatrixObserverArchive(tmp_path, replica_id="a")
    matrix = np.eye(4, dtype=np.float32)
    first = archive.observe(
        run_id="r", model_digest="m", layer_name="l", layer_index=0, step_index=0,
        matrix=matrix, capture_mode="full"
    )
    second = archive.observe(
        run_id="r", model_digest="m", layer_name="l", layer_index=0, step_index=0,
        matrix=matrix, capture_mode="full"
    )
    assert first.matrix_sha256 == second.matrix_sha256
    assert first.artifact_path == second.artifact_path


def test_full_capture_budget_fails_closed(tmp_path):
    archive = MatrixObserverArchive(tmp_path, replica_id="a")
    matrix = np.ones((128, 128), dtype=np.float32)
    try:
        archive.observe(
            run_id="r", model_digest="m", layer_name="l", layer_index=0, step_index=0,
            matrix=matrix, capture_mode="full", max_full_bytes=16
        )
    except ValueError as exc:
        assert "byte budget" in str(exc)
    else:
        raise AssertionError("oversize activation capture must fail closed")
