# AI Decision Agent with On-Chain Verification

Integrates with TrustAudit Agent to store high-trust executions on-chain.

## Setup

```bash
cd blockchain-agent
npm install
cp .env.example .env
# Edit .env with your values
```

## Usage

```bash
node src/agent.js "Your prompt here"
```

## Examples

```bash
# Important - will be stored on-chain
node src/agent.js "Approve treasury transfer of 5 ETH"

# Trivial - will be skipped
node src/agent.js "Say hello"
```

## Flow

1. Send prompt to TrustAudit Agent
2. Parse response (trust_score, valid, constraints)
3. If decision=true → hash output → store on-chain
4. If decision=false → skip

## Output

```
=== AI Decision Agent ===
Input: "Approve treasury transfer of 5 ETH"

Decision: true
Reason: High trust execution with constraints
Output: APPROVE_TREASURY_TRANSFER:5_ETH

--- On-Chain Storage ---
Hash: 0x...
Tx Hash: 0x...
Status: CONFIRMED
```
