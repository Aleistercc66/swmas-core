#!/usr/bin/env python3
"""Debug token balance fetching for Arbitrum"""
import asyncio
from web3 import Web3

# Test wallet
WALLET = '0x8BF6a1798305A7398b11C09449f0e0EADb737EAe'

# Arbitrum tokens
TOKENS = {
    'USDC': '0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8',
    'USDT': '0xFd086bC7CD5C481DCC9C85ebE478A1c0b69Fcbb9',
    'DAI': '0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1',
    'WETH': '0x82aF49447D8a07e3bd95BD0d56f35241523fBab1',
    'ARB': '0x912CE59144191C1204E64559FE8253a0e49E6548',
}

ERC20_ABI = [
    {"constant":True,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"type":"function"},
    {"constant":True,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"type":"function"},
    {"constant":True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"},
    {"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},
]

async def main():
    print("="*60)
    print("DEBUG: Arbitrum Token Balances")
    print("="*60)
    
    w3 = Web3(Web3.HTTPProvider('https://arbitrum-one.publicnode.com'))
    print(f"\nRPC Connected: {w3.is_connected()}")
    print(f"Block: {w3.eth.block_number}")
    print(f"Wallet: {WALLET}")
    
    # Check native balance
    native = w3.eth.get_balance(WALLET)
    print(f"\nNative ETH: {w3.from_wei(native, 'ether')} ETH")
    
    print("\n--- TOKEN CHECKS ---")
    for symbol, addr in TOKENS.items():
        try:
            checksum = w3.to_checksum_address(addr)
            code = w3.eth.get_code(checksum)
            print(f"\n{symbol}:")
            print(f"  Address: {checksum}")
            print(f"  Has code: {len(code) > 0}")
            
            if len(code) > 0:
                contract = w3.eth.contract(address=checksum, abi=ERC20_ABI)
                
                # Try to get balance
                raw = contract.functions.balanceOf(w3.to_checksum_address(WALLET)).call()
                print(f"  Raw balance: {raw}")
                
                # Get decimals
                try:
                    dec = contract.functions.decimals().call()
                except:
                    dec = 6  # Default for USDC/USDT
                    print(f"  Decimals (defaulted): {dec}")
                
                human = raw / (10 ** dec)
                print(f"  Human balance: {human}")
            else:
                print(f"  ❌ No contract at this address!")
                
        except Exception as e:
            print(f"  ❌ ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(main())
