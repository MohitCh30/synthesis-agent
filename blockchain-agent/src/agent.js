import dotenv from 'dotenv';
import { ethers } from 'ethers';

dotenv.config();

const RPC_URL = process.env.RPC_URL;
const CONTRACT_ADDRESS = process.env.CONTRACT_ADDRESS;
let PRIVATE_KEY = process.env.PRIVATE_KEY || '';

if (!PRIVATE_KEY.startsWith('0x')) {
  PRIVATE_KEY = '0x' + PRIVATE_KEY;
}

const ABI = [
  {
    inputs: [{ internalType: "bytes32", name: "hash", type: "bytes32" }],
    name: "storeExecution",
    outputs: [],
    stateMutability: "nonpayable",
    type: "function"
  }
];

const FINANCIAL_KEYWORDS = [
  'transfer', 'payment', 'send', 'receive', 'deposit', 'withdraw',
  'approve', 'execute', 'swap', 'mint', 'burn', 'stake', 'unstake',
  'vote', 'proposal', 'governance', 'treasury', 'budget', 'funds',
  'eth', 'wei', 'token', 'nft', 'dao', 'delegate'
];

function isSignificantAction(input) {
  const lower = input.toLowerCase();
  return FINANCIAL_KEYWORDS.some(keyword => lower.includes(keyword));
}

async function callAIAgent(input) {
  try {
    const response = await fetch('http://localhost:8000/agent/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ input })
    });
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('AI Agent call failed:', error.message);
    return null;
  }
}

function parseDecision(agentResponse, originalInput) {
  if (!agentResponse) {
    return { decision: false, reason: 'No response from agent', output: null };
  }

  const output = agentResponse.output || '';
  const trustScore = agentResponse.trust_score || 0;
  const valid = agentResponse.valid !== false;

  if (!isSignificantAction(originalInput)) {
    return { decision: false, reason: 'Non-financial/non-governance action', output };
  }

  if (trustScore >= 0.8 && valid) {
    return { decision: true, reason: 'Significant financial/governance action with high trust', output };
  }

  return { decision: false, reason: 'Low trust score or invalid output', output };
}

async function storeOnChain(hash) {
  try {
    const provider = new ethers.JsonRpcProvider(RPC_URL);
    const wallet = new ethers.Wallet(PRIVATE_KEY, provider);
    const contract = new ethers.Contract(CONTRACT_ADDRESS, ABI, wallet);

    const tx = await contract.storeExecution(hash);
    console.log(`  Transaction sent: ${tx.hash}`);

    const receipt = await tx.wait();
    console.log(`  Confirmed in block: ${receipt.blockNumber}`);

    return { 
      success: true, 
      txHash: tx.hash, 
      blockNumber: receipt.blockNumber,
      network: 'base_sepolia'
    };
  } catch (error) {
    console.error(`  On-chain storage failed: ${error.message}`);
    return { success: false, error: error.message, network: 'base_sepolia' };
  }
}

async function main(input) {
  console.log('\n=== AI Decision Agent ===');
  console.log(`Input: "${input}"`);
  console.log('');

  const agentResponse = await callAIAgent(input);
  
  if (!agentResponse) {
    console.log('Decision: ERROR');
    console.log('Reason: Failed to get response from AI agent');
    console.log('\n=== Complete ===\n');
    return { status: 'failure', error: 'Failed to get AI agent response' };
  }

  const { decision, reason, output } = parseDecision(agentResponse, input);

  console.log(`Decision: ${decision}`);
  console.log(`Reason: ${reason}`);
  console.log(`Output: ${output ? output.trim() : 'N/A'}`);

  if (decision && output) {
    console.log('');
    console.log('--- On-Chain Storage ---');

    const hash = ethers.keccak256(ethers.toUtf8Bytes(output));
    console.log(`Hash: ${hash}`);

    const result = await storeOnChain(hash);

    console.log('\n=== Result ===');
    console.log(JSON.stringify(result, null, 2));
    console.log('\n=== Complete ===\n');

    return result;
  } else {
    console.log('On-Chain Storage: SKIPPED');
    console.log('\n=== Complete ===\n');
    return { status: 'skipped', reason };
  }
}

const input = process.argv[2];

if (!input) {
  console.error('Usage: node src/agent.js "<input>"');
  process.exit(1);
}

main(input).catch(console.error);
