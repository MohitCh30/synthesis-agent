# TrustAudit Agent

## The Problem

AI agents make promises. They say "I'll answer in one word" and then ramble for 50 words. They claim to follow constraints but provide no proof. How can you trust an AI that can't verify its own behavior?

## The Solution

**TrustAudit Agent** — an AI agent that executes tasks, audits its own output against stated constraints, assigns a trust score (0-1), and generates cryptographic proofs of execution integrity.

This agent doesn't just execute tasks. It proves it kept its promises.

## How It Works

```
User Request → Agent Execution → Constraint Validation → Trust Score + Execution Hash
```

1. **Execute**: Agent runs the task using local LLM (Mistral via Ollama)
2. **Extract**: Parse constraints from natural language ("answer in 1 word", "YES or NO only")
3. **Detect**: Find contradictory instructions before wasting compute
4. **Validate**: Check output against all constraints
5. **Score**: Compute trust score (0-1) with weighted deductions
6. **Prove**: Generate SHA256 execution hash for tamper detection

## Key Features

- **Self-Auditing**: Agent evaluates and verifies its own actions
- **Constraint Engine**: Parses max_words, max_lines, sentence_count, format constraints
- **Contradiction Detection**: Catches impossible requests ("answer in 1 word but explain")
- **Trust Scoring**: Weighted trust score with transparent deduction logic
- **Execution Proofs**: SHA256 hashes prove execution integrity
- **Immutable Logs**: Append-only SQLite logging for full auditability
- **Verification Endpoint**: Recompute hash to detect tampering
- **On-Chain Anchoring**: Execution proofs anchored on Base Sepolia

## Tech Stack

- **Backend**: FastAPI (Python)
- **LLM**: Ollama with Mistral model (local, private)
- **Database**: SQLite (immutable append-only logs)
- **Blockchain**: Base Sepolia (on-chain execution anchoring)
- **Hashing**: SHA256 for execution proofs
- **Verification**: On-chain anchored execution proofs via smart contract

## Tracks

1. **Agents that Trust** — This agent builds trust through transparency, verification, and self-auditing
2. **Agents that Cooperate** — Trust is essential for multi-agent cooperation; this system provides verifiable execution proofs

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Start Ollama (in background)
ollama serve

# Start the agent
uvicorn app.main:app --reload

# Test the agent
curl -X POST http://localhost:8000/agent/run \
  -H "Content-Type: application/json" \
  -d '{"input": "Is the sky blue? Answer YES or NO only."}'
```

## Demo Flow

See `demo.sh` for a complete demonstration showing:
1. Valid execution with trust_score = 1.0
2. Constraint violation with trust_score = 0.5
3. Contradiction detection before execution
4. Verification endpoint to detect tampering

## Why This Matters

In a world where AI agents make decisions, execute actions, and interact with each other, **trust is paramount**. TrustAudit Agent provides:

- **Transparency**: Every execution is logged with full metadata
- **Verification**: Hash-based proofs prevent tampering
- **Accountability**: Trust scores hold the agent accountable for its outputs
- **Interoperability**: Any party can verify execution integrity

## Project Structure

```
synthesis-agent/
├── app/
│   ├── main.py              # FastAPI app
│   ├── models.py            # Request/response schemas
│   ├── routes/agent.py      # API endpoints
│   ├── services/
│   │   ├── constraints.py   # Constraint parsing & validation
│   │   ├── logger.py       # Immutable logging
│   │   ├── verifier.py     # Hash computation & verification
│   │   ├── blockchain.py   # On-chain anchoring (Base Sepolia)
│   │   └── llm.py         # Ollama integration
│   └── db/database.py      # SQLite models
├── contracts/
│   └── ExecutionRegistry.sol  # Smart contract
├── logs/                    # Append-only execution logs
├── requirements.txt
├── demo.sh                  # Demo script
└── README.md
```

## On-Chain Verification

Execution hashes are anchored on **Base Sepolia** for trustless verification.

### On-Chain Proof

| Field | Value |
|-------|-------|
| Network | Base Sepolia |
| Transaction Hash | `0x227446a3a6c0a34ddfd1f4cfb3c0298b57372a59364ac982c6a923561cb3f859` |
| Block Number | 39107108 |
| Status | CONFIRMED |
| Contract | `0x03Ce9c7C6441Bd274DC462d1c682F976ee695526` |

### Transaction

<img width="1385" height="898" alt="Screenshot From 2026-03-20 10-32-47" src="https://github.com/user-attachments/assets/6605121d-28f1-4db6-8d07-2b496a135916" /> 

### Event Logs

<img width="1396" height="575" alt="Screenshot From 2026-03-20 10-34-50" src="https://github.com/user-attachments/assets/1a4a9469-895b-4a1c-ac46-d2b8de0d54b0" />

### What Was Stored

The execution hash of the AI agent's response to:
> "Approve treasury transfer of 5 ETH"

Stored hash (keccak256):
```
0x2f9b41e20e681182ed318d7ca4721195e289bdc5150d253cb24eac6c724b85d7
```

### Smart Contract Event

```solidity
event ExecutionStored(
    bytes32 indexed hash,
    address indexed sender,
    uint256 timestamp
);
```

### Verification

Anyone can verify by:
1. Finding the `tx_hash` in the response
2. Looking up the transaction on [Basescan](https://sepolia.basescan.org/tx/0x227446a3a6c0a34ddfd1f4cfb3c0298b57372a59364ac982c6a923561cb3f859)
3. Confirming the `ExecutionStored` event with matching hash

This provides **trustless verification** - no reliance on our server.

### How It Works

1. Every execution generates a SHA256 hash: `SHA256(input | output | timestamp)`
2. This hash is stored on-chain via `ExecutionRegistry` contract
3. Transaction hash provides immutable proof of execution
4. Anyone can verify by checking the contract events

### Deployment

```bash
# Deploy contract to Base Sepolia
# 1. Compile: npx hardhat compile
# 2. Deploy: npx hardhat run scripts/deploy.js --network base_sepolia

# Configure environment
export RPC_URL="https://sepolia.base.org"
export CONTRACT_ADDRESS="your_contract_address"
export PRIVATE_KEY="your_private_key"
export WALLET_ADDRESS="your_wallet_address"
```

### Verification

Anyone can verify an execution by:
1. Finding the `tx_hash` in the response
2. Looking up the transaction on Basescan
3. Confirming the `ExecutionStored` event with matching hash

This provides **trustless verification** - no reliance on our server.

## License

MIT
