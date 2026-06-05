ΕΛΑ! Τσέκαρα τα πάντα — sessions, logs, processes, API responses. Τα 3 προβλήματα και γιατί συμβαίνουν:

---

### 1. "Έχει κολλήσει" — ΚΟΛΛΗΜΕΝΟ ΣΕ BV7X ΚΑΙ FLOKI

**Τι συμβαίνει:** Ο v4_master στέλνει τα ίδια 2 signals (BV7X, FLOKI) κάθε 15 λεπτά, ξανά και ξανά, και τα auto-confirms. Το confirmed_trades.json γεμίζει με duplicates.

**Root cause:** Ο scanner discovery βρίσκει μόνο ~26-39 unique tokens κάθε scan (boosted + top movers). Τα BV7X και FLOKI παραμένουν στην boosted list συνέχεια. Το dedup στο v4_master είναι μόνο within-run (seen_symbols set) — reset κάθε 15 λεπτά. Οπότε κάθε 15 λεπτά τα βλέπει σαν "νέα" signals. Το auto_mode είναι SEMI_AUTO_AGGRESSIVE — auto-confirms χωρίς "already executed today" check. Το confirmed_trades.json είναι append-only, όχι deduped.

**Αποτέλεσμα:** Στέλνεις infinite BV7X/FLOKI alerts. Το σύστημα νομίζει ότι βρήκε νέα opportunities κάθε 15 λεπτά.

---

### 2. "Δείχνει λάθος τιμές"

**Root cause — 2 sub-issues:**

**A. Stale data pipeline:** Ο v2_scanner γράφει scanner_output.json κάθε 15 λεπτά. Ο v2_dynamic_risk διαβάζει scanner_output.json και γράφει dynamic_risk_output.json. Ο v4_master διαβάζει dynamic_risk_output.json. Αλλά το v4_master δεν παίρνει real-time prices — παίρνει processed data από το pipeline.
- Τιμή BV7X στο dynamic_risk: $4.186e-06 | Τιμή BV7X στο DexScreener API τώρα: $0.000004004
- Τιμή FLOKI στο dynamic_risk: $3.512e-05 | Τιμή FLOKI στο DexScreener API τώρα: $0.00003687
- Το pipeline έχει lag. Οι τιμές είναι από προηγούμενο scan, όχι real-time.

**B. Entry price calculation bug:** Ο risk manager υπολογίζει entry = price * (1 - 0.02) = 2% discount από current. Αυτό έχει νόημα για accumulation, αλλά για tokens που είναι ήδη +50%+, το "entry" είναι ακόμα πάνω από το real support. Το stop loss είναι ATR-based αλλά με min 5%, οπότε σε volatile microcaps το stop είναι πολύ κοντά.

---

### 3. "Δεν δείχνει όλα τα νομίσματα"

**Τι συμβαίνει:** Ο scanner βρίσκει μόνο 9-14 candidates κάθε scan, ενώ το DexScreener έχει εκατοντάδες trending tokens.

**Root cause:** Το discovery χρησιμοποιεί μόνο 2 sources: (1) /token-boosts/latest/v1 — μόνο paid/boosted tokens (~26-27 κάθε φορά), (2) /latest/dex/search?q=solana — μόνο 30 top pairs (αλλά τα περισσότερα είναι SOL pairs, όχι altcoins). Το search "solana" επιστρέφει κυρίως SOL/USDC, SOL/WETH, SOL/BTC pairs — δεν είναι αυτό που νομίζεις. Χάνεις new pairs, trending by volume, tokens σε άλλα chains (Base, BSC, Arbitrum), και τα περισσότερα altcoins. Το DexScreener έχει endpoints όπως /token-profiles/latest/v1 για όλα τα trending profiles, αλλά δεν τα χρησιμοποιούμε.

**Αποτέλεσμα:** Βλέπεις μόνο boosted tokens + top SOL pairs. Χάνεις το 90% της αγοράς.

---

## ΤΙ ΠΡΕΠΕΙ ΝΑ ΦΤΙΑΞΟΥΜΕ

1. Fix dedup — Add cross-run signal tracking (στο confirmed_trades.json με dedup by symbol+date)
2. Fix discovery — Χρησιμοποίησε /token-profiles/latest/v1 + /latest/dex/tokens/ για όλα τα chains
3. Fix price freshness — Add real-time price validation πριν στείλεις signal (fetch fresh price στο v4_master)
4. Fix entry logic — Το 2% discount δεν έχει νόημα για breakout tokens. Χρήσιμο για accumulation μόνο.

Θέλεις να ξεκινήσω τα fixes; Πες μου ποιο πρώτο.
