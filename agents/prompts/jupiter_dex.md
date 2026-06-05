# 🪐 JUPITER DEX INTEGRATION

## Purpose
Execute trades on Solana via Jupiter DEX aggregator.

## Architecture

### Paper Trading Mode (DEFAULT)
- Simulate execution using real market prices
- Track virtual P&L
- Zero risk while validating system

### Real Execution Mode (FUTURE)
- Connect to Solana wallet
- Execute real swaps via Jupiter API
- Track actual P&L

## Jupiter API Endpoints

### Quote API
```
GET https://quote-api.jup.ag/v6/quote?inputMint=USDC&outputMint=TOKEN&amount=AMOUNT&slippageBps=50
```

### Swap API
```
POST https://quote-api.jup.ag/v6/swap
Body: {
  "quoteResponse": quote_data,
  "userPublicKey": wallet_address,
  "wrapAndUnwrapSol": true
}
```

## Supported Tokens
- WIF (dogwifhat)
- POPCAT (Popcat)
- JTO (Jito)
- BONK (Bonk)
- PEPE (Pepe)
- USA (America)
- And any Solana SPL token

## Risk Controls for DEX Execution
1. **Max slippage:** 1% (100 bps)
2. **Min liquidity:** $50K (checked before execution)
3. **Price impact check:** Reject if >2%
4. **Timeout:** Cancel if not confirmed in 30s
5. **Gas estimation:** Ensure wallet has SOL for fees

## Paper Trading Rules
1. Use real-time price from DexScreener as "execution price"
2. Apply slippage penalty (0.5-1%)
3. Track virtual position
4. Calculate P&L based on price movement
5. Log everything for performance analysis

## Execution Flow
```
Signal Approved
    ↓
Check wallet balance (real) / virtual balance (paper)
    ↓
Get Jupiter quote (real price + slippage)
    ↓
Validate: slippage < 1%, price impact < 2%
    ↓
Paper: Log virtual trade
Real: Sign + send transaction
    ↓
Track position until TP or SL hit
    ↓
Log outcome
```

## Configuration
```
MODE=paper  # paper | real
WALLET_ADDRESS=YOUR_SOLANA_WALLET
PRIVATE_KEY=ENCRYPTED_KEY  # Only for real mode
SOL_BALANCE_MIN=0.01  # For gas fees
MAX_SLIPPAGE_BPS=100  # 1%
```

## Safety
- NEVER store private keys in plain text
- Use environment variables or encrypted storage
- Default to paper trading until user explicitly enables real mode
- Require confirmation before first real trade
