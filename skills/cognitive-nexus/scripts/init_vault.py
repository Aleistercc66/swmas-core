#!/usr/bin/env python3
"""
Cognitive Nexus Vault Initializer
Bootstraps the complete Obsidian vault structure with all folders, templates, and system files.
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

VAULT_SECTIONS = {
    "00_nexus": "Dashboard & System triggers — Neural Dashboard, Canvas maps, system controls",
    "inbox": "Raw data & manual inputs awaiting AI processing",
    "daily": "Chronological logging — daily entries, session logs",
    "projects": "Active projects with live data and active workflows",
    "knowledge": "Validated, processed knowledge — the source of truth",
    "decisions": "Decision records with full rationale and context",
    "ai_outputs": "Raw AI outputs before merge and validation",
    "conflicts": "Disagreements between AI agents requiring human/Hermes intervention",
    "system": "Prompts, scripts, system rules, and configuration"
}

SUBFOLDERS = {
    "projects": ["active", "archived", "templates"],
    "knowledge": ["concepts", "entities", "relationships", "sources"],
    "decisions": ["pending", "approved", "rejected", "superseded"],
    "ai_outputs": ["gemini", "kimi", "claude", "hermes", "openclaw"],
    "conflicts": ["hermes-vs-claude", "hermes-vs-kimi", "gemini-vs-claude", "multi-agent"],
    "system": ["prompts", "scripts", "rules", "config"],
    "inbox": ["manual", "automated", "urgent"]
}

DASHBOARD_TEMPLATE = """---
title: 00 — NEXUS DASHBOARD
type: dashboard
status: active
created: {date}
updated: {date}
---

# 🧠 COGNITIVE NEXUS DASHBOARD

> **System Status**: `ACTIVE`  
> **Last Update**: `{{date:YYYY-MM-DD HH:mm}}`  
> **Operator**: OpenClaw  
> **Local Oracle**: Hermes

---

## 🔴 LIVE INGESTION FEED

```dataview
TABLE
  file.ctime AS "Received",
  file.size AS "Size",
  status AS "Status",
  priority AS "Priority"
FROM "inbox"
WHERE status != "processed"
SORT priority DESC, file.ctime DESC
```

---

## ⚠️ CONFLICT RADAR

```dataview
TABLE
  file.mtime AS "Detected",
  conflict_type AS "Type",
  agents_involved AS "Agents",
  severity AS "Severity",
  resolution_status AS "Status"
FROM "conflicts"
WHERE resolution_status != "resolved"
SORT severity DESC, file.mtime DESC
```

---

## 🤖 AGENT STATUS BOARD

| Agent | Role | Status | Current Task | Pending Files |
|-------|------|--------|-------------|---------------|
| Gemini | 🕵️ Scout | {{gemini_status}} | {{gemini_task}} | {{gemini_pending}} |
| Kimi | 🗜️ Extractor | {{kimi_status}} | {{kimi_task}} | {{kimi_pending}} |
| Claude | 🏗️ Architect | {{claude_status}} | {{claude_task}} | {{claude_pending}} |
| Hermes | 🔮 Oracle | {{hermes_status}} | {{hermes_task}} | {{hermes_pending}} |
| OpenClaw | ⚙️ Operator | {{openclaw_status}} | {{openclaw_task}} | {{openclaw_pending}} |

---

## 📊 PROJECT TOPOLOGY

```dataview
TABLE
  status AS "Status",
  completion AS "Progress",
  priority AS "Priority",
  linked_notes AS "Connections"
FROM "projects"
WHERE status = "active"
SORT priority DESC, file.mtime DESC
```

---

## 🔄 SYSTEM TRIGGERS

```shell
# Run Full Pipeline
# /cmd full-pipeline

# Nightly Batch
# /cmd nightly-batch

# Resolve Conflicts
# /cmd resolve-conflicts

# Vault Health Check
# /cmd vault-health
```

---

## 📝 QUICK LOG

- **{{date:YYYY-MM-DD}}**: Dashboard initialized

"""

NEXUS_MAP_TEMPLATE = """{
  "nodes": [
    {"id": "dashboard", "x": 400, "y": 50, "width": 200, "height": 80, "type": "text", "text": "🧠 NEXUS DASHBOARD"},
    {"id": "inbox", "x": 100, "y": 200, "width": 150, "height": 60, "type": "file", "file": "inbox/README.md"},
    {"id": "gemini", "x": 300, "y": 200, "width": 120, "height": 60, "type": "text", "text": "🕵️ Gemini Scout"},
    {"id": "kimi", "x": 450, "y": 200, "width": 120, "height": 60, "type": "text", "text": "🗜️ Kimi Extractor"},
    {"id": "claude", "x": 600, "y": 200, "width": 120, "height": 60, "type": "text", "text": "🏗️ Claude Architect"},
    {"id": "hermes", "x": 750, "y": 200, "width": 120, "height": 60, "type": "text", "text": "🔮 Hermes Oracle"},
    {"id": "openclaw", "x": 900, "y": 200, "width": 120, "height": 60, "type": "text", "text": "⚙️ OpenClaw Operator"},
    {"id": "knowledge", "x": 600, "y": 350, "width": 150, "height": 60, "type": "file", "file": "knowledge/README.md"},
    {"id": "conflicts", "x": 750, "y": 350, "width": 150, "height": 60, "type": "file", "file": "conflicts/README.md"},
    {"id": "decisions", "x": 450, "y": 350, "width": 150, "height": 60, "type": "file", "file": "decisions/README.md"}
  ],
  "edges": [
    {"fromNode": "dashboard", "fromSide": "bottom", "toNode": "inbox", "toSide": "top"},
    {"fromNode": "inbox", "fromSide": "right", "toNode": "gemini", "toSide": "left"},
    {"fromNode": "gemini", "fromSide": "right", "toNode": "kimi", "toSide": "left"},
    {"fromNode": "kimi", "fromSide": "right", "toNode": "claude", "toSide": "left"},
    {"fromNode": "claude", "fromSide": "right", "toNode": "hermes", "toSide": "left"},
    {"fromNode": "hermes", "fromSide": "bottom", "toNode": "conflicts", "toSide": "top", "label": "REJECTED"},
    {"fromNode": "hermes", "fromSide": "right", "toNode": "openclaw", "toSide": "left", "label": "APPROVED"},
    {"fromNode": "openclaw", "fromSide": "bottom", "toNode": "knowledge", "toSide": "top"},
    {"fromNode": "claude", "fromSide": "bottom", "toNode": "decisions", "toSide": "top"}
  ]
}
"""

README_TEMPLATE = """---
title: {folder_name}
type: system-folder
status: active
created: {date}
updated: {date}
---

# {folder_name}

**Purpose**: {description}

**Contents**: {{folder_contents}}

**Rules**:
- {rule1}
- {rule2}
- {rule3}

"""

RULES_BY_FOLDER = {
    "inbox": [
        "Every file here must have a `status` field in YAML frontmatter",
        "Files are processed FIFO unless marked `priority: urgent`",
        "After processing, status changes to `processed` and file moves to `/ai_outputs/` or `/knowledge/`"
    ],
    "knowledge": [
        "Every file must have backlinks to related knowledge nodes",
        "Metadata must include `source`, `validation_date`, and `validated_by`",
        "No file here without passing through the full pipeline"
    ],
    "decisions": [
        "Every decision must have `rationale`, `alternatives_considered`, and `decision_maker`",
        "Status must be one of: pending, approved, rejected, superseded",
        "Superseded decisions must link to the replacing decision"
    ],
    "conflicts": [
        "Every conflict must specify `agents_involved`, `conflict_type`, and `severity`",
        "Resolution must include `resolution_status` and `resolution_method`",
        "Hermes has veto power over all cloud agent outputs"
    ],
    "ai_outputs": [
        "Files organized by agent subfolder",
        "Must include `agent`, `task_id`, and `output_date` in metadata",
        "Raw outputs are ephemeral — merged to knowledge or discarded after validation"
    ]
}

SYSTEM_RULES = """---
title: System Rules
type: system-rules
status: active
created: {date}
updated: {date}
---

# 🔒 COGNITIVE NEXUS SYSTEM RULES

## 1. IMMUTABILITY PRINCIPLE

The Obsidian vault is the **Single Source of Truth**. No data lives exclusively in AI memory. Every interaction produces a durable artifact.

## 2. ZERO-API POLICY

Reasoning layers (Hermes, OpenClaw) operate **without external API keys**. Cloud agents (Gemini, Kimi, Claude) use browser-based workflows only.

## 3. STRICT AGENT SEPARATION

| Agent | Scope | Data Access | Output Destination |
|-------|-------|-------------|-------------------|
| Gemini | Research | Web only | `/ai_outputs/gemini/` |
| Kimi | Compression | Web/Browser | `/ai_outputs/kimi/` |
| Claude | Synthesis | Web/Browser | `/ai_outputs/claude/` |
| Hermes | Validation | **Local only** | `/conflicts/` or `/decisions/` |
| OpenClaw | Execution | **File system** | `/knowledge/`, `/projects/` |

## 4. PIPELINE ENFORCEMENT

The industrial loop is **mandatory and linear**:
1. Ingestion → 2. Scouting → 3. Compression → 4. Synthesis → 5. Validation → 6. Execution

No skipping. No shortcuts. Hermes must validate before OpenClaw executes.

## 5. ARCHIVE OVER DELETE

**Never delete files.** The system archives:
- Processed `/inbox/` items → `/daily/`
- Old `/ai_outputs/` → `/system/archive/`
- Superseded decisions → `/decisions/superseded/`

## 6. YAML MANDATORY METADATA

Every `.md` file must have YAML frontmatter with:
```yaml
---
title: "Note Title"
type: [inbox|knowledge|decision|conflict|project|system]
status: [active|pending|processed|archived|superseded]
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

## 7. BACKLINK MANDATORY

Every knowledge node must link to at least one other node. Orphan notes are flagged by the nightly batch.

## 8. CONFLICT RESOLUTION HIERARCHY

1. Hermes critique (primary filter)
2. Human override (if Hermes and human disagree)
3. Vote system (if multiple humans involved)
4. Escalation to `/conflicts/multi-agent/`

## 9. DAILY RISK LIMIT

OpenClaw can modify at most **10% of vault files** in a single day without explicit human approval.

## 10. SELF-IMPROVEMENT LOOP

Every night at 02:00, the system:
1. Scans for orphans
2. Proposes connections via Hermes
3. Archives old data
4. Updates dashboard
5. Reports conflicts
"""


def create_vault(vault_path: str, vault_name: str) -> None:
    """Create the complete vault structure."""
    vault = Path(vault_path) / vault_name
    vault.mkdir(parents=True, exist_ok=True)
    
    date = datetime.now().strftime("%Y-%m-%d")
    
    # Create main folders
    for folder, description in VAULT_SECTIONS.items():
        folder_path = vault / folder
        folder_path.mkdir(exist_ok=True)
        
        # Create subfolders
        if folder in SUBFOLDERS:
            for sub in SUBFOLDERS[folder]:
                (folder_path / sub).mkdir(exist_ok=True)
        
        # Create README.md for each folder
        rules = RULES_BY_FOLDER.get(folder, [
            "Files must have YAML frontmatter",
            "Use backlinks for connections",
            "Archive, never delete"
        ])
        
        readme = README_TEMPLATE.format(
            folder_name=folder.replace("_", " ").title(),
            description=description,
            date=date,
            rule1=rules[0] if len(rules) > 0 else "Use YAML frontmatter",
            rule2=rules[1] if len(rules) > 1 else "Create backlinks",
            rule3=rules[2] if len(rules) > 2 else "Archive, never delete"
        )
        
        (folder_path / "README.md").write_text(readme, encoding="utf-8")
    
    # Create Dashboard
    dashboard = DASHBOARD_TEMPLATE.format(date=date)
    (vault / "00_nexus" / "00_NEXUS_DASHBOARD.md").write_text(dashboard, encoding="utf-8")
    
    # Create NEXUS_MAP.canvas
    (vault / "00_nexus" / "NEXUS_MAP.canvas").write_text(NEXUS_MAP_TEMPLATE, encoding="utf-8")
    
    # Create system rules
    system_rules = SYSTEM_RULES.format(date=date)
    (vault / "system" / "SYSTEM_RULES.md").write_text(system_rules, encoding="utf-8")
    
    # Create .obsidian folder with basic config
    obsidian = vault / ".obsidian"
    obsidian.mkdir(exist_ok=True)
    
    # Create community-plugins.json for Dataview and Canvas
    plugins_config = '{"enabledPlugins": ["dataview", "obsidian-shellcommands", "smart-connections"]}'
    (obsidian / "community-plugins.json").write_text(plugins_config, encoding="utf-8")
    
    # Create app.json for basic settings
    app_config = '{"alwaysUpdateLinks": true, "newLinkFormat": "relative", "useMarkdownLinks": true}'
    (obsidian / "app.json").write_text(app_config, encoding="utf-8")
    
    # Create a vault root README
    root_readme = f"""---
title: {vault_name}
type: vault-root
status: active
created: {date}
updated: {date}
---

# 🧠 {vault_name}

**Cognitive Nexus Multi-Agent Superbrain System**

This vault serves as the **Single Source of Truth** for a local AI-driven multi-agent orchestration system.

## Quick Start

1. Open `00_nexus/00_NEXUS_DASHBOARD.md` for the control center
2. Check `00_nexus/NEXUS_MAP.canvas` for the visual pipeline
3. Drop raw data into `inbox/` to trigger the industrial loop
4. Review `system/SYSTEM_RULES.md` for the non-negotiable rules

## The Pipeline

```
[inbox] → Gemini → Kimi → Claude → Hermes → OpenClaw → [knowledge]
                                     ↓
                               [conflicts] → human resolution
```

## Agents

- 🕵️ **Gemini**: The Scout — web research, raw data collection
- 🗜️ **Kimi**: The Extractor — compression, structured extraction
- 🏗️ **Claude**: The Architect — synthesis, strategy, documentation
- 🔮 **Hermes**: The Oracle — local validation, red teaming, Devil's Advocate
- ⚙️ **OpenClaw**: The Operator — file operations, automation, execution

## System Rules Summary

1. **Immutability**: Vault is the only source of truth
2. **Zero-API**: Local agents never use external APIs
3. **Strict Separation**: No overlapping agent roles
4. **Pipeline Enforcement**: Linear flow, no skipping
5. **Archive Over Delete**: Never delete, always archive
6. **YAML Mandatory**: Every file has metadata
7. **Backlinks Mandatory**: No orphan knowledge nodes
8. **Conflict Hierarchy**: Hermes → Human → Vote → Escalation
9. **Daily Risk Limit**: Max 10% vault modification per day
10. **Self-Improvement**: Nightly batch at 02:00

## System Status

{{dashboard_status}}

"""
    (vault / "README.md").write_text(root_readme, encoding="utf-8")
    
    print(f"✅ Vault created: {vault}")
    print(f"📁 Sections: {len(VAULT_SECTIONS)}")
    print(f"📂 Subfolders: {sum(len(v) for v in SUBFOLDERS.values())}")
    print(f"🧠 Dashboard: {vault / '00_nexus' / '00_NEXUS_DASHBOARD.md'}")
    print(f"🗺️  Canvas Map: {vault / '00_nexus' / 'NEXUS_MAP.canvas'}")
    print(f"\n🚀 Next steps:")
    print(f"   1. Open Obsidian → Open folder as vault → {vault}")
    print(f"   2. Install plugins: Dataview, Canvas, Shell Commands, Smart Connections")
    print(f"   3. Run: python3 pipeline_orchestrator.py --topic 'Your First Topic'")


def main():
    parser = argparse.ArgumentParser(description="Initialize Cognitive Nexus Obsidian Vault")
    parser.add_argument("--path", default="~/obsidian-vault", help="Parent directory for the vault")
    parser.add_argument("--name", default="Cognitive-Nexus", help="Vault folder name")
    args = parser.parse_args()
    
    vault_path = os.path.expanduser(args.path)
    create_vault(vault_path, args.name)


if __name__ == "__main__":
    main()
