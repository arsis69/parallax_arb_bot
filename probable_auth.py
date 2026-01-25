"""
Probable Markets Authentication
Gets API credentials for orderbook access
L1 Authentication using ClobAuth EIP-712 signatures (from official docs)
"""

import os
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()

try:
    from eth_account import Account
    from eth_account.messages import encode_typed_data
except ImportError:
    print("Installing eth-account library...")
    import subprocess
    subprocess.run(["pip", "install", "eth-account"], check=True)
    from eth_account import Account
    from eth_account.messages import encode_typed_data

API_BASE = "https://api.probable.markets"
CHAIN_ID = 56  # BSC Mainnet

HEADERS = {
    'User-Agent': 'Mozilla/5.0',
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}

# Message to sign (from docs)
MSG_TO_SIGN = "This message attests that I control the given wallet"


def build_l1_signature(private_key, address, timestamp, nonce):
    """
    Build L1 authentication signature using ClobAuth format from docs
    """
    # Domain as per docs
    domain = {
        'name': 'ClobAuthDomain',
        'version': '1',
        'chainId': CHAIN_ID,
    }

    # Types as per docs
    types = {
        'ClobAuth': [
            {'name': 'address', 'type': 'address'},
            {'name': 'timestamp', 'type': 'string'},
            {'name': 'nonce', 'type': 'uint256'},
            {'name': 'message', 'type': 'string'},
        ]
    }

    # Message as per docs
    message = {
        'address': address,
        'timestamp': str(timestamp),
        'nonce': nonce,
        'message': MSG_TO_SIGN,
    }

    typed_data = {
        'types': {
            'EIP712Domain': [
                {'name': 'name', 'type': 'string'},
                {'name': 'version', 'type': 'string'},
                {'name': 'chainId', 'type': 'uint256'},
            ],
            **types
        },
        'primaryType': 'ClobAuth',
        'domain': domain,
        'message': message
    }

    print(f"   Domain: {domain}")
    print(f"   Message: {message}")

    # Sign
    encoded = encode_typed_data(full_message=typed_data)
    signed = Account.sign_message(encoded, private_key=private_key)

    # Return signature hex with 0x prefix
    sig_hex = signed.signature.hex()
    if not sig_hex.startswith('0x'):
        sig_hex = '0x' + sig_hex

    print(f"   Signature: {sig_hex[:50]}...")
    return sig_hex


def create_api_key(address, signature, timestamp, nonce):
    """Create API key using L1 authentication headers"""
    headers = {
        **HEADERS,
        'prob_address': address,
        'prob_signature': signature,
        'prob_timestamp': str(timestamp),
        'prob_nonce': str(nonce),
    }

    print(f"   Sending request to: {API_BASE}/public/api/v1/auth/api-key/{CHAIN_ID}")
    print(f"   Headers:")
    print(f"     prob_address: {address}")
    print(f"     prob_signature: {signature[:50]}...")
    print(f"     prob_timestamp: {timestamp}")
    print(f"     prob_nonce: {nonce}")

    resp = requests.post(
        f"{API_BASE}/public/api/v1/auth/api-key/{CHAIN_ID}",
        headers=headers,
        json={},  # Empty body as per docs
        timeout=30
    )

    print(f"   Response status: {resp.status_code}")
    print(f"   Response: {resp.text[:500]}")

    if resp.status_code == 200:
        return resp.json()
    return None


def get_existing_api_key(address, signature, timestamp, nonce):
    """Try to get existing API key"""
    headers = {
        **HEADERS,
        'prob_address': address,
        'prob_signature': signature,
        'prob_timestamp': str(timestamp),
        'prob_nonce': str(nonce),
    }

    resp = requests.get(
        f"{API_BASE}/public/api/v1/auth/api-key/{CHAIN_ID}",
        headers=headers,
        timeout=30
    )

    print(f"   Response status: {resp.status_code}")
    if resp.status_code == 200:
        return resp.json()
    print(f"   Response: {resp.text[:300]}")
    return None


def main():
    print("\n" + "=" * 60)
    print("PROBABLE MARKETS AUTHENTICATION")
    print("Using ClobAuth EIP-712 format from official docs")
    print("=" * 60)

    # Load private key
    private_key = os.getenv('pv_key')
    if not private_key:
        print("ERROR: pv_key not found in .env")
        return

    # Ensure 0x prefix
    if not private_key.startswith('0x'):
        private_key = '0x' + private_key

    # Get address from private key
    account = Account.from_key(private_key)
    address = account.address
    print(f"\nWallet address: {address}")

    # Step 1: Create timestamp and nonce (nonce can be 0 as per docs)
    timestamp = int(time.time())  # Unix timestamp in seconds
    nonce = 0  # Can use 0 as per docs

    print(f"\n1. Building L1 signature...")
    print(f"   Timestamp: {timestamp}")
    print(f"   Nonce: {nonce}")

    signature = build_l1_signature(private_key, address, timestamp, nonce)

    # Step 2: Try to get existing API key first
    print("\n2. Checking for existing API key...")
    credentials = get_existing_api_key(address, signature, timestamp, nonce)

    # Step 3: If no existing key, create new one
    if not credentials:
        print("\n3. Creating new API key...")
        credentials = create_api_key(address, signature, timestamp, nonce)

    if credentials:
        print("\n" + "=" * 60)
        print("API CREDENTIALS OBTAINED!")
        print("=" * 60)

        api_key = credentials.get('apiKey', '')
        secret = credentials.get('secret', '')
        passphrase = credentials.get('passphrase', '')

        print(f"API Key: {api_key}" if api_key else "API Key: (not returned)")
        print(f"Secret: {secret[:30]}..." if secret else "Secret: (not returned)")
        print(f"Passphrase: {passphrase}" if passphrase else "Passphrase: (not returned)")

        # Save to file
        creds = {
            'address': address,
            'api_key': api_key,
            'secret': secret,
            'passphrase': passphrase
        }

        with open('probable_credentials.json', 'w') as f:
            json.dump(creds, f, indent=2)

        print(f"\nCredentials saved to: probable_credentials.json")
        print("=" * 60)
        return creds
    else:
        print("\n" + "=" * 60)
        print("FAILED TO GET API CREDENTIALS")
        print("=" * 60)
        return None


if __name__ == "__main__":
    main()
