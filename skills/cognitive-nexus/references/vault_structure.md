# Vault Structure & YAML Metadata Schemas

## Folder Structure

```
vault/
├── 00_nexus/                   # Dashboard & System triggers
│   ├── 00_NEXUS_DASHBOARD.md  # Main control panel
│   ├── NEXUS_MAP.canvas        # Visual pipeline map
│   ├── nightly_proposals.md   # Hermes connection proposals
│   └── conflict_report.md     # Active conflicts summary
│
├── inbox/                      # Raw data awaiting processing
│   ├── manual/                 # Human-created inputs
│   ├── automated/              # System-generated inputs
│   ├── urgent/                 # Priority items
│   └── README.md               # Inbox rules
│
├── daily/                      # Chronological logging
│   ├── nightly_YYYYMMDD.md     # Nightly batch reports
│   ├── health_YYYYMMDD.md      # Health check reports
│   └── README.md               # Daily logging rules
│
├── projects/                   # Active projects
│   ├── active/                 # Currently running projects
│   ├── archived/               # Completed projects
│   ├── templates/              # Project templates
│   └── README.md               # Project rules
│
├── knowledge/                  # Validated knowledge (Source of Truth)
│   ├── concepts/               # Concept definitions
│   ├── entities/               # Named entities (people, orgs, etc.)
│   ├── relationships/          # Relationship mappings
│   ├── sources/                # Source documentation
│   └── README.md               # Knowledge rules
│
├── decisions/                  # Decision records
│   ├── pending/                # Awaiting approval
│   ├── approved/               # Approved decisions
│   ├── rejected/               # Rejected proposals
│   ├── superseded/             # Replaced by newer decisions
│   └── README.md               # Decision rules
│
├── ai_outputs/                 # Raw AI outputs (before validation)
│   ├── gemini/                 # Gemini research outputs
│   ├── kimi/                   # Kimi extraction outputs
│   ├── claude/                 # Claude synthesis outputs
│   ├── hermes/                 # Hermes validation outputs
│   ├── openclaw/               # OpenClaw execution logs
│   └── README.md               # AI output rules
│
├── conflicts/                  # Disagreements between agents
│   ├── hermes-vs-claude/       # Hermes rejecting Claude
│   ├── hermes-vs-kimi/         # Hermes rejecting Kimi
│   ├── gemini-vs-claude/       # Gemini data contradicting Claude
│   ├── multi-agent/            # Escalated conflicts
│   └── README.md               # Conflict rules
│
├── system/                     # System configuration
│   ├── prompts/                # Agent system prompts
│   ├── scripts/                # Python/Bash scripts
│   ├── rules/                  # System rules and policies
│   ├── config/                 # Configuration files
│   └── README.md               # System rules
│
└── .obsidian/                  # Obsidian configuration
    ├── app.json                # App settings
    ├── community-plugins.json  # Enabled plugins
    └── plugins/                # Plugin data
```

## YAML Metadata Schemas

### Inbox Files

```yaml
---
title: "Task Title"
type: task
status: pending           # pending | processing | processed | archived
priority: normal          # urgent | high | normal | low
topic: "Subject Topic"
task_id: "YYYYMMDD_HHMMSS"
created: YYYY-MM-DD HH:MM:SS
updated: YYYY-MM-DD HH:MM:SS
agent: "system"           # system | gemini | kimi | claude | hermes | openclaw
stage: ingestion          # ingestion | scouting | compression | synthesis | validation | execution
source: "manual"          # manual | automated | webhook | scheduled
---
```

### Knowledge Files

```yaml
---
title: "Knowledge Title"
type: knowledge
status: active            # active | archived | superseded | draft
validated: true
validation_date: YYYY-MM-DD HH:MM:SS
validated_by: "hermes"
task_id: "YYYYMMDD_HHMMSS"
source: "claude_synthesis" # gemini_research | kimi_extract | claude_synthesis
backlinks:
  - "knowledge/related_note.md"
  - "projects/project_name.md"
tags:
  - tag1
  - tag2
---
```

### Decision Files

```yaml
---
title: "Decision Title"
type: decision
status: approved          # pending | approved | rejected | superseded
decision_type: strategic  # strategic | tactical | operational | conflict_resolution
original_conflict: "conflicts/hermes-vs-claude/..."  # if applicable
decision_date: YYYY-MM-DD HH:MM:SS
decided_by: "human"       # human | hermes | vote
rationale: "Brief explanation"
alternatives_considered:
  - "Alternative 1"
  - "Alternative 2"
consequences:
  - "Expected outcome 1"
  - "Expected outcome 2"
---
```

### Conflict Files

```yaml
---
title: "Conflict Title"
type: conflict
status: pending           # pending | resolved | escalated
agents_involved: "claude, hermes"
conflict_type: "validation_rejection"  # validation_rejection | data_disagreement | logic_gap
severity: medium          # critical | high | medium | low
resolution_status: pending  # pending | resolved | escalated
resolution_method: ""       # hermes_approved | human_override | compromise | vote
resolution_rationale: ""
resolution_date: ""
resolution_by: ""
---
```

### AI Output Files

```yaml
---
title: "Agent Output Title"
type: ai_output
agent: gemini             # gemini | kimi | claude | hermes | openclaw
stage: scouting           # scouting | compression | synthesis | validation | execution
task_id: "YYYYMMDD_HHMMSS"
topic: "Subject Topic"
status: complete          # pending | complete | failed
output_date: YYYY-MM-DD HH:MM:SS
source: "web_research"    # web_research | gemini_output | kimi_extract | claude_synthesis
quality: high             # high | medium | low
---
```

### Project Files

```yaml
---
title: "Project Name"
type: project
status: active           # active | paused | completed | cancelled
priority: high            # urgent | high | medium | low
completion: 25            # Percentage 0-100
start_date: YYYY-MM-DD
end_date: YYYY-MM-DD
linked_notes:
  - "knowledge/topic1.md"
  - "knowledge/topic2.md"
related_decisions:
  - "decisions/approved/decision1.md"
tags:
  - project
  - active
---
```

### System Files

```yaml
---
title: "System File Title"
type: system              # system | system-rules | system-config | system-prompt
status: active
version: "1.0.0"
last_updated: YYYY-MM-DD HH:MM:SS
author: "openclaw"
---
```

### Daily Log Files

```yaml
---
title: "Daily Log YYYY-MM-DD"
type: daily
status: complete
log_date: YYYY-MM-DD
batch_count: 5
conflicts_resolved: 2
knowledge_created: 3
---
```

## Metadata Rules

1. **All files must have YAML frontmatter** — Files without `---` at the top are flagged by health check
2. **Title is mandatory** — Every file must have a `title` field
3. **Type is mandatory** — Every file must have a `type` field from the valid set
4. **Status is mandatory** — Every file must have a `status` field
5. **Created date is mandatory** — Every file must have a `created` or `log_date` field
6. **Backlinks for knowledge** — Knowledge files must have `backlinks` array
7. **Agent attribution for AI outputs** — AI output files must specify which agent created them

## File Naming Conventions

### Inbox
- `task_YYYYMMDD_HHMMSS.md` — Task files
- `input_YYYYMMDD_HHMMSS.md` — Generic inputs
- `urgent_YYYYMMDD_HHMMSS.md` — Priority items

### Knowledge
- `{topic}_{task_id}.md` — Main knowledge files
- `concept_{name}.md` — Concept definitions
- `entity_{name}.md` — Entity files

### AI Outputs
- `{task_id}_{agent}_{stage}.md` — Stage-specific outputs
- Example: `20240101_120000_gemini_scouting.md`

### Conflicts
- `{task_id}_{agent1}-vs-{agent2}.md` — Conflict files
- Example: `20240101_120000_claude-vs-hermes.md`

### Decisions
- `decision_YYYYMMDD_{number}.md` — Decision records
- Example: `decision_20240101_001.md`

### Daily Logs
- `nightly_YYYYMMDD.md` — Nightly batch reports
- `health_YYYYMMDD.md` — Health check reports

## Archive Rules

- **Never delete** — Always move to `/system/archive/`
- **Preserve metadata** — Keep YAML frontmatter when archiving
- **Add archive_date** — Append `archive_date: YYYY-MM-DD` to metadata
- **Preserve structure** — Maintain folder hierarchy in archive

## Example Complete File

```markdown
---
title: "Solana DEX Aggregators"
type: knowledge
status: active
validated: true
validation_date: 2024-01-15 14:30:00
validated_by: "hermes"
task_id: "20240115_120000"
source: "claude_synthesis"
backlinks:
  - "knowledge/solana_defi.md"
  - "knowledge/jupiter_dex.md"
  - "projects/solana_trading_bot.md"
tags:
  - solana
  - defi
  - dex
  - aggregator
---

# Solana DEX Aggregators

## Overview

Solana DEX aggregators combine liquidity from multiple decentralized exchanges...

## Key Aggregators

| Name | Liquidity | Features | Risk Level |
|------|-----------|----------|------------|
| Jupiter | $500M+ | Best routing, limit orders | Low |
| Raydium | $200M+ | AMM + orderbook | Medium |
| Orca | $150M+ | Concentrated liquidity | Low |

## Strategic Implications

- Jupiter dominates with superior routing algorithms
- Raydium offers dual liquidity pools
- Orca's Whirlpools enable concentrated liquidity strategies

## Decisions

- [[decisions/approved/decision_20240115_001.md|Use Jupiter for primary routing]]

## Sources

- Gemini research: [[ai_outputs/gemini/20240115_120000_gemini_research.md]]
- Kimi extract: [[ai_outputs/kimi/20240115_120000_kimi_extract.md]]
- Claude synthesis: [[ai_outputs/claude/20240115_120000_claude_synthesis.md]]

## Validation

- **Validator**: Hermes
- **Date**: 2024-01-15 14:30:00
- **Status**: ✅ APPROVED
- **Critique**: Minor risk assessment gaps noted but acceptable for current knowledge level

## Related Knowledge

- [[knowledge/solana_defi.md|Solana DeFi Ecosystem]]
- [[knowledge/jupiter_dex.md|Jupiter DEX]]
- [[knowledge/raydium.md|Raydium Protocol]]
```
