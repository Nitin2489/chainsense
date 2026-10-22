import csv
import json
import os
import time
import hashlib
from pathlib import Path

from dotenv import load_dotenv
from servers.blockchain_client import commit_to_chain
from crypto.merkle import build_merkle_tree

load_dotenv()

RECORDS_PER_METHOD = 2000
BATCH_SIZE = 20
OUTPUT_DIR = Path("logs/benchmarks")

MODES = ("direct", "batch_hash", "batch_merkle")


def record_hash(record):
    raw = json.dumps(record, sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()


def generate_records(count):
    # Deterministic synthetic records make runs reproducible.
    return [
        {
            "client_id": f"benchmark_client_{i}",
            "payload": {
                "temperature": 20 + (i % 150) / 10,
                "humidity": 30 + (i % 600) / 10,
                "sequence": i,
            },
            "signature": f"benchmark_placeholder_{i}",
            "timestamp": 1_800_000_000 + i,
        }
        for i in range(count)
    ]


def commitment_for(mode, records):
    if mode == "direct":
        return record_hash(records[0])

    if mode == "batch_hash":
        raw = json.dumps(records, sort_keys=True).encode()
        return hashlib.sha256(raw).hexdigest()

    if mode == "batch_merkle":
        _, root = build_merkle_tree(records)
        return root

    raise ValueError(f"Unknown mode: {mode}")


def run():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    records = generate_records(RECORDS_PER_METHOD)
    output_path = OUTPUT_DIR / "benchmark_results.csv"

    rows = []

    # Distinct IDs avoid overwriting commitments from other methods.
    next_batch_id = int(time.time()) * 1000

    for mode in MODES:
        chunks = (
            [[record] for record in records]
            if mode == "direct"
            else [
                records[i:i + BATCH_SIZE]
                for i in range(0, len(records), BATCH_SIZE)
            ]
        )

        for chunk_index, chunk in enumerate(chunks):
            batch_id = next_batch_id
            next_batch_id += 1

            start = time.perf_counter()
            commitment = commitment_for(mode, chunk)
            commit_generation_seconds = time.perf_counter() - start

            gas_used, chain_latency = commit_to_chain(
                batch_id=batch_id,
                commit_hash=commitment,
                batch_size=len(chunk),
                mode=mode,
            )

            rows.append({
                "mode": mode,
                "batch_id": batch_id,
                "batch_size": len(chunk),
                "gas_used": gas_used,
                "gas_per_record": gas_used / len(chunk),
                "commit_generation_seconds": commit_generation_seconds,
                "chain_latency_seconds": chain_latency,
            })

            if (chunk_index + 1) % 10 == 0 or chunk_index + 1 == len(chunks):
                print(
                    f"{mode}: {chunk_index + 1}/{len(chunks)} transactions"
                )

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nSaved raw results to: {output_path.resolve()}")

    print("\n=== SUMMARY ===")
    for mode in MODES:
        selected = [row for row in rows if row["mode"] == mode]
        total_records = sum(row["batch_size"] for row in selected)
        total_gas = sum(row["gas_used"] for row in selected)
        print(
            f"{mode}: transactions={len(selected)}, "
            f"records={total_records}, total_gas={total_gas:,}, "
            f"gas_per_record={total_gas / total_records:.2f}"
        )


if __name__ == "__main__":
    run()