import csv
import math
from collections import defaultdict
from pathlib import Path

LOG_FILE = Path("logs/experiments.csv")
EXPECTED_COLUMNS = [
    "timestamp",
    "mode",
    "batch_id",
    "batch_size",
    "commit_time",
    "chain_latency",
    "gas_used",
    "gas_per_record",
]

def main():
    if not LOG_FILE.exists():
        raise SystemExit(f"Missing experiment log: {LOG_FILE}")

    results = defaultdict(list)
    malformed = 0

    with LOG_FILE.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.reader(handle)

        for row in reader:
            if not row or all(not value.strip() for value in row):
                continue

            if len(row) != len(EXPECTED_COLUMNS):
                malformed += 1
                continue

            try:
                timestamp, mode, batch_id, batch_size, commit_time, latency, gas, gas_per_record = row

                item = {
                    "timestamp": float(timestamp),
                    "mode": mode.strip(),
                    "batch_id": int(batch_id),
                    "batch_size": int(batch_size),
                    "commit_time": float(commit_time),
                    "chain_latency": float(latency),
                    "gas_used": int(gas),
                    "gas_per_record": float(gas_per_record),
                }

                numeric_values = [
                    item["timestamp"],
                    item["commit_time"],
                    item["chain_latency"],
                    item["gas_per_record"],
                ]

                if (
                    not item["mode"]
                    or item["batch_size"] <= 0
                    or item["gas_used"] <= 0
                    or any(not math.isfinite(value) for value in numeric_values)
                    or any(value < 0 for value in numeric_values[1:])
                ):
                    malformed += 1
                    continue

                results[item["mode"]].append(item)

            except (ValueError, OverflowError):
                malformed += 1

    print(f"Valid rows: {sum(len(rows) for rows in results.values())}")
    print(f"Rejected rows: {malformed}")

    if not results:
        raise SystemExit("No valid experiment rows found.")

    print("\n===== SUMMARY BY MODE =====")
    for mode, rows in sorted(results.items()):
        total_records = sum(row["batch_size"] for row in rows)
        total_gas = sum(row["gas_used"] for row in rows)

        print(f"\nMode: {mode}")
        print(f"  Transactions/batches logged: {len(rows)}")
        print(f"  Records represented:         {total_records}")
        print(f"  Mean gas per transaction:    {total_gas / len(rows):.2f}")
        print(f"  Total gas / records:         {total_gas / total_records:.2f}")
        print(f"  Mean recorded gas/record:    {sum(r['gas_per_record'] for r in rows) / len(rows):.2f}")
        print(f"  Mean chain latency (s):      {sum(r['chain_latency'] for r in rows) / len(rows):.6f}")
        print(f"  Mean commit computation (s): {sum(r['commit_time'] for r in rows) / len(rows):.6f}")
        print(f"  Batch sizes:                 {sorted(set(r['batch_size'] for r in rows))}")

    modes = set(results)
    if len(modes) < 2:
        print("\nComparison unavailable: logs contain fewer than two modes.")
        print("Run controlled experiments before calculating a gas-reduction claim.")

if __name__ == "__main__":
    main()
