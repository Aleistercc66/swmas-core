---
name: cognitive-nexus
description: Cognitive Nexus & Multi-Agent Superbrain orchestration system. Use when the user needs to set up, manage, or operate a local AI-driven multi-agent system using Obsidian as the immutable Source of Truth. This skill covers (1) Obsidian vault structure creation and management, (2) Multi-agent orchestration with roles (Gemini Scout, Kimi Extractor, Claude Architect, Hermes Oracle, OpenClaw Operator), (3) The industrial pipeline loop (Ingestion → Scouting → Compression → Synthesis → Validation → Execution), (4) Neural Dashboard setup with Dataview and Canvas, (5) Nightly batch self-improvement loop, (6) Conflict resolution and validation workflows. Triggers on phrases like "cognitive nexus", "multi-agent brain", "obsidian vault setup", "agent orchestration", "nexus dashboard", "ai pipeline", "knowledge vault", "file-based memory system", "the industrial loop", "hermes validation", or any request involving multiple AI agents working together with Obsidian as the memory backbone.
---

# Cognitive Nexus & Multi-Agent Superbrain

A local, file-based multi-agent orchestration system using Obsidian as the immutable Source of Truth. Zero-API policy for reasoning layers — everything operates through local file access, desktop automation, browser workflows, and local LLM runtimes.

## System Overview

The Cognitive Nexus is a strict pipeline where information flows through specialized agents, each with a non-overlapping role, producing validated knowledge artifacts stored permanently in the Obsidian vault.

### The Pipeline (Industrial Loop)

```
/inbox → [Gemini Scout] → [Kimi Extractor] → [Claude Architect] → [Hermes Oracle] → [OpenClaw Operator] → /knowledge
                    ↓                                              ↓
              /ai_outputs/                                    /conflicts/
```

1. **Ingestion**: Raw data enters `/inbox` (manual or automated)
2. **Scouting (Gemini)**: Web research, raw data collection, trend identification
3. **Compression (Kimi)**: Structure extraction, noise removal, raw data → JSON/Markdown
4. **Synthesis (Claude)**: Strategy creation, complex planning, final documentation
5. **Validation (Hermes)**: Local validation, red teaming, conflict detection → `/conflicts/` if rejected
6. **Execution (OpenClaw)**: File operations, vault updates, batch processing, automation

### Vault Structure

```
vault/
├── 00_nexus/           # Dashboard, system triggers, maps
├── inbox/              # Raw data awaiting processing
├── daily/              # Chronological logs
├── projects/           # Active projects with live data
├── knowledge/          # Validated, processed knowledge
├── decisions/          # Decision records with rationale
├── ai_outputs/         # Raw AI outputs before merge
├── conflicts/          # Disagreements requiring human/Hermes intervention
└── system/             # Prompts, scripts, system rules
```

## Core Rules (Non-Negotiable)

- Every piece of information ends in a `.md` file
- No data lives exclusively in AI chat memory
- No deletion without manual approval — system archives, never deletes
- Every knowledge node must have backlinks
- All metadata at file top in YAML frontmatter
- Every strategic decision recorded in `/decisions/` with rationale
- Every conflict goes to `/conflicts/` for human/Hermes resolution

## Agent Roles (Strict Separation of Concerns)

| Agent | Role | Function | Location |
|-------|------|----------|----------|
| **Gemini** | The Scout | Research layer, web scraping, trend detection | Browser/Cloud |
| **Kimi** | The Extractor | Compression, PDF/text ingestion, structured extraction | Browser/Cloud |
| **Claude** | The Architect | Synthesis, strategy, complex planning, documentation | Browser/Cloud |
| **Hermes** | The Oracle | Local validation, red teaming, Devil's Advocate, bias detection | **Local Only** |
| **OpenClaw** | The Operator | File operations, batch processing, automation, vault maintenance | **Local Only** |

### Key Constraints

- **Hermes**: 100% local, never touches cloud. Handles sensitive data and personal information. Validates all Claude outputs before execution.
- **OpenClaw**: Direct file system access, batch processing, script execution. Bridge between AI reasoning and the physical vault.
- **Cloud trio** (Gemini, Kimi, Claude): Browser-based workflows, no local file access. Their outputs must be captured and saved by OpenClaw.

## Quick Commands

### Initialize Vault
```bash
# Run the vault initialization script
python3 scripts/init_vault.py --path ~/obsidian-vault --name "Cognitive Nexus"
```

### Run Full Pipeline
```bash
# Execute the complete industrial loop for a topic
python3 scripts/pipeline_orchestrator.py --topic "Quantum Computing 2024" --auto
```

### Nightly Batch
```bash
# Run the self-improvement batch
python3 scripts/nightly_batch.py --vault ~/obsidian-vault
```

### Resolve Conflicts
```bash
# Interactive conflict resolution
python3 scripts/conflict_resolver.py --vault ~/obsidian-vault
```

## Dashboard Components

### 00_NEXUS_DASHBOARD.md
The central control file. Uses Obsidian Dataview queries to show:
- **Live Ingestion Feed**: New files in `/inbox` awaiting AI processing
- **Conflict Radar**: Files in `/conflicts/` requiring intervention
- **Agent Status**: Active/pending tasks per agent
- **Project Topology**: Active projects with status

### NEXUS_MAP.canvas
Visual canvas mapping:
- Active projects → their live data outputs
- Agent dependencies and data flows
- Knowledge node connections

## Workflow Details

For detailed orchestration workflows, see [references/orchestration_workflow.md](references/orchestration_workflow.md).

For agent role specifications and prompts, see [references/agent_roles.md](references/agent_roles.md).

For vault structure and YAML metadata schemas, see [references/vault_structure.md](references/vault_structure.md).

For dashboard setup with Dataview queries and Canvas configuration, see [references/dashboard_setup.md](references/dashboard_setup.md).

## Nightly Self-Improving Loop

Every night at 02:00 (configurable), OpenClaw executes:
1. **Vault Scan**: Identify orphan notes (no backlinks)
2. **Hermes Analysis**: Analyze orphans for potential connections
3. **Dashboard Update**: Propose connections in 00_NEXUS_DASHBOARD.md
4. **Inbox Cleanup**: Archive processed `/inbox` items to `/daily/`
5. **AI Output Archive**: Move old `/ai_outputs/` to archive
6. **Conflict Report**: Summarize unresolved conflicts

## Usage Patterns

### Pattern 1: Research Pipeline
User: "Research quantum computing breakthroughs and build a knowledge base"
1. Ingest topic to `/inbox/`
2. Gemini scouts web sources
3. Kimi compresses findings
4. Claude synthesizes strategy
5. Hermes validates locally
6. OpenClaw writes to `/knowledge/`

### Pattern 2: Conflict Resolution
User: "Hermes rejected Claude's plan — help me resolve it"
1. OpenClaw detects conflict in `/conflicts/`
2. Presents both viewpoints with Hermes critique
3. User or Hermes makes final call
4. OpenClaw archives the resolution in `/decisions/`

### Pattern 3: Project Bootstrap
User: "Start a new project for AI trading bot development"
1. OpenClaw creates `/projects/ai-trading-bot/` structure
2. Sets up `README.md` with YAML metadata
3. Links to relevant `/knowledge/` nodes
4. Dashboard auto-updates project topology

### Pattern 4: Knowledge Retrieval
User: "What do we know about Solana DEX aggregators?"
1. OpenClaw queries `/knowledge/` backlinks
2. Presents connected nodes with metadata
3. Shows decision history in `/decisions/`
4. Highlights conflicts if any exist

## Scripts Reference

- `scripts/init_vault.py` — Bootstrap the vault structure with all folders and templates
- `scripts/pipeline_orchestrator.py` — Run the full industrial loop or a specific stage
- `scripts/nightly_batch.py` — Self-improving batch: orphan detection, cleanup, archiving
- `scripts/conflict_resolver.py` — Interactive conflict resolution with Hermes
- `scripts/vault_health.py` — Diagnostic: broken links, orphan notes, missing metadata
- `scripts/backup_vault.py` — Archive old files, create compressed snapshots

## Assets Reference

- `assets/templates/` — Obsidian note templates for each vault section
- `assets/queries/` — Pre-built Dataview queries for the dashboard
- `assets/canvas/` — Canvas templates for project topology maps

## Integration with OpenClaw

This skill is designed to work with OpenClaw as the Operator agent. OpenClaw has direct access to:
- File system operations (create, move, update, archive)
- Script execution (Python, PowerShell, Bash)
- Obsidian plugin integration (Dataview, Canvas, Shell Commands)
- Local LLM runtime management (Hermes)

## Setup Requirements

- **Obsidian**: Latest version with plugins: Dataview, Canvas, Shell Commands, Smart Connections
- **Python**: 3.9+ for local scripts
- **Hermes**: Local LLM runtime (Ollama, llama.cpp, or similar)
- **OpenClaw**: Running with file system access to the vault directory
- **Browser**: For cloud agent workflows (Gemini, Kimi, Claude)
