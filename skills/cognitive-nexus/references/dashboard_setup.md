# Dashboard Setup Guide

## Required Obsidian Plugins

1. **Dataview** — Query and display vault data dynamically
2. **Canvas** — Visual node-based maps
3. **Shell Commands** — Execute system scripts from Obsidian
4. **Smart Connections** — AI-powered note connections (optional but recommended)

## Dashboard Structure

### 00_NEXUS_DASHBOARD.md

The central control panel. Uses Dataview queries to create live views.

#### Live Ingestion Feed

```markdown
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
```

#### Conflict Radar

```markdown
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
```

#### Agent Status Board

```markdown
## 🤖 AGENT STATUS BOARD

| Agent | Role | Status | Current Task | Pending Files |
|-------|------|--------|-------------|---------------|
| Gemini | 🕵️ Scout | Active | Web research: Solana | 3 |
| Kimi | 🗜️ Extractor | Idle | — | 0 |
| Claude | 🏗️ Architect | Busy | Strategy doc | 1 |
| Hermes | 🔮 Oracle | Pending | Validation queue | 2 |
| OpenClaw | ⚙️ Operator | Active | File ops | 5 |
```

#### Project Topology

```markdown
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
```

#### Knowledge Graph Summary

```markdown
## 🧠 KNOWLEDGE GRAPH

```dataview
TABLE
  file.mtime AS "Updated",
  validated_by AS "Validator",
  backlinks AS "Connections",
  tags AS "Tags"
FROM "knowledge"
WHERE status = "active"
SORT file.mtime DESC
LIMIT 20
```
```

#### Decision Log

```markdown
## 📋 RECENT DECISIONS

```dataview
TABLE
  decision_date AS "Date",
  decided_by AS "Decider",
  status AS "Status",
  decision_type AS "Type"
FROM "decisions"
SORT decision_date DESC
LIMIT 10
```
```

#### System Health

```markdown
## 🏥 SYSTEM HEALTH

```dataview
TABLE
  file.mtime AS "Last Check",
  health_score AS "Score"
FROM "daily"
WHERE type = "health-check"
SORT file.mtime DESC
LIMIT 1
```
```

## NEXUS_MAP.canvas

The visual pipeline map showing agent flow and dependencies.

### Canvas Structure

```json
{
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
```

## Shell Commands Integration

### System Triggers (via Shell Commands Plugin)

Add these commands to Obsidian's Shell Commands plugin:

#### Trigger Full Pipeline
```bash
Name: Run Full Pipeline
Command: python3 /path/to/scripts/pipeline_orchestrator.py --topic "$(prompt)" --auto
Shortcut: Ctrl+Shift+P
```

#### Trigger Nightly Batch
```bash
Name: Run Nightly Batch
Command: python3 /path/to/scripts/nightly_batch.py
Shortcut: Ctrl+Shift+N
```

#### Resolve Conflicts
```bash
Name: Resolve Conflicts
Command: python3 /path/to/scripts/conflict_resolver.py --interactive
Shortcut: Ctrl+Shift+C
```

#### Check Vault Health
```bash
Name: Vault Health Check
Command: python3 /path/to/scripts/vault_health.py --save
Shortcut: Ctrl+Shift+H
```

#### Initialize New Vault
```bash
Name: Initialize Vault
Command: python3 /path/to/scripts/init_vault.py --path ~/obsidian-vault
Shortcut: Ctrl+Shift+I
```

## Dataview Queries Collection

### Query 1: High Priority Inbox
```dataview
TABLE
  file.ctime AS "Received",
  topic AS "Topic",
  stage AS "Stage"
FROM "inbox"
WHERE priority = "urgent" AND status != "processed"
SORT file.ctime DESC
```

### Query 2: Knowledge by Tag
```dataview
TABLE
  title AS "Title",
  validated_by AS "Validator",
  file.mtime AS "Updated"
FROM "knowledge"
WHERE contains(tags, "solana")
SORT file.mtime DESC
```

### Query 3: Active Projects Progress
```dataview
TABLE
  title AS "Project",
  completion AS "Progress",
  priority AS "Priority",
  end_date AS "Deadline"
FROM "projects"
WHERE status = "active"
SORT completion DESC
```

### Query 4: Unresolved Critical Conflicts
```dataview
TABLE
  title AS "Conflict",
  agents_involved AS "Agents",
  file.mtime AS "Detected"
FROM "conflicts"
WHERE severity = "critical" AND resolution_status != "resolved"
SORT file.mtime DESC
```

### Query 5: Recent Decisions
```dataview
TABLE
  title AS "Decision",
  decided_by AS "Decided By",
  decision_type AS "Type",
  decision_date AS "Date"
FROM "decisions"
WHERE status = "approved"
SORT decision_date DESC
LIMIT 10
```

### Query 6: Orphan Notes (for nightly batch review)
```dataview
LIST
FROM "knowledge"
WHERE !backlinks
SORT file.mtime DESC
```

### Query 7: AI Output Status
```dataview
TABLE
  agent AS "Agent",
  stage AS "Stage",
  status AS "Status",
  output_date AS "Date"
FROM "ai_outputs"
WHERE status = "pending"
SORT output_date DESC
```

### Query 8: Daily Activity Summary
```dataview
TABLE
  file.mtime AS "Date",
  batch_count AS "Batches",
  conflicts_resolved AS "Resolved",
  knowledge_created AS "New Knowledge"
FROM "daily"
WHERE type = "daily"
SORT file.mtime DESC
LIMIT 7
```

## CSS Snippets (Optional)

Add to `.obsidian/snippets/nexus.css` for visual styling:

```css
/* Dashboard styling */
.dashboard-header {
  color: #ff6b6b;
  font-size: 1.5em;
  border-bottom: 2px solid #ff6b6b;
}

/* Status indicators */
.status-active { color: #51cf66; }
.status-pending { color: #ffd43b; }
.status-rejected { color: #ff6b6b; }
.status-archived { color: #868e96; }

/* Priority badges */
.priority-urgent { background: #ff6b6b; color: white; }
.priority-high { background: #ffd43b; color: black; }
.priority-normal { background: #74c0fc; color: black; }
.priority-low { background: #868e96; color: white; }
```

## Mobile Dashboard

For mobile access, create a simplified `00_MOBILE_DASHBOARD.md`:

```markdown
---
title: "Mobile Dashboard"
type: dashboard
status: active
---

# 📱 Mobile Nexus

## Quick Actions
- [[inbox/README.md|Inbox]] | [[conflicts/README.md|Conflicts]] | [[knowledge/README.md|Knowledge]]

## Urgent Tasks
```dataview
LIST
FROM "inbox"
WHERE priority = "urgent" AND status != "processed"
SORT file.ctime DESC
LIMIT 5
```

## Active Projects
```dataview
LIST
FROM "projects"
WHERE status = "active"
SORT priority DESC
LIMIT 5
```
```

## Dashboard Automation

The dashboard updates automatically via:
1. OpenClaw file operations (when executing pipeline)
2. Nightly batch (updates stats and proposals)
3. Manual refresh (Dataview auto-refreshes on file changes)

## Performance Tips

1. **Limit query results** — Use `LIMIT` to prevent slow loading
2. **Use indexes** — Dataview indexes improve with more queries
3. **Avoid deep nesting** — Flat queries are faster than nested
4. **Cache results** — Use `dataviewjs` for complex calculations
5. **Mobile optimization** — Simplified views for mobile devices
