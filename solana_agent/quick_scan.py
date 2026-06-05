#!/usr/bin/env python3
import requests, json

print("🔥 SOLANA MARKET SCAN — " + __import__('datetime').datetime.now().strftime('%H:%M') + "\n")

# Get boosted tokens
r = requests.get('https://api.dexscreener.com/token-boosts/top/v1', timeout=15)
boosted = r.json() if r.status_code == 200 else []

# Get latest profiles
r2 = requests.get('https://api.dexscreener.com/token-profiles/latest/v1', timeout=15)
profiles = r2.json() if r2.status_code == 200 else []

print(f"📡 Boosted tokens: {len(boosted)} | Latest profiles: {len(profiles)}\n")

# Get pair data for top boosted
for b in boosted[:5]:
    addr = b.get('tokenAddress', '')
    if not addr:
        continue
    
    # Get pair data
    pr = requests.get(f'https://api.dexscreener.com/latest/dex/tokens/{addr}', timeout=10)
    if pr.status_code != 200:
        continue
    
    pdata = pr.json()
    pairs = pdata.get('pairs', [])
    if not pairs:
        continue
    
    p = pairs[0]  # Best pair
    symbol = p['baseToken']['symbol']
    liq = p.get('liquidity', {}).get('usd', 0)
    vol = p.get('volume', {}).get('h24', 0)
    ch24 = p.get('priceChange', {}).get('h24', 0) or 0
    ch1h = p.get('priceChange', {}).get('h1', 0) or 0
    ch5m = p.get('priceChange', {}).get('m5', 0) or 0
    mc = p.get('marketCap', 0) or p.get('fdv', 0) or 0
    buys = p.get('txns', {}).get('h24', {}).get('buys', 0) or 0
    sells = p.get('txns', {}).get('h24', {}).get('sells', 0) or 0
    
    ratio = buys / max(sells, 1)
    
    print(f"💎 {symbol} | Boosted! 🔥")
    print(f"   MC: ${mc:,.0f} | Liq: ${liq:,.0f} | Vol: ${vol:,.0f}")
    print(f"   24h: {ch24:+.1f}% | 1h: {ch1h:+.1f}% | 5m: {ch5m:+.1f}%")
    print(f"   Buy/Sell: {ratio:.1f}x | Buys: {buys} | Sells: {sells}")
    print(f"   📊 https://dexscreener.com/solana/{addr}")
    print()

# Look for momentum plays in profiles
print("⚡ MOMENTUM PLAYS:\n")
for prof in profiles[:5]:
    addr = prof.get('tokenAddress', '')
    if not addr:
        continue
    
    pr = requests.get(f'https://api.dexscreener.com/latest/dex/tokens/{addr}', timeout=10)
    if pr.status_code != 200:
        continue
    
    pdata = pr.json()
    pairs = pdata.get('pairs', [])
    if not pairs:
        continue
    
    p = pairs[0]
    symbol = p['baseToken']['symbol']
    liq = p.get('liquidity', {}).get('usd', 0)
    vol = p.get('volume', {}).get('h24', 0)
    ch24 = p.get('priceChange', {}).get('h24', 0) or 0
    ch1h = p.get('priceChange', {}).get('h1', 0) or 0
    ch5m = p.get('priceChange', {}).get('m5', 0) or 0
    mc = p.get('marketCap', 0) or p.get('fdv', 0) or 0
    
    if ch24 > 10 and liq > 3000:
        print(f"🚀 {symbol}")
        print(f"   MC: ${mc:,.0f} | Liq: ${liq:,.0f} | Vol: ${vol:,.0f}")
        print(f"   24h: {ch24:+.1f}% | 1h: {ch1h:+.1f}% | 5m: {ch5m:+.1f}%")
        print(f"   📊 https://dexscreener.com/solana/{addr}")
        print()

print("🏁 Scan complete!")
