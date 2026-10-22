import hashlib
import json


def hash_data(data):
    if isinstance(data, dict):
        data = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def hash_pair(left, right):
    return hashlib.sha256((left + right).encode("utf-8")).hexdigest()


def build_merkle_tree(records):
    leaves = [hash_data(record) for record in records]

    if not leaves:
        return [], None

    tree = [leaves]

    while len(tree[-1]) > 1:
        level = tree[-1]
        next_level = []

        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i + 1] if i + 1 < len(level) else left
            next_level.append(hash_pair(left, right))

        tree.append(next_level)

    return tree, tree[-1][0]


def get_merkle_proof(tree, index):
    if not tree or index < 0 or index >= len(tree[0]):
        raise ValueError("Invalid Merkle tree or leaf index")

    proof = []

    for level in tree[:-1]:
        sibling_index = index ^ 1

        if sibling_index < len(level):
            proof.append(level[sibling_index])
        else:
            proof.append(level[index])

        index //= 2

    return proof


def verify_merkle_proof(record, proof, root, index):
    if index < 0:
        return False

    current_hash = hash_data(record)

    for sibling in proof:
        if index % 2 == 0:
            current_hash = hash_pair(current_hash, sibling)
        else:
            current_hash = hash_pair(sibling, current_hash)

        index //= 2

    return current_hash == root
