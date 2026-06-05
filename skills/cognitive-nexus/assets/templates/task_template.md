---
title: "{{title}}"
type: task
status: pending
priority: normal
topic: "{{topic}}"
task_id: "{{task_id}}"
created: {{date}}
updated: {{date}}
agent: "system"
stage: "ingestion"
source: "manual"
---

# {{title}}

## Pipeline Status

- [ ] Ingestion (System)
- [ ] Scouting (Gemini)
- [ ] Compression (Kimi)
- [ ] Synthesis (Claude)
- [ ] Validation (Hermes)
- [ ] Execution (OpenClaw)

## Current Stage

**Ingestion**: Topic received and queued for processing.

## Notes

- **Topic**: {{topic}}
- **Task ID**: {{task_id}}
- **Received**: {{date}}
