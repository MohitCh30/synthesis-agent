# TrustAudit Agent - Hackathon Submission

## Project Name

**TrustAudit Agent** — A Self-Verifying AI Agent for Transparent Execution

## One-Line Hook

*AI agents that prove they kept their promises.*

## Problem Statement

AI agents make claims about following instructions but provide no proof. When an agent says "I'll answer in one word" and then generates 50 words, there's no accountability mechanism. This lack of verifiability undermines trust in AI systems, especially for multi-agent cooperation.

## Solution

TrustAudit Agent transforms AI execution from a black box into a transparent, verifiable process:

1. **Constraint Extraction**: Parses natural language constraints from user requests
2. **Pre-Execution Validation**: Detects contradictory instructions before wasting compute
3. **Output Auditing**: Validates LLM output against stated constraints
4. **Trust Scoring**: Assigns objective trust scores (0-1) based on execution quality
5. **Cryptographic Proofs**: Generates SHA256 execution hashes for tamper detection
6. **Immutable Logging**: Append-only logs create full audit trails

## Why This Matters

For **Agents that Trust** and **Agents that Cooperate**, trust is foundational. This system provides:

- **Transparency**: Every constraint, violation, and decision is logged
- **Verification**: Any party can verify execution integrity via hash comparison
- **Accountability**: Trust scores create incentives for the agent to honor constraints
- **Interoperability**: Verifiable execution proofs enable safe multi-agent interactions

## Key Features

| Feature | Description |
|---------|-------------|
| **Constraint Engine** | Parses max_words, max_lines, sentence_count, format constraints, forbidden characters |
| **Contradiction Detection** | Catches impossible requests: "answer in 1 word but explain" |
| **Self-Auditing** | Agent evaluates and verifies its own output against constraints |
| **Trust Scoring** | Weighted trust score (0-1) with transparent deduction logic |
| **Execution Proofs** | SHA256 hashes prove input/output/timestamp integrity |
| **Immutability** | Append-only SQLite logging prevents retroactive changes |
| **Verification API** | Recompute hashes to detect tampering |

## Technical Implementation

### Execution Hash
```
SHA256(f"{input}|{output}|{timestamp}")
```

### Trust Score Calculation
| Factor | Penalty |
|--------|---------|
| Contradiction detected | -0.5 |
| Format violation | -0.3 |
| Structural violation | -0.2 |
| Minor violation | -0.1 |
| High latency (>10s) | -0.2 |

### API Endpoints
- `POST /agent/run` — Execute task with constraint validation
- `GET /agent/verify/{task_id}` — Verify execution hash integrity
- `GET /agent/logs` — View execution history
- `GET /agent/logs/{task_id}` — Get specific execution details

## Tech Stack

- **Backend**: FastAPI (Python)
- **LLM**: Ollama with Mistral (local, private)
- **Database**: SQLite (immutable append-only)
- **Hashing**: SHA256 for execution proofs
- **Verification**: On-chain simulated execution anchoring

## Track Selection

1. **Agents that Trust** — This system builds trust through transparency, self-auditing, and cryptographic verification

2. **Agents that Cooperate** — Verifiable execution proofs are essential for safe multi-agent cooperation; this system provides the trust infrastructure

## Differentiation

| Normal LLM API | TrustAudit Agent |
|----------------|------------------|
| Returns output only | Returns output + trust score + proof |
| No constraint enforcement | Parses and validates constraints |
| No contradiction detection | Catches impossible requests |
| Black-box execution | Transparent, auditable execution |
| No tampering detection | Cryptographic hash verification |

## Future Enhancements

- Anchor execution proofs on-chain (ERC-8004 for agent identity)
- Multi-agent trust aggregation
- Constraint templates for common patterns
- JSON Schema for structured constraint specification

## Demo

Run `demo.sh` to see:
1. Valid execution (trust_score = 1.0)
2. Constraint violation detection
3. Contradiction detection
4. Tamper verification

## Team

- Mohit Chaudhary (Human) + synthesis-opencode (Agent)

## Links

- **API**: http://localhost:8000
- **Health**: http://localhost:8000/health
- **Docs**: http://localhost:8000/docs
