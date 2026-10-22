import importlib
import sys
import types

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def aggregator(monkeypatch):
    # Replace the blockchain module before importing the aggregator.
    fake_blockchain = types.ModuleType("servers.blockchain_client")
    fake_blockchain.commit_to_chain = lambda **kwargs: (21000, 0.01)
    fake_blockchain.get_committed_batch = lambda batch_id: None

    monkeypatch.setitem(
        sys.modules, "servers.blockchain_client", fake_blockchain
    )
    sys.modules.pop("servers.aggregator", None)

    module = importlib.import_module("servers.aggregator")

    module.current_batch = []
    module.batch_start_time = None
    module.completed_batches = []
    module.batch_counter = 0
    module.MODE = "batch_merkle"

    yield module

    sys.modules.pop("servers.aggregator", None)


@pytest.fixture
def client(aggregator):
    with TestClient(aggregator.app) as test_client:
        yield test_client


def test_stats_starts_empty(client):
    response = client.get("/stats")
    assert response.status_code == 200
    assert response.json()["completed_batches"] == 0


def test_verify_rejects_invalid_batch_id(client):
    response = client.post(
        "/verify", params={"batch_id": 1, "record_index": 0}
    )
    assert response.json() == {"error": "Invalid batch ID"}


def test_verify_rejects_invalid_record_index(client, aggregator):
    record = {"client_id": "client_0", "payload": {"value": 0}}
    aggregator.completed_batches = [
        {"records": [record], "tree": [["abc"]], "root": "abc"}
    ]

    response = client.post(
        "/verify", params={"batch_id": 1, "record_index": 5}
    )
    assert response.json() == {"error": "Invalid record index"}


def test_verify_rejects_non_merkle_mode(client, aggregator):
    aggregator.MODE = "batch_hash"
    record = {"client_id": "client_0", "payload": {"value": 0}}
    aggregator.completed_batches = [
        {"records": [record], "tree": [["abc"]], "root": "abc"}
    ]

    response = client.post(
        "/verify", params={"batch_id": 1, "record_index": 0}
    )
    assert response.json() == {
        "error": "Verification only valid for Merkle mode"
    }

def test_verify_accepts_valid_merkle_proof(client, aggregator):
    from crypto.merkle import build_merkle_tree

    records = [
        {"client_id": "client_0", "payload": {"value": 0}},
        {"client_id": "client_1", "payload": {"value": 1}},
        {"client_id": "client_2", "payload": {"value": 2}},
    ]
    tree, root = build_merkle_tree(records)

    aggregator.completed_batches = [
        {
            "batch_id": 1,
            "records": records,
            "tree": tree,
            "root": root,
        }
    ]
    
    aggregator.get_committed_batch = lambda batch_id: {
    "batch_id": 1,
    "commit_hash": "0x" + root,
    "batch_size": len(records),
    "timestamp": 123
    }

    response = client.post(
        "/verify", params={"batch_id": 1, "record_index": 1}
    )

    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is True
    assert result["batch_id"] == 1
    assert result["record_index"] == 1
    assert result["root"] == root
    assert result["proof_length"] == 2

def test_verify_rejects_record_changed_after_tree_creation(client, aggregator):
    from crypto.merkle import build_merkle_tree

    records = [
        {"client_id": "client_0", "payload": {"value": 0}},
        {"client_id": "client_1", "payload": {"value": 1}},
        {"client_id": "client_2", "payload": {"value": 2}},
    ]
    tree, root = build_merkle_tree(records)

    # Corrupt a record after its original Merkle tree was created.
    records[1] = {
        "client_id": "client_1",
        "payload": {"value": 999},
    }

    aggregator.completed_batches = [
        {
            "batch_id": 1,
            "records": records,
            "tree": tree,
            "root": root,
        }
    ]
    aggregator.get_committed_batch = lambda batch_id: {
    "batch_id": 1,
    "commit_hash": "0x" + root,
    "batch_size": len(records),
    "timestamp": 123
    }    

    response = client.post(
        "/verify", params={"batch_id": 1, "record_index": 1}
    )

    assert response.status_code == 200
    assert response.json()["valid"] is False
def test_verify_rejects_missing_blockchain_commitment(client, aggregator):
    from crypto.merkle import build_merkle_tree

    records = [
        {"client_id": "client_0", "payload": {"value": 0}}
    ]
    tree, root = build_merkle_tree(records)

    aggregator.completed_batches = [{
        "batch_id": 1,
        "records": records,
        "tree": tree,
        "root": root
    }]
    aggregator.get_committed_batch = lambda batch_id: None

    response = client.post(
        "/verify",
        params={"batch_id": 1, "record_index": 0}
    )

    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert response.json()["error"] == "No blockchain commitment found"


def test_verify_rejects_on_chain_root_mismatch(client, aggregator):
    from crypto.merkle import build_merkle_tree

    records = [
        {"client_id": "client_0", "payload": {"value": 0}}
    ]
    tree, root = build_merkle_tree(records)

    aggregator.completed_batches = [{
        "batch_id": 1,
        "records": records,
        "tree": tree,
        "root": root
    }]
    aggregator.get_committed_batch = lambda batch_id: {
        "batch_id": 1,
        "commit_hash": "0x" + "a" * 64,
        "batch_size": len(records),
        "timestamp": 123
    }

    response = client.post(
        "/verify",
        params={"batch_id": 1, "record_index": 0}
    )

    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert "does not match" in response.json()["error"]


def test_verify_rejects_on_chain_batch_size_mismatch(client, aggregator):
    from crypto.merkle import build_merkle_tree

    records = [
        {"client_id": "client_0", "payload": {"value": 0}}
    ]
    tree, root = build_merkle_tree(records)

    aggregator.completed_batches = [{
        "batch_id": 1,
        "records": records,
        "tree": tree,
        "root": root
    }]
    aggregator.get_committed_batch = lambda batch_id: {
        "batch_id": 1,
        "commit_hash": "0x" + root,
        "batch_size": 2,
        "timestamp": 123
    }

    response = client.post(
        "/verify",
        params={"batch_id": 1, "record_index": 0}
    )

    assert response.status_code == 200
    assert response.json()["valid"] is False
    assert response.json()["error"] == "On-chain batch size mismatch"