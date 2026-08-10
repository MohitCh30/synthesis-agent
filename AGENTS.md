# AGENTS.md — TrustAudit Agent

## System Identity

**Name:** TrustAudit Agent
**Purpose:** An AI execution layer that validates its own outputs against stated constraints, computes cryptographic proofs of execution, and anchors significant executions on-chain.
**Problem:** AI agents make promises they cannot verify. This agent proves it kept its promises.

---

## Live Endpoints

Deployment is self-hosted, exposed through a Cloudflare Tunnel (the Railway
URLs below are from the previous deployment).
The origin must only accept traffic from the tunnel — direct-to-origin access
would let clients spoof `CF-Connecting-IP` and bypass per-IP rate limiting.

**Base URL:** https://web-production-a7b03.up.railway.app (previous Railway deployment)
**Swagger UI:** https://web-production-a7b03.up.railway.app/docs
**Health Check:** GET https://web-production-a7b03.up.railway.app/

---

## How to Interact With This Agent

### Run a Task

```
POST https://web-production-a7b03.up.railway.app/agent/run
Content-Type: application/json

{ "input": "Is the sky blue? Answer YES or NO only." }
```

**Response fields:**
- `output` — the LLM response
- `valid` — true if all constraints were satisfied
- `trust_score` — float 0.0 to 1.0 (1.0 = perfect compliance)
- `trust_explanation` — explanation of any deductions
- `constraints_detected` — list of constraints parsed from the input
- `violations` — list of constraints that were violated
- `execution_hash` — SHA256 fingerprint of this execution
- `task_id` — unique ID for this execution
- `onchain` — blockchain anchoring result (null if not triggered)

### Verify a Past Execution

```
GET https://web-production-a7b03.up.railway.app/agent/verify/{task_id}
```

Recomputes the SHA256 hash and compares against stored value. Returns tampered=false if execution is intact.

### View Execution History

```
GET https://web-production-a7b03.up.railway.app/agent/history
```

Returns append-only log of all executions with trust scores and hashes.

---

## API Protections

- **Rate limiting** — per-IP sliding-window limits (no external dependency):
  `/agent/run` 10/min, `/agent/classify` 30/min, `/agent/filter` 30/min, other `/agent/*` reads 60/min.
  Returns 429 with `Retry-After`. Tunable via `RATE_LIMIT_*_PER_MINUTE` env vars.
  Client IP comes from Cloudflare's `CF-Connecting-IP` header (trustworthy through the tunnel);
  client-supplied `X-Forwarded-For` is ignored as spoofable. Uvicorn must run with
  `--no-proxy-headers` (see Procfile) — otherwise uvicorn itself honors spoofed
  `X-Forwarded-For` from loopback peers and rewrites `request.client` before middleware runs.
- **Model allowlist** — `AgentRequest.model` is restricted to plain chat models
  (`GROQ_ALLOWED_MODELS`, default `llama-3.1-8b-instant`, `llama-3.3-70b-versatile`).
  Agentic Groq models with built-in server-side URL-visit/search tools are rejected
  to prevent provider-side URL fetching triggered by clients. The application server
  itself never fetches URLs from user input.
- **DELETE /agent/logs/{task_id}** — gated behind `X-Admin-Key` header matching the `ADMIN_API_KEY`
  env var. If `ADMIN_API_KEY` is not set, deletion returns 403. This protects the append-only
  audit trail that `/agent/verify` and on-chain anchoring depend on.
- **Input bounds** — prompt/text fields limited to 8000 chars; `limit` 1–200 and `offset >= 0` on `/agent/logs`.
- **Error handling** — upstream provider error details are logged server-side only; API responses
  and stored log reasons use generic messages.
- **Security headers** — `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` on all responses.

---

## Constraint System

### Supported Constraints

| Constraint | Example Input | What It Checks |
|---|---|---|
| max_words | "answer in 5 words" | Word count of output |
| max_lines | "keep it to 2 lines" | Line count of output |
| sentence_count | "write 3 sentences" | Number of sentences |
| words_per_sentence | "5 words each" | Words per sentence |
| format | "answer YES or NO only" | Output matches allowed values |
| forbidden_chars | 'answer with letter x only' | Character restrictions |

### Contradiction Detection

Before executing, the agent checks for impossible requests:
- "Answer in 1 word but explain your reasoning" — contradiction detected, trust_score -0.5
- "Answer YES or NO only but give details" — contradiction detected

---

## Trust Scoring

Base score: 1.0

| Violation Type | Penalty |
|---|---|
| Contradiction detected | -0.5 |
| Format violation | -0.3 |
| Structural violation | -0.2 |
| Minor violation | -0.1 |
| Latency > 10s | -0.2 |

Score clamped to [0.0, 1.0]. Score of 1.0 means agent fully kept its promises.

---

## Cryptographic Proof System

Every execution generates SHA256(input + output + timestamp). This hash is:
1. Stored in append-only SQLite — tamper-detectable via verify endpoint
2. Anchored on Base Sepolia if execution meets criteria

### On-Chain Anchoring Criteria

ALL three must be true:
- Contains financial/governance keyword (transfer, payment, approve, execute, vote, proposal, governance, treasury, dao, stake, mint, burn, swap)
- trust_score >= 0.8
- valid == true

### Blockchain Details

| Field | Value |
|---|---|
| Network | Base Sepolia |
| Contract | 0x03Ce9c7C6441Bd274DC462d1c682F976ee695526 |
| Verified TX | 0x227446a3a6c0a34ddfd1f4cfb3c0298b57372a59364ac982c6a923561cb3f859 |
| Block | 39107108 |
| Basescan | https://sepolia.basescan.org/tx/0x227446a3a6c0a34ddfd1f4cfb3c0298b57372a59364ac982c6a923561cb3f859 |

Contract emits events only — no on-chain storage — to minimise gas. Anyone can verify by recomputing the hash independently.

---

## Sample Interactions for Judges

### Test 1 — Format constraint should pass
```
POST /agent/run
{ "input": "Is water wet? Answer YES or NO only." }
Expected: valid=true, trust_score=1.0
```

### Test 2 — Word limit should pass
```
POST /agent/run
{ "input": "What is 2+2? Answer in exactly 1 word." }
Expected: valid=true, trust_score=1.0
```

### Test 3 — Contradiction should be flagged
```
POST /agent/run
{ "input": "Answer in one word. Explain your full reasoning in detail." }
Expected: valid=false, trust_score~0.3
```

### Test 4 — Financial keyword triggers on-chain anchoring
```
POST /agent/run
{ "input": "Should I approve this treasury transfer? Answer YES or NO only." }
Expected: valid=true, trust_score=1.0, onchain.status=confirmed
```

### Test 5 — Verify execution integrity
```
GET /agent/verify/{task_id}
Expected: tampered=false
```

---

## Architecture

```
Input
  -> Constraint Engine — parses rules, detects contradictions
  -> LLM Execution — Groq llama-3.1-8b-instant
  -> Output Validation — checks each constraint
  -> Trust Scoring — weighted penalty calculation
  -> Hash Generation — SHA256(input + output + timestamp)
  -> Decision Layer — Node.js, filters by keyword + score + valid
  -> On-Chain Anchoring — Web3.py, Base Sepolia, event emission
  -> Response + Logging — append-only SQLite
```

## Tech Stack

| Component | Technology |
|---|---|
| Backend | FastAPI (Python) |
| LLM | Groq — llama-3.1-8b-instant |
| Database | SQLite append-only |
| Blockchain | Base Sepolia via Web3.py |
| Decision Layer | Node.js |
| Smart Contract | Solidity 0.8 event-only |
| Deployment | Railway |
| Hashing | SHA256 + keccak256 |

---

## Hackathon Tracks

1. Agents that Trust — self-auditing AI with cryptographic execution proofs
2. Agents that Cooperate — trust infrastructure for verifiable multi-agent coordination

---

## Known Limitations

- Constraint parsing is regex-based and fails on ambiguous natural language
- SQLite on Railway uses ephemeral storage — logs reset on redeploy
- On-chain anchoring requires testnet ETH from faucet
- LLM does not always follow constraints — validation layer provides objective checking the model cannot influence
