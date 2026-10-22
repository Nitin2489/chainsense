import os

from dotenv import load_dotenv

load_dotenv()
import time

from web3 import Web3

HARDHAT_URL = os.getenv(
    "MCS_RPC_URL",
    "http://127.0.0.1:8545",
)
CONTRACT_ADDRESS = os.getenv("MCS_CONTRACT_ADDRESS", "").strip()
PRIVATE_KEY = os.getenv("MCS_PRIVATE_KEY", "").strip()

ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "batchId", "type": "uint256"},
            {"internalType": "bytes32", "name": "commitHash", "type": "bytes32"},
            {"internalType": "uint256", "name": "batchSize", "type": "uint256"},
            {"internalType": "string", "name": "mode", "type": "string"},
        ],
        "name": "commitBatch",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "", "type": "uint256"}
        ],
        "name": "batches",
        "outputs": [
            {"internalType": "uint256", "name": "batchId", "type": "uint256"},
            {"internalType": "bytes32", "name": "commitHash", "type": "bytes32"},
            {"internalType": "uint256", "name": "batchSize", "type": "uint256"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
]

w3 = Web3(Web3.HTTPProvider(HARDHAT_URL))

if not w3.is_connected():
    raise ConnectionError(f"Cannot connect to blockchain RPC: {HARDHAT_URL}")

if not CONTRACT_ADDRESS:
    raise RuntimeError(
        "MCS_CONTRACT_ADDRESS is not set. Configure it in your environment."
    )

if not PRIVATE_KEY:
    raise RuntimeError(
        "MCS_PRIVATE_KEY is not set. Use a development-only key for local testing."
    )

account = w3.eth.account.from_key(PRIVATE_KEY)
contract_address = Web3.to_checksum_address(CONTRACT_ADDRESS)

if not w3.eth.get_code(contract_address):
    raise RuntimeError(
        f"No contract bytecode found at {contract_address} on the configured RPC."
    )

contract = w3.eth.contract(address=contract_address, abi=ABI)


def commit_to_chain(batch_id, commit_hash, batch_size, mode):
    """Submit a batch commitment and return (gas_used, confirmation_latency)."""
    normalized_hash = commit_hash.removeprefix("0x")

    try:
        commit_bytes = bytes.fromhex(normalized_hash)
    except ValueError as exc:
        raise ValueError("commit_hash must be a valid hexadecimal string") from exc

    if len(commit_bytes) != 32:
        raise ValueError("commit_hash must contain exactly 32 bytes")

    nonce = w3.eth.get_transaction_count(account.address)

    txn = contract.functions.commitBatch(
        batch_id,
        commit_bytes,
        batch_size,
        mode,
    ).build_transaction({
        "from": account.address,
        "nonce": nonce,
        "chainId": w3.eth.chain_id,
        "gas": 3000000,
        "gasPrice": w3.to_wei("1", "gwei"),
    })

    signed_txn = w3.eth.account.sign_transaction(txn, PRIVATE_KEY)

    start_time = time.perf_counter()
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    latency = time.perf_counter() - start_time

    if receipt.status != 1:
        raise RuntimeError(
            f"Batch commitment transaction failed: {tx_hash.hex()}"
        )

    return receipt.gasUsed, latency


def get_committed_batch(batch_id):
    """Read a batch commitment from the contract's public mapping."""
    result = contract.functions.batches(batch_id).call()
    return {
        "batch_id": result[0],
        "commit_hash": "0x" + result[1].hex().removeprefix("0x"),
        "batch_size": result[2],
        "timestamp": result[3],
    }

