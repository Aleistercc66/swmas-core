# Master Blockchain Trading Agent Configuration

## Risk Levels
- CONSERVATIVE: Max 5% per position, 1x leverage, 3% stop loss
- MODERATE: Max 10% per position, 3x leverage, 5% stop loss  
- AGGRESSIVE: Max 20% per position, 5x leverage, 8% stop loss
- DEGEN: Max 50% per position, 10x leverage, 15% stop loss

## Supported Exchanges
1. **Binance** - Spot + Futures (API key required)
2. **Bybit** - Spot + Derivatives (API key required)
3. **OKX** - Spot + Futures (API key required)
4. **Jupiter** - Solana DEX aggregator (no key needed)

## Data Sources
- **On-chain**: Solana RPC, Helius, Birdeye
- **Off-chain**: Exchange APIs, DexScreener
- **Social**: Twitter/X sentiment (optional)

## Learning System
- Learning cycle: Every 1 hour
- Market scan: Every 5 minutes
- Strategy optimization: Daily

## Risk Management
- Max daily loss: 5% (moderate)
- Max drawdown: 20%
- Position sizing: Kelly Criterion + confidence adjustment
- Correlation limits enforced

## Telegram Alerts
Set BOT_TOKEN and CHAT_ID in environment or .env file
