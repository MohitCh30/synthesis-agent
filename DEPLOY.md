# Contract Deployment Instructions

## Prerequisites

1. Install dependencies:
```bash
npm install
npm install -D @nomicfoundation/hardhat-toolbox
```

2. Configure environment:
```bash
export PRIVATE_KEY="your_testnet_private_key"
export BASESCAN_API_KEY="your_basescan_api_key"
```

## Hardhat Config (hardhat.config.js)

```javascript
require("@nomicfoundation/hardhat-toolbox");

module.exports = {
  solidity: "0.8.0",
  networks: {
    base_sepolia: {
      url: "https://sepolia.base.org",
      accounts: [process.env.PRIVATE_KEY]
    }
  }
};
```

## Deploy Script (scripts/deploy.js)

```javascript
const hre = require("hardhat");

async function main() {
  const ExecutionRegistry = await hre.ethers.getContractFactory("ExecutionRegistry");
  const contract = await ExecutionRegistry.deploy();
  await contract.waitForDeployment();
  console.log("Deployed to:", await contract.getAddress());
}

main().catch(console.error);
```

## Deploy

```bash
npx hardhat compile
npx hardhat run scripts/deploy.js --network base_sepolia
```

## Set Environment Variables

```bash
export RPC_URL="https://sepolia.base.org"
export CONTRACT_ADDRESS="deployed_contract_address"
export PRIVATE_KEY="your_private_key"
export WALLET_ADDRESS="your_wallet_address"
```

## Verify on Basescan

1. Go to https://sepolia.basescan.org
2. Search your contract address
3. View "Events" tab to see all anchored execution hashes
