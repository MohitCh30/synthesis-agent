# TrustAudit Agent

**AI outputs you can verify, validate, and trust.**

---

## 🚀 Live Deployment

**Base URL:** https://web-production-a7b03.up.railway.app/

**Swagger UI:** https://web-production-a7b03.up.railway.app/docs

> This project is fully deployed and publicly accessible. No local setup required.

---

## ⚠️ Important Note

The project was initially designed for local execution (Ollama).
Due to deployment requirements, it was migrated to a cloud-based architecture using **Groq API** + **Railway**.

---

## 🔍 What This Project Does

- Executes LLM tasks with constraint awareness
- Detects contradictory instructions
- Computes trust score (0–1)
- Logs execution with SHA256 hash
- Anchors execution on blockchain (Base Sepolia)

---

## The Problem

AI agents make promises. They say "I'll answer in one word" and then ramble for 50 words. They claim to follow constraints but provide no proof. How can you trust an AI that can't verify its own behavior?

## The Solution

**TrustAudit Agent** — an AI agent that executes tasks, audits its own output against stated constraints, assigns a trust score (0-1), and generates cryptographic proofs of execution integrity.

This agent doesn't just execute tasks. It proves it kept its promises.

## How It Works

```
User Request → Agent Execution → Constraint Validation → Trust Score + Execution Hash
```

1. **Execute**: Agent runs the task using Groq LLM (llama-3.1-8b-instant)
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

## 🧪 How to Use

### Option A — Swagger UI (Recommended)

Open https://web-production-a7b03.up.railway.app/docs and use **POST /agent/run**

### Option B — cURL

```bash
curl -X POST https://web-production-a7b03.up.railway.app/agent/run \
  -H "Content-Type: application/json" \
  -d '{"input": "Is the sky blue? Answer YES or NO only."}'
```

### Option C — Python

```python
import requests

response = requests.post(
    "https://web-production-a7b03.up.railway.app/agent/run",
    json={"input": "Say YES only"}
)
print(response.json())
```

---

## 📌 Sample Output Explained

| Field | Description |
|-------|-------------|
| `valid` | Whether all constraints were satisfied |
| `trust_score` | Reliability score (0.0 = failed, 1.0 = perfect) |
| `reason` | Why the trust score changed (constraint violations) |
| `execution_hash` | Unique SHA256 fingerprint of this execution |
| `onchain.tx_hash` | Blockchain transaction hash for immutable proof |
| `onchain.status` | "confirmed" if anchored on-chain |

---

## 🔗 Blockchain Verification

Each execution can be anchored on **Base Sepolia** for tamper-proof verification.

### On-Chain Proof

| Field | Value |
|-------|-------|
| Network | Base Sepolia |
| Transaction Hash | `0x227446a3a6c0a34ddfd1f4cfb3c0298b57372a59364ac982c6a923561cb3f859` |
| Block Number | 39107108 |
| Status | CONFIRMED |
| Contract | `0x03Ce9c7C6441Bd274DC462d1c682F976ee695526` |

### Transaction 

<img width="1385" height="898" alt="Screenshot From 2026-03-20 10-32-47" src="https://github.com/user-attachments/assets/385ff14d-113b-4195-bb4e-e607263e1e07" /> 

### Transaction Log

<img width="1396" height="575" alt="Screenshot From 2026-03-20 10-34-50" src="https://github.com/user-attachments/assets/7fd81847-e975-4e4e-9d17-d2f4809a20c7" />


Anyone can verify by:
1. Finding the `tx_hash` in the response
2. Looking up the transaction on [Basescan](https://sepolia.basescan.org/tx/0x227446a3a6c0a34ddfd1f4cfb3c0298b57372a59364ac982c6a923561cb3f859)
3. Confirming the `ExecutionStored` event with matching hash

This provides **trustless verification** - no reliance on our server.

---

## ⚠️ Note on Database

SQLite is used for logging. Since Railway uses ephemeral storage, logs may reset on redeploy. For production, consider migrating to a persistent database.

---

## 🧠 Architecture

| Component | Technology |
|-----------|------------|
| Backend | FastAPI (Python) |
| LLM | Groq (llama-3.1-8b-instant) |
| Database | SQLite |
| Blockchain | Base Sepolia (Web3.py) |
| Deployment | Railway |
| Hashing | SHA256 |

---

## 🎯 Why This Matters

In a world where AI agents make decisions, execute actions, and interact with each other, **trust is paramount**. Most AI systems produce outputs without accountability. **TrustAudit introduces validation, scoring, and verifiable proof** — so you never have to trust an AI blindly again.

---

## Tracks

1. **Agents that Trust** — This agent builds trust through transparency, verification, and self-auditing
2. **Agents that Cooperate** — Trust is essential for multi-agent cooperation; this system provides verifiable execution proofs

---

## Quick Start (Local Development)

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export GROQ_API_KEY="your_groq_api_key"
export RPC_URL="https://sepolia.base.org"
export CONTRACT_ADDRESS="your_contract_address"
export PRIVATE_KEY="your_private_key"

# Start the agent
uvicorn app.main:app --reload

# Test the agent
curl -X POST http://localhost:8000/agent/run \
  -H "Content-Type: application/json" \
  -d '{"input": "Is the sky blue? Answer YES or NO only."}'
```

## Project Structure

```
synthesis-agent/
├── app/
│   ├── main.py              # FastAPI app
│   ├── models.py            # Request/response schemas
│   ├── routes/agent.py      # API endpoints
│   ├── services/
│   │   ├── constraints.py   # Constraint parsing & validation
│   │   ├── logger.py        # Immutable logging
│   │   ├── verifier.py      # Hash computation & verification
│   │   ├── blockchain.py     # On-chain anchoring (Base Sepolia)
│   │   └── llm.py           # Groq integration
│   └── db/database.py       # SQLite models
├── contracts/
│   └── ExecutionRegistry.sol  # Smart contract
├── requirements.txt
├── Procfile                   # Railway deployment
└── README.md
```

## License

MIT
