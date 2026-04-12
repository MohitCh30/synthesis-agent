# AI Decision Agent

## Overview

The AI Decision Agent is a filtering layer between user input and blockchain storage. It analyzes AI agent responses and decides which executions warrant on-chain anchoring.

## Role

- **Decision Making**: Determine if an execution is significant enough for on-chain storage
- **Filtering**: Prevent trivial actions from consuming blockchain resources
- **Security**: Only allow financial and governance actions on-chain

## Decision Criteria

An execution is marked for on-chain storage if it meets ALL criteria:

### 1. Significance Check
Must contain at least one financial or governance keyword:
- Financial: `transfer`, `payment`, `approve`, `send`, `receive`, `deposit`, `withdraw`, `swap`, `mint`, `burn`, `stake`
- Governance: `vote`, `proposal`, `governance`, `treasury`, `dao`, `delegate`

### 2. Trust Score
Must have `trust_score >= 0.8` from the TrustAudit Agent.

### 3. Validity
Must have `valid = true` (no constraint violations).

## Input → Output Format

### Input
```javascript
{
  "input": "Approve treasury transfer of 5 ETH"
}
```

### AI Agent Response
```javascript
{
  "task_id": "uuid",
  "output": "APPROVED: 5 ETH transfer from Treasury to...",
  "trust_score": 1.0,
  "valid": true,
  "constraints": {...}
}
```

### Decision Output
```javascript
{
  "decision": true,
  "reason": "Significant financial/governance action with high trust",
  "output": "APPROVED: 5 ETH transfer from Treasury to..."
}
```

## Blockchain Interaction

### Flow
```
Input → AI Agent → Decision Agent → Hash → Smart Contract → Transaction
```

### Hash Computation
```javascript
const hash = ethers.keccak256(ethers.toUtf8Bytes(output));
```

### Smart Contract Call
```javascript
const tx = await contract.storeExecution(hash);
await tx.wait();
```

### Transaction Result
```javascript
{
  "success": true,
  "txHash": "0x...",
  "blockNumber": 39107108,
  "network": "base_sepolia"
}
```

## Examples

### Example 1: Significant Action (On-Chain)
```
Input: "Approve treasury transfer of 5 ETH"
Decision: true
Reason: Significant financial/governance action with high trust
On-Chain: YES
```

### Example 2: Trivial Action (Skipped)
```
Input: "Say hello"
Decision: false
Reason: Non-financial/non-governance action
On-Chain: NO (SKIPPED)
```

### Example 3: Low Trust (Skipped)
```
Input: "Answer in one word. Explain your reasoning."
Decision: false
Reason: Low trust score or invalid output
On-Chain: NO (SKIPPED)
```

## Usage

```bash
cd blockchain-agent
node src/agent.js "Your prompt here"
```

## Environment Variables

```bash
RPC_URL=https://sepolia.base.org
CONTRACT_ADDRESS=0x...
PRIVATE_KEY=0x...
```

## Error Handling

| Error | Response |
|-------|----------|
| AI Agent unreachable | `decision: false, error logged` |
| Invalid private key | `decision: false, tx failed` |
| Transaction timeout | `decision: true, tx: pending` |

## Security Considerations

- Private keys never logged or exposed
- Only significant actions consume gas
- Whitelisted keywords prevent spam
- Trust score provides additional filtering

## Architecture

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────┐
│   User     │────▶│  AI Agent       │────▶│  Decision    │
│   Input    │     │  (FastAPI)     │     │  Agent       │
└─────────────┘     └─────────────────┘     └──────┬───────┘
                                                    │
                                           ┌────────▼────────┐
                                           │  Blockchain      │
                                           │  (Base Sepolia)  │
                                           └──────────────────┘
```
