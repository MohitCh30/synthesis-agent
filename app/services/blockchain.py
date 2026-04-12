import os
import logging
from typing import Optional

from web3 import Web3
from web3.exceptions import TimeExhausted, TransactionNotFound

logger = logging.getLogger(__name__)

CONTRACT_ABI = [
    {
        "inputs": [{"internalType": "bytes32", "name": "hash", "type": "bytes32"}],
        "name": "storeExecution",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

_w3: Optional[Web3] = None


def get_web3() -> Optional[Web3]:
    global _w3
    if _w3 is None:
        rpc_url = os.getenv("RPC_URL", "https://sepolia.base.org")
        if not rpc_url:
            logger.warning("RPC_URL not configured")
            return None
        try:
            _w3 = Web3(Web3.HTTPProvider(rpc_url))
            if not _w3.is_connected():
                logger.warning("RPC connected but chain not reachable")
                return None
            logger.info(f"Web3 connected to {rpc_url}")
        except Exception as e:
            logger.error(f"Web3 connection error: {e}")
            return None
    return _w3


def store_execution_onchain(execution_hash: str) -> Optional[dict]:
    rpc_url = os.getenv("RPC_URL")
    contract_address = os.getenv("CONTRACT_ADDRESS")
    private_key = os.getenv("PRIVATE_KEY")
    wallet_address = os.getenv("WALLET_ADDRESS")

    if not rpc_url:
        logger.warning("RPC_URL not set - skipping on-chain storage")
        return None

    if not contract_address:
        logger.warning("CONTRACT_ADDRESS not set - skipping on-chain storage")
        return None

    if not private_key:
        logger.warning("PRIVATE_KEY not set - skipping on-chain storage")
        return None

    if not wallet_address:
        logger.warning("WALLET_ADDRESS not set - skipping on-chain storage")
        return None

    try:
        w3 = get_web3()
        if not w3:
            return None

        contract = w3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=CONTRACT_ABI
        )

        hash_bytes32 = bytes.fromhex(execution_hash) if len(execution_hash) == 64 else Web3.keccak(text=execution_hash)

        nonce = w3.eth.get_transaction_count(Web3.to_checksum_address(wallet_address))

        tx = contract.functions.storeExecution(hash_bytes32).build_transaction({
            'from': wallet_address,
            'nonce': nonce,
            'gas': 100000,
            'gasPrice': w3.eth.gas_price
        })

        if not private_key.startswith('0x'):
            private_key = '0x' + private_key

        signed_tx = w3.eth.account.sign_transaction(tx, private_key)

        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        logger.info(f"Execution anchored on-chain: {tx_hash.hex()}")

        return {
            "tx_hash": tx_hash.hex(),
            "network": "base_sepolia",
            "status": "confirmed" if receipt.status == 1 else "failed",
            "block_number": receipt.blockNumber
        }

    except TimeExhausted:
        logger.warning(f"Transaction timeout for hash {execution_hash[:16]}...")
        return {"tx_hash": None, "network": "base_sepolia", "status": "timeout"}
    except TransactionNotFound:
        logger.warning(f"Transaction not found for hash {execution_hash[:16]}...")
        return {"tx_hash": None, "network": "base_sepolia", "status": "pending"}
    except Exception as e:
        logger.error(f"On-chain anchoring failed: {e}")
        return None
