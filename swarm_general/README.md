# 🌐 SWMAS General Purpose Swarm System (GPSS) v2.0

**Self-Wvolving Multiplicative AI Swarm — All Directions**

> 🔥 **Tracks 1-2 ACTIVE** | 🧠 **Brain: AImind** | 🤖 **8 Agent Types** | 🛠️ **27+ Skills**

---

## 🎯 Philosophy

Το SWMAS δεν είναι πια μόνο για trading.

Είναι ένα **γενικού σκοπού AI swarm** που μπορεί να:
- Σκεφτεί 🧠
- Μάθει 📚
- Δράσει ⚡
- Προσαρμοστεί 🔄
- Εξελιχθεί 🧬

**Προς όλες τις κατευθύνσεις. Χωρίς όρια.**

---

## 🧭 8 Directions

| # | Direction | Emoji | Agent | Purpose |
|---|-----------|-------|-------|---------|
| 1 | Research & Intelligence | 🕵️ | ResearchAgent | Deep research, OSINT, data gathering |
| 2 | Content & Creation | ✍️ | ContentAgent | Writing, coding, creative tasks |
| 3 | Automation & Execution | 🤖 | AutomationAgent | Workflow automation, integrations |
| 4 | Monitoring & Alerting | 📊 | MonitorAgent | Health checks, metrics, alerts |
| 5 | Communication & Coordination | 🗣️ | CommsAgent | Telegram, Discord, Email, Slack |
| 6 | Analysis & Decision Support | 🧮 | AnalysisAgent | Data analysis, forecasting |
| 7 | Problem Solving & Debugging | 🔧 | SolverAgent | Root cause analysis, fixes |
| 8 | Learning & Adaptation | 📚 | LearnAgent | Skill building, evolution |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│         🧠 BRAIN (AImind)               │
│    Strategic Decision Center            │
└─────────────────┬───────────────────────┘
                  │
    ┌─────────────┼─────────────┐
    │             │             │
┌───▼───┐   ┌────▼────┐   ┌────▼────┐
│Research│   │Execution│   │Analysis │
│ Agent  │   │  Agent  │   │  Agent  │
└────────┘   └─────────┘   └─────────┘
    │             │             │
┌───▼───┐   ┌────▼────┐   ┌────▼────┐
│Content │   │Monitor  │   │Problem  │
│ Agent  │   │  Agent  │   │ Solver  │
└────────┘   └─────────┘   └─────────┘
    │             │             │
┌───▼───┐   ┌────▼────┐   ┌────▼────┐
│Comms   │   │Learn    │   │Auto     │
│ Agent  │   │  Agent  │   │  Agent  │
└────────┘   └─────────┘   └─────────┘

┌─────────────────────────────────────────┐
│      🔄 SHARED INFRASTRUCTURE           │
│  Memory | Skills | Tools | APIs | Comms  │
└─────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Start the Swarm
```bash
cd /root/.openclaw/workspace/swarm_general
./run_general_swarm.sh
```

### 2. Check Status
```bash
./status.sh
```

### 3. Stop the Swarm
```bash
./stop.sh
```

---

## 📱 Telegram Commands

Via @WorkSS11_bot:

| Command | Description |
|---------|-------------|
| `/status` | Swarm status |
| `/agents` | Active agents |
| `/tasks` | Running tasks |
| `/skills` | Available skills |
| `/task <desc>` | Submit a task |
| `/directions` | Show all directions |
| `/help` | Help message |

---

## 🛠️ Skills Ecosystem (27+)

### Research Skills
- `web_search` — Search the web
- `deep_research` — Deep research with synthesis
- `osint_gather` — Open source intelligence
- `data_scrape` — Scrape websites
- `fact_check` — Verify facts

### Content Skills
- `write_text` — Write text content
- `write_code` — Write code
- `edit_text` — Edit and improve
- `summarize` — Summarize content
- `translate` — Translate languages
- `creative_write` — Creative writing
- `generate_doc` — Generate docs

### Automation Skills
- `schedule_task` — Schedule tasks
- `run_script` — Execute scripts
- `api_call` — Make API calls
- `webhook_trigger` — Trigger webhooks
- `file_operation` — File operations
- `workflow_orchestrate` — Orchestrate workflows

### Monitoring Skills
- `ping_check` — Health checks
- `log_monitor` — Monitor logs
- `metric_collect` — Collect metrics
- `alert_send` — Send alerts
- `health_report` — Health reports
- `anomaly_detect` — Detect anomalies

### Communication Skills
- `telegram_send` — Telegram messages
- `email_send` — Email
- `discord_send` — Discord
- `broadcast` — Multi-channel
- `meeting_schedule` — Schedule meetings
- `reminder_set` — Set reminders

### Analysis Skills
- `data_analyze` — Analyze data
- `chart_create` — Create charts
- `report_generate` — Generate reports
- `statistical_test` — Statistical tests
- `predict_model` — Predictive modeling
- `trend_analyze` — Analyze trends

---

## 🔄 Autonomous Operation Modes

1. **Reactive** — User sends command → Agent executes → Reports back
2. **Proactive** — Agent monitors → Detects trigger → Acts → Alerts
3. **Continuous** — Agent runs loop → Gathers → Analyzes → Decides → Acts
4. **Collaborative** — Multiple agents coordinate → Divide → Synthesize
5. **Evolutionary** — Agent self-assesses → Identifies gaps → Learns

---

## 📁 File Structure

```
swarm_general/
├── core/
│   ├── brain_connector.py      # Connection to AImind
│   ├── task_router.py          # Task routing logic
│   ├── agent_factory.py        # Agent creation/management
│   ├── skill_registry.py       # Skill discovery & loading
│   ├── context_engine.py       # Session & memory management
│   └── autonomous_loop.py      # Self-directed operations
├── agents/
│   ├── research_agent.py       # Research & OSINT
│   ├── content_agent.py        # Content & code creation
│   ├── automation_agent.py     # Workflow automation
│   ├── monitor_agent.py        # Monitoring & alerts
│   ├── comms_agent.py          # Communication hub
│   ├── analysis_agent.py       # Data analysis
│   ├── solver_agent.py         # Problem solving
│   └── learn_agent.py          # Learning & adaptation
├── config/
│   └── swarm_config.yaml       # Main configuration
├── memory/
│   ├── short_term.py           # Active session memory
│   ├── long_term.py            # Persistent knowledge
│   └── episodic.py             # Event/timeline memory
├── logs/
│   └── [execution logs]
├── run_general_swarm.sh        # Launcher
├── stop.sh                     # Stopper
├── status.sh                   # Status checker
├── general_orchestrator.py     # Main entry point
└── README.md                   # This file
```

---

## 💪 Power Moves

- **Parallel Execution** — Multiple agents work simultaneously
- **Skill Sharing** — Agents teach each other new capabilities
- **Memory Persistence** — Learn from every task, improve over time
- **Auto-Scaling** — Spawn new agents when load increases
- **Fault Tolerance** — Failed tasks auto-retry with different strategies

---

## 🎯 Success Metrics

- Tasks completed per hour
- Success rate per agent type
- Average response time
- User satisfaction score
- New skills learned per day
- Cross-domain task ratio

---

## 🔗 Integration

### With Telegram Orchestrator (@WorkSS11_bot)
The general swarm integrates seamlessly with the existing Telegram bot:

```python
# In telegram_orchestrator.py
from general_orchestrator import get_orchestrator

orchestrator = get_orchestrator()
result = await orchestrator.handle_telegram_command(command, args, user_id)
```

### With Trading Agents
Existing trading agents (master_agent, blockchain_analyzer, etc.) can be spawned as specialized agents within the general swarm.

---

## 🛡️ Safety & Boundaries

- No destructive operations without confirmation
- All actions logged and auditable
- User approval required for high-risk tasks
- Graceful degradation on failures
- Resource limits enforced

---

## 🚀 Future Enhancements

- [ ] Self-evolution engine
- [ ] Cross-domain knowledge transfer
- [ ] Advanced predictive task generation
- [ ] Multi-agent collaborative problem solving
- [ ] Real-time swarm visualization dashboard
- [ ] Voice/video processing agents
- [ ] External tool marketplace integration

---

## 💻 Development

### Adding a New Agent

```python
# agents/my_agent.py
class MyAgent:
    def __init__(self, agent_id, orchestrator, config):
        self.agent_id = agent_id
        self.orchestrator = orchestrator
        
    async def execute(self, task):
        # Your logic here
        return {'success': True, 'result': 'Done'}
```

### Adding a New Skill

```python
# In skill_registry.py
SKILL_CATALOG['my_skill'] = {
    'category': 'my_category',
    'level': 1,
    'description': 'What it does'
}
```

---

**Έτοιμοι; Πάμε να το τρέξουμε! 🔥⚡🚀**

---

*Built for SWMAS — Self-Wvolving Multiplicative AI Swarm*
*Version 2.0 | May 2026*
