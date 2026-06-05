#!/usr/bin/env python3
"""Quick scan for hot movers with clean momentum"""
import requests

terms = ['PEPE', 'BONK', 'WIF', 'FLOKI', 'SHIB', 'DOGE', 'TRUMP', 'USA', 'AI', 'GME']
url = 'https://api.dexscreener.com/latest/dex/search'

hot_tokens = []
for term in terms:
    try:
        resp = requests.get(url, params={'q': term}, timeout=10)
        pairs = resp.json().get('pairs', [])
        for p in pairs[:2]:
            pc = p.get('priceChange') or {}
            chg_24h = float(pc.get('h24') or 0)
            chg_1h = float(pc.get('h1') or 0)
            chg_6h = float(pc.get('h6') or 0)
            chg_5m = float(pc.get('m5') or 0)
            vol = float((p.get('volume') or {}).get('h24') or 0)
            liq = float((p.get('liquidity') or {}).get('usd') or 0)
            sym = p['baseToken']['symbol']
            price = p.get('priceUsd') or '0'
            
            # Clean momentum: all positive
            if chg_24h > 3 and chg_1h >= -0.5 and chg_6h >= -1 and vol > 5000 and liq > 20000:
                hot_tokens.append({
                    'sym': sym, 'price': price,
                    'chg_24h': chg_24h, 'chg_1h': chg_1h, 'chg_6h': chg_6h, 'chg_5m': chg_5m,
                    'vol': vol, 'liq': liq
                })
    except Exception as e:
        pass

# Sort by composite score (24h * 0.4 + 1h * 0.3 + 6h * 0.3)
hot_tokens.sort(key=lambda x: x['chg_24h']*0.4 + x['chg_1h']*0.3 + x['chg_6h']*0.3, reverse=True)

print('🔥 HOT MOVERS WITH CLEAN MOMENTUM:')
print('='*60)
for t in hot_tokens[:8]:
    print(f"{t['sym']}: ${t['price']}")
    print(f"  24h: {t['chg_24h']:+.1f}% | 6h: {t['chg_6h']:+.1f}% | 1h: {t['chg_1h']:+.1f}% | 5m: {t['chg_5m']:+.1f}%")
    print(f"  Vol: ${t['vol']:,.0f} | Liq: ${t['liq']:,.0f}")
    print()

if not hot_tokens:
    print('No hot movers found right now with clean momentum')
    print('Market might be choppy or in pullback mode')
