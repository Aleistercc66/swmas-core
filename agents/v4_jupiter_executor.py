#!/usr/bin/env python3
"""
🪐 JUPITER DEX EXECUTOR
Paper trading + real execution via Jupiter aggregator
"""
import requests
import json
import time
from datetime import datetime
from pathlib import Path

# Jupiter API endpoints
JUPITER_QUOTE_API = "https://api.jup.ag/swap/v1/quote"
JUPITER_SWAP_API = "https://api.jup.ag/swap/v1/swap"

# Paper trading state file
PAPER_STATE = "/root/.openclaw/workspace/agents/logs/paper_trading.json"

# Token mint addresses (Solana mainnet)
TOKEN_MINTS = {
    "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
    "SOL": "So11111111111111111111111111111111111111112",
    "WIF": "EKpQGSJtjMFqKZ9KQanSq7RcjZHBu5PvTjQ7yLRdZZ3V",
    "POPCAT": "7GCihgDB8fe6KNjn2MYtkzZcRjQy3t9GHdC8uHYmW2hr",
    "JTO": "jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2r2PXcSL",
    "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    "PEPE": "A3eME5CetyZPBoWbRUwY3tUe25x82GnsfWc2Eb3YxXz",  # Check if exists on Solana
    "USA": "69kdRLyP5DTRkpHraaSZaqmXMfHRi4pm8wM7dxMeBxyz",  # Example - verify real address
}

class JupiterExecutor:
    def __init__(self, mode="paper", wallet_address=None):
        self.mode = mode  # "paper" or "real"
        self.wallet_address = wallet_address
        self.paper_balance = 10000.0  # Virtual USDT
        self.positions = []
        self.trade_history = []
        self.load_state()
    
    def load_state(self):
        if Path(PAPER_STATE).exists():
            with open(PAPER_STATE, "r") as f:
                state = json.load(f)
                self.paper_balance = state.get("balance", 10000.0)
                self.positions = state.get("positions", [])
                self.trade_history = state.get("history", [])
    
    def save_state(self):
        state = {
            "balance": self.paper_balance,
            "positions": self.positions,
            "history": self.trade_history,
            "last_update": datetime.now().isoformat(),
        }
        with open(PAPER_STATE, "w") as f:
            json.dump(state, f, indent=2)
    
    def get_token_price(self, symbol):
        """Get token price from DexScreener (our existing data)"""
        try:
            with open("/root/.openclaw/workspace/agents/tmp_state/scanner_output.json", "r") as f:
                scanner = json.load(f)
            for pair in scanner.get("pairs", []):
                if pair.get("symbol") == symbol:
                    return pair.get("price", 0)
        except:
            pass
        return 0
    
    def get_jupiter_quote(self, input_mint, output_mint, amount, slippage_bps=100):
        """Get Jupiter swap quote"""
        try:
            params = {
                "inputMint": input_mint,
                "outputMint": output_mint,
                "amount": str(int(amount * 1e6)),  # USDC has 6 decimals
                "slippageBps": slippage_bps,
            }
            resp = requests.get(JUPITER_QUOTE_API, params=params, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            print(f"  Jupiter quote error: {e}")
        return None
    
    def calculate_position_size(self, symbol, entry_price, stop_price, risk_pct=1.0):
        """Calculate position size based on risk"""
        risk_amount = self.paper_balance * (risk_pct / 100)
        stop_distance = abs(entry_price - stop_price) / entry_price
        if stop_distance == 0:
            return 0
        position_size_usdt = risk_amount / stop_distance
        return min(position_size_usdt, self.paper_balance * 0.1)  # Max 10% per trade
    
    def execute_paper_trade(self, signal):
        """Execute a paper trade"""
        symbol = signal["symbol"]
        
        # CHECK: Already have open position for this symbol?
        existing = [p for p in self.positions if p.get("symbol") == symbol and p.get("status") == "OPEN"]
        if existing:
            print(f"   ⚠️ Already holding {symbol} — skipping duplicate")
            return None
        
        entry_price = signal["entry_zone"]["primary"]
        stop_price = signal["stop_loss"]
        tp1 = signal["take_profits"]["tp1_2x_risk"]
        tp2 = signal["take_profits"]["tp2_3x_risk"]
        tp3 = signal["take_profits"]["tp3_4x_risk"]
        rr = signal["risk_reward_ratio"]
        conf = signal["confidence"]
        
        # CHECK: Max 5 open positions
        if len([p for p in self.positions if p.get("status") == "OPEN"]) >= 5:
            print(f"   ⚠️ Max 5 positions reached — skipping {symbol}")
            return None
        
        # Calculate position size
        position_usdt = self.calculate_position_size(symbol, entry_price, stop_price)
        token_amount = position_usdt / entry_price
        
        # Apply slippage (paper trading simulation)
        actual_entry = entry_price * 1.005  # 0.5% slippage
        
        # Deduct from balance
        self.paper_balance -= position_usdt
        
        position = {
            "id": f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "symbol": symbol,
            "entry_price": actual_entry,
            "stop_price": stop_price,
            "tp1": tp1,
            "tp2": tp2,
            "tp3": tp3,
            "position_usdt": position_usdt,
            "token_amount": token_amount,
            "status": "OPEN",
            "opened_at": datetime.now().isoformat(),
            "current_pnl": 0,
            "highest_pnl": 0,
        }
        
        self.positions.append(position)
        
        trade_record = {
            "id": position["id"],
            "symbol": symbol,
            "type": "OPEN",
            "price": actual_entry,
            "amount": position_usdt,
            "timestamp": datetime.now().isoformat(),
            "mode": "paper",
        }
        self.trade_history.append(trade_record)
        self.save_state()
        
        print(f"\n📝 PAPER TRADE EXECUTED")
        print(f"   Symbol: {symbol}")
        print(f"   Entry: ${actual_entry:.8f} (with 0.5% slippage)")
        print(f"   Position: ${position_usdt:.2f} USDT")
        print(f"   Tokens: {token_amount:.2f}")
        print(f"   Stop: ${stop_price:.8f}")
        print(f"   TP1: ${tp1:.8f} | TP2: ${tp2:.8f} | TP3: ${tp3:.8f}")
        print(f"   Remaining balance: ${self.paper_balance:.2f} USDT")
        
        return position
    
    def check_positions(self):
        """Monitor open positions and check for exits"""
        current_prices = {}
        try:
            with open("/root/.openclaw/workspace/agents/tmp_state/scanner_output.json", "r") as f:
                scanner = json.load(f)
            for pair in scanner.get("pairs", []):
                current_prices[pair["symbol"]] = pair.get("price", 0)
        except:
            pass
        
        for pos in self.positions:
            if pos["status"] != "OPEN":
                continue
            
            symbol = pos["symbol"]
            current_price = current_prices.get(symbol, 0)
            if current_price == 0:
                continue
            
            entry = pos["entry_price"]
            stop = pos["stop_price"]
            tp1 = pos["tp1"]
            tp2 = pos["tp2"]
            tp3 = pos["tp3"]
            
            # Calculate P&L
            pnl_pct = (current_price - entry) / entry * 100
            pnl_usdt = pos["position_usdt"] * (pnl_pct / 100)
            pos["current_pnl"] = pnl_usdt
            pos["highest_pnl"] = max(pos["highest_pnl"], pnl_usdt)
            
            # Check exits
            exit_triggered = False
            exit_price = current_price
            exit_reason = ""
            
            if current_price <= stop:
                exit_triggered = True
                exit_reason = "STOP_LOSS"
                exit_price = stop
            elif current_price >= tp3:
                exit_triggered = True
                exit_reason = "TP3_HIT"
                exit_price = tp3
            elif current_price >= tp2:
                exit_triggered = True
                exit_reason = "TP2_HIT"
                exit_price = tp2
            elif current_price >= tp1:
                exit_triggered = True
                exit_reason = "TP1_HIT"
                exit_price = tp1
            
            if exit_triggered:
                # Close position
                actual_exit = exit_price * 0.995  # 0.5% slippage on exit
                pnl = pos["position_usdt"] * ((actual_exit - entry) / entry)
                
                self.paper_balance += pos["position_usdt"] + pnl
                pos["status"] = "CLOSED"
                pos["exit_price"] = actual_exit
                pos["exit_reason"] = exit_reason
                pos["pnl"] = pnl
                pos["closed_at"] = datetime.now().isoformat()
                
                trade_record = {
                    "id": pos["id"],
                    "symbol": symbol,
                    "type": "CLOSE",
                    "price": actual_exit,
                    "pnl": pnl,
                    "reason": exit_reason,
                    "timestamp": datetime.now().isoformat(),
                    "mode": "paper",
                }
                self.trade_history.append(trade_record)
                self.save_state()
                
                emoji = "🟢" if pnl > 0 else "🔴"
                print(f"\n{emoji} POSITION CLOSED")
                print(f"   Symbol: {symbol}")
                print(f"   Exit: ${actual_exit:.8f}")
                print(f"   Reason: {exit_reason}")
                print(f"   P&L: ${pnl:+.2f} USDT")
                print(f"   Balance: ${self.paper_balance:.2f} USDT")
    
    def get_portfolio_summary(self):
        """Get current portfolio state"""
        open_positions = [p for p in self.positions if p["status"] == "OPEN"]
        total_pnl = sum(p.get("pnl", 0) for p in self.positions if p["status"] == "CLOSED")
        open_pnl = sum(p.get("current_pnl", 0) for p in open_positions)
        
        wins = sum(1 for p in self.positions if p["status"] == "CLOSED" and p.get("pnl", 0) > 0)
        losses = sum(1 for p in self.positions if p["status"] == "CLOSED" and p.get("pnl", 0) < 0)
        total_closed = wins + losses
        win_rate = (wins / total_closed * 100) if total_closed > 0 else 0
        
        return {
            "balance": self.paper_balance,
            "open_positions": len(open_positions),
            "total_pnl": total_pnl,
            "open_pnl": open_pnl,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "total_trades": len(self.trade_history),
        }

def main():
    print("🪐 JUPITER DEX EXECUTOR")
    print("Mode: PAPER TRADING (simulation)")
    print(f"Virtual balance: $10,000 USDT")
    print()
    
    executor = JupiterExecutor(mode="paper")
    
    # Monitor for signals and execute
    while True:
        try:
            # Check for new signals from dynamic risk
            with open("/root/.openclaw/workspace/agents/tmp_state/dynamic_risk_output.json", "r") as f:
                risk = json.load(f)
            
            approved = risk.get("approved", [])
            for opp in approved:
                if opp.get("confidence", 0) >= 60 and opp.get("risk_reward_ratio", 0) >= 2:
                    # Check if we already have a position
                    existing = [p for p in executor.positions if p["symbol"] == opp["symbol"] and p["status"] == "OPEN"]
                    if not existing:
                        print(f"\n🎯 NEW SIGNAL: {opp['symbol']} — Executing paper trade...")
                        executor.execute_paper_trade(opp)
            
            # Check existing positions
            executor.check_positions()
            
            # Print summary every hour
            if datetime.now().minute == 0:
                summary = executor.get_portfolio_summary()
                print(f"\n📊 PORTFOLIO SUMMARY")
                print(f"   Balance: ${summary['balance']:.2f}")
                print(f"   Open positions: {summary['open_positions']}")
                print(f"   Total P&L: ${summary['total_pnl']:+.2f}")
                print(f"   Win rate: {summary['win_rate']:.1f}%")
                print(f"   Trades: {summary['total_trades']}")
            
        except Exception as e:
            print(f"  Error: {e}")
        
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main()
