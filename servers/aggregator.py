from fastapi import FastAPI
from pydantic import BaseModel
import threading
import time
import hashlib
import json
import os
import csv

from crypto.merkle import (
    build_merkle_tree,
    get_merkle_proof,
    verify_merkle_proof
)

from servers.blockchain_client import commit_to_chain, get_committed_batch


app = FastAPI()

# ==========================================================
# CONFIGURATION
# ==========================================================

BATCH_SIZE = 20
MODE = "batch_merkle"   # "direct" | "batch_hash" | "batch_merkle"

LOG_FILE = "logs/experiments.csv"

# ==========================================================
# DATA MODEL
# ==========================================================

class Submission(BaseModel):
    client_id: str
    payload: dict
    signature: str
    timestamp: float


# ==========================================================
# STATE
# ==========================================================

current_batch = []
batch_start_time = None

completed_batches = []
batch_counter = 0

lock = threading.Lock()


# ==========================================================
# HELPERS
# ==========================================================

def simple_batch_hash(records):
    raw = json.dumps(records, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()


def log_to_csv(row):
    file_exists = os.path.isfile(LOG_FILE)

    os.makedirs("logs", exist_ok=True)

    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow([
                "timestamp",
                "mode",
                "batch_id",
                "batch_size",
                "commit_time",
                "chain_latency",
                "gas_used",
                "gas_per_record"
            ])

        writer.writerow(row)


# ==========================================================
# MAIN SUBMISSION ENDPOINT
# ==========================================================

@app.post("/submit")
def submit_data(data: Submission):

    global current_batch, batch_start_time, batch_counter

    with lock:

        # ==================================================
        # DIRECT MODE (each record on-chain)
        # ==================================================
        if MODE == "direct":

            commit_hash = simple_batch_hash([data.dict()])

            gas_used, chain_latency = commit_to_chain(
                batch_id=0,
                commit_hash=commit_hash,
                batch_size=1,
                mode="direct"
            )

            log_to_csv([
                time.time(),
                "direct",
                0,
                1,
                0,
                chain_latency,
                gas_used,
                gas_used
            ])

            return {"status": "ok", "mode": "direct"}


        # ==================================================
        # BATCHED MODES
        # ==================================================

        if not current_batch:
            batch_start_time = time.time()

        current_batch.append(data.dict())

        if len(current_batch) >= BATCH_SIZE:

            batch_counter += 1
            batch_end_time = time.time()

            records_copy = current_batch.copy()

            # -------------------------------
            # Commit generation
            # -------------------------------

            commit_start = time.time()

            if MODE == "batch_hash":
                commit_value = simple_batch_hash(records_copy)
                tree = None

            elif MODE == "batch_merkle":
                tree, commit_value = build_merkle_tree(records_copy)

            else:
                return {"error": "Invalid mode"}

            commit_time = time.time() - commit_start

            # -------------------------------
            # Real Blockchain Commit
            # -------------------------------

            gas_used, chain_latency = commit_to_chain(
                batch_id=batch_counter,
                commit_hash=commit_value,
                batch_size=len(records_copy),
                mode=MODE
            )

            gas_per_record = gas_used / len(records_copy)

            # -------------------------------
            # Save Batch Info
            # -------------------------------

            batch_info = {
                "batch_id": batch_counter,
                "records": records_copy,
                "root": commit_value,
                "tree": tree,
                "start_time": batch_start_time,
                "end_time": batch_end_time
            }

            completed_batches.append(batch_info)

            # -------------------------------
            # Log Results
            # -------------------------------

            log_to_csv([
                time.time(),
                MODE,
                batch_counter,
                len(records_copy),
                commit_time,
                chain_latency,
                gas_used,
                gas_per_record
            ])

            print("\nðŸ“¦ Batch CLOSED")
            print("Mode:", MODE)
            print("Batch ID:", batch_counter)
            print("Records:", len(records_copy))
            print("Gas:", gas_used)
            print("Gas / record:", round(gas_per_record, 2))

            # Reset batch
            current_batch = []
            batch_start_time = None

    return {"status": "ok", "mode": MODE}


# ==========================================================
# VERIFICATION ENDPOINT
# ==========================================================

# ==========================================================
# VERIFICATION ENDPOINT
# ==========================================================

@app.post("/verify")
def verify(batch_id: int, record_index: int):

    if batch_id <= 0 or batch_id > len(completed_batches):
        return {"error": "Invalid batch ID"}

    batch = completed_batches[batch_id - 1]

    if record_index < 0 or record_index >= len(batch["records"]):
        return {"error": "Invalid record index"}

    if MODE != "batch_merkle":
        return {"error": "Verification only valid for Merkle mode"}

    # Retrieve the commitment stored on-chain.
    try:
        on_chain_batch = get_committed_batch(batch_id)
    except Exception as exc:
        print(f"Blockchain verification lookup failed: {exc}")
        return {
            "valid": False,
            "error": "Unable to retrieve blockchain commitment"
        }

    if not on_chain_batch:
        return {
            "valid": False,
            "error": "No blockchain commitment found"
        }

    # Check that the returned commitment belongs to this batch.
    if on_chain_batch["batch_id"] != batch_id:
        return {
            "valid": False,
            "error": "On-chain batch ID mismatch"
        }

    # Ensure the blockchain commitment represents the local batch size.
    if on_chain_batch["batch_size"] != len(batch["records"]):
        return {
            "valid": False,
            "error": "On-chain batch size mismatch"
        }

    # Normalize the root and the on-chain bytes32 hash.
    local_root = batch["root"].removeprefix("0x").lower()
    on_chain_root = (
        on_chain_batch["commit_hash"].removeprefix("0x").lower()
    )

    if not on_chain_root or on_chain_root == "0" * 64:
        return {
            "valid": False,
            "error": "No valid blockchain commitment found"
        }

    # The local Merkle root must match the blockchain commitment.
    if local_root != on_chain_root:
        return {
            "valid": False,
            "error": "Local Merkle root does not match blockchain commitment"
        }

    # Verify the record's proof against the committed on-chain root.
    record = batch["records"][record_index]
    tree = batch["tree"]
    proof = get_merkle_proof(tree, record_index)

    is_valid = verify_merkle_proof(
        record,
        proof,
        on_chain_root,
        record_index
    )

    return {
        "valid": is_valid,
        "batch_id": batch_id,
        "record_index": record_index,
        "root": on_chain_root,
        "proof_length": len(proof),
        "blockchain_verified": True
    }


# ==========================================================
# STATS
# ==========================================================

@app.get("/stats")
def stats():
    return {
        "mode": MODE,
        "open_batch_size": len(current_batch),
        "completed_batches": len(completed_batches)
    }

