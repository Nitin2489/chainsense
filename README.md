# ChainSense

**Blockchain-Anchored Crowd Sensing**  
*FastAPI · Solidity · Hardhat · Python · Merkle Trees*

ChainSense is a hybrid off-chain/on-chain prototype for mobile crowd sensing. Sensing records are handled off-chain by a FastAPI aggregator, while compact batch commitments are anchored to an Ethereum-compatible smart contract. Merkle batching enables verification that an individual record belongs to a committed batch without placing raw sensing data on-chain.

## Highlights

- **Hybrid architecture:** keep sensing payloads off-chain and anchor compact commitments on-chain.
- **Merkle-root commitments:** commit a 32-byte Merkle root for each batch.
- **Record-level verification:** generate Merkle inclusion proofs with **O(log B)** proof size/work for a batch of size **B**.
- **Benchmark modes:** compare direct per-record commits, flat batch-hash commits, and Merkle batch commits.
- **Experiment logging:** record transaction gas, gas per record, latency, batch size, and mode in CSV output.
- **Test coverage:** unit tests cover the Merkle implementation and aggregator behavior.

## Architecture

1. Simulated clients submit sensing records to the FastAPI aggregator.
2. The aggregator collects records into batches.
3. In direct mode, records are committed individually. In batch-hash mode, a batch hash is committed. In batch-Merkle mode, the Merkle root is committed.
4. The Solidity contract stores batch commitment metadata on the EVM chain.
5. In Merkle mode, an inclusion proof can be checked against the committed root to verify membership of a record in a batch.

Raw sensing payloads are not stored on-chain by this prototype. A commitment provides tamper evidence for the committed data; it does not by itself prove that a sensor reading is truthful.

## Benchmark results

The latest recorded local Hardhat benchmark processed **2,000 synthetic records per mode**:

| Mode | Transactions | Records | Total gas | Gas per record |
|---|---:|---:|---:|---:|
| Direct | 2,000 | 2,000 | 287,020,928 | 143,510.46 |
| Flat batch hash (batch size 20) | 100 | 2,000 | 14,355,820 | 7,177.91 |
| Merkle batch (batch size 20) | 100 | 2,000 | 14,358,208 | 7,179.10 |

In this run, Merkle batching reduced gas per record by approximately **95%** compared with direct commits. Merkle and flat-hash batching had similar gas costs; Merkle's distinguishing benefit is record-level inclusion proofs.

**How to interpret these results:** measurements are from a local Hardhat network and synthetic records, not a public Ethereum deployment or real sensor deployment. Gas values depend on contract state and benchmark methodology. Treat the table above as the latest run recorded in `logs/benchmarks/benchmark_results.csv`; older figures in project notes or a resume may come from a different run and should not be presented as this run's measurements.

## Tech stack

- **API / aggregation:** Python, FastAPI
- **Smart contract:** Solidity
- **Local EVM development:** Hardhat
- **Blockchain client:** Web3.py
- **Integrity verification:** SHA-256 Merkle tree and inclusion proofs
- **Testing / analysis:** pytest, CSV benchmark logs, Python analysis scripts

## Repository layout

```text
blockchain/       Solidity contract, deployment scripts, and blockchain configuration
clients/          Simulated client and benchmark utilities
crypto/           Merkle tree and proof implementation
servers/          FastAPI aggregator and blockchain client
tests/            Merkle and aggregator tests
logs/benchmarks/  Recorded benchmark results
```

Other root-level scripts support benchmark execution and results analysis.

## Run locally

Use Python and Node.js/npm versions compatible with the project's dependency files.

1. Install Python dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

2. Install the blockchain project dependencies from the `blockchain` directory using its package lockfile.

3. Start a local Hardhat node and deploy `BatchCommit.sol` using the project's deployment scripts.

4. Configure your local environment using `.env.example`. Set the local RPC URL, deployed contract address, and a **local development account key only**. Never commit `.env` or a real wallet private key.

5. Start the FastAPI aggregator using the project's configured entry point, then run the benchmark and tests:

   ```powershell
   python -m pytest .\tests -q
   python .\benchmark_methods.py
   ```

Check the scripts and configuration in this repository for the exact working directory and entry-point details.

## Current scope and limitations

- Sensor inputs are simulated; this is a prototype, not a production mobile sensing deployment.
- Blockchain measurements reported here use a local Hardhat network, not public-chain gas fees.
- The prototype uses a single aggregator and does not establish truthfulness of sensor inputs.
- Adaptive batching is a design direction, not a claim that live adaptive batch sizing is fully integrated.
- Replay protection, signing-key management, privacy, and production threat handling require further end-to-end validation.

## License

See [LICENSE](LICENSE).
