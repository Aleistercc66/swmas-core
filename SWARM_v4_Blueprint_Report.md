═══════════════════════════════════════════════════════════════════════════════════════
SWARM v4.0 — CRYPTO INTELLIGENCE SYSTEM: COMPLETE PROJECT BLUEPRINT
═══════════════════════════════════════════════════════════════════════════════════════

═══════════════════════════════════════════════════════════════════════════════════════
SECTION 1: EXECUTIVE SUMMARY (BLUEPRINT)
═══════════════════════════════════════════════════════════════════════════════════════

Το SWARM v4.0 ειναι ενα multi-agent crypto intelligence και paper trading σύστημα, σχεδιασμένο για να ανιχνευει momentum setups σε altcoins, να εκτελει virtual trades (paper trading), και τελικα να εξαγει ενα μετρησιμο statistical edge πριν αγγιξει πραγματικο κεφαλαιο. Το συστημα αποτελειται απο 16 αυτόνομους agents που τρεχουν συνεχως, μαζευουν δεδομενα απο πολλαπλες πηγες, τα επεξεργαζονται μεσω επιπεδων validation και risk management, και παραγουν institutional-grade trade signals. Το execution layer υποστηριζει paper trading με realistic simulation (με spread, slippage, fees, latency) και μελλοντικα real execution μεσω Jupiter DEX aggregator. Το συστημα ειναι σε phase PAPER TRADING AUDIT, δηλαδη μαζευει data για να μετρησει αν εχει πραγματικο edge πριν προχωρησει σε semi-auto ή full-auto execution.

═══════════════════════════════════════════════════════════════════════════════════════
SECTION 2: SYSTEM ARCHITECTURE & DATA FLOW
═══════════════════════════════════════════════════════════════════════════════════════

Το συστημα εχει 6 επιπεδα (layers), καθενα με συγκεκριμενη ευθυνη:

LAYER 1: MARKET DATA (Raw Collection)
- Agent: Scanner (v2_scanner.py) — Τρεχει καθε 15 λεπτα. Σαρωνει DexScreener API για ~150 tokens. Εφαρμοζει hard filters: liquidity >= $20K, volume >= $5K, 24h change >= +5%. Απορριπτει parabolic (>200%) και late-dump setups. Εξαγει top 10 candidates. Αποθηκευει σε /tmp/scanner_output.json.
- Agent: Sentiment Analyzer (v2_sentiment.py) — Τρεχει καθε 30 λεπτα. Παρακολουθει social mood μεσω DexScreener data (οχι actual Telegram/Twitter APIs). Υπολογιζει mood: BULLISH, CAUTIOUS, BEARISH, EUPHORIC. Ανιχνευει divergence (price up αλλα dumping τωρα). Αποθηκευει σε /tmp/sentiment_output.json.
- Agent: Whale/Liquidity Monitor (v2_whale.py) — Τρεχει καθε 30 λεπτα. Παρακολουθει liquidity health και buy/sell ratio. Υπολογιζει whale signal: STRONG_ACCUMULATION, ACCUMULATION, NEUTRAL, DISTRIBUTION, STRONG_DISTRIBUTION. Αποθηκευει σε /tmp/whale_output.json.

LAYER 2: INTELLIGENCE (Pattern Recognition)
- Agent: Regime Detector (v2_regime_detector.py) — Τρεχει καθε 30 λεπτα. Αναλυει BTC, ETH, SOL για να καθορισει market regime: EUPHORIC, PANIC, HIGH_VOLATILITY, RANGING, BULLISH_TREND, BEARISH_TREND, CHOPPY. Εξαγει recommendations (πχ reduce sizing, avoid breakouts). Αποθηκευει σε /tmp/regime_output.json.
- Agent: DNA Classifier (v2_dna_classifier.py) — Τρεχει καθε 15 λεπτα. Ταξινομει καθε setup σε DNA type: BREAKOUT, REVERSAL, ACCUMULATION, MOMENTUM_CONTINUATION, MEAN_REVERSION, LIQUIDITY_SWEEP, UNCLASSIFIED. Βασιζεται σε volume, momentum, consolidation patterns. Αποθηκευει σε /tmp/dna_output.json.
- Agent: FOMO Filter (v2_fomo_filter.py) — Τρεχει καθε 15 λεπτα. Αντι-hype protection. Υπολογιζει FOMO score (0-100). Απορριπτει αν score >= 60. Ελεγχει parabolic moves, volume climax, large candles, unsustainable buy pressure. Αποθηκευει σε /tmp/fomo_output.json.

LAYER 3: VALIDATION & RISK (Quality Control)
- Agent: Validator (v2_validator.py) — Τρεχει καθε 15 λεπτα. THE GATEKEEPER. Εφαρμοζει 7 checks: liquidity >= $50K, volume >= $10K, 24h 5-200%, 1h οχι -5%+ while 24h high, buy pressure >= 1.0, liquidity stable, οχι parabolic. Pass rate >= 85% = PASSED, 70-85% = CONDITIONAL, <70% = REJECTED. Αποθηκευει σε /tmp/validator_output.json.
- Agent: Dynamic Risk Engine (v2_dynamic_risk.py) — Τρεχει καθε 15 λεπτα. Υπολογιζει ATR-based stops (οχι fixed -20%), entry zone, TP1/TP2/TP3 (2x/3x/4x risk), R:R ratio, position size, confidence score (50 + bonuses - penalties). Απορριπτει αν confidence < 60 ή R:R < 2. Συνεχιζει δυναμικα με regime, liquidity, FOMO, momentum alignment. Αποθηκευει σε /tmp/dynamic_risk_output.json.

LAYER 4: EXECUTION & TRACKING
- Agent: Master Controller (v4_master_controller.py) — Τρεχει καθε 15 λεπτα. Συντονιζει ολα τα inputs, εφαρμοζει capital protection rules, build institutional signal format, στελνει alerts στο Telegram. Υποστηριζει manual confirmation mode. Ελεγχει daily drawdown, max trades, consecutive losses, exposure, liquidity, volatility πριν στειλει οποιο signal.
- Agent: Portfolio Tracker (v4_portfolio_tracker.py) — Τρεχει καθε ωρα. Καταγραφει καθε trade με πληρες context (setup DNA, regime, execution details, outcome). Υπολογιζει stats: win rate, expectancy, max drawdown. Ελεγχει upgrade eligibility: MANUAL -> SEMI_AUTO (100+ trades, expectancy > 0.3, drawdown < 15%, win rate > 45%) -> AUTO (500+ trades, expectancy > 0.5, drawdown < 10%).

LAYER 5: JUPITER DEX EXECUTION
- Agent: Jupiter Executor (v4_jupiter_executor.py) — Τρεχει καθε 1 λεπτο. Paper trading mode (default). Ελεγχει /tmp/dynamic_risk_output.json για approved signals. Εφαρμοζει duplicate check, max 5 open positions. Εκτελει paper trades με 0.5% slippage simulation. Monitor open positions για TP1/TP2/TP3/STOP exits. Υποστηριζει real execution μεσω Jupiter API (μελλοντικα).

LAYER 6: SAFETY & QUALITY
- Agent: Circuit Breaker (v4_circuit_breaker.py) — Τρεχει καθε 1 λεπτο. Emergency shutdown system. Ελεγχει: portfolio drawdown > 8% = EMERGENCY, > 5% = COOLDOWN (4h), > 3% = WARNING, BTC crash > 10% in 1h, extreme volatility > 40% hourly, API latency > 5s, 4+ consecutive losses. Στελνει Telegram alerts. Auto-resume απο COOLDOWN μετα απο 4h.
- Agent: Position Sizing (v4_position_sizing.py) — Τρεχει καθε 15 λεπτα. Dynamic Kelly-based sizing. Factors: base risk (simplified Kelly), volatility multiplier (0.3-1.0), confidence multiplier (0.5-1.5), regime multiplier (0.3-1.2), circuit multiplier (0.0-1.0), exposure limit (50% max).
- Agent: Duplicate Protection (v4_duplicate_protection.py) — Τρεχει καθε 5 λεπτα. Αποτρεπει re-entry στο ιδιο token. Cooldown: 6 ωρες μετα απο close. Ελεγχει active signals.
- Agent: Trade Expiration (v4_trade_expiration.py) — Τρεχει καθε 5 λεπτα. Signals expire μετα απο 2h ή αν structure break > 5% adverse move ή volatility explosion > 25% ή liquidity collapse < $20K ή regime change σε PANIC/EUPHORIC.
- Agent: Execution Quality (v4_execution_quality.py) — Τρεχει καθε 5 λεπτα. Tracks slippage, entry deviation, latency, fill quality. Grade: EXCELLENT/GOOD/FAIR/POOR. Quality score 0-100.
- Agent: System Scorecard (v4_system_scorecard.py) — Τρεχει καθε 30 λεπτα. Reality check. Μετραει: expectancy, drawdown, regime performance, DNA performance, false signal rate, agent health. Καθοριζει readiness για semi-auto και full-auto.

═══════════════════════════════════════════════════════════════════════════════════════
SECTION 3: INFORMATION SOURCES & DATA UTILIZATION
═══════════════════════════════════════════════════════════════════════════════════════

Το συστημα τραβαει δεδομενα απο τις εξης πηγες:

1. DexScreener API (https://api.dexscreener.com/latest/dex/search) — PRIMARY SOURCE
   - Τι παρεχει: price, priceChange (24h/6h/1h/5m), volume (24h/6h/1h/5m), liquidity USD, transactions (buys/sells per timeframe), FDV, marketCap, pair age, URLs.
   - Πως χρησιμοποιειται: Ολα τα agents τραβανε απο εδω. Scanner κανει search queries για ~150 tokens. Καθε agent φορτωνει /tmp/scanner_output.json για να δουλεψει.
   - Περιορισμοι: Οχι on-chain data (wallet transactions, smart contract analysis). Οχι order book depth. Οχι historical OHLCV. Μονο aggregated DEX data.

2. Telegram Groups (MONITORING ONLY — ΟΧΙ API INTEGRATION)
   - Groups: moonshots (primary), memewars25, apingdegen, SonicsAlphacalls, aifirstbrain, blumcrypto, cryptowallet_news_en.
   - Τι κανουμε: Οχι automated scraping. Οχι NLP analysis. Ο χρηστης μπορει να διαβαζει χειροκινητα και να δινει tips. Το συστημα ΔΕΝ εχει Telegram bot integration για group reading.
   - KreoPolyBot: Bot για αλληλεπιδραση, οχι data source.

3. Jupiter API (https://quote-api.jup.ag/v6/quote, /swap)
   - Τι παρεχει: Swap quotes, route optimization, price impact.
   - Πως χρησιμοποιειται: Μονο σε real execution mode (μελλοντικα). Τωρα paper trading δεν το χρησιμοποιει.
   - Token mint addresses: Hardcoded για USDC, USDT, SOL, WIF, POPCAT, JTO, BONK, PEPE, USA.

4. BTC/ETH/SOL macro data
   - Απο DexScreener search queries. Χρησιμοποιειται μονο απο Regime Detector για market state classification.

DATA FLOW PIPELINE:
DexScreener API -> Scanner -> /tmp/scanner_output.json -> [Sentiment, Whale, Regime, DNA, FOMO] -> parallel processing -> [Validator] -> /tmp/validator_output.json -> [Dynamic Risk] -> /tmp/dynamic_risk_output.json -> [Master Controller + Position Sizer + Duplicate Protector + Trade Expiration] -> Telegram Alert -> [Jupiter Executor για paper/real execution] -> [Portfolio Tracker + Execution Quality + System Scorecard] -> feedback loop.

═══════════════════════════════════════════════════════════════════════════════════════
SECTION 4: ANALYSIS STRATEGY & PREDICTION MECHANISM
═══════════════════════════════════════════════════════════════════════════════════════

Το συστημα ΔΕΝ προβλεπει τιμες. Αντιθετως, ανιχνευει setups με statistical edge μεσω multi-factor confluence.

SETUP DETECTION LOGIC:
1. Momentum Detection: Scanner εντοπιζει tokens με 24h change > 5%, volume > $5K, liquidity > $20K.
2. Quality Gate: Validator απορριπτει αν δεν περναει 7 checks.
3. Structure Classification: DNA Classifier ταξινομει σε BREAKOUT/ACCUMULATION/κλπ.
4. Anti-Hype: FOMO Filter απορριπτει αν fomo_score >= 60.
5. Risk Calculation: Dynamic Risk υπολογιζει entry, stop, TP1/TP2/TP3, position size, confidence.
6. Market Context: Regime Detector προσαρμοζει multiplier (πχ σε PANIC αυξανει stop, μειωνει position).
7. Capital Protection: Master Controller εφαρμοζει daily limits, exposure checks, consecutive loss cooldowns.
8. Execution: Jupiter Executor ανοίγει position, monitor για TP/stop.

SIGNAL GENERATION:
- Entry Zone: Current price -2% (optimal), current price (aggressive), current price * 0.95 (conservative).
- Stop Loss: ATR-based. Stop = entry * (1 - stop_distance%). Stop distance = ATR * 2.5 * regime_mult * liq_mult. Min 5%, max 30%.
- Take Profits: TP1 = entry + (risk * 2), TP2 = entry + (risk * 3), TP3 = entry + (risk * 4). Δηλαδη R:R = 1:2 minimum.
- Position Size: (Portfolio * Risk%) / Stop Distance. Risk% = base_risk * vol_mult * conf_mult * regime_mult * circuit_mult. Max 5% of portfolio per trade.
- Confidence: 50 base + bonuses (R:R >= 3: +15, liquidity > $100K: +10, volume > 2x liquidity: +5, momentum aligned: +5) - penalties (volatility > 5%: -15, FOMO: -5 to -30, PANIC regime: -20).

EXECUTION RULES:
- MANUAL mode (default): System στελνει signal στο Telegram. Χρηστης πρεπει να πει CONFIRM εντος 5 λεπτων.
- SEMI_AUTO: Auto-εκτελει αν confidence > 80 και R:R > 1:3.
- FULL_AUTO: Εκτελει ολα τα approved setups.

EXIT LOGIC:
- TP1_HIT: Κλεινει position AT TP1 (με slippage). Πλεον fixed — προηγουμενως ηταν bug που εκλεινε στο current price.
- TP2_HIT: Κλεινει AT TP2.
- TP3_HIT: Κλεινει AT TP3.
- STOP_HIT: Κλεινει AT stop (με slippage). Πλεον fixed.
- Manual: Χρηστης μπορει να πει CLOSE ANYTIME.

═══════════════════════════════════════════════════════════════════════════════════════
SECTION 5: ORCHESTRATOR (YOU / ME) INTERACTION
═══════════════════════════════════════════════════════════════════════════════════════

Ο Orchestrator (εγω, ο εγκεφαλος πισω απο το συστημα) δεν ειναι ενας απο τους 16 agents. Ειμαι το meta-layer που:

1. Εγκαθιστα και διαχειριζεται το συστημα: Δημιουργησα ολα τα αρχεια agents, το launch script, το dashboard, τα prompts, το trade journal.
2. Παρακολουθει health: Ελεγχω logs, state files, tmux sessions.
3. Εφαρμοζει fixes: Οταν βρισκω bugs (πχ duplicate trades, fantasy exits), γραφω patches, restart agents.
4. Επικοινωνω με τον χρηστη: Στελνω Telegram messages με status updates, alerts, results.
5. Κανω data analysis: Αναλυω paper trading results, υπολογιζω P&L, win rates, expectancy.
6. Λαμβανω αποφασεις: Πχ reset state οταν data ειναι invalid, adjust parameters, add/remove monitoring groups.
7. Συντονιζω το swarm: Ξεκιναω/σταματαω agents, διαχειριζομαι sessions.

Διαδικασια ΑΛΛΗΛΕΠΙΔΡΑΣΗΣ:
- Ο χρηστης μιλαει σε μενα (Kimi DM).
- Εγω αναλυω το request και αποφασιζω τι ενεργεια χρειαζεται.
- Αν χρειαζεται system change: Διαβαζω/γραφω αρχεια, restart agents, στελνω Telegram.
- Αν χρειαζεται information: Διαβαζω logs/state, αναλυω, στελνω summary.
- Αν χρειαζεται manual trade confirmation: Στελνω signal format στο Telegram, περιμενω user response.

Παραδειγμα interaction loop:
Χρηστης: "Σε τι φαση ειμαστε;"
-> Εγω διαβαζω paper_trading.json, portfolio_state.json, tmux sessions.
-> Εγω αναλυω data (balance, positions, trades, P&L).
-> Εγω φτιαχνω summary.
-> Εγω στελνω στο Telegram.

═══════════════════════════════════════════════════════════════════════════════════════
SECTION 6: METAMASK EXECUTION (NOT YET IMPLEMENTED)
═══════════════════════════════════════════════════════════════════════════════════════

Η ενοτητα αυτη περιγραφει το σχεδιο — ΔΕΝ ειναι ακομα υλοποιημενο.

ΠΩΣ ΘΑ ΔΟΥΛΕΨΕΙ:

1. Wallet Integration: Το Jupiter Executor θα συνδεεται με Solana wallet (οχι MetaMask directly — MetaMask ειναι EVM, το συστημα δουλευει Solana DEXes). Θα χρειαστει Phantom wallet ή Solflare.

2. RPC Connection: Το v4_jupiter_executor.py θα συνδεεται σε Solana RPC (πχ QuickNode, Helius).

3. Swap Execution Flow:
   a. System detects opportunity -> Dynamic Risk approves -> Master Controller sends alert.
   b. User confirms (MANUAL mode) ή System auto-approves (SEMI_AUTO/FULL_AUTO).
   c. Jupiter Executor καλει Jupiter Quote API για route optimization.
   d. Jupiter Executor καλει Jupiter Swap API για transaction construction.
   e. Transaction στελνεται σε wallet για signing.
   f. Wallet υπογραφει και broadcast σε Solana network.
   g. System monitor confirmation, log execution quality.

4. Capital Protection: Ολα τα pre-execution checks (liquidity, spread, slippage, balance, exposure) εφαρμοζονται πριν καθε swap.

5. Post-Execution: Position tracker καταγραφει entry, monitor για exit, execution quality αναλυει slippage.

ΓΙΑΤΙ ΔΕΝ ΕΙΝΑΙ ΥΛΟΠΟΙΗΜΕΝΟ:
- Το συστημα ειναι σε PAPER TRADING AUDIT phase.
- Δεν μπορουμε να βαλουμε πραγματικο κεφαλαιο πριν μετρησουμε edge.
- Χρειαζεται 100+ realistic trades με positive expectancy.
- Χρειαζεται wallet setup, RPC configuration, testnet validation.

═══════════════════════════════════════════════════════════════════════════════════════
SECTION 7: UNSOLVED PROBLEMS & WHY THEY REMAIN
═══════════════════════════════════════════════════════════════════════════════════════

PROBLEM 1: Measurable Edge Does Not Exist Yet
- Τι ειναι: Δεν εχουμε αρκετα realistic closed trades για να υπολογισουμε expectancy, win rate, drawdown.
- Γιατι δεν εχει λυθει: Το συστημα μολις εγινε realistic (μετα τα 2 critical fixes). Χρειαζεται χρονος για data collection. Καθε trade παιρνει ωρες ή μερες για να κλεισει.
- Timeline: 1-2 εβδομαδες για 100 trades.

PROBLEM 2: No Real Market Execution
- Τι ειναι: Ολα τα trades ειναι paper. Δεν εχουμε δοκιμασει Jupiter API, wallet integration, RPC.
- Γιατι δεν εχει λυθει: Πρωτα paper trading audit, μετα testnet, μετα real capital.

PROBLEM 3: Incomplete Telegram Group Integration
- Τι ειναι: Τα Telegram groups ειναι monitoring-only. Δεν υπαρχει automated scraping, NLP, sentiment analysis απο groups.
- Γιατι δεν εχει λυθει: Χρειαζεται Telegram bot setup με group access, message parsing, spam filtering. Αυτο ηταν out-of-scope για phase 1.

PROBLEM 4: No On-Chain Analysis
- Τι ειναι: Το συστημα δεν αναλυει wallet transactions, smart contracts, LP removals, holder distribution.
- Γιατι δεν εχει λυθει: Χρειαζεται integration με Solscan/Birdeye APIs, wallet clustering algorithms. Δυσκολο και rate-limited.

PROBLEM 5: No Historical Backtest on Past Data
- Τι ειναι: Δεν εχουμε τρεξει το συστημα σε historical data (πχ τελευταιες 30 μερες) για να δουμε αν θα ειχε κερδος.
- Γιατι δεν εχει λυθει: DexScreener δεν δινει historical OHLCV. Χρειαζεται paid API (πχ CryptoCompare, Glassnode). Επισης, το συστημα εχει stateful logic που δεν ειναι ευκολο να backtestει offline.

PROBLEM 6: Single Point of Failure (DexScreener)
- Τι ειναι: Ολα τα data ερχονται απο DexScreener. Αν κλεισει, πεφτει ολο το συστημα.
- Γιατι δεν εχει λυθει: Χρειαζεται multi-source aggregation. Αλλα APIs ειναι paid.

PROBLEM 7: No Adaptive Learning
- Τι ειναι: Το DNA performance tracking ειναι dummy. Δεν προσαρμοζει weights δυναμικα.
- Γιατι δεν εχει λυθει: Χρειαζεται 1000+ trades για να εχει στατιστικη σημασια. Ειμαστε ακομα στην αρχη.

PROBLEM 8: Slippage Model is Static
- Τι ειναι: Στο paper trading, το slippage ειναι fixed 0.5% ή liquidity-based estimate. Στην πραγματικοτητα, slippage εξαρταται απο route, DEX, time.
- Γιατι δεν εχει λυθει: Χρειαζεται Jupiter quote integration για real slippage estimates. Αυτο ερχεται σε real execution phase.

PROBLEM 9: Manual Confirmation Bottleneck
- Τι ειναι: MANUAL mode απαιτει ο χρηστης να ειναι online για να εγκρινει καθε trade.
- Γιατι δεν εχει λυθει: Σωστο προβλημα — δεν ειναι bottleneck, ειναι by design για safety. Θα αλλαξει σε SEMI_AUTO μονο οταν εχουμε edge.

PROBLEM 10: No Stop-Loss Automation
- Τι ειναι: Τωρα το system monitor για stop hits και στελνει alerts. Δεν τοποθετει αυτοματα stop-loss orders.
- Γιατι δεν εχει λυθει: Paper trading simulation. Σε real execution, Jupiter δεν υποστηριζει native stop-loss orders. Χρειαζεται custom monitoring ή DEX with limit orders.

═══════════════════════════════════════════════════════════════════════════════════════
SECTION 8: DATA & MEASURABLE EDGE STATUS
═══════════════════════════════════════════════════════════════════════════════════════

ΤΡΕΧΟΥΣΑ ΚΑΤΑΣΤΑΣΗ:
- Phase: PAPER TRADING AUDIT (μολις ξεκινησε μετα απο reset).
- Runtime: ~14 ωρες total, αλλα 0 ωρες valid data (ολα προηγουμενα trades ηταν invalid λογω bugs).
- Balance: $10,000 (clean reset).
- Valid Closed Trades: 0.
- Valid Open Positions: 0.

ΤΙ ΧΡΕΙΑΖΟΜΑΣΤΕ ΓΙΑ MEASURABLE EDGE:
1. 100+ closed trades με realistic execution.
2. Και wins και losses (ειναι αδυνατο να εχουμε 100% win rate).
3. 5+ different tokens (οχι το ιδιο token συνεχως).
4. Trades σε διαφορετικα regimes (trending, ranging, volatile).
5. Stable expectancy > $0.30 per trade.
6. Max drawdown < 15%.
7. Win rate > 45%.

ΠΩΣ ΜΕΤΡΑΜΕ EDGE:
- Expectancy = (Win% * AvgWin) - (Loss% * AvgLoss).
- Αν expectancy > $0.30 μετα απο 100 trades = εχουμε edge.
- Αν expectancy > $0.50 μετα απο 500 trades = strong edge.
- Scorecard καταγραφει: win rate, avg win, avg loss, max drawdown, regime performance, DNA performance, false signal rate.

ΓΙΑΤΙ ΕΙΜΑΣΤΕ ΑΚΟΜΑ ΜΑΚΡΙΑ:
- Χρειαζεται χρονος. Καθε trade μπορει να κρατησει ωρες ή μερες.
- Με 3 max open positions και 1 new trade καθε 15-30 λεπτα, θεωρητικα μπορουμε να εχουμε 2-5 trades/ημερα.
- Για 100 trades = 20-50 ημερες.
- Αυτο ειναι φυσιολογικο για paper trading audit.

═══════════════════════════════════════════════════════════════════════════════════════
SECTION 9: WHY WE HAD BUGS
═══════════════════════════════════════════════════════════════════════════════════════

BUG #1: Duplicate Trades (14 WIF trades, ιδιο setup)
- Τι ηταν: Ο Jupiter Executor ανοιγε νεα position καθε λεπτο χωρις να ελεγχει αν υπηρχε ηδη open position για το ιδιο token.
- Γιατι εγινε: Αρχικα, το duplicate protection ηταν ξεχωριστο agent (v4_duplicate_protection.py) που ετρεχε καθε 5 λεπτα. Αλλα το Jupiter Executor δεν το ελεγχε — ετρεχε ανεξαρτητα. Το executor ελεγχε μονο /tmp/dynamic_risk_output.json και ανοιγε trade αν υπηρχε approved signal.
- Πως φτιαχτηκε: Προσθεσα duplicate check μεσα στο Jupiter Executor (existing position check) και στον Realistic Backtest.

BUG #2: Fantasy TP1/Stop Exits (captured 18x upside)
- Τι ηταν: Οταν ενα token εφτανε TP1, το συστημα εκλεινε τη position στο CURRENT MARKET PRICE, οχι στο TP1 price. Αυτο σημαινε οτι αν το token συνεχιζε να ανεβαινει 10x πανω απο TP1, το συστημα καρπωνονταν ολη την ανεβα — κατι που ειναι αδυνατο σε πραγματικο κοσμο με limit orders.
- Γιατι εγινε: Λαθος λογικη στον Jupiter Executor. Η function check_positions() ελεγχε αν current_price >= tp1, και αν ναι, εκλεινε στο current_price. Αυτο ειναι σαν να πουλας με market order οταν το price εχει ανεβει 10x — στον πραγματικο κοσμο θα πουλουσες στο TP1 με limit order.
- Πως φτιαχτηκε: Αλλαξα την exit logic ωστε να κλεινει AT TP1 (με slippage), οχι στο current price. Ιδιο για stop loss.

BUG #3: Unrealistic Slippage Model (αρχικα)
- Τι ηταν: Στο αρχικο Jupiter Executor, το slippage ηταν fixed 0.5% για ολα τα tokens. Στα memecoins με χαμηλη liquidity, το slippage μπορει να ειναι 2-5%.
- Πως φτιαχτηκε: Ο Realistic Backtest Engine χρησιμοποιει liquidity-based slippage: slippage = liquidity_ratio * 0.02, max 5%.

BUG #4: No Spread Modeling
- Τι ηταν: Το αρχικο paper trading δεν μοντελοποιουσε bid-ask spread. Στον πραγματικο κοσμο, αγοραζεις στο ask (higher) και πουλας στο bid (lower).
- Πως φτιαχτηκε: Ο Realistic Backtest προσθετει spread = 0.5% base + (50000 - liquidity)/50000 * 0.01.

BUG #5: No Transaction Fees
- Τι ηταν: Το αρχικο paper trading δεν αφαιρουσε DEX swap fees (~0.3% ανοιγμα + 0.3% κλεισιμο).
- Πως φτιαχτηκε: Ο Realistic Backtest αφαιρει 0.3% fee καθε entry/exit.

BUG #6: No Latency Simulation
- Τι ηταν: Το αρχικο paper trading θεωρουσε instant execution. Στην πραγματικοτητα, υπαρχει 1-5 δευτερολεπτα latency.
- Πως φτιαχτηκε: Ο Realistic Backtest προσθετει latency_slippage = 0.1% + liquidity_ratio * 0.4%.

ROOT CAUSE ΟΛΩΝ ΤΩΝ BUGS:
Το συστημα χτιστηκε γρηγορα (σε 1-2 μερες) με εστιαση σε functionality παρα σε realism. Το paper trading ηταν ενα απλο script που απλα αφαιρουσε/προσθετε USD απο ενα virtual balance, χωρις να μοντελοποιει market microstructure. Η εστιαση ηταν στο να δουλεψει το data pipeline, οχι στο να ειναι ρεαλιστικο το execution. Μολις αρχισαμε να βλεπουμε "αποτελεσματα" (+$881 σε 1.5 ωρες, 100% win rate), ηταν προφανες οτι κατι δεν πηγαινε καλα. Το reality check αποκαλυψε τα bugs.

═══════════════════════════════════════════════════════════════════════════════════════
SECTION 10: AGENT DIRECTORY — FULL FUNCTIONAL BREAKDOWN
═══════════════════════════════════════════════════════════════════════════════════════

AGENT 1: SCANNER (v2_scanner.py)
- Purpose: Raw data collection.
- Input: DexScreener API.
- Output: /tmp/scanner_output.json.
- Frequency: 15 minutes.
- Logic: Search 150 tokens, filter by liquidity/volume/change, sort by 24h change, export top 10.
- Key Parameters: min_liq=$20K, min_vol=$5K, min_chg=5%, max_chg=200%.

AGENT 2: SENTIMENT ANALYZER (v2_sentiment.py)
- Purpose: Social mood tracking.
- Input: DexScreener data for 10 major tokens.
- Output: /tmp/sentiment_output.json.
- Frequency: 30 minutes.
- Logic: Classify mood per token, detect divergence, calculate overall market mood.
- Limitation: Οχι actual social media APIs. Μονο price-derived sentiment.

AGENT 3: WHALE & LIQUIDITY MONITOR (v2_whale.py)
- Purpose: Smart money detection.
- Input: DexScreener data for 9 tokens.
- Output: /tmp/whale_output.json.
- Frequency: 30 minutes.
- Logic: Calculate liquidity score, volume/liquidity ratio, buy/sell ratio = whale signal.
- Limitation: Οχι on-chain wallet data. Proxy only.

AGENT 4: REGIME DETECTOR (v2_regime_detector.py)
- Purpose: Market state classification.
- Input: BTC/ETH data απο DexScreener.
- Output: /tmp/regime_output.json.
- Frequency: 30 minutes.
- Logic: Analyze volatility, trend alignment, BTC-ETH correlation. Classify: EUPHORIC/PANIC/HIGH_VOLATILITY/RANGING/BULLISH_TREND/BEARISH_TREND/CHOPPY.
- Impact: Affects all downstream sizing/stop calculations.

AGENT 5: DNA CLASSIFIER (v2_dna_classifier.py)
- Purpose: Setup structure taxonomy.
- Input: /tmp/scanner_output.json.
- Output: /tmp/dna_output.json.
- Frequency: 15 minutes.
- Logic: 6 DNA types based on volume, momentum, consolidation, rejection patterns.
- Future: Performance tracking per DNA type.

AGENT 6: FOMO FILTER (v2_fomo_filter.py)
- Purpose: Anti-hype protection.
- Input: /tmp/scanner_output.json.
- Output: /tmp/fomo_output.json.
- Frequency: 15 minutes.
- Logic: FOMO score 0-100. Reject if >= 60. Checks parabolic moves, volume climax, extreme candles.

AGENT 7: VALIDATOR (v2_validator.py)
- Purpose: Quality gatekeeper.
- Input: /tmp/scanner_output.json.
- Output: /tmp/validator_output.json.
- Frequency: 15 minutes.
- Logic: 7 checks, pass rate >= 85% = PASSED. Rejects 90%+ of inputs.
- Key Parameters: min_liq=$50K, min_vol=$10K, 24h 5-200%, buy pressure >= 1.0.

AGENT 8: DYNAMIC RISK ENGINE (v2_dynamic_risk.py)
- Purpose: Technical levels calculation.
- Input: /tmp/validator_output.json + /tmp/regime_output.json + /tmp/fomo_output.json.
- Output: /tmp/dynamic_risk_output.json.
- Frequency: 15 minutes.
- Logic: ATR-based stops, dynamic position sizing, confidence scoring. Minimum R:R 1:2, confidence >= 60.
- Key Formula: stop_distance = ATR * 2.5 * regime_mult * liq_mult. Position = (Portfolio * Risk%) / Stop Distance.

AGENT 9: MASTER CONTROLLER (v4_master_controller.py)
- Purpose: Signal dispatch & capital protection.
- Input: /tmp/dynamic_risk_output.json + /tmp/dna_output.json + /tmp/regime_output.json.
- Output: Telegram alerts.
- Frequency: 15 minutes.
- Logic: Capital protection checks (drawdown, max trades, consecutive losses, exposure, liquidity, volatility). Build standardized signal format. Send to Telegram.
- Modes: MANUAL (default), SEMI_AUTO (future), AUTO (future).

AGENT 10: PORTFOLIO TRACKER (v4_portfolio_tracker.py)
- Purpose: Performance logging & mode upgrade.
- Input: /root/.openclaw/workspace/agents/logs/paper_trading.json.
- Output: /root/.openclaw/workspace/agents/logs/trade_history.json, portfolio_state.json.
- Frequency: 1 hour.
- Logic: Log every trade with full context. Calculate stats. Check upgrade eligibility.
- Upgrade: MANUAL -> SEMI_AUTO (100+ trades, expectancy > 0.3, drawdown < 15%, WR > 45%).

AGENT 11: JUPITER EXECUTOR (v4_jupiter_executor.py)
- Purpose: Paper trading execution.
- Input: /tmp/dynamic_risk_output.json.
- Output: /root/.openclaw/workspace/agents/logs/paper_trading.json.
- Frequency: 1 minute.
- Logic: Execute paper trades with 0.5% slippage. Monitor positions for TP/stop. Max 5 open positions.
- Status: DEPRECATED — replaced by Realistic Backtest Engine.

AGENT 12: REALISTIC BACKTEST ENGINE (v4_realistic_backtest.py)
- Purpose: Realistic paper trading.
- Input: /tmp/dynamic_risk_output.json + DexScreener API.
- Output: /root/.openclaw/workspace/agents/logs/paper_trading.json.
- Frequency: 5 minutes.
- Logic: Simulate spread, liquidity-based slippage, fees (0.3%), latency, partial fills, max 3 positions.
- Key Fix: Exits at TP1/stop level, οχι current market price.

AGENT 13: CIRCUIT BREAKER (v4_circuit_breaker.py)
- Purpose: Emergency shutdown.
- Input: portfolio_state.json + /tmp/regime_output.json + /tmp/scanner_output.json.
- Output: /root/.openclaw/workspace/agents/logs/circuit_breaker.json.
- Frequency: 1 minute.
- Logic: 5 checks (drawdown, BTC crash, volatility, API health, consecutive losses). States: NORMAL -> WARNING -> COOLDOWN -> EMERGENCY.
- Auto-resume: COOLDOWN after 4h. EMERGENCY requires manual reset.

AGENT 14: POSITION SIZING (v4_position_sizing.py)
- Purpose: Dynamic sizing.
- Input: /tmp/dynamic_risk_output.json + /tmp/regime_output.json + circuit_breaker.json.
- Output: Console logs.
- Frequency: 15 minutes.
- Logic: Kelly simplified. Factors: base_risk, vol_mult, conf_mult, regime_mult, circuit_mult, exposure limit.

AGENT 15: DUPLICATE PROTECTION (v4_duplicate_protection.py)
- Purpose: Anti-re-entry.
- Input: /tmp/dynamic_risk_output.json + trade_history.json.
- Output: /root/.openclaw/workspace/agents/logs/active_signals.json.
- Frequency: 5 minutes.
- Logic: 6h cooldown per symbol. Check active signals.

AGENT 16: TRADE EXPIRATION (v4_trade_expiration.py)
- Purpose: Signal timeout.
- Input: /tmp/dynamic_risk_output.json + /tmp/scanner_output.json + /tmp/regime_output.json.
- Output: active_signals.json (cleaned).
- Frequency: 5 minutes.
- Logic: Expire after 2h, structure break > 5%, volatility > 25%, liquidity < $20K, regime PANIC/EUPHORIC.

AGENT 17: EXECUTION QUALITY (v4_execution_quality.py)
- Purpose: Slippage & fill tracking.
- Input: paper_trading.json.
- Output: /root/.openclaw/workspace/agents/logs/execution_quality.json.
- Frequency: 5 minutes.
- Logic: Analyze entry deviation, slippage, latency. Grade EXCELLENT/GOOD/FAIR/POOR.

AGENT 18: SYSTEM SCORECARD (v4_system_scorecard.py)
- Purpose: Reality check.
- Input: paper_trading.json + all agent logs.
- Output: /root/.openclaw/workspace/agents/logs/system_scorecard.json.
- Frequency: 30 minutes.
- Logic: Calculate expectancy, drawdown, regime/DNA performance, false signals, agent health. Determine readiness.

═══════════════════════════════════════════════════════════════════════════════════════
SECTION 11: FILE STRUCTURE & CONFIGURATION
═══════════════════════════════════════════════════════════════════════════════════════

DIRECTORY: /root/.openclaw/workspace/agents/
├── launch_swarm.sh              (Launcher script)
├── v2_scanner.py               (Agent 1)
├── v2_sentiment.py             (Agent 2)
├── v2_whale.py                 (Agent 3)
├── v2_regime_detector.py       (Agent 4)
├── v2_dna_classifier.py        (Agent 5)
├── v2_fomo_filter.py           (Agent 6)
├── v2_validator.py             (Agent 7)
├── v2_dynamic_risk.py          (Agent 8)
├── v4_master_controller.py     (Agent 9)
├── v4_portfolio_tracker.py     (Agent 10)
├── v4_jupiter_executor.py      (Agent 11 — deprecated)
├── v4_realistic_backtest.py    (Agent 12 — active)
├── v4_circuit_breaker.py       (Agent 13)
├── v4_position_sizing.py       (Agent 14)
├── v4_duplicate_protection.py  (Agent 15)
├── v4_trade_expiration.py      (Agent 16)
├── v4_execution_quality.py     (Agent 17)
├── v4_system_scorecard.py      (Agent 18)
├── prompts/
│   ├── capital_protection.md
│   ├── circuit_breaker.md
│   ├── dna_classifier.md
│   ├── execution_layer.md
│   ├── jupiter_dex.md
│   ├── master_controller.md
│   ├── performance_analyst.md
│   ├── risk_manager.md
│   ├── scanner_agent.md
│   ├── sentiment_agent.md
│   ├── trade_journal.md
│   ├── validator_agent.md
│   └── whale_agent.md
├── logs/
│   ├── paper_trading.json      (State file)
│   ├── portfolio_state.json
│   ├── trade_history.json
│   ├── circuit_breaker.json
│   ├── execution_quality.json
│   ├── system_scorecard.json
│   ├── scorecard_history.json
│   ├── active_signals.json
│   └── *.log files per agent
└── dashboard/
    └── index.html              (Web dashboard)

═══════════════════════════════════════════════════════════════════════════════════════
SECTION 12: OPERATIONAL PHASES & ROADMAP
═══════════════════════════════════════════════════════════════════════════════════════

CURRENT PHASE: PAPER TRADING AUDIT
- Status: Collecting realistic data after critical fixes.
- Balance: $10,000 virtual.
- Valid Trades: 0.
- Goal: Measure actual edge.

PHASE 1: PAPER TRADING AUDIT (NOW — 2-4 εβδομαδες)
- Collect 100+ realistic trades.
- Calculate expectancy, win rate, drawdown.
- Verify system works across different regimes.
- Fix any new bugs discovered.

PHASE 2: TESTNET VALIDATION (μετα απο positive expectancy)
- Deploy on Solana testnet.
- Test Jupiter API integration.
- Test wallet signing (Phantom/Solflare).
- Verify real slippage vs model.

PHASE 3: SEMI-AUTO PILOT (μετα απο testnet success)
- Enable SEMI_AUTO mode.
- Auto-execute high-confidence setups (>80 conf, >1:3 R:R).
- Manual confirmation for everything else.
- Small real capital ($100-500).

PHASE 4: FULL AUTONOMOUS (μετα απο 500+ trades, expectancy > 0.5)
- Enable FULL_AUTO mode.
- Full capital deployment.
- Continuous monitoring and optimization.

═══════════════════════════════════════════════════════════════════════════════════════
SECTION 13: OMISSIONS & KNOWN GAPS
═══════════════════════════════════════════════════════════════════════════════════════

Τα εξης δεν εχουν καλυφθει ακομα:

1. On-Chain Wallet Analysis: Δεν αναλυουμε actual wallet transactions, holder distribution, smart contract safety.
2. Multi-DEX Aggregation: Χρησιμοποιουμε μονο DexScreener. Δεν εχουμε Birdeye, CoinGecko, CoinMarketCap APIs.
3. Historical OHLCV Data: Δεν εχουμε access σε historical klines για backtesting σε παρελθοντικα δεδομενα.
4. Telegram Group NLP: Δεν αναλυουμε αυτοματα τα μηνυματα των groups. Ειναι manual monitoring.
5. Twitter/Social Media Scraping: Καμια integration με Twitter/X APIs.
6. News/Event Calendar: Δεν παρακολουθουμε crypto news, token unlocks, earnings, macro events.
7. Cross-Chain Analysis: Εστιαζουμε Solana μονο. Δεν παρακολουθουμε Ethereum, BSC, Arbitrum, Base.
8. Options/Futures Data: Μονο spot DEX. Οχι perps, οχι funding rates.
9. Machine Learning Models: Ολα τα signals ειναι rule-based. Δεν εχουμε trained models.
10. Order Book Depth: Δεν αναλυουμε L2 data. Μονο aggregated DEX metrics.
11. Arbitrage Detection: Δεν ψαχνουμε για price discrepancies across DEXes.
12. MEV Protection: Δεν προστατευουμε απο sandwich attacks σε real execution.
13. Gas Optimization: Στο paper trading δεν υπολογιζουμε gas fees.
14. Tax Reporting: Καμια integration για P&L tracking για tax purposes.
15. Mobile App: Καμια mobile interface. Μονο Telegram + web dashboard.
16. Multi-User Support: Σχεδιασμενο για 1 χρηστη μονο.
17. Paper Trading Realism: Ακομα και το "realistic" engine ειναι προσεγγιση. Δεν ειναι 100% accurate.
18. Stop-Loss Automation: Δεν τοποθετουμε αυτοματα stop orders. Monitor μονο.
19. Trailing Stops: Δεν υποστηριζουμε trailing stops.
20. Partial Exits: Δεν υποστηριζουμε scaling out (πχ 33% at TP1, 33% at TP2). Ολοκληρη position κλεινει στο πρωτο TP.

═══════════════════════════════════════════════════════════════════════════════════════
END OF REPORT
═══════════════════════════════════════════════════════════════════════════════════════
