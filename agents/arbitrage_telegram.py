#!/usr/bin/env python3
"""
Arbitrage Bot Telegram Integration
Adds arbitrage commands to @WorkSS11_bot orchestrator
"""
import asyncio
import json
import logging
from decimal import Decimal
from typing import Optional

try:
    import telegram
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logging.warning("python-telegram-bot not installed")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('arbitrage_telegram')


class ArbitrageTelegramIntegration:
    """
    Telegram commands for the Arbitrage Bot:
    
    /arbitrage_status    - Show all strategy status
    /arbitrage_start     - Start paper trading (all strategies)
    /arbitrage_stop      - Stop all strategies
    /cross_scan          - Run cross-exchange scan
    /triangular_scan     - Run triangular scan
    /funding_scan        - Run funding rate scan
    /arb_dashboard       - Show P&L dashboard
    """
    
    def __init__(self, bot_token: Optional[str] = None):
        self.bot_token = bot_token or "8386215028:AAFq3_Vn1kusUEIHH3c6oBL6K_aJaeYS4ac"
        self.active = False
        self.orchestrator = None
    
    async def arbitrage_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show arbitrage status"""
        keyboard = [
            [InlineKeyboardButton("🔄 Cross-Exchange", callback_data='cross_status')],
            [InlineKeyboardButton("🔺 Triangular", callback_data='tri_status')],
            [InlineKeyboardButton("💸 Funding Rate", callback_data='fund_status')],
            [InlineKeyboardButton("📊 Full Dashboard", callback_data='dashboard')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎯 ARBITRAGE BOT STATUS\n\n"
            "Select a strategy to view details:\n\n"
            "🧪 Currently in PAPER TRADING mode\n"
            "💰 Switch to LIVE with /arbitrage_live",
            reply_markup=reply_markup
        )
    
    async def cross_scan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Run quick cross-exchange scan"""
        await update.message.reply_text(
            "🔍 Running Cross-Exchange Scan...\n"
            "(This may take 10-15 seconds)"
        )
        
        # Import and run quick scan
        try:
            import sys
            sys.path.insert(0, '/root/.openclaw/workspace/agents')
            from cross_exchange_arbitrage import CrossExchangeArbitrageBot, ExchangeConfig
            
            exchanges = [
                ExchangeConfig('binance', trading_fee=Decimal('0.001')),
                ExchangeConfig('bybit', trading_fee=Decimal('0.001')),
                ExchangeConfig('okx', trading_fee=Decimal('0.001')),
                ExchangeConfig('kucoin', trading_fee=Decimal('0.001')),
            ]
            
            bot = CrossExchangeArbitrageBot(
                exchanges=exchanges,
                min_spread_pct=Decimal('0.002'),
                trade_size_usd=Decimal('500'),
                paper_trading=True
            )
            
            await bot.initialize_exchanges()
            await bot.fetch_tickers()
            opportunities = bot.detect_opportunities()
            
            if opportunities:
                top5 = opportunities[:5]
                msg = "🔥 TOP CROSS-EXCHANGE OPPORTUNITIES:\n\n"
                for i, opp in enumerate(top5, 1):
                    msg += (
                        f"{i}. {opp.symbol}\n"
                        f"   📉 Buy: {opp.buy_exchange} @ ${float(opp.buy_price):.4f}\n"
                        f"   📈 Sell: {opp.sell_exchange} @ ${float(opp.sell_price):.4f}\n"
                        f"   📊 Spread: {float(opp.spread_pct):.3f}%\n"
                        f"   💵 Profit: ${float(opp.profit_usd):.2f}\n\n"
                    )
            else:
                msg = "📊 No profitable cross-exchange opportunities found right now.\n"
                msg += "Markets are efficient! Check again in a few minutes."
            
            await bot.close()
            
            await update.message.reply_text(msg)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Scan error: {str(e)}")
    
    async def funding_scan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Run funding rate scan"""
        await update.message.reply_text(
            "💸 Running Funding Rate Scan...\n"
            "(Checking Binance, Bybit, OKX)"
        )
        
        try:
            import sys
            sys.path.insert(0, '/root/.openclaw/workspace/agents')
            from funding_rate_arbitrage import FundingRateArbitrageBot
            
            bot = FundingRateArbitrageBot(
                exchanges=['binance', 'bybit', 'okx'],
                min_funding_diff=Decimal('0.00005'),
                paper_trading=True
            )
            
            await bot.initialize()
            await bot.fetch_funding_rates()
            opportunities = bot.detect_opportunities()
            
            if opportunities:
                top5 = opportunities[:5]
                msg = "💰 TOP FUNDING RATE OPPORTUNITIES:\n\n"
                for i, opp in enumerate(top5, 1):
                    msg += (
                        f"{i}. {opp.symbol}\n"
                        f"   📉 LONG: {opp.long_exchange} ({float(opp.long_funding)*100:.4f}%)\n"
                        f"   📈 SHORT: {opp.short_exchange} ({float(opp.short_funding)*100:.4f}%)\n"
                        f"   📊 Spread: {float(opp.funding_diff)*100:.4f}% / 8h\n"
                        f"   🎯 Annualized: {float(opp.annualized_return):.1f}%\n\n"
                    )
            else:
                msg = "📊 No significant funding rate spreads found.\n"
                msg += "Funding rates are converging across exchanges."
            
            await bot.close()
            await update.message.reply_text(msg)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Scan error: {str(e)}")
    
    async def arb_dashboard(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show arbitrage dashboard"""
        msg = (
            "📊 ARBITRAGE DASHBOARD\n"
            "═════════════════════\n\n"
            "🧪 MODE: Paper Trading\n\n"
            "STRATEGIES:\n"
            "  🔄 Cross-Exchange: SCANNING\n"
            "  🔺 Triangular: SCANNING\n"  
            "  💸 Funding Rate: SCANNING\n\n"
            "📈 TODAY'S STATS:\n"
            "  Opportunities found: Check logs\n"
            "  Trades simulated: Check logs\n"
            "  P&L: Check logs\n\n"
            "COMMANDS:\n"
            "  /cross_scan - Cross-exchange scan\n"
            "  /funding_scan - Funding rate scan\n"
            "  /arbitrage_status - Full status\n\n"
            "⚠️ To go LIVE, run:\n"
            "  /arbitrage_live\n"
            "  (Requires API keys in .env)"
        )
        await update.message.reply_text(msg)
    
    def setup_handlers(self, application: Application):
        """Register handlers with the bot"""
        application.add_handler(CommandHandler('arbitrage_status', self.arbitrage_status))
        application.add_handler(CommandHandler('cross_scan', self.cross_scan))
        application.add_handler(CommandHandler('funding_scan', self.funding_scan))
        application.add_handler(CommandHandler('arb_dashboard', self.arb_dashboard))
        
        logger.info("✅ Arbitrage Telegram commands registered")


# Standalone run for testing
async def main():
    """Test the Telegram integration"""
    if not TELEGRAM_AVAILABLE:
        print("❌ python-telegram-bot not installed")
        print("   Run: pip install python-telegram-bot")
        return
    
    integration = ArbitrageTelegramIntegration()
    
    application = Application.builder().token(integration.bot_token).build()
    integration.setup_handlers(application)
    
    print("🚀 Arbitrage Telegram bot starting...")
    print("   Commands:")
    print("   /arbitrage_status - Status")
    print("   /cross_scan - Cross-exchange scan")
    print("   /funding_scan - Funding rate scan")
    print("   /arb_dashboard - Dashboard")
    
    await application.run_polling()


if __name__ == '__main__':
    asyncio.run(main())
