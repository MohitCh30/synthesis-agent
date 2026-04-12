#!/bin/bash

# TrustAudit Agent Demo
# This script demonstrates the agent's trust and verification capabilities

BASE_URL="http://localhost:8000"

echo "=========================================="
echo "  TrustAudit Agent Demo"
echo "  AI agents that prove they kept promises"
echo "=========================================="
echo ""

# Check if server is running
echo "1. Checking agent status..."
curl -s $BASE_URL/health | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'   Status: {d[\"status\"]}, LLM: {d[\"model\"]}')"
echo ""

# Demo 1: Valid execution
echo "=========================================="
echo "2. DEMO 1: Valid Execution"
echo "   Prompt: 'Is the sky blue? Answer YES or NO only.'"
echo "=========================================="
RESULT=$(curl -s -X POST $BASE_URL/agent/run \
  -H "Content-Type: application/json" \
  -d '{"input": "Is the sky blue? Answer YES or NO only."}')
  
echo "$RESULT" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(f'   Output: {d[\"output\"].strip()}')
print(f'   Valid: {d[\"valid\"]}')
print(f'   Trust Score: {d[\"trust_score\"]}')
print(f'   Explanation: {d[\"trust_explanation\"]}')
print(f'   Execution Hash: {d[\"execution_hash\"][:32]}...')
print(f'   Verification: {d[\"verification\"]}')
TASK_ID=d['task_id']
"

echo ""
echo "   Verifying execution integrity..."
curl -s $BASE_URL/agent/verify/$(echo "$RESULT" | python3 -c "import json,sys; print(json.load(sys.stdin)['task_id'])") | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(f'   Tampered: {d[\"tampered\"]}')
print(f'   Valid: {d[\"valid\"]}')
"
echo ""

# Demo 2: Constraint violation
echo "=========================================="
echo "3. DEMO 2: Constraint Violation"
echo "   Prompt: 'What is 2+2? Answer in 1 word.'"
echo "=========================================="
RESULT2=$(curl -s -X POST $BASE_URL/agent/run \
  -H "Content-Type: application/json" \
  -d '{"input": "What is 2+2? Answer in 1 word."}')

echo "$RESULT2" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(f'   Output: {d[\"output\"].strip()}')
print(f'   Valid: {d[\"valid\"]}')
print(f'   Trust Score: {d[\"trust_score\"]}')
print(f'   Violations: {d[\"violations\"]}')
print(f'   Explanation: {d[\"trust_explanation\"]}')
"
echo ""

# Demo 3: Contradiction detection
echo "=========================================="
echo "4. DEMO 3: Contradiction Detection"
echo "   Prompt: 'Answer in one word. Explain your reasoning.'"
echo "=========================================="
RESULT3=$(curl -s -X POST $BASE_URL/agent/run \
  -H "Content-Type: application/json" \
  -d '{"input": "Answer in one word. Explain your reasoning."}')

echo "$RESULT3" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(f'   Contradiction Detected: {d[\"contradiction_detected\"]}')
print(f'   Reason: {d[\"contradiction_reason\"]}')
print(f'   Trust Score: {d[\"trust_score\"]}')
print(f'   Explanation: {d[\"trust_explanation\"]}')
print(f'   Output Preview: {d[\"output\"][:60]}...')
"
echo ""

# Demo 4: Forbidden character
echo "=========================================="
echo "5. DEMO 4: Forbidden Character Detection"
echo "   Prompt: 'What is water? Answer with letter \"x\" only.'"
echo "=========================================="
RESULT4=$(curl -s -X POST $BASE_URL/agent/run \
  -H "Content-Type: application/json" \
  -d '{"input": "What is water? Answer with the letter \"x\" only."}')

echo "$RESULT4" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(f'   Output: {d[\"output\"].strip()}')
print(f'   Valid: {d[\"valid\"]}')
print(f'   Violations: {d[\"violations\"]}')
print(f'   Trust Score: {d[\"trust_score\"]}')
"
echo ""

# Demo 5: View logs
echo "=========================================="
echo "6. Viewing Execution Logs"
echo "=========================================="
curl -s $BASE_URL/agent/logs | python3 -c "
import json,sys
logs=json.load(sys.stdin)
print(f'   Total executions logged: {len(logs)}')
print(f'   Most recent entry:')
if logs:
    d=logs[0]
    print(f'   - Task ID: {d[\"task_id\"][:16]}...')
    print(f'   - Trust Score: {d[\"trust_score\"]}')
    print(f'   - Valid: {d[\"valid\"]}')
    print(f'   - Contradiction: {d.get(\"contradiction_detected\", False)}')
"
echo ""

echo "=========================================="
echo "  Demo Complete!"
echo "  TrustAudit Agent: Proving AI keeps promises"
echo "=========================================="
