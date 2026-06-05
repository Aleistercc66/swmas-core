#!/usr/bin/env python3
"""
MetaMask / Wallet Commands for Telegram Orchestrator
Integrates wallet management directly into the bot
"""
import os
import asyncio
import logging
from typing import Dict, Optional
from telegram import Update
from telegram.ext import ContextTypes

# Import wallet manager
from core.wallet_manager import WalletManager, quick_setup_metamask

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('wallet_commands')


class WalletCommandHandler:
    """
    Handles all wallet-related Telegram commands.
    Connects user's MetaMask to the orchestrator.
    """
    
    def __init__(self):
        self.wallet_manager: Optional[WalletManager] = None
        self.trading_bridge: Optional['WalletTradingBridge'] = None
        self._pending_setup: Dict[int, Dict] = {}  # user_id -> setup state
    
    async def initialize(self):
        """Initialize wallet system"""
        self.wallet_manager = WalletManager()
        # Initialize without password — will ask user when needed
        # But still load existing wallets (they're just encrypted until password is provided)
        await self.wallet_manager.initialize()
        logger.info(f"💼 Wallet commands initialized ({len(self.wallet_manager.wallets)} wallets loaded)")
    
    # ============== COMMAND HANDLERS ==============
    
    async def cmd_wallet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /wallet — Show wallet menu and status
        """
        user_id = update.effective_user.id
        
        if not self.wallet_manager:
            await update.message.reply_text(
                "⚠️ Wallet system not initialized. Use /wallet_setup first!"
            )
            return
        
        wallets = await self.wallet_manager.list_wallets()
        
        if not wallets:
            text = """
💼 **NO WALLETS CONFIGURED** 💼

You haven't connected any MetaMask wallets yet.

**To connect:**
`/wallet_setup` — Connect your MetaMask

**Supported chains:**
• Ethereum
• Arbitrum
• Base
• Optimism
• Polygon
• Solana
"""
            await update.message.reply_text(text, parse_mode="Markdown")
            return
        
        text = "💼 **YOUR WALLETS** 💼\n\n"
        for w in wallets:
            active = "🟢" if w['is_active'] else "⚪"
            text += f"{active} **{w['name']}**\n"
            text += f"   `{w['address'][:6]}...{w['address'][-4:]}`\n"
            text += f"   Chain: {w['chain']}\n\n"
        
        text += "\n**Commands:**\n"
        text += "`/balance` — Check balances\n"
        text += "`/wallet_add` — Add another wallet\n"
        text += "`/wallet_remove <name>` — Remove wallet"
        
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def cmd_wallet_setup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /wallet_setup — Interactive MetaMask setup wizard
        Supports BOTH:
          • Private Key import
          • Secret Recovery Phrase (12/24 words) import
        """
        user_id = update.effective_user.id
        
        text = """
🔐 **META MASK SETUP** 🔐

I'll help you connect your MetaMask wallet securely.

**IMPORTANT SECURITY NOTES:**
• Your private key / seed phrase will be ENCRYPTED
• I NEVER store keys in plain text
• You need a master password to decrypt

**Step 1:** Enter your master password (for encryption)
**Step 2:** Choose import method (private key OR seed phrase)
**Step 3:** Enter your credentials
**Step 4:** Select blockchain

**⚠️ WARNING:**
Only use this with wallets you're comfortable automating.
Consider using a dedicated trading wallet (not your main savings).

Reply with your master password to continue:
"""
        await update.message.reply_text(text, parse_mode="Markdown")
        
        # Set state: waiting for password
        self._pending_setup[user_id] = {'step': 'password'}
    
    async def _ask_import_method(self, update: Update, user_id: int):
        """Ask user to choose import method"""
        await update.message.reply_text(
            "✅ Password set!\n\n"
            "**Step 2:** Choose import method\n\n"
            "Reply with one of:\n"
            "• `key` — Import from Private Key\n"
            "• `phrase` — Import from Secret Recovery Phrase (12/24 words)\n\n"
            "💡 *Tip: Use `phrase` to import your MetaMask with all accounts*",
            parse_mode="Markdown"
        )
        self._pending_setup[user_id]['step'] = 'import_method'
    
    async def _ask_private_key(self, update: Update, user_id: int):
        """Ask for private key"""
        await update.message.reply_text(
            "🔑 **Private Key Import**\n\n"
            "Send your private key\n"
            "Format: `0xabc123...` or raw key\n\n"
            "⚠️ This message will be deleted for security!",
            parse_mode="Markdown"
        )
        self._pending_setup[user_id]['step'] = 'private_key'
    
    async def _ask_seed_phrase(self, update: Update, user_id: int):
        """Ask for seed phrase"""
        await update.message.reply_text(
            "📝 **Secret Recovery Phrase Import**\n\n"
            "Send your 12 or 24-word Secret Recovery Phrase\n\n"
            "Example format:\n"
            "`abandon abandon abandon ... about`\n\n"
            "💡 This will derive your Account 1 (index 0) by default.\n"
            "You can import more accounts later with `/wallet_add`\n\n"
            "⚠️ This message will be deleted for security!",
            parse_mode="Markdown"
        )
        self._pending_setup[user_id]['step'] = 'seed_phrase'
    
    async def _ask_chain(self, update: Update, user_id: int):
        """Ask for blockchain selection"""
        await update.message.reply_text(
            "✅ Received!\n\n"
            "**Step 3:** Select blockchain\n"
            "Reply with one of:\n"
            "• `ethereum` (default)\n"
            "• `arbitrum`\n"
            "• `base`\n"
            "• `optimism`\n"
            "• `polygon`\n"
            "• `solana`",
            parse_mode="Markdown"
        )
        self._pending_setup[user_id]['step'] = 'chain'
    
    async def _finalize_wallet_setup(
        self, 
        update: Update, 
        user_id: int,
        chain: str
    ):
        """Finalize wallet setup with collected data"""
        state = self._pending_setup[user_id]
        
        # Initialize wallet manager with password
        await self.wallet_manager.initialize(master_password=state['password'])
        
        try:
            if state.get('import_method') == 'phrase':
                # Import from mnemonic
                from core.wallet_manager import MnemonicWallet
                
                wallet = await self.wallet_manager.import_from_mnemonic(
                    name='MetaMask Main',
                    mnemonic_phrase=state['seed_phrase'],
                    chain=chain,
                    account_index=state.get('account_index', 0),
                    password=state['password']
                )
                
                # Show confirmation
                word_count = len(state['seed_phrase'].strip().split())
                await update.message.reply_text(
                    f"✅ **WALLET CONNECTED!** ✅\n\n"
                    f"Method: Secret Recovery Phrase ({word_count} words)\n"
                    f"Account: {state.get('account_index', 0) + 1}\n"
                    f"Name: {wallet.name}\n"
                    f"Address: `{wallet.address}`\n"
                    f"Chain: {chain.upper()}\n\n"
                    f"💡 Want more accounts from same phrase?\n"
                    f"Use `/wallet_add` to import Account 2, 3, etc.\n\n"
                    f"Use `/balance` to check your balance!\n"
                    f"Use `/wallet` to see all wallets.",
                    parse_mode="Markdown"
                )
                
            else:
                # Import from private key
                wallet = await self.wallet_manager.add_wallet(
                    name='MetaMask Main',
                    private_key=state['private_key'],
                    chain=chain,
                    password=state['password']
                )
                
                await update.message.reply_text(
                    f"✅ **WALLET CONNECTED!** ✅\n\n"
                    f"Method: Private Key\n"
                    f"Name: {wallet.name}\n"
                    f"Address: `{wallet.address}`\n"
                    f"Chain: {chain.upper()}\n\n"
                    f"Use `/balance` to check your balance!\n"
                    f"Use `/wallet` to see all wallets.",
                    parse_mode="Markdown"
                )
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ **Setup failed:** {str(e)}\n\n"
                f"Please check your credentials and try again.\n"
                f"Use `/wallet_setup` to restart."
            )
        
        # Clear pending setup
        del self._pending_setup[user_id]
        
        # Delete password from memory
        if 'password' in state:
            state['password'] = '***cleared***'
        if 'private_key' in state:
            state['private_key'] = '***cleared***'
        if 'seed_phrase' in state:
            state['seed_phrase'] = '***cleared***'

    async def handle_setup_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle messages during wallet setup wizard.
        Supports both Private Key and Secret Recovery Phrase imports.
        Also handles /wallet_add flow.
        """
        user_id = update.effective_user.id
        
        if user_id not in self._pending_setup:
            return False  # Not in setup mode
        
        state = self._pending_setup[user_id]
        text = update.message.text.strip()
        
        # Check if this is a wallet_add flow
        if state.get('step', '').startswith('wallet_add'):
            return await self._handle_wallet_add(update, user_id, text)
        
        if state['step'] == 'password':
            # Got master password
            state['password'] = text
            
            # Delete password message for security
            try:
                await update.message.delete()
            except:
                pass
            
            # Move to import method selection
            await self._ask_import_method(update, user_id)
            return True
                
        elif state['step'] == 'import_method':
            # User chose import method — be smart about parsing
            text_lower = text.lower().strip()
            
            # Try to extract just the first word (ignore extra text, colons, etc.)
            first_word = text_lower.split()[0] if text_lower.split() else ''
            # Strip common punctuation like colons
            first_word = first_word.rstrip(':;.,!?')
            
            # Also check if text starts with these keywords
            is_key = first_word in ('key', 'private key', 'private_key', 'pk') or \
                     text_lower.startswith('key') or text_lower.startswith('private')
            
            is_phrase = first_word in ('phrase', 'seed', 'mnemonic', 'recovery', 'secret') or \
                        text_lower.startswith('phrase') or text_lower.startswith('seed') or \
                        text_lower.startswith('mnemonic') or text_lower.startswith('secret')
            
            if is_key:
                state['import_method'] = 'key'
                await self._ask_private_key(update, user_id)
                
            elif is_phrase:
                state['import_method'] = 'phrase'
                await self._ask_seed_phrase(update, user_id)
                
            else:
                # If it's clearly a private key (0x... or hex), accept as key
                if text.startswith('0x') or len(text) == 64:
                    state['import_method'] = 'key'
                    state['private_key'] = text
                    await self._ask_chain(update, user_id)
                    return True
                
                # If it's a valid mnemonic phrase (12+ words), accept as phrase
                from core.wallet_manager import MnemonicWallet
                if MnemonicWallet.validate_mnemonic(text):
                    state['import_method'] = 'phrase'
                    state['seed_phrase'] = text
                    # Validate
                    words = text.split()
                    await update.message.reply_text(
                        f"✅ Valid {len(words)}-word phrase detected!\n\n"
                        f"💡 Which MetaMask account to import?\n"
                        f"Account 1 = index 0 (default)\n"
                        f"Account 2 = index 1, etc.\n\n"
                        f"Reply with the account number (1-10) or `default` for Account 1:"
                    )
                    state['step'] = 'account_index'
                    return True
                
                await update.message.reply_text(
                    "❌ Invalid choice. Reply with `key` or `phrase`\n\n"
                    "💡 *Tip: You can also send your private key or seed phrase directly!*"
                )
            return True
                
        elif state['step'] == 'private_key':
            # Got private key
            state['private_key'] = text
            
            # Delete key message for security
            try:
                await update.message.delete()
            except:
                pass
            
            # Move to chain selection
            await self._ask_chain(update, user_id)
            return True
                
        elif state['step'] == 'seed_phrase':
            # Got seed phrase — strip common prefixes like "Phrase:" or "Seed:"
            raw_text = text.strip()
            # Remove common prefixes
            prefixes = ['phrase:', 'seed:', 'mnemonic:', 'secret:', 'recovery phrase:', 'recovery:']
            clean_text = raw_text
            for prefix in prefixes:
                if clean_text.lower().startswith(prefix):
                    clean_text = clean_text[len(prefix):].strip()
                    break
            
            state['seed_phrase'] = clean_text
            
            # Validate the phrase
            from core.wallet_manager import MnemonicWallet
            is_valid = MnemonicWallet.validate_mnemonic(clean_text)
            
            if not is_valid:
                await update.message.reply_text(
                    "❌ **Invalid Secret Recovery Phrase!**\n\n"
                    "Must be 12, 15, 18, 21, or 24 valid BIP-39 words.\n"
                    "Check for typos or extra spaces.\n\n"
                    "Please send it again:"
                )
                return True  # Stay in seed_phrase step
            
            # Delete phrase message for security
            try:
                await update.message.delete()
            except:
                pass
            
            # Check if user wants specific account index
            words = clean_text.split()
            await update.message.reply_text(
                f"✅ Valid {len(words)}-word phrase received!\n\n"
                f"💡 Which MetaMask account to import?\n"
                f"Account 1 = index 0 (default)\n"
                f"Account 2 = index 1, etc.\n\n"
                f"Reply with the account number (1-10) or `default` for Account 1:"
            )
            state['step'] = 'account_index'
            return True
        
        elif state['step'] == 'account_index':
            # Got account index selection
            if text.lower() in ('default', '1', 'account 1'):
                state['account_index'] = 0
            else:
                try:
                    idx = int(text) - 1  # User sees 1-based, we store 0-based
                    if idx < 0 or idx > 9:
                        raise ValueError()
                    state['account_index'] = idx
                except:
                    await update.message.reply_text(
                        "❌ Invalid account number. Send a number 1-10 or `default`"
                    )
                    return True
            
            # Move to chain selection
            await self._ask_chain(update, user_id)
            return True
                
        elif state['step'] == 'chain':
            # Got chain selection
            chain = text.lower().strip()
            valid_chains = ['ethereum', 'arbitrum', 'base', 'optimism', 'polygon', 'solana']
            
            if chain not in valid_chains:
                await update.message.reply_text(
                    f"❌ Invalid chain. Choose from: {', '.join(valid_chains)}"
                )
                return True
            
            # Finalize setup
            await self._finalize_wallet_setup(update, user_id, chain)
            return True
        
        return True
    
    async def cmd_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /balance — Check wallet balance
        """
        if not self.wallet_manager:
            await update.message.reply_text("⚠️ Wallet system not initialized. Use /wallet_setup first!")
            return
        
        wallets = await self.wallet_manager.list_wallets()
        
        if not wallets:
            await update.message.reply_text("💼 No wallets configured. Use /wallet_setup to connect MetaMask.")
            return
        
        await update.message.reply_text("🔍 Checking balances...")
        
        for wallet in wallets:
            if not wallet['is_active']:
                continue
            
            try:
                balance = await self.wallet_manager.get_balance(
                    name=wallet['name'],
                    chain=wallet['chain']
                )
                
                if 'error' in balance:
                    await update.message.reply_text(
                        f"❌ `{wallet['name']}`: {balance['error']}",
                        parse_mode="Markdown"
                    )
                else:
                    symbol = balance.get('symbol', 'ETH')
                    native = balance.get('native_balance', 0)
                    
                    await update.message.reply_text(
                        f"💰 **{wallet['name']}**\n"
                        f"Address: `{balance['address']}`\n"
                        f"Balance: `{native:.6f} {symbol}`\n"
                        f"Chain: {wallet['chain'].upper()}",
                        parse_mode="Markdown"
                    )
                    
            except Exception as e:
                logger.error(f"Balance check failed: {e}")
                await update.message.reply_text(f"❌ Error checking {wallet['name']}: {str(e)}")
    
    async def cmd_portfolio(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /portfolio — Show full portfolio with native + token balances
        """
        if not self.wallet_manager:
            await update.message.reply_text("⚠️ Wallet system not initialized. Use /wallet_setup first!")
            return
        
        wallets = await self.wallet_manager.list_wallets()
        
        if not wallets:
            await update.message.reply_text("💼 No wallets configured. Use /wallet_setup to connect MetaMask.")
            return
        
        await update.message.reply_text("📊 Building portfolio...")
        
        for wallet in wallets:
            if not wallet['is_active']:
                continue
            
            try:
                # Use NEW method with prices
                portfolio = await self.wallet_manager.get_portfolio_with_value(
                    name=wallet['name'],
                    chain=wallet['chain']
                )
                
                if 'error' in portfolio:
                    await update.message.reply_text(
                        f"❌ `{wallet['name']}`: {portfolio['error']}",
                        parse_mode="Markdown"
                    )
                    continue
                
                # Build portfolio text with prices
                native = portfolio.get('native', {})
                tokens = portfolio.get('tokens', {})
                total_usd = portfolio.get('total_portfolio_usd')
                
                text = f"📊 **PORTFOLIO: {wallet['name']}** 📊\n\n"
                text += f"🔹 **Address:** `{wallet['address']}`\n"
                text += f"🔹 **Chain:** {wallet['chain'].upper()}\n"
                
                # Total value
                if total_usd:
                    text += f"💰 **Total Value: ${total_usd:.2f}**\n"
                text += "\n"
                
                # Native balance
                native_symbol = native.get('symbol', 'ETH')
                native_balance = native.get('balance', 0)
                native_price = native.get('price_usd')
                native_usd = native.get('usd_value')
                
                text += f"💎 **Native:** `{native_balance:.6f} {native_symbol}`"
                if native_usd:
                    text += f" _(~${native_usd:.2f})_"
                text += "\n\n"
                
                # Token balances with prices
                if tokens and 'error' not in tokens:
                    text += "🪙 **TOKENS:**\n"
                    for symbol, info in tokens.items():
                        balance = info.get('balance', 0)
                        price = info.get('price_usd')
                        usd_value = info.get('usd_value')
                        
                        if balance > 0:
                            if balance >= 1:
                                text += f"  • **{symbol}:** `{balance:.4f}`"
                            elif balance >= 0.01:
                                text += f"  • **{symbol}:** `{balance:.6f}`"
                            else:
                                text += f"  • **{symbol}:** `{balance:.8f}`"
                            
                            if price:
                                text += f" @ ${price:.4f}"
                            if usd_value:
                                text += f" = **${usd_value:.2f}**"
                            text += "\n"
                    
                    text += f"\n📈 **Total Tokens:** {len(tokens)}\n"
                else:
                    text += "🪙 **Tokens:** None detected\n"
                
                text += f"\n💡 Use `/balance` for native only"
                
                await update.message.reply_text(text, parse_mode="Markdown")
                    
            except Exception as e:
                logger.error(f"Portfolio check failed: {e}")
                await update.message.reply_text(f"❌ Error building portfolio: {str(e)}")
    
    async def cmd_wallet_add(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /wallet_add — Add another wallet (e.g., Account 2, 3 from same seed)
        """
        user_id = update.effective_user.id
        
        wallets = await self.wallet_manager.list_wallets()
        if not wallets:
            await update.message.reply_text(
                "❌ No wallets configured yet. Use `/wallet_setup` first!",
                parse_mode="Markdown"
            )
            return
        
        # Check if we have a mnemonic-based wallet to derive from
        text = """
➕ **ADD NEW WALLET** ➕

How would you like to add a wallet?

**Option 1:** Import from same Secret Recovery Phrase
(requires existing phrase-based wallet)

**Option 2:** Import new Private Key

Reply with:
• `same` — Derive from existing seed phrase
• `new` — Import new private key
• `cancel` — Cancel
"""
        await update.message.reply_text(text, parse_mode="Markdown")
        
        self._pending_setup[user_id] = {
            'step': 'wallet_add_method',
            'existing_wallets': wallets
        }
    
    async def _handle_wallet_add(self, update: Update, user_id: int, text: str):
        """Handle /wallet_add flow"""
        state = self._pending_setup[user_id]
        
        if state['step'] == 'wallet_add_method':
            choice = text.lower()
            
            if choice in ('cancel', 'exit', 'stop'):
                del self._pending_setup[user_id]
                await update.message.reply_text("❌ Cancelled.")
                return True
            
            if choice in ('same', 'phrase', 'mnemonic', 'seed'):
                # Need to get the seed phrase from an existing wallet
                # For security, we need to re-enter the phrase
                await update.message.reply_text(
                    "📝 **Derive from Seed Phrase**\n\n"
                    "Enter your Secret Recovery Phrase again:\n"
                    "(needed to derive new account)\n\n"
                    "⚠️ This message will be deleted for security!",
                    parse_mode="Markdown"
                )
                state['step'] = 'wallet_add_phrase'
                return True
            
            elif choice in ('new', 'key', 'private'):
                await update.message.reply_text(
                    "🔑 **New Private Key**\n\n"
                    "Send the new private key:\n"
                    "Format: `0xabc123...` or raw key\n\n"
                    "⚠️ This message will be deleted for security!",
                    parse_mode="Markdown"
                )
                state['step'] = 'wallet_add_new_key'
                return True
            
            else:
                await update.message.reply_text(
                    "❌ Invalid choice. Reply with `same`, `new`, or `cancel`"
                )
                return True
        
        elif state['step'] == 'wallet_add_phrase':
            # Got phrase
            state['seed_phrase'] = text
            
            # Validate
            from core.wallet_manager import MnemonicWallet
            if not MnemonicWallet.validate_mnemonic(text):
                await update.message.reply_text(
                    "❌ Invalid phrase. Please send again:"
                )
                return True
            
            # Delete for security
            try:
                await update.message.delete()
            except:
                pass
            
            # Ask for account index
            await update.message.reply_text(
                "✅ Valid phrase!\n\n"
                "Which account to import?\n"
                "Account 1 = index 0\n"
                "Account 2 = index 1\n"
                "etc.\n\n"
                "Reply with account number (1-10):"
            )
            state['step'] = 'wallet_add_index'
            return True
        
        elif state['step'] == 'wallet_add_index':
            # Got index
            try:
                idx = int(text) - 1
                if idx < 0 or idx > 9:
                    raise ValueError()
                state['account_index'] = idx
            except:
                await update.message.reply_text(
                    "❌ Invalid number. Send 1-10:"
                )
                return True
            
            # Ask for chain
            await update.message.reply_text(
                "Select blockchain:\n"
                "`ethereum`, `arbitrum`, `base`, `optimism`, `polygon`, `solana`"
            )
            state['step'] = 'wallet_add_chain'
            return True
        
        elif state['step'] == 'wallet_add_chain':
            chain = text.lower().strip()
            valid = ['ethereum', 'arbitrum', 'base', 'optimism', 'polygon', 'solana']
            
            if chain not in valid:
                await update.message.reply_text(
                    f"❌ Invalid chain. Choose from: {', '.join(valid)}"
                )
                return True
            
            # Derive and add
            try:
                # Re-initialize if needed
                if not self.wallet_manager._secure_storage:
                    await update.message.reply_text(
                        "🔐 Enter your master password to decrypt:"
                    )
                    state['step'] = 'wallet_add_password'
                    state['pending_chain'] = chain
                    return True
                
                wallet = await self.wallet_manager.import_from_mnemonic(
                    name=f"MetaMask Account {state['account_index'] + 1}",
                    mnemonic_phrase=state['seed_phrase'],
                    chain=chain,
                    account_index=state['account_index'],
                    password=self.wallet_manager._master_password
                )
                
                await update.message.reply_text(
                    f"✅ **WALLET ADDED!** ✅\n\n"
                    f"Name: {wallet.name}\n"
                    f"Address: `{wallet.address}`\n"
                    f"Chain: {chain.upper()}",
                    parse_mode="Markdown"
                )
                
            except Exception as e:
                await update.message.reply_text(
                    f"❌ Failed to add wallet: {str(e)}"
                )
            
            del self._pending_setup[user_id]
            return True
        
        elif state['step'] == 'wallet_add_password':
            # Got password for decryption
            try:
                await self.wallet_manager.initialize(master_password=text)
                
                chain = state.get('pending_chain', 'ethereum')
                wallet = await self.wallet_manager.import_from_mnemonic(
                    name=f"MetaMask Account {state['account_index'] + 1}",
                    mnemonic_phrase=state['seed_phrase'],
                    chain=chain,
                    account_index=state['account_index'],
                    password=text
                )
                
                await update.message.reply_text(
                    f"✅ **WALLET ADDED!** ✅\n\n"
                    f"Name: {wallet.name}\n"
                    f"Address: `{wallet.address}`\n"
                    f"Chain: {chain.upper()}",
                    parse_mode="Markdown"
                )
                
            except Exception as e:
                await update.message.reply_text(
                    f"❌ Failed: {str(e)}"
                )
            
            try:
                await update.message.delete()
            except:
                pass
            
            del self._pending_setup[user_id]
            return True
        
        elif state['step'] == 'wallet_add_new_key':
            # Got new private key
            state['private_key'] = text
            
            try:
                await update.message.delete()
            except:
                pass
            
            await update.message.reply_text(
                "Select blockchain:\n"
                "`ethereum`, `arbitrum`, `base`, `optimism`, `polygon`, `solana`"
            )
            state['step'] = 'wallet_add_new_chain'
            return True
        
        elif state['step'] == 'wallet_add_new_chain':
            chain = text.lower().strip()
            valid = ['ethereum', 'arbitrum', 'base', 'optimism', 'polygon', 'solana']
            
            if chain not in valid:
                await update.message.reply_text(
                    f"❌ Invalid chain. Choose from: {', '.join(valid)}"
                )
                return True
            
            # Need password
            if not self.wallet_manager._secure_storage:
                await update.message.reply_text(
                    "🔐 Enter master password:"
                )
                state['step'] = 'wallet_add_new_password'
                state['pending_chain'] = chain
                return True
            
            try:
                wallet = await self.wallet_manager.add_wallet(
                    name=f"Wallet {len(await self.wallet_manager.list_wallets()) + 1}",
                    private_key=state['private_key'],
                    chain=chain,
                    password=self.wallet_manager._master_password
                )
                
                await update.message.reply_text(
                    f"✅ **WALLET ADDED!** ✅\n\n"
                    f"Name: {wallet.name}\n"
                    f"Address: `{wallet.address}`\n"
                    f"Chain: {chain.upper()}",
                    parse_mode="Markdown"
                )
                
            except Exception as e:
                await update.message.reply_text(f"❌ Failed: {str(e)}")
            
            del self._pending_setup[user_id]
            return True
        
        elif state['step'] == 'wallet_add_new_password':
            # Got password for new key
            try:
                await self.wallet_manager.initialize(master_password=text)
                chain = state.get('pending_chain', 'ethereum')
                
                wallet = await self.wallet_manager.add_wallet(
                    name=f"Wallet {len(await self.wallet_manager.list_wallets()) + 1}",
                    private_key=state['private_key'],
                    chain=chain,
                    password=text
                )
                
                await update.message.reply_text(
                    f"✅ **WALLET ADDED!** ✅\n\n"
                    f"Name: {wallet.name}\n"
                    f"Address: `{wallet.address}`\n"
                    f"Chain: {chain.upper()}",
                    parse_mode="Markdown"
                )
                
            except Exception as e:
                await update.message.reply_text(f"❌ Failed: {str(e)}")
            
            try:
                await update.message.delete()
            except:
                pass
            
            del self._pending_setup[user_id]
            return True
        
        return True

    async def cmd_trade(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        /trade — Trading interface
        """
        text = """
📈 **TRADING COMMANDS** 📈

**Swap Tokens:**
`/swap <from> <to> <amount>` — Swap tokens
Example: `/swap ETH USDC 0.5`

**Limit Orders:**
`/limit_buy <token> <price> <amount>`
`/limit_sell <token> <price> <amount>`

**Portfolio:**
`/portfolio` — View all positions
`/pnl` — Profit/loss summary

**Settings:**
`/slippage <percent>` — Set max slippage
`/gas <speed>` — Set gas speed (slow/normal/fast)

⚠️ **Trading requires wallet setup first!**
Use `/wallet_setup` to connect MetaMask.
"""
        await update.message.reply_text(text, parse_mode="Markdown")
    
    async def is_setting_up(self, user_id: int) -> bool:
        """Check if user is in wallet setup flow"""
        return user_id in self._pending_setup


# ============== FACTORY ==============

wallet_handler = WalletCommandHandler()

async def initialize_wallet_system():
    """Initialize the wallet command handler"""
    await wallet_handler.initialize()
    return wallet_handler
