# 🧬 SETUP DNA CLASSIFICATION SYSTEM

## Purpose
Classify every detected setup into its structural DNA type. This enables the Performance Agent to track which "species" of setups perform best in which regimes.

## DNA Types

### 1. BREAKOUT
**Definition:** Price breaking above resistance with volume confirmation.
**Signature:**
- Price near recent highs
- Volume spike on breakout candle
- Liquidity increasing
- Compression before expansion (triangle/pennant)

**Regime Fit:** Works best in trending markets, post-consolidation.
**Risk:** False breakout, immediate rejection.

---

### 2. REVERSAL
**Definition:** Exhausted trend showing reversal signals.
**Signature:**
- Extreme overextension (>50% in 24h often)
- Volume climax (huge volume spike at extreme)
- Divergence (price higher, momentum lower)
- Long upper wicks / rejection candles

**Regime Fit:** Works in ranging markets, at range extremes.
**Risk:** Catching falling knives, trend continuation.

---

### 3. ACCUMULATION
**Definition:** Quiet buying, low volume, steady price climb.
**Signature:**
- Low but consistent volume
- Higher lows pattern
- Buy pressure > Sell pressure consistently
- Minimal social hype
- Price grinding up slowly

**Regime Fit:** Works in early trend, before breakout.
**Risk:** Dead token, no follow-through.

---

### 4. MOMENTUM CONTINUATION
**Definition:** Trend already established, riding the wave.
**Signature:**
- Strong 24h move (+20% to +80%)
- 1h and 5m still positive
- Volume sustaining (not just spike)
- Pullbacks shallow (<5%)

**Regime Fit:** Works in strong trending markets.
**Risk:** Late entry, immediate reversal.

---

### 5. MEAN REVERSION
**Definition:** Price too far from average, statistical snap-back expected.
**Signature:**
- Price > 2 ATR from 20-period average
- Extreme RSI equivalent (via volume/price velocity)
- Volume declining at extremes
- Quick snap-back on lower timeframes

**Regime Fit:** Works in ranging markets.
**Risk:** Trend continuation, no reversion.

---

### 6. LIQUIDITY SWEEP
**Definition:** Whales engineering stop hunts, then reversing.
**Signature:**
- Quick wick below support, then immediate recovery
- High volume on the wick, then volume drops
- Price reclaims level within hours
- Stop cascade visible in transaction data

**Regime Fit:** Works in manipulated/low-liquidity markets.
**Risk:** Genuine breakdown, no recovery.

---

## Classification Logic

```
if (price > 50% in 24h AND volume_climax AND long_wick)
    → REVERSAL

elif (breaks_resistance AND volume_spike AND consolidation_before)
    → BREAKOUT

elif (low_volume AND steady_climb AND buy_pressure > 1.2x)
    → ACCUMULATION

elif (trending AND pullbacks_shallow AND volume_sustained)
    → MOMENTUM_CONTINUATION

elif (price > 2_ATR_from_avg AND volume_declining)
    → MEAN_REVERSION

elif (wick_below_support AND immediate_reclaim)
    → LIQUIDITY_SWEEP

else
    → UNCLASSIFIED (requires more data)
```

## Output Format
```
DNA CLASSIFICATION: [TYPE]

Structural Evidence:
- [Specific metric supporting classification]
- [Specific metric supporting classification]

Regime Compatibility:
- Current Regime: [TRENDING/RANGING/VOLATILE]
- Fit Score: [0-100]
- Recommended Action: [PROCEED / CAUTION / REJECT]

Historical Performance (from database):
- This DNA type win rate in [REGIME]: [X]%
- Average R:R achieved: [ratio]
```

## Rules
1. **One DNA per setup** — No hybrid classifications
2. **Evidence-based** — Must have at least 3 supporting metrics
3. **Regime-sensitive** — Same DNA behaves differently per regime
4. **Tracked for performance** — Every classification logged
5. **Updated dynamically** — DNA can change as structure evolves
