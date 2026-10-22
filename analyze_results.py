import csv
from collections import defaultdict

file_path = "logs/experiments.csv"

stats = defaultdict(lambda: {
    "total_gas": 0,
    "total_latency": 0,
    "total_records": 0,
    "total_batches": 0
})

with open(file_path, "r") as f:
    reader = csv.DictReader(f)

    for row in reader:
        mode = row["mode"]
        gas = float(row["gas_used"])
        latency = float(row["chain_latency"])
        batch_size = int(row["batch_size"])

        stats[mode]["total_gas"] += gas
        stats[mode]["total_latency"] += latency
        stats[mode]["total_records"] += batch_size
        stats[mode]["total_batches"] += 1

print("\n===== EXPERIMENT RESULTS =====\n")

for mode, data in stats.items():
    avg_gas = data["total_gas"] / data["total_batches"]
    avg_latency = data["total_latency"] / data["total_batches"]
    gas_per_record = data["total_gas"] / data["total_records"]

    print(f"Mode: {mode}")
    print(f"  Total batches: {data['total_batches']}")
    print(f"  Total records: {data['total_records']}")
    print(f"  Avg gas per batch: {avg_gas:.2f}")
    print(f"  Avg gas per record: {gas_per_record:.2f}")
    print(f"  Avg chain latency: {avg_latency:.4f} sec")
    print("")
