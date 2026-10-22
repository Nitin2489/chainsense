import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv(
    "logs/experiments.csv",
    engine="python",
    on_bad_lines="skip"
)

print("Total valid rows:", len(df))

summary = df.groupby("mode").agg({
    "gas_used": "mean",
    "gas_per_record": "mean",
    "chain_latency": "mean",
    "batch_id": "count"
}).reset_index()

summary.rename(columns={"batch_id": "total_batches"}, inplace=True)

print("\n===== SUMMARY =====\n")
print(summary)
