import pytest

from crypto.merkle import (
    build_merkle_tree,
    get_merkle_proof,
    verify_merkle_proof,
)


def make_records(count):
    return [
        {"client_id": f"client_{i}", "payload": {"value": i}}
        for i in range(count)
    ]


@pytest.mark.parametrize("count", [1, 2, 3, 5, 20, 21, 100])
def test_batch_size(count):
    records = make_records(count)
    tree, root = build_merkle_tree(records)

    assert root is not None

    for index, record in enumerate(records):
        proof = get_merkle_proof(tree, index)

        assert verify_merkle_proof(record, proof, root, index), (
            f"Valid proof failed: batch_size={count}, index={index}"
        )

        changed = {
            **record,
            "payload": {"value": record["payload"]["value"] + 10000},
        }

        assert not verify_merkle_proof(changed, proof, root, index), (
            f"Tampered record passed: batch_size={count}, index={index}"
        )
