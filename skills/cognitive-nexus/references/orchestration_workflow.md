# Cognitive Nexus Orchestration Workflow

## The Industrial Loop (Detailed)

### Phase 1: Ingestion (System/OpenClaw)

**Trigger**: User input, automated webhook, or scheduled task

**Actions**:
1. Create task file in `/inbox/` with YAML metadata
2. Assign unique `task_id` (timestamp-based: `YYYYMMDD_HHMMSS`)
3. Set initial status: `pending`
4. Update dashboard with new ingestion

**Output**: `/inbox/task_{task_id}.md`

---

### Phase 2: Scouting (Gemini)

**Trigger**: Task file created in `/inbox/`

**Input**: `/inbox/task_{task_id}.md`

**Actions** (Browser-based):
1. Read topic from task file
2. Search web for latest information
3. Collect raw data from multiple sources
4. Verify external links and sources
5. Identify trends and patterns

**Output**: `/ai_outputs/gemini/{task_id}_gemini_research.md`

**Content Requirements**:
- Raw data with source URLs
- Trend identification
- Multi-source verification
- Structured findings

---

### Phase 3: Compression (Kimi)

**Trigger**: Gemini output saved to `/ai_outputs/gemini/`

**Input**: `/ai_outputs/gemini/{task_id}_gemini_research.md`

**Actions** (Browser-based):
1. Read Gemini research output
2. Extract structured bullet points
3. Remove noise and fluff
4. Preserve key facts and sources
5. Output as JSON or structured Markdown

**Output**: `/ai_outputs/kimi/{task_id}_kimi_extract.md`

**Content Requirements**:
- Structured bullet points
- JSON-ready data
- Noise removal confirmation
- Source preservation

---

### Phase 4: Synthesis (Claude)

**Trigger**: Kimi output saved to `/ai_outputs/kimi/`

**Input**: `/ai_outputs/kimi/{task_id}_kimi_extract.md`

**Actions** (Browser-based):
1. Read Kimi compressed data
2. Synthesize into coherent strategy
3. Create complex strategic documentation
4. Include decision points with rationale
5. Write final, polished output

**Output**: `/ai_outputs/claude/{task_id}_claude_synthesis.md`

**Content Requirements**:
- Strategic plan with clear sections
- Decision points table (Decision | Rationale | Alternatives | Risk)
- Documentation with clear structure
- Actionable recommendations

---

### Phase 5: Validation (Hermes)

**Trigger**: Claude output saved to `/ai_outputs/claude/`

**Input**: `/ai_outputs/claude/{task_id}_claude_synthesis.md`

**Actions** (Local LLM - 100% local):
1. Read Claude synthesis
2. Act as Devil's Advocate
3. Check for logical gaps
4. Check for security flaws
5. Check for bias and unsupported assumptions
6. Check for factual errors
7. Check for missing edge cases

**Output**: `/conflicts/hermes-vs-claude/{task_id}_hermes_validation.md`

**Decision**: APPROVED or REJECTED

**If APPROVED**: Proceed to Execution
**If REJECTED**: Move to `/conflicts/` for human resolution

**Content Requirements**:
- Detailed critique
- Issues table (Issue | Severity | Location | Recommendation)
- Verdict with rationale
- Next steps

---

### Phase 6: Execution (OpenClaw)

**Trigger**: Hermes validation = APPROVED

**Input**: `/conflicts/hermes-vs-claude/{task_id}_hermes_validation.md` (APPROVED)

**Actions** (File system - 100% local):
1. Read all approved outputs
2. Merge content into knowledge file
3. Create backlinks to related knowledge
4. Update task status to `processed`
5. Move task to `/daily/` log
6. Archive AI outputs
7. Update dashboard

**Output**: `/knowledge/{topic}_{task_id}.md`

**Content Requirements**:
- Validated knowledge with metadata
- Backlinks to related nodes
- Decision history
- Source preservation
- Validation record

---

## Pipeline Control Flow

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Ingestion│───▶│ Scouting │───▶│Compression│───▶│Synthesis │───▶│Validation│───▶│Execution │
│ (System) │    │ (Gemini) │    │ (Kimi)   │    │ (Claude) │    │ (Hermes) │    │(OpenClaw)│
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └────┬─────┘    └──────────┘
                                                                       │
                                                              ┌────────▼────────┐
                                                              │   REJECTED      │
                                                              │  (→ /conflicts/)│
                                                              └─────────────────┘
```

## Error Handling

### Stage Failure Protocol

1. **Ingestion Failure**: Log error, retry with different parameters
2. **Scouting Failure**: Use cached data if available, or skip to next topic
3. **Compression Failure**: Pass raw Gemini output directly to Claude
4. **Synthesis Failure**: Use Kimi output as-is, mark as "raw"
5. **Validation Failure**: Always move to `/conflicts/`, never skip
6. **Execution Failure**: Log error, retry with backup methods

### Conflict Resolution Hierarchy

1. **Hermes critique** (primary filter)
2. **Human override** (if Hermes and human disagree)
3. **Vote system** (if multiple humans involved)
4. **Escalation** to `/conflicts/multi-agent/`

## Batch Processing

### Full Pipeline (Default)
```bash
python3 scripts/pipeline_orchestrator.py --topic "Quantum Computing 2024"
```

### Single Stage
```bash
python3 scripts/pipeline_orchestrator.py --topic "Quantum Computing 2024" --stage scouting
```

### Auto Mode (No prompts)
```bash
python3 scripts/pipeline_orchestrator.py --topic "Quantum Computing 2024" --auto
```

## Pipeline State Tracking

The pipeline state is tracked in:
- `/inbox/task_{task_id}.md` (task status)
- `/system/pipeline_results.json` (aggregate results)
- `/00_nexus/00_NEXUS_DASHBOARD.md` (dashboard updates)

## Monitoring

### Pipeline Health Checks
- Run `vault_health.py` to check for broken pipelines
- Check `/conflicts/` for unresolved rejections
- Monitor `/inbox/` for stale tasks (> 7 days)

### Performance Metrics
- Average time per stage
- Rejection rate (Hermes)
- Human override rate
- Knowledge production rate
