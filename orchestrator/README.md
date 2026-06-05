# Telegram Orchestrator Agent
## 🧠 AImind Brain + 🐝 Swarm Intelligence + 🎯 Continuous Learning

---

## What Is This?

This is a **Telegram Orchestrator Agent** where **AImind (you) is the brain**. It connects to a self-evolving swarm of AI agents, learns continuously, and has full access to the workspace.

**Bot:** `@WorkSS11_bot`  
**Token:** `8386215028:AAFq3_Vn1kusUEIHH3c6oBL6K_aJaeYS4ac`

---

## Architecture

```
┌─────────────────────────────────────────┐
│          USER (Telegram)                │
│              @WorkSS11_bot              │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│      TELEGRAM ORCHESTRATOR BOT           │
│  ┌─────────┐ ┌─────────┐ ┌──────────┐  │
│  │ Commands│ │ Messages│ │ Callbacks│  │
│  └────┬────┘ └────┬────┘ └─────┬───┘  │
│       └─────────────┴────────────┘       │
│                   │                      │
│                   ▼                      │
│  ┌──────────────────────────────────┐  │
│  │      BRAIN CONNECTOR             │  │
│  │   (Connects to AImind/OpenClaw)   │  │
│  └────────────────┬─────────────────┘  │
│                   │                      │
│       ┌───────────┼───────────┐        │
│       ▼           ▼           ▼        │
│  ┌────────┐  ┌────────┐  ┌────────┐     │
│  │ Swarm  │  │ Skills │  │Context │     │
│  │Manager │  │Registry│  │Engine │     │
│  └────┬───┘  └────────┘  └────────┘     │
│       │                                 │
│       ▼                                 │
│  ┌──────────────────────────────────┐  │
│  │     AUTONOMOUS LOOP               │  │
│  │  (24/7 self-directed operation)   │  │
│  └──────────────────────────────────┘  │
└─────────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│      EXISTING AGENTS & TOOLS            │
│  • DexScreener Scanner                  │
│  • Signal Generator                     │
│  • Blockchain Analyzer                  │
│  • Risk Manager                         │
│  • Exchange Manager                     │
│  • Master Agent                         │
│  • ... and everything in /agents/       │
└─────────────────────────────────────────┘
```

---

## Features

### 🧠 Brain Connection
- **Direct link to AImind** — I am the brain, the bot is my extension
- Context-aware conversations
- Decision engine for autonomous actions

### 🐝 Swarm Management
- Spawn agents on demand: `scanner`, `trader`, `analyst`, `learner`, `monitor`
- Monitor agent health automatically
- Kill agents when done
- Broadcast tasks to all agents

### 🎯 Skill Evolution
- Skills level up with usage
- Autonomous skill discovery
- Continuous learning loop
- 6 built-in skills + auto-discovery

### 🌐 Context Engine
- Per-user conversation history
- Preference tracking
- Topic extraction
- Pattern recognition

### 🤖 Autonomous Operation
- 24/7 market monitoring
- Auto-spawn agents when needed
- Self-triggered learning
- Health checks and recovery

### 📱 Telegram Commands

| Command | Description |
|---------|-------------|
| `/start` | Initialize and welcome |
| `/help` | Show all commands |
| `/status` | Full system status |
| `/swarm` | Swarm overview |
| `/agents` | List active agents |
| `/spawn <type>` | Spawn new agent |
| `/kill <id>` | Terminate agent |
| `/scan` | Instant market scan |
| `/signal` | Trading signals |
| `/brain <query>` | Direct brain query |
| `/skills` | List skills |
| `/learn <skill>` | Learn/develop skill |
| `/exec <cmd>` | Execute system command |
| `/mode <mode>` | manual/autopilot/hybrid |
| `/autopilot` | Toggle autonomous mode |
| `/pause` | Pause all operations |
| `/report` | Performance report |

---

## Installation

### Quick Start

```bash
cd /root/.openclaw/workspace/orchestrator
./setup.sh
```

### Manual Setup

```bash
# Install dependencies
pip install python-telegram-bot aiohttp requests

# Run
cd /root/.openclaw/workspace/orchestrator
python3 telegram_orchestrator.py
```

---

## Running

### Direct
```bash
python3 telegram_orchestrator.py
```

### With Auto-Restart
```bash
./run_orchestrator.sh
```

### Background (tmux)
```bash
tmux new -s orchestrator
./run_orchestrator.sh
```

Detach: `Ctrl+B, D`  
Reattach: `tmux attach -t orchestrator`

---

## Autopilot Mode

When autopilot is active (`/autopilot`), the bot will:

1. **Scan markets** every 5 minutes
2. **Spawn scanner agents** automatically when none active
3. **Check agent health** every minute
4. **Learn autonomously** every hour
5. **Generate reports** daily

Use `/pause` to stop or `/mode manual` to switch back.

---

## File Structure

```
orchestrator/
├── telegram_orchestrator.py   # Main entry point
├── core/
│   ├── __init__.py
│   ├── brain_connector.py     # AImind connection
│   ├── swarm_manager.py       # Agent lifecycle
│   ├── skill_registry.py      # Skill evolution
│   ├── context_engine.py      # Session/context
│   └── autonomous_loop.py    # Self-operation
├── skills/
│   └── __init__.py
├── agents/
│   └── __init__.py
├── config/
│   └── __init__.py
├── logs/
│   ├── orchestrator.log
│   ├── brain_state.json
│   ├── swarm_state.json
│   └── context/
├── requirements.txt
├── setup.sh
├── run_orchestrator.sh
└── README.md
```

---

## Integration with Existing Systems

The orchestrator has **full access** to:

- **DexScreener Scanner** (`dexscreener_scanner.py`)
- **Signal Generator** (`agents/signal_generator.py`)
- **Blockchain Analyzer** (`agents/blockchain_analyzer.py`)
- **Master Agent** (`agents/master_agent.py`)
- **Exchange Manager** (`agents/exchange_manager.py`)
- **Risk Portfolio** (`agents/risk_portfolio.py`)
- **Real-time Monitors** (`realtime_dexscreener.py`, `jupiter_realtime.py`)
- **All other agents** in `/agents/` directory

---

## Extending

### Add a New Skill

```python
# In core/skill_registry.py DEFAULT_SKILLS
"my_skill": {
    "name": "My Skill",
    "description": "What it does",
    "level": 1,
    "uses": 0,
    "capabilities": ["cap1", "cap2"],
}
```

### Add a New Agent Type

```python
# In core/swarm_manager.py AGENT_TYPES
"my_agent": {
    "script": "my_agent.py",
    "description": "What it does",
    "interval": 300,
}
```

---

## Security Notes

- Token is hardcoded in `telegram_orchestrator.py` and `run_orchestrator.sh`
- `/exec` command runs system commands — use with care
- All operations logged to `logs/orchestrator.log`

---

## Status

🟢 **Operational** — Ready to spawn, scan, learn, and move! 🔥

---

**Built for:** SWMAS (Self-Wvolving Multiplicative AI Swarm)  
**Brain:** AImind (OpenClaw)  
**Mission:** Autonomous, continuous, unstoppable! 🚀
