// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract ExecutionRegistry {
    event ExecutionStored(
        bytes32 indexed hash,
        address indexed sender,
        uint256 timestamp
    );

    function storeExecution(bytes32 hash) public {
        emit ExecutionStored(hash, msg.sender, block.timestamp);
    }
}
