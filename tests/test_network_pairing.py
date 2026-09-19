from __future__ import annotations

import sqlite3

import pytest

from cace_studio.network_pairing import (
    NetworkPairingService,
    PAIRING_CAPABILITIES,
)


def test_enable_returns_separate_directional_codes_and_hashes_only(tmp_path):
    service = NetworkPairingService(tmp_path / "network.db")
    codes = service.enable("acct-a")
    assert codes.receive_code.startswith("CACE-RCV-")
    assert codes.outgoing_code.startswith("CACE-OUT-")
    assert codes.receive_code != codes.outgoing_code
    assert codes.capabilities == PAIRING_CAPABILITIES

    with sqlite3.connect(tmp_path / "network.db") as db:
        stored = [row[0] for row in db.execute("SELECT code_hash FROM pairing_codes")]
    assert codes.receive_code not in stored
    assert codes.outgoing_code not in stored
    assert all(len(value) == 64 for value in stored)


def test_outgoing_connection_consumes_source_outgoing_and_peer_receive(tmp_path):
    service = NetworkPairingService(tmp_path / "network.db")
    a = service.enable("acct-a", instance_id="a")
    b = service.enable("acct-b", instance_id="b")

    link, replacement = service.connect_outgoing(
        "acct-a",
        "a",
        b.receive_code,
    )
    assert link.source_instance_id == "a"
    assert link.target_instance_id == "b"
    assert link.capabilities == PAIRING_CAPABILITIES
    assert replacement["replacement_code"].startswith("CACE-OUT-")

    with pytest.raises(PermissionError):
        service.connect_outgoing("acct-a", "a", b.receive_code)


def test_incoming_accept_uses_peer_outgoing_code(tmp_path):
    service = NetworkPairingService(tmp_path / "network.db")
    a = service.enable("acct-a", instance_id="a")
    b = service.enable("acct-b", instance_id="b")

    link, replacement = service.accept_incoming(
        "acct-b",
        "b",
        a.outgoing_code,
    )
    assert link.source_instance_id == "a"
    assert link.target_instance_id == "b"
    assert replacement["replacement_code"].startswith("CACE-RCV-")


def test_bidirectional_link_requires_second_explicit_pairing(tmp_path):
    service = NetworkPairingService(tmp_path / "network.db")
    a = service.enable("acct-a", instance_id="a")
    b = service.enable("acct-b", instance_id="b")
    forward, _ = service.connect_outgoing("acct-a", "a", b.receive_code)
    assert forward.source_instance_id == "a"

    a_receive = service.rotate("acct-a", "a", "receive")
    b_outgoing = service.rotate("acct-b", "b", "outgoing")
    reverse, _ = service.connect_outgoing(
        "acct-b",
        "b",
        a_receive["code"],
    )
    assert reverse.source_instance_id == "b"
    assert reverse.target_instance_id == "a"


def test_disable_revokes_links_and_codes(tmp_path):
    service = NetworkPairingService(tmp_path / "network.db")
    a = service.enable("acct-a", instance_id="a")
    b = service.enable("acct-b", instance_id="b")
    service.connect_outgoing("acct-a", "a", b.receive_code)
    service.disable("acct-a", "a")
    status = service.status("acct-a", "a")
    assert status["enabled"] is False
    assert status["links"] == []
    with pytest.raises(PermissionError):
        service.connect_outgoing("acct-a", "a", b.receive_code)


def test_pairing_never_grants_privileged_capabilities(tmp_path):
    forbidden = {
        "shell",
        "filesystem",
        "proof.write",
        "evidence.write",
        "wallet.private_key",
        "model.control",
        "plugin.install",
    }
    assert forbidden.isdisjoint(PAIRING_CAPABILITIES)
