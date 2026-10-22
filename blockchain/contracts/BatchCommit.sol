// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract BatchCommit {

    struct BatchRecord {
        uint256 batchId;
        bytes32 commitHash;
        uint256 batchSize;
        uint256 timestamp;
        string mode;
    }

    mapping(uint256 => BatchRecord) public batches;

    uint256 public totalBatches;

    event BatchCommitted(
        uint256 indexed batchId,
        bytes32 commitHash,
        uint256 batchSize,
        uint256 timestamp,
        string mode
    );

    function commitBatch(
        uint256 batchId,
        bytes32 commitHash,
        uint256 batchSize,
        string calldata mode
    ) external {

        batches[batchId] = BatchRecord({
            batchId: batchId,
            commitHash: commitHash,
            batchSize: batchSize,
            timestamp: block.timestamp,
            mode: mode
        });

        totalBatches++;

        emit BatchCommitted(
            batchId,
            commitHash,
            batchSize,
            block.timestamp,
            mode
        );
    }
}
