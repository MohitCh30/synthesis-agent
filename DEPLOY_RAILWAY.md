# Railway Deployment Guide

## Prerequisites
- Groq account: https://console.groq.com
- Railway account: https://railway.app
- GitHub repo connected to Railway

## Step 1: Get Groq API Key

1. Sign up at https://console.groq.com
2. Go to API Keys
3. Create a new API key
4. Copy the key (format: `gsk_...`)

## Step 2: Deploy to Railway

### Option A: Via Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
cd synthesis-agent
railway init

# Add environment variables
railway variables set GROQ_API_KEY=your_key_here
railway variables set RPC_URL=https://sepolia.base.org
railway variables set CONTRACT_ADDRESS=0x03Ce9c7C6441Bd274DC462d1c682F976ee695526
railway variables set PRIVATE_KEY=your_key_here
railway variables set WALLET_ADDRESS=your_address_here

# Deploy
railway up
```

### Option B: Via Railway Dashboard

1. Go to https://railway.app
2. Create New Project → Deploy from GitHub
3. Select your repo
4. Add Environment Variables:
   - `GROQ_API_KEY`
   - `RPC_URL`
   - `CONTRACT_ADDRESS`
   - `PRIVATE_KEY`
   - `WALLET_ADDRESS`
5. Railway auto-detects Python, click Deploy

## Step 3: Configure Start Command

Railway should auto-detect `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

If not:
1. Go to Project Settings → Start Command
2. Set: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

## Step 4: Verify Deployment

```bash
# Get your deployment URL
railway domain

# Test health endpoint
curl https://your-url.railway.app/health

# Test agent
curl -X POST https://your-url.railway.app/agent/run \
  -H "Content-Type: application/json" \
  -d '{"input": "Is the sky blue? Answer YES or NO only."}'
```

## Environment Variables Reference

| Variable | Required | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | YES | Groq API key for LLM |
| `RPC_URL` | YES | Base Sepolia RPC URL |
| `CONTRACT_ADDRESS` | YES | Deployed contract address |
| `PRIVATE_KEY` | YES | Wallet private key (for tx signing) |
| `WALLET_ADDRESS` | NO | Your wallet address |
| `PORT` | AUTO | Railway sets this |

## Troubleshooting

### "GROQ_API_KEY not configured"
- Verify the variable is set in Railway dashboard
- Restart the deployment after setting variables

### "Connection timeout"
- Groq API may be slow on free tier
- Check Groq status at https://status.groq.com

### Cold starts
- Railway free tier may have cold starts
- Consider upgrading to Pro for always-on instances
