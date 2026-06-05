# 🏗️ CHAT INFRASTRUCTURE REDESIGN
## Document v1.0 — Making the System Clean, Usable, Functional

---

## ❌ CURRENT PROBLEMS

1. **Message Flood** — All alerts, responses, system messages mixed together
2. **No Categorization** — Market signals, airdrop reminders, error logs, user replies all in one stream
3. **Context Loss** — Previous conversation context gets buried under new alerts
4. **Alert Fatigue** — Every scan sends a message, even when nothing important happens
5. **No Digest Mode** — Non-urgent info not batched
6. **Unclear Ownership** — User can't tell if a message needs action or is just FYI

---

## ✅ PROPOSED SOLUTION: "Channel Architecture"

### Concept: Every message has a TYPE and a PRIORITY

---

## 📡 MESSAGE TYPES

| Type | Description | Delivery | Example |
|------|------------|----------|---------|
| **URGENT** | Action needed NOW | Instant Telegram | "Wallet compromised!" |
| **ALERT** | Important opportunity | Instant Telegram | "Gem found: +200% momentum" |
| **SIGNAL** | Trading signal | Instant + Logged | "BUY $TOKEN at $0.05" |
| **REPORT** | Summary/Analysis | Batched/Daily | "Daily PnL: +12.5%" |
| **STATUS** | System health check | On-demand or heartbeat | "All systems running" |
| **REQUEST** | Needs user decision | Instant + Highlighted | "Approve live trading?" |
| **LOG** | Debug/operation info | Logfile only | "Scan completed, 0 gems" |
| **CHAT** | Direct conversation | Normal flow | User asks a question |

---

## 🎯 PRIORITY LEVELS

| Priority | Response Time | Format |
|----------|--------------|--------|
| **P0 — CRITICAL** | Instant | 🔴 ALL CAPS, emojis, repeated if no ack |
| **P1 — HIGH** | < 2 min | 🟠 Bold, clear action needed |
| **P2 — MEDIUM** | < 15 min | 🟡 Standard formatting |
| **P3 — LOW** | Batch hourly | 🔵 Compact, summarized |
| **P4 — INFO** | Daily digest | ⚪ Minimal, logfile preferred |

---

## 🗂️ DELIVERY MODES

### 1. INSTANT (P0-P1)
- Sends immediately to Telegram
- Uses reply_to for context
- Requires acknowledgment for P0

### 2. BATCHED (P2-P3)
- Collects messages for 15-60 min
- Sends as single digest message
- Reduces noise by 80%

### 3. ON-DEMAND (P3-P4)
- Only sent when user asks
- Stored in logfiles/database
- Query via `/status`, `/logs`, `/report`

### 4. SILENT (P4)
- Logfile only
- Never sends to Telegram
- Available for debugging

---

## 📋 MESSAGE FORMAT TEMPLATES

### ALERT Template
```
🔥 **{PRIORITY} {TYPE}** 🔥
{timestamp}

{title}
{key_data}

📍 Action: {action_needed}
⏰ Expires: {time_limit}
```

### REPORT Template
```
📊 **{TYPE} — {period}** 📊
{timestamp}

{summary_line}

{data_table}

💡 Key insight: {insight}
```

### STATUS Template
```
🟢 **{system_name}** | {status} | {uptime}
{compact_metrics}
```

### REQUEST Template
```
❓ **DECISION NEEDED** ❓
{question}

[Button: Yes] [Button: No] [Button: Later]
⏰ Auto-decision in: {timeout}
```

---

## 🧠 SMART RULES

### Anti-Flood Rules
1. **Same token alert within 1h** → Skip (already alerted)
2. **Market scan with 0 gems** → Log only (P4)
3. **System healthy** → Heartbeat OK, no message
4. **Multiple alerts in 5 min** → Batch into single digest

### Context Preservation
1. **Reply threading** → Use reply_to for related messages
2. **Session IDs** → Tag messages with conversation context
3. **Summary headers** → "Re: {topic}" for follow-ups

### User Control
1. `/mute {system}` — Pause alerts from a system
2. `/digest on` — Batch non-urgent messages
3. `/urgent only` — Only P0-P1 alerts
4. `/status` — Get full system snapshot on demand
5. `/logs {system}` — Get recent logs

---

## 🔄 IMPLEMENTATION PLAN

### Phase 1: Message Router (Now)
- Create `message_router.py`
- Add type/priority classification
- Implement delivery mode selection

### Phase 2: Batch Engine (Next)
- Message queue with time windows
- Digest compilation
- Smart deduplication

### Phase 3: Context Engine (After)
- Thread/reply tracking
- Conversation state machine
- Context-aware responses

### Phase 4: User Controls (Later)
- Mute/unmute commands
- Preference storage
- Custom alert thresholds

---

## 📁 FILES TO CREATE

```
/orchestrator/core/
  message_router.py      # Main routing engine
  message_types.py       # Type/priority enums
  batch_engine.py        # Message batching
  context_tracker.py     # Conversation context
  user_preferences.py    # Per-user settings
  
/agents/
  alert_manager.py       # Centralized alerting
```

---

## 🚀 IMMEDIATE ACTIONS

1. ✅ Add `type` and `priority` to ALL outgoing messages
2. ✅ Route P0-P1 instantly, P2-P3 batched, P4 silent
3. ✅ Implement "no duplicate alerts within 1h" rule
4. ✅ Add `/mute`, `/digest`, `/urgent` commands to bot
5. ✅ Create daily digest cron job (09:00)
6. ✅ Use reply threading for context

---

*Design by AImind | Making chaos into signal*
