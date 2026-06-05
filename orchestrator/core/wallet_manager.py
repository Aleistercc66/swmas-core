#!/usr/bin/env python3
"""
MetaMask Wallet Integration Module
Securely connects to MetaMask wallets for trading
Supports BOTH:
  - Raw Private Key import
  - Secret Recovery Phrase (BIP-39 Mnemonic) import with HD derivation (BIP-44)
"""
import os
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, asdict
from datetime import datetime

# Web3
from web3 import Web3
from eth_account import Account

# Solana
from solders.keypair import Keypair

# BIP-39 Mnemonic
from mnemonic import Mnemonic

# BIP-32/44 HD Wallet Derivation
from bip32 import BIP32

# Encryption
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('wallet_manager')


class SecureKeyStorage:
    """Securely encrypts and stores private keys"""

    def __init__(self, password: str):
        self.password = password.encode()
        self.key = self._derive_key()
        self.cipher = Fernet(self.key)

    def _derive_key(self) -> bytes:
        """Derive encryption key from password"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'metamask_salt_2024',  # Fixed salt - in production use random + store
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.password))
        return key

    def encrypt(self, data: str) -> str:
        """Encrypt data"""
        return self.cipher.encrypt(data.encode()).decode()

    def decrypt(self, encrypted: str) -> str:
        """Decrypt data"""
        return self.cipher.decrypt(encrypted.encode()).decode()


class MnemonicWallet:
    """
    BIP-39 Secret Recovery Phrase → BIP-44 HD Wallet Derivation.
    Compatible with MetaMask default derivation paths.
    """

    # MetaMask default paths
    PATHS = {
        'ethereum':    "m/44'/60'/0'/0/0",
        'arbitrum':    "m/44'/60'/0'/0/0",
        'base':        "m/44'/60'/0'/0/0",
        'optimism':    "m/44'/60'/0'/0/0",
        'polygon':     "m/44'/60'/0'/0/0",
        'bsc':         "m/44'/60'/0'/0/0",
        'avalanche':   "m/44'/60'/0'/0/0",
        'solana':      "m/44'/501'/0'/0'",
    }

    @staticmethod
    def validate_mnemonic(phrase: str, language: str = 'english') -> bool:
        """Validate a BIP-39 mnemonic phrase (12, 15, 18, 21, or 24 words)"""
        mnemo = Mnemonic(language)
        words = phrase.strip().lower().split()
        if len(words) not in (12, 15, 18, 21, 24):
            return False
        return mnemo.check(phrase)

    @classmethod
    def derive_private_key(
        cls,
        mnemonic_phrase: str,
        chain: str = 'ethereum',
        account_index: int = 0,
        passphrase: str = ""
    ) -> str:
        """
        Derive private key from mnemonic phrase.

        Args:
            mnemonic_phrase: BIP-39 seed phrase (12/24 words)
            chain: Blockchain for derivation path
            account_index: Account index (0 = first account, like MetaMask)
            passphrase: Optional BIP-39 passphrase

        Returns:
            Private key as hex string (0x...)
        """
        # Validate
        if not cls.validate_mnemonic(mnemonic_phrase):
            raise ValueError("Invalid mnemonic phrase! Must be 12, 15, 18, 21, or 24 valid BIP-39 words.")

        # Generate seed from mnemonic
        mnemo = Mnemonic('english')
        seed = mnemo.to_seed(mnemonic_phrase, passphrase=passphrase)

        # Get derivation path
        base_path = cls.PATHS.get(chain, cls.PATHS['ethereum'])

        # Replace account index in path
        # m/44'/60'/0'/0/0 -> m/44'/60'/0'/0/{account_index}
        path_parts = base_path.split('/')
        path_parts[-1] = str(account_index)
        path = '/'.join(path_parts)

        # BIP-32 derivation
        bip32 = BIP32.from_seed(seed)

        if chain == 'solana':
            # Solana: raw bytes
            privkey_bytes = bip32.get_privkey_from_path(path)
            # Convert to base58 or array format for solana
            import base58
            return base58.b58encode(privkey_bytes).decode()
        else:
            # EVM chains: hex private key
            privkey_bytes = bip32.get_privkey_from_path(path)
            return '0x' + privkey_bytes.hex()

    @classmethod
    def get_address_from_mnemonic(
        cls,
        mnemonic_phrase: str,
        chain: str = 'ethereum',
        account_index: int = 0,
        passphrase: str = ""
    ) -> str:
        """Get wallet address from mnemonic without exposing private key"""
        private_key = cls.derive_private_key(mnemonic_phrase, chain, account_index, passphrase)

        if chain == 'solana':
            keypair = Keypair.from_base58_string(private_key)
            return str(keypair.pubkey())
        else:
            account = Account.from_key(private_key)
            return account.address

    @classmethod
    def generate_new_mnemonic(cls, strength: int = 128, language: str = 'english') -> str:
        """Generate a new BIP-39 mnemonic phrase (128=12 words, 256=24 words)"""
        mnemo = Mnemonic(language)
        return mnemo.generate(strength=strength)

    @classmethod
    def derive_multiple_accounts(
        cls,
        mnemonic_phrase: str,
        chain: str = 'ethereum',
        count: int = 5,
        passphrase: str = ""
    ) -> List[Dict[str, str]]:
        """Derive multiple accounts from same seed (like MetaMask accounts 1,2,3...)"""
        accounts = []
        for i in range(count):
            pk = cls.derive_private_key(mnemonic_phrase, chain, i, passphrase)
            if chain == 'solana':
                kp = Keypair.from_base58_string(pk)
                addr = str(kp.pubkey())
            else:
                acc = Account.from_key(pk)
                addr = acc.address
            accounts.append({
                'index': i,
                'address': addr,
                'private_key': pk  # Only expose this securely!
            })
        return accounts


@dataclass
class WalletConfig:
    """Wallet configuration"""
    name: str
    address: str
    chain: str
    encrypted_key: Optional[str] = None  # Encrypted private key
    is_active: bool = False
    created_at: str = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class WalletManager:
    """
    Manages multiple wallets with secure key storage.
    Compatible with MetaMask (same key format).
    """

    WALLETS_FILE = Path("/root/.openclaw/workspace/orchestrator/config/wallets.json")

    def __init__(self):
        self.wallets: Dict[str, WalletConfig] = {}
        self._secure_storage: Optional[SecureKeyStorage] = None
        self._master_password: Optional[str] = None

    async def initialize(self, master_password: Optional[str] = None):
        """Initialize wallet manager"""
        if master_password:
            self._master_password = master_password
            self._secure_storage = SecureKeyStorage(master_password)

        # Load existing wallets
        await self._load_wallets()
        logger.info(f"💼 Wallet Manager initialized ({len(self.wallets)} wallets)")

    async def add_wallet(
        self,
        name: str,
        private_key: str,
        chain: str = 'ethereum',
        password: Optional[str] = None
    ) -> WalletConfig:
        """
        Add a new wallet (MetaMask-compatible).

        Args:
            name: Wallet name (e.g., "Main MetaMask")
            private_key: Private key (0x... or raw)
            chain: Blockchain (ethereum, solana, arbitrum, etc.)
            password: Encryption password (uses master if not provided)
        """
        # Derive address from key
        if chain == 'solana':
            # Solana keypair
            try:
                if private_key.startswith('['):
                    # Byte array format
                    key_bytes = json.loads(private_key)
                    keypair = Keypair.from_bytes(bytes(key_bytes))
                else:
                    # Base58 format
                    keypair = Keypair.from_base58_string(private_key)
                address = str(keypair.pubkey())
            except Exception as e:
                logger.error(f"❌ Invalid Solana key: {e}")
                raise ValueError(f"Invalid Solana private key: {e}")
        else:
            # EVM chains (Ethereum, Arbitrum, etc.)
            try:
                # Ensure 0x prefix
                if not private_key.startswith('0x'):
                    private_key = '0x' + private_key
                account = Account.from_key(private_key)
                address = account.address
            except Exception as e:
                logger.error(f"❌ Invalid EVM key: {e}")
                raise ValueError(f"Invalid private key: {e}")

        # Encrypt key
        storage = self._secure_storage
        if not storage:
            if not password:
                raise ValueError("Password required for key encryption")
            storage = SecureKeyStorage(password)

        encrypted_key = storage.encrypt(private_key)

        # Create wallet config
        wallet = WalletConfig(
            name=name,
            address=address,
            chain=chain,
            encrypted_key=encrypted_key,
            is_active=True
        )

        # Save
        self.wallets[name] = wallet
        await self._save_wallets()

        logger.info(f"✅ Wallet added: {name} ({address[:6]}...{address[-4:]})")
        return wallet

    async def import_from_mnemonic(
        self,
        name: str,
        mnemonic_phrase: str,
        chain: str = 'ethereum',
        account_index: int = 0,
        password: Optional[str] = None
    ) -> WalletConfig:
        """
        Import wallet from MetaMask Secret Recovery Phrase (BIP-39 mnemonic).
        
        Derives the private key using BIP-44 HD wallet derivation.
        MetaMask default path: m/44'/60'/0'/0/0 for first account.
        
        Args:
            name: Wallet name (e.g., "MetaMask Main")
            mnemonic_phrase: 12 or 24 word Secret Recovery Phrase
            chain: Blockchain (ethereum, solana, arbitrum, etc.)
            account_index: Account index (0=first account, like MetaMask Account 1)
            password: Encryption password
        
        Returns:
            WalletConfig for the imported wallet
        """
        # Validate mnemonic
        if not MnemonicWallet.validate_mnemonic(mnemonic_phrase):
            raise ValueError(
                "❌ Invalid Secret Recovery Phrase!\n"
                "Must be 12, 15, 18, 21, or 24 valid BIP-39 words.\n"
                "Check for typos or extra spaces."
            )
        
        logger.info(f"🔐 Deriving {chain} wallet from mnemonic (account {account_index})...")
        
        # Derive private key from mnemonic
        private_key = MnemonicWallet.derive_private_key(
            mnemonic_phrase=mnemonic_phrase,
            chain=chain,
            account_index=account_index
        )
        
        # Derive address
        if chain == 'solana':
            keypair = Keypair.from_base58_string(private_key)
            address = str(keypair.pubkey())
        else:
            if not private_key.startswith('0x'):
                private_key = '0x' + private_key
            account = Account.from_key(private_key)
            address = account.address
        
        # Encrypt key
        storage = self._secure_storage
        if not storage:
            if not password:
                raise ValueError("Password required for key encryption")
            storage = SecureKeyStorage(password)
        
        encrypted_key = storage.encrypt(private_key)
        
        # Create wallet config
        wallet = WalletConfig(
            name=name,
            address=address,
            chain=chain,
            encrypted_key=encrypted_key,
            is_active=True
        )
        
        # Save
        self.wallets[name] = wallet
        await self._save_wallets()
        
        word_count = len(mnemonic_phrase.strip().split())
        logger.info(
            f"✅ Wallet imported from {word_count}-word phrase: {name} "
            f"({address[:6]}...{address[-4:]} | Account {account_index})"
        )
        return wallet

    async def import_all_metamask_accounts(
        self,
        mnemonic_phrase: str,
        chain: str = 'ethereum',
        count: int = 5,
        password: Optional[str] = None
    ) -> List[WalletConfig]:
        """
        Import multiple MetaMask accounts from same seed phrase.
        MetaMask Account 1 = index 0, Account 2 = index 1, etc.
        """
        wallets = []
        for i in range(count):
            name = f"MetaMask Account {i + 1}"
            try:
                wallet = await self.import_from_mnemonic(
                    name=name,
                    mnemonic_phrase=mnemonic_phrase,
                    chain=chain,
                    account_index=i,
                    password=password
                )
                wallets.append(wallet)
            except Exception as e:
                logger.error(f"❌ Failed to import account {i + 1}: {e}")
                break
        return wallets

    async def get_wallet(self, name: str) -> Optional[WalletConfig]:
        """Get wallet by name"""
        return self.wallets.get(name)

    async def get_active_wallet(self, chain: Optional[str] = None) -> Optional[WalletConfig]:
        """Get first active wallet (optionally filtered by chain)"""
        for wallet in self.wallets.values():
            if wallet.is_active:
                if chain is None or wallet.chain == chain:
                    return wallet
        return None

    async def list_wallets(self) -> List[Dict]:
        """List all wallets (without sensitive data)"""
        return [
            {
                'name': w.name,
                'address': w.address,
                'chain': w.chain,
                'is_active': w.is_active,
                'created_at': w.created_at
            }
            for w in self.wallets.values()
        ]

    async def get_private_key(self, name: str, password: Optional[str] = None) -> Optional[str]:
        """Decrypt and return private key (use carefully!)"""
        wallet = self.wallets.get(name)
        if not wallet or not wallet.encrypted_key:
            return None

        storage = self._secure_storage
        if not storage:
            if not password:
                return None
            storage = SecureKeyStorage(password)

        try:
            return storage.decrypt(wallet.encrypted_key)
        except Exception as e:
            logger.error(f"❌ Decryption failed: {e}")
            return None

    async def remove_wallet(self, name: str):
        """Remove a wallet"""
        if name in self.wallets:
            del self.wallets[name]
            await self._save_wallets()
            logger.info(f"🗑️ Wallet removed: {name}")

    async def _load_wallets(self):
        """Load wallets from file"""
        if not self.WALLETS_FILE.exists():
            return

        try:
            data = json.loads(self.WALLETS_FILE.read_text())
            for name, wallet_data in data.items():
                self.wallets[name] = WalletConfig(**wallet_data)
        except Exception as e:
            logger.error(f"❌ Failed to load wallets: {e}")

    async def _save_wallets(self):
        """Save wallets to file"""
        self.WALLETS_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {name: asdict(w) for name, w in self.wallets.items()}
        self.WALLETS_FILE.write_text(json.dumps(data, indent=2))

    # ============== WEB3 INTEGRATION ==============

    async def get_balance(self, name: Optional[str] = None, chain: str = 'ethereum') -> Dict:
        """Get wallet balance"""
        wallet = await self.get_active_wallet(chain) if not name else self.wallets.get(name)
        if not wallet:
            return {'error': 'No wallet found'}

        try:
            if chain == 'solana':
                from solana.rpc.async_api import AsyncClient
                client = AsyncClient("https://api.mainnet-beta.solana.com")
                # Fetch balance logic here
                return {'address': wallet.address, 'chain': chain, 'balance': 'TBD'}
            else:
                # EVM balance
                w3 = Web3(Web3.HTTPProvider(
                    'https://ethereum-rpc.publicnode.com' if chain == 'ethereum' else
                    'https://arbitrum-one.publicnode.com' if chain == 'arbitrum' else
                    'https://base-mainnet.publicnode.com' if chain == 'base' else
                    'https://optimism-mainnet.publicnode.com' if chain == 'optimism' else
                    'https://polygon-bor.publicnode.com'
                ))

                balance_wei = w3.eth.get_balance(wallet.address)
                balance_eth = w3.from_wei(balance_wei, 'ether')

                return {
                    'address': wallet.address,
                    'chain': chain,
                    'native_balance': float(balance_eth),
                    'symbol': 'ETH' if chain in ['ethereum', 'arbitrum', 'base'] else 'MATIC'
                }
        except Exception as e:
            logger.error(f"❌ Balance check failed: {e}")
            return {'error': str(e)}

    # ============== FULL TOKEN LIST ==============
    
    # Extended token lists with prices + DeFi tokens
    TOKEN_LISTS = {
        'ethereum': {
            'USDC': '0xA0b86a33E6441e0A421e56E4773C3C1C0E7E4938',
            'USDT': '0xdAC17F958D2ee523a2206206994597C13D831ec7',
            'DAI': '0x6B175474E89094C44Da98b954EedeAC495271d0F',
            'WETH': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
            'WBTC': '0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599',
            'AAVE': '0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9',
            'LINK': '0x514910771AF9Ca656af840dff83E8264EcF986CA3',
            'UNI': '0x1f9840a85d5aF5bf1D1762F925BDaD4f4eF67821',
            'MKR': '0x9f8F72aA9304c8B593d555F12eF6589CC3A5A3D8',
            'CRV': '0xD533a949740bb3306d119CC777fa900bA034cd52',
            'SNX': '0xC011a73ee8576Fb46F45E1c2676E99f18081974',
            'COMP': '0xc00e94Cb662C3520282E6f5717214004A7f26888',
            'YFI': '0x0bc529c00C6401aC9B86A8d61E8d0b6F8c3A9e72',
            '1INCH': '0x111111111117dC0aa78b770fA6A738034120C302',
            'LDO': '0x5A98FcBE5169038E6A4dE8754c8e2E4e0D85B8E8',
            'FXS': '0x3432B6A60D23Ca0dFCa7761B7ab56459d9C964D0',
        },
        'arbitrum': {
            'USDC': '0xaf88d065e77c8cC2239327C5EDb3A432268e5831',  # Native
            'USDC.e': '0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8',  # Bridged
            'USDT': '0xFd086bC7CD5C481DCC9C85ebE478A1c0b69Fcbb9',
            'DAI': '0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1',
            'WETH': '0x82aF49447D8a07e3bd95BD0d56f35241523fBab1',
            'WBTC': '0x2f2a2543B76A4166549F7aaB2e75Bef0aefC5B0f',
            'ARB': '0x912CE59144191C1204E64559FE8253a0e49E6548',
            'AAVE': '0x0783588f7bA0b1b5D5D9f0D58D4e5A5bA8E4E7A0',  # Aave v3 Arbitrum
            'LINK': '0xf97f4df75117a78c1A5a0DBb814Af92458539FB4',
            'UNI': '0xFa7F8980b0f1E64A2062791ccE837fE6a47dA7b8',
            'GMX': '0xfc5A1A6EB076a2C7aD06eD22C90d7E710E35ad0a',
            'MAGIC': '0x539bdE0d7Dbd336b79148AA742AA21aC9B2aE9e6',
            'RDNT': '0x3082CC23568eA640225c2467353dC9E5aE96f18E',
            'STG': '0x6694340fc020c5E6B96567843da2df01b2CE1eb6',
            'JOE': '0x371c7ec6D8039ff7933a2AA28EB827Ffe1F52f07',
            'GRAIL': '0x3d9907F9a36877b3B26f18A9771c2E4C8E47B8f1',
            'PENDLE': '0x0c880f6761F1af2d9Aa228e907E0c7bE3eC5D3A8',
        },
        'base': {
            'USDC': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',  # Native
            'USDbC': '0xd9aAEc86B65D86f6A7B5B1d0c45cFa3Ee1fF6B6F',  # Bridged
            'DAI': '0x4f4cD4b9C8248E34D1C11c5Dca2B0b1A6D8E7C6E',
            'WETH': '0x4200000000000000000000000000000000000006',
            'AAVE': '0x0761bD546B5D0A8F2cD6a8E5F5A8c9E7e6D5f4E3',
            'BRETT': '0x532f27101965dd16442E59d40670FaF5eBB142E4',
            'AERO': '0x940181a94A35A4569E4529A3CDfB74e38FD98631',
            'DEGEN': '0x4ed4E862860beD51a9570b96d89aF5E1B0Efefed',
        },
        'optimism': {
            'USDC': '0x0b2c639c533813f4aa9d7837caf62653d097ff85',  # Native
            'USDC.e': '0x7F5c764cBc14f9669B88837ca1490cCa17c31607',  # Bridged
            'USDT': '0x94b008aA00579c1307B0EF2c499aD98a8ce58e58',
            'DAI': '0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1',
            'WETH': '0x4200000000000000000000000000000000000006',
            'AAVE': '0x76FB3e31A5c5c5D5E3D3A9aE5e5A5c9e7e6D5f4E',
            'OP': '0x4200000000000000000000000000000000000042',
            'VELO': '0x3c8B650257cFb8f3A8A8C4A5C8E5B6A8E4E7D3C',
            'SNX': '0x8700dAec35aF8Ff88c16BdF0418774cb3D7599B4',
            'PERP': '0xbc396689893d065f41bc2c6ecbee5e0085233447',
        },
        'polygon': {
            'USDC': '0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',  # Native
            'USDC.e': '0x7F5c764cBc14f9669B88837ca1490cCa17c31607',  # Bridged
            'USDT': '0xc2132D05D31c914a87C6611C10748AEb04B58e8F',
            'DAI': '0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063',
            'WETH': '0x7ceB23fD6bC0adD59E62ac25578270cFf1b9f619',
            'WBTC': '0x1BFD67037B42Cf73acF2047067bd4F2C47D9BfD6',
            'AAVE': '0xD6DF932A45C0f255f85145f286eA0a2927aF40D4',
            'LINK': '0x53E0bca35eC356BD5ddDFebbDf1c0d03A9e5c3B1',
            'CRV': '0x172370d5Cd63279eFa6d502DAB29171933a610AF',
            'MATIC': '0x0000000000000000000000000000000000001010',  # Native MATIC
        },
        'solana': {
            'USDC': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
            'USDT': 'Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB',
            'SOL': 'So11111111111111111111111111111111111111112',  # Wrapped SOL
            'BONK': 'DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263',
            'RAY': '4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R',
            'SRM': 'SRMuApVNdxXokk5GT7XD5cUUgXMBCoAz2LHe1BQpxb',
            'FIDA': 'EchesyfXe4kuaLhNuybST3VccyGYfe4LBrZxv7CqAJL7',
        },
    }
    
    # Use full token list for portfolio
    TOKEN_ADDRESSES = TOKEN_LISTS  # Alias for backwards compatibility
    
    ERC20_ABI = [
        {"constant":True,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"type":"function"},
        {"constant":True,"inputs":[],"name":"symbol","outputs":[{"name":"","type":"string"}],"type":"function"},
        {"constant":True,"inputs":[],"name":"decimals","outputs":[{"name":"","type":"uint8"}],"type":"function"},
        {"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"},
        {"constant":True,"inputs":[],"name":"totalSupply","outputs":[{"name":"","type":"uint256"}],"type":"function"},
    ]
    
    async def get_token_balances(
        self,
        wallet_address: str,
        chain: str = 'ethereum',
        tokens: Optional[List[str]] = None
    ) -> Dict[str, Dict]:
        """
        Get ERC-20 token balances for a wallet.
        """
        if chain not in self.TOKEN_ADDRESSES:
            return {'error': f'Chain {chain} not supported for token balances'}
        
        w3 = Web3(Web3.HTTPProvider(
            'https://ethereum-rpc.publicnode.com' if chain == 'ethereum' else
            'https://arbitrum-one.publicnode.com' if chain == 'arbitrum' else
            'https://base-mainnet.publicnode.com' if chain == 'base' else
            'https://optimism-mainnet.publicnode.com' if chain == 'optimism' else
            'https://polygon-bor.publicnode.com'
        ))
        
        chain_tokens = self.TOKEN_ADDRESSES.get(chain, {})
        if tokens:
            chain_tokens = {k: v for k, v in chain_tokens.items() if k in tokens}
        
        results = {}
        
        for symbol, address in chain_tokens.items():
            try:
                checksum = w3.to_checksum_address(address)
                code = w3.eth.get_code(checksum)
                if not code:
                    continue
                
                contract = w3.eth.contract(address=checksum, abi=self.ERC20_ABI)
                raw_balance = contract.functions.balanceOf(
                    w3.to_checksum_address(wallet_address)
                ).call()
                
                decimals = contract.functions.decimals().call()
                balance = raw_balance / (10 ** decimals)
                
                if balance > 0:
                    results[symbol] = {
                        'balance': balance,
                        'decimals': decimals,
                        'raw_balance': raw_balance,
                        'address': address,
                    }
                    
            except Exception as e:
                logger.debug(f"Token {symbol} check failed: {e}")
                continue
        
        return results
    
    async def get_token_price(self, token_symbol: str, chain: str = 'ethereum') -> Optional[float]:
        """
        Get token price in USD using CoinGecko API (free tier).
        """
        try:
            import requests
            
            # CoinGecko IDs for common tokens
            COINGECKO_IDS = {
                'USDC': 'usd-coin',
                'USDT': 'tether',
                'DAI': 'dai',
                'WETH': 'weth',
                'ETH': 'ethereum',
                'WBTC': 'wrapped-bitcoin',
                'AAVE': 'aave',
                'LINK': 'chainlink',
                'UNI': 'uniswap',
                'MKR': 'maker',
                'CRV': 'curve-dao-token',
                'SNX': 'havven',
                'COMP': 'compound-governance-token',
                'YFI': 'yearn-finance',
                '1INCH': '1inch',
                'LDO': 'lido-dao',
                'FXS': 'frax-share',
                'ARB': 'arbitrum',
                'GMX': 'gmx',
                'MAGIC': 'magic',
                'RDNT': 'radiant-capital',
                'STG': 'stargate-finance',
                'JOE': 'joe',
                'GRAIL': 'camelot-token',
                'PENDLE': 'pendle',
                'BRETT': 'based-brett',
                'AERO': 'aerodrome-finance',
                'DEGEN': 'degen-base',
                'OP': 'optimism',
                'VELO': 'velodrome-finance',
                'PERP': 'perpetual-protocol',
                'BONK': 'bonk',
                'RAY': 'raydium',
                'SOL': 'solana',
                'MATIC': 'matic-network',
                'POL': 'polygon-ecosystem-token',
            }
            
            token_id = COINGECKO_IDS.get(token_symbol.upper())
            if not token_id:
                return None
            
            url = f"https://api.coingecko.com/api/v3/simple/price?ids={token_id}&vs_currencies=usd"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if token_id in data and 'usd' in data[token_id]:
                return float(data[token_id]['usd'])
            
            return None
            
        except Exception as e:
            logger.warning(f"Price fetch failed for {token_symbol}: {e}")
            return None
    
    async def get_token_balances_with_prices(
        self,
        wallet_address: str,
        chain: str = 'ethereum'
    ) -> Dict[str, Dict]:
        """
        Get token balances + USD prices for full portfolio valuation.
        """
        # Get raw balances
        balances = await self.get_token_balances(wallet_address, chain)
        
        if 'error' in balances:
            return balances
        
        # Add prices to each token
        results = {}
        for symbol, info in balances.items():
            # Get price
            price = await self.get_token_price(symbol, chain)
            
            # Calculate USD value
            balance = info.get('balance', 0)
            usd_value = balance * price if price else None
            
            results[symbol] = {
                **info,
                'price_usd': price,
                'usd_value': usd_value,
            }
        
        return results
    
    async def get_portfolio_with_value(
        self,
        name: Optional[str] = None,
        chain: Optional[str] = None
    ) -> Dict:
        """
        Get full portfolio with USD values.
        """
        wallet = await self.get_active_wallet(chain) if not name else self.wallets.get(name)
        if not wallet:
            return {'error': 'No wallet found'}
        
        try:
            # Get native balance
            native = await self.get_balance(wallet.name, wallet.chain)
            native_balance = native.get('native_balance', 0)
            native_symbol = native.get('symbol', 'ETH')
            
            # Get native price
            native_price = await self.get_token_price(native_symbol, wallet.chain)
            native_usd = native_balance * native_price if native_price else None
            
            # Get tokens with prices
            tokens = await self.get_token_balances_with_prices(
                wallet_address=wallet.address,
                chain=wallet.chain
            )
            
            # Calculate total portfolio value
            total_usd = native_usd or 0
            if 'error' not in tokens:
                for symbol, info in tokens.items():
                    if info.get('usd_value'):
                        total_usd += info['usd_value']
            
            return {
                'wallet': {
                    'name': wallet.name,
                    'address': wallet.address,
                    'chain': wallet.chain,
                },
                'native': {
                    'symbol': native_symbol,
                    'balance': native_balance,
                    'price_usd': native_price,
                    'usd_value': native_usd,
                },
                'tokens': tokens,
                'total_tokens': len(tokens) if 'error' not in tokens else 0,
                'total_portfolio_usd': total_usd if total_usd > 0 else None,
            }
            
        except Exception as e:
            logger.error(f"❌ Portfolio with value failed: {e}")
            return {'error': str(e)}
    
    async def get_custom_token_balance(
        self,
        wallet_address: str,
        token_address: str,
        chain: str = 'ethereum'
    ) -> Optional[Dict]:
        """
        Get balance of ANY token by contract address.
        
        Returns: {symbol, balance, decimals, address}
        """
        try:
            w3 = Web3(Web3.HTTPProvider(
                'https://ethereum-rpc.publicnode.com' if chain == 'ethereum' else
                'https://arbitrum-one.publicnode.com' if chain == 'arbitrum' else
                'https://base-mainnet.publicnode.com' if chain == 'base' else
                'https://optimism-mainnet.publicnode.com' if chain == 'optimism' else
                'https://polygon-bor.publicnode.com'
            ))
            
            checksum = w3.to_checksum_address(token_address)
            contract = w3.eth.contract(address=checksum, abi=self.ERC20_ABI)
            
            # Get token details
            symbol = contract.functions.symbol().call()
            decimals = contract.functions.decimals().call()
            raw = contract.functions.balanceOf(w3.to_checksum_address(wallet_address)).call()
            
            balance = raw / (10 ** decimals)
            
            return {
                'symbol': symbol,
                'balance': balance,
                'decimals': decimals,
                'raw_balance': raw,
                'address': token_address,
            }
            
        except Exception as e:
            logger.error(f"Custom token check failed: {e}")
            return None
    
    async def send_token(
        self,
        wallet_name: str,
        token_symbol: str,
        to_address: str,
        amount: float,
        chain: Optional[str] = None,
        password: Optional[str] = None
    ) -> Dict:
        """
        Send ERC-20 token to another address.
        
        Args:
            wallet_name: Source wallet
            token_symbol: Token to send (e.g., 'USDC')
            to_address: Recipient address
            amount: Amount to send
            chain: Blockchain
            password: Master password for decryption
        
        Returns:
            {status, tx_hash, explorer_url, error}
        """
        try:
            wallet = self.wallets.get(wallet_name)
            if not wallet:
                return {'error': 'Wallet not found'}
            
            chain = chain or wallet.chain
            
            # Decrypt private key
            if not password and not self._master_password:
                return {'error': 'Password required'}
            
            pwd = password or self._master_password
            private_key = self.key_storage.decrypt(wallet.encrypted_key, pwd)
            
            # Setup Web3
            w3 = Web3(Web3.HTTPProvider(
                'https://ethereum-rpc.publicnode.com' if chain == 'ethereum' else
                'https://arbitrum-one.publicnode.com' if chain == 'arbitrum' else
                'https://base-mainnet.publicnode.com' if chain == 'base' else
                'https://optimism-mainnet.publicnode.com' if chain == 'optimism' else
                'https://polygon-bor.publicnode.com'
            ))
            
            # Get token address
            chain_tokens = self.TOKEN_LISTS.get(chain, {})
            token_address = chain_tokens.get(token_symbol.upper())
            
            if not token_address:
                return {'error': f'Token {token_symbol} not found for {chain}'}
            
            # Create contract
            checksum = w3.to_checksum_address(token_address)
            contract = w3.eth.contract(address=checksum, abi=self.ERC20_ABI)
            
            # Get decimals
            decimals = contract.functions.decimals().call()
            amount_raw = int(amount * (10 ** decimals))
            
            # Build transaction
            tx = contract.functions.transfer(
                w3.to_checksum_address(to_address),
                amount_raw
            ).build_transaction({
                'from': wallet.address,
                'nonce': w3.eth.get_transaction_count(wallet.address),
                'gas': 100000,  # Estimate
                'gasPrice': w3.to_wei('0.1', 'gwei'),  # Will use EIP-1559
            })
            
            # Sign and send
            signed = w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
            
            # Build explorer URL
            explorers = {
                'ethereum': f'https://etherscan.io/tx/{tx_hash.hex()}',
                'arbitrum': f'https://arbiscan.io/tx/{tx_hash.hex()}',
                'base': f'https://basescan.org/tx/{tx_hash.hex()}',
                'optimism': f'https://optimistic.etherscan.io/tx/{tx_hash.hex()}',
                'polygon': f'https://polygonscan.com/tx/{tx_hash.hex()}',
            }
            
            return {
                'status': 'sent',
                'tx_hash': tx_hash.hex(),
                'explorer_url': explorers.get(chain, ''),
                'amount': amount,
                'token': token_symbol,
                'to': to_address,
            }
            
        except Exception as e:
            logger.error(f"❌ Send token failed: {e}")
            return {'error': str(e)}
    
    async def send_native(
        self,
        wallet_name: str,
        to_address: str,
        amount_eth: float,
        chain: Optional[str] = None,
        password: Optional[str] = None
    ) -> Dict:
        """
        Send native currency (ETH/MATIC) to another address.
        """
        try:
            wallet = self.wallets.get(wallet_name)
            if not wallet:
                return {'error': 'Wallet not found'}
            
            chain = chain or wallet.chain
            
            # Decrypt private key
            pwd = password or self._master_password
            if not pwd:
                return {'error': 'Password required'}
            
            private_key = self.key_storage.decrypt(wallet.encrypted_key, pwd)
            
            # Setup Web3
            w3 = Web3(Web3.HTTPProvider(
                'https://ethereum-rpc.publicnode.com' if chain == 'ethereum' else
                'https://arbitrum-one.publicnode.com' if chain == 'arbitrum' else
                'https://base-mainnet.publicnode.com' if chain == 'base' else
                'https://optimism-mainnet.publicnode.com' if chain == 'optimism' else
                'https://polygon-bor.publicnode.com'
            ))
            
            # Build transaction
            tx = {
                'from': wallet.address,
                'to': w3.to_checksum_address(to_address),
                'value': w3.to_wei(amount_eth, 'ether'),
                'nonce': w3.eth.get_transaction_count(wallet.address),
                'gas': 21000,
                'gasPrice': w3.to_wei('0.1', 'gwei'),
                'chainId': w3.eth.chain_id,
            }
            
            # Sign and send
            signed = w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
            
            explorers = {
                'ethereum': f'https://etherscan.io/tx/{tx_hash.hex()}',
                'arbitrum': f'https://arbiscan.io/tx/{tx_hash.hex()}',
                'base': f'https://basescan.org/tx/{tx_hash.hex()}',
                'optimism': f'https://optimistic.etherscan.io/tx/{tx_hash.hex()}',
                'polygon': f'https://polygonscan.com/tx/{tx_hash.hex()}',
            }
            
            return {
                'status': 'sent',
                'tx_hash': tx_hash.hex(),
                'explorer_url': explorers.get(chain, ''),
                'amount': amount_eth,
                'token': 'ETH' if chain in ['ethereum', 'arbitrum', 'base', 'optimism'] else 'MATIC',
                'to': to_address,
            }
            
        except Exception as e:
            logger.error(f"❌ Send native failed: {e}")
            return {'error': str(e)}
        results = {}
        
        for symbol, address in chain_tokens.items():
            try:
                # Check if contract exists
                if not w3.eth.get_code(w3.to_checksum_address(address)):
                    continue
                
                # Create contract instance
                contract = w3.eth.contract(
                    address=w3.to_checksum_address(address),
                    abi=self.ERC20_ABI
                )
                
                # Get balance
                raw_balance = contract.functions.balanceOf(
                    w3.to_checksum_address(wallet_address)
                ).call()
                
                # Get decimals
                decimals = contract.functions.decimals().call()
                
                # Convert to human-readable
                balance = raw_balance / (10 ** decimals)
                
                if balance > 0:
                    results[symbol] = {
                        'balance': balance,
                        'decimals': decimals,
                        'raw_balance': raw_balance,
                        'address': address,
                    }
                    
            except Exception as e:
                logger.debug(f"Token {symbol} check failed: {e}")
                continue
        
        return results
    
    async def get_portfolio(
        self,
        name: Optional[str] = None,
        chain: Optional[str] = None
    ) -> Dict:
        """
        Get full portfolio including native balance + all token balances.
        
        Returns:
            {
                'wallet': wallet_info,
                'native': {symbol, balance},
                'tokens': {symbol: balance_info},
                'total_tokens': count,
            }
        """
        wallet = await self.get_active_wallet(chain) if not name else self.wallets.get(name)
        if not wallet:
            return {'error': 'No wallet found'}
        
        try:
            # Get native balance
            native = await self.get_balance(wallet.name, wallet.chain)
            
            # Get token balances
            tokens = await self.get_token_balances(
                wallet_address=wallet.address,
                chain=wallet.chain
            )
            
            # Check if tokens is an error dict
            if 'error' in tokens:
                tokens = {}
            
            return {
                'wallet': {
                    'name': wallet.name,
                    'address': wallet.address,
                    'chain': wallet.chain,
                },
                'native': {
                    'symbol': native.get('symbol', 'ETH'),
                    'balance': native.get('native_balance', 0),
                },
                'tokens': tokens,
                'total_tokens': len(tokens),
            }
            
        except Exception as e:
            logger.error(f"❌ Portfolio check failed: {e}")
            return {'error': str(e)}


# ============== FAST SETUP ==============

async def quick_setup_metamask(
    private_key: str,
    chain: str = 'ethereum',
    name: str = 'MetaMask Main',
    password: str = 'secure_password_123'
) -> WalletManager:
    """
    Quick setup for MetaMask wallet from PRIVATE KEY.

    Usage:
        manager = await quick_setup_metamask('0xabc123...', 'ethereum')
        wallet = await manager.get_active_wallet()
        balance = await manager.get_balance()
    """
    manager = WalletManager()
    await manager.initialize(master_password=password)

    # Add wallet
    wallet = await manager.add_wallet(
        name=name,
        private_key=private_key,
        chain=chain,
        password=password
    )

    return manager


async def quick_setup_from_mnemonic(
    mnemonic_phrase: str,
    chain: str = 'ethereum',
    name: str = 'MetaMask Main',
    password: str = 'secure_password_123',
    account_index: int = 0
) -> WalletManager:
    """
    Quick setup for MetaMask wallet from SECRET RECOVERY PHRASE.

    Usage:
        phrase = 'abandon abandon abandon ... art'
        manager = await quick_setup_from_mnemonic(phrase, 'ethereum')
        wallet = await manager.get_active_wallet()
        balance = await manager.get_balance()
    """
    manager = WalletManager()
    await manager.initialize(master_password=password)

    # Import from mnemonic
    wallet = await manager.import_from_mnemonic(
        name=name,
        mnemonic_phrase=mnemonic_phrase,
        chain=chain,
        account_index=account_index,
        password=password
    )

    return manager


if __name__ == "__main__":
    # Demo / test
    async def test():
        print("=" * 60)
        print("💼 WALLET MANAGER - DEMO")
        print("=" * 60)
        
        # Demo 1: Generate new mnemonic
        print("\n📌 1. Generate new Secret Recovery Phrase:")
        new_phrase = MnemonicWallet.generate_new_mnemonic(strength=128)
        print(f"   12-word phrase: {new_phrase}")
        
        # Demo 2: Derive address from known test phrase
        print("\n📌 2. Derive address from test phrase:")
        test_phrase = "abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about"
        is_valid = MnemonicWallet.validate_mnemonic(test_phrase)
        print(f"   Valid: {is_valid}")
        addr = MnemonicWallet.get_address_from_mnemonic(test_phrase, 'ethereum', 0)
        print(f"   Address (Account 0): {addr}")
        
        # Demo 3: Derive multiple accounts
        print("\n📌 3. Derive multiple MetaMask accounts:")
        accounts = MnemonicWallet.derive_multiple_accounts(test_phrase, 'ethereum', count=3)
        for acc in accounts:
            print(f"   Account {acc['index']}: {acc['address']}")
        
        print("\n📌 4. Quick setup from mnemonic:")
        manager = await quick_setup_from_mnemonic(test_phrase, 'ethereum', 'Test Wallet', 'demo_pass')
        wallets = await manager.list_wallets()
        for w in wallets:
            print(f"   Imported: {w['name']} -> {w['address']}")
        
        print("\n" + "=" * 60)
        print("✅ All demos passed!")
        print("=" * 60)

    asyncio.run(test())
