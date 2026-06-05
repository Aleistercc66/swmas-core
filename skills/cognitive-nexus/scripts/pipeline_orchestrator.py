#!/usr/bin/env python3
"""
Cognitive Nexus Pipeline Orchestrator
Runs the full industrial loop: Ingestion → Scouting → Compression → Synthesis → Validation → Execution
"""

import os
import sys
import json
import yaml
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

PIPELINE_STAGES = [
    "ingestion",
    "scouting",
    "compression",
    "synthesis",
    "validation",
    "execution"
]

AGENT_MAP = {
    "scouting": "gemini",
    "compression": "kimi",
    "synthesis": "claude",
    "validation": "hermes",
    "execution": "openclaw"
}

OUTPUT_MAP = {
    "scouting": "ai_outputs/gemini",
    "compression": "ai_outputs/kimi",
    "synthesis": "ai_outputs/claude",
    "validation": "conflicts/hermes-vs-claude",
    "execution": "knowledge"
}


def get_vault_path() -> Path:
    """Get vault path from environment or default."""
    return Path(os.environ.get("COGNITIVE_NEXUS_VAULT", "~/obsidian-vault/Cognitive-Nexus")).expanduser()


def create_task_file(vault: Path, topic: str, task_id: str) -> Path:
    """Create a task tracking file in inbox."""
    task_file = vault / "inbox" / f"task_{task_id}.md"
    
    content = f"""---
title: "Task: {topic}"
type: task
status: pending
priority: normal
topic: "{topic}"
task_id: "{task_id}"
created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
agent: "system"
stage: "ingestion"
---

# Task: {topic}

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

- **Topic**: {topic}
- **Task ID**: {task_id}
- **Received**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

"""
    
    task_file.write_text(content, encoding="utf-8")
    return task_file


def stage_ingestion(vault: Path, topic: str, task_id: str) -> Tuple[bool, str]:
    """Stage 1: Ingestion — Create task file and initial metadata."""
    print(f"🔄 [Stage 1/6] INGESTION: '{topic}'")
    
    try:
        task_file = create_task_file(vault, topic, task_id)
        
        # Update task status
        update_task_status(task_file, "ingestion", "complete")
        
        print(f"   ✅ Task created: {task_file}")
        return True, str(task_file)
    except Exception as e:
        print(f"   ❌ Ingestion failed: {e}")
        return False, str(e)


def stage_scouting(vault: Path, topic: str, task_id: str) -> Tuple[bool, str]:
    """Stage 2: Scouting — Gemini research and raw data collection."""
    print(f"🔄 [Stage 2/6] SCOUTING (Gemini): '{topic}'")
    
    output_dir = vault / "ai_outputs" / "gemini"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"{task_id}_gemini_research.md"
    
    content = f"""---
title: "Gemini Research: {topic}"
type: ai_output
agent: gemini
stage: scouting
task_id: "{task_id}"
topic: "{topic}"
status: complete
output_date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
source: "web_research"
---

# Gemini Research: {topic}

## Research Instructions

1. Search web for latest information on: **{topic}**
2. Collect raw data from multiple sources
3. Identify trends and verify external links
4. Output structured findings with source URLs

## Raw Data Collection

<!-- Gemini fills this section with research findings -->

## Sources

<!-- List all sources with URLs -->

## Next Steps

- Pass to Kimi for compression and extraction
- File: {output_file}

"""
    
    output_file.write_text(content, encoding="utf-8")
    
    print(f"   ✅ Gemini research template created: {output_file}")
    print(f"   📝 Action: Open Gemini in browser, paste topic, save results to this file")
    
    return True, str(output_file)


def stage_compression(vault: Path, topic: str, task_id: str) -> Tuple[bool, str]:
    """Stage 3: Compression — Kimi extraction and structuring."""
    print(f"🔄 [Stage 3/6] COMPRESSION (Kimi): '{topic}'")
    
    output_dir = vault / "ai_outputs" / "kimi"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"{task_id}_kimi_extract.md"
    
    content = f"""---
title: "Kimi Extract: {topic}"
type: ai_output
agent: kimi
stage: compression
task_id: "{task_id}"
topic: "{topic}"
status: pending
output_date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
source: "gemini_output"
---

# Kimi Extract: {topic}

## Compression Instructions

1. Read Gemini research from: `ai_outputs/gemini/{task_id}_gemini_research.md`
2. Extract structured bullet points from raw data
3. Remove noise and fluff
4. Output as JSON or structured Markdown
5. Preserve all key facts and sources

## Extracted Data

<!-- Kimi fills this section with compressed, structured data -->

## Structured Output

```json
{{
  "topic": "{topic}",
  "key_findings": [],
  "sources": [],
  "trends": [],
  "data_quality": "high|medium|low"
}}
```

## Next Steps

- Pass to Claude for synthesis and strategy
- File: {output_file}

"""
    
    output_file.write_text(content, encoding="utf-8")
    
    print(f"   ✅ Kimi extraction template created: {output_file}")
    print(f"   📝 Action: Open Kimi in browser, paste Gemini output, save extracted data")
    
    return True, str(output_file)


def stage_synthesis(vault: Path, topic: str, task_id: str) -> Tuple[bool, str]:
    """Stage 4: Synthesis — Claude strategy and documentation."""
    print(f"🔄 [Stage 4/6] SYNTHESIS (Claude): '{topic}'")
    
    output_dir = vault / "ai_outputs" / "claude"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"{task_id}_claude_synthesis.md"
    
    content = f"""---
title: "Claude Synthesis: {topic}"
type: ai_output
agent: claude
stage: synthesis
task_id: "{task_id}"
topic: "{topic}"
status: pending
output_date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
source: "kimi_extract"
---

# Claude Synthesis: {topic}

## Synthesis Instructions

1. Read Kimi extraction from: `ai_outputs/kimi/{task_id}_kimi_extract.md`
2. Synthesize findings into a coherent strategy or plan
3. Create complex strategic documentation
4. Include decision points with rationale
5. Write the final, polished output

## Strategic Plan

<!-- Claude fills this section with the synthesized strategy -->

## Decision Points

| Decision | Rationale | Alternatives | Risk Level |
|----------|-----------|--------------|------------|
| <!-- Decision 1 --> | | | |
| <!-- Decision 2 --> | | | |

## Documentation

<!-- Claude writes the final documentation here -->

## Next Steps

- Pass to Hermes for validation
- File: {output_file}

"""
    
    output_file.write_text(content, encoding="utf-8")
    
    print(f"   ✅ Claude synthesis template created: {output_file}")
    print(f"   📝 Action: Open Claude in browser, paste Kimi output, save synthesis")
    
    return True, str(output_file)


def stage_validation(vault: Path, topic: str, task_id: str) -> Tuple[bool, str]:
    """Stage 5: Validation — Hermes red teaming and critique."""
    print(f"🔄 [Stage 5/6] VALIDATION (Hermes): '{topic}'")
    
    output_dir = vault / "conflicts" / "hermes-vs-claude"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"{task_id}_hermes_validation.md"
    
    content = f"""---
title: "Hermes Validation: {topic}"
type: conflict
agent: hermes
stage: validation
task_id: "{task_id}"
topic: "{topic}"
status: pending
validation_date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
source: "claude_synthesis"
severity: "pending"
---

# Hermes Validation: {topic}

## Validation Instructions (Hermes — Local Only)

1. Read Claude synthesis from: `ai_outputs/claude/{task_id}_claude_synthesis.md`
2. Act as Devil's Advocate — find all flaws
3. Check for:
   - Logical gaps and inconsistencies
   - Security flaws and vulnerabilities
   - Bias and unsupported assumptions
   - Factual errors
   - Missing edge cases
4. Output: APPROVED or REJECTED with detailed critique

## Validation Report

### Critique

<!-- Hermes fills this with detailed critique -->

### Findings

| Issue | Severity | Location | Recommendation |
|-------|----------|----------|----------------|
| <!-- Issue 1 --> | critical|high|medium|low | | |

### Verdict

**Status**: `PENDING` → `APPROVED` or `REJECTED`

**Rationale**:

<!-- Hermes explains the verdict -->

## Next Steps

- If APPROVED: Pass to OpenClaw for execution
- If REJECTED: Move to `/conflicts/` for human resolution
- File: {output_file}

"""
    
    output_file.write_text(content, encoding="utf-8")
    
    print(f"   ✅ Hermes validation template created: {output_file}")
    print(f"   📝 Action: Run Hermes locally, paste Claude output, execute validation")
    
    return True, str(output_file)


def stage_execution(vault: Path, topic: str, task_id: str) -> Tuple[bool, str]:
    """Stage 6: Execution — OpenClaw file operations and vault update."""
    print(f"🔄 [Stage 6/6] EXECUTION (OpenClaw): '{topic}'")
    
    output_dir = vault / "knowledge"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a sanitized filename
    safe_topic = "".join(c if c.isalnum() or c in "-_ " else "_" for c in topic).replace(" ", "_")
    output_file = output_dir / f"{safe_topic}_{task_id}.md"
    
    content = f"""---
title: "{topic}"
type: knowledge
status: active
validated: true
validation_date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
validated_by: "hermes"
task_id: "{task_id}"
source: "claude_synthesis"
backlinks: []
---

# {topic}

## Overview

<!-- OpenClaw merges validated content here -->

## Key Findings

<!-- Extracted from Kimi + Claude output -->

## Strategic Implications

<!-- From Claude synthesis -->

## Decisions

<!-- Link to /decisions/ records -->

## Sources

<!-- Preserved from Gemini research -->

## Validation

- **Validator**: Hermes
- **Date**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **Status**: ✅ APPROVED

## Related Knowledge

<!-- Backlinks to other knowledge nodes -->

"""
    
    output_file.write_text(content, encoding="utf-8")
    
    print(f"   ✅ Knowledge file created: {output_file}")
    print(f"   📝 Action: OpenClaw merges validated content into this file")
    
    return True, str(output_file)


def update_task_status(task_file: Path, stage: str, status: str) -> None:
    """Update the task file with current stage status."""
    content = task_file.read_text(encoding="utf-8")
    
    # Update stage in YAML
    content = content.replace(
        f"stage: \"{stage}\"",
        f"stage: \"{stage}\"\nstatus: {status}"
    )
    
    # Update checklist
    stage_display = stage.title()
    if status == "complete":
        content = content.replace(
            f"- [ ] {stage_display}",
            f"- [x] {stage_display} ✅"
        )
    
    task_file.write_text(content, encoding="utf-8")


def run_full_pipeline(vault: Path, topic: str, auto: bool = False) -> Dict:
    """Run the complete industrial loop."""
    task_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print(f"\n🏭 INDUSTRIAL LOOP STARTING")
    print(f"📋 Topic: {topic}")
    print(f"🆔 Task ID: {task_id}")
    print(f"=" * 60)
    
    results = {}
    
    # Stage 1: Ingestion
    success, result = stage_ingestion(vault, topic, task_id)
    results["ingestion"] = {"success": success, "file": result}
    if not success:
        print(f"\n❌ Pipeline halted at Ingestion")
        return results
    
    # Stage 2: Scouting
    success, result = stage_scouting(vault, topic, task_id)
    results["scouting"] = {"success": success, "file": result}
    if not success:
        print(f"\n❌ Pipeline halted at Scouting")
        return results
    
    # Stage 3: Compression
    success, result = stage_compression(vault, topic, task_id)
    results["compression"] = {"success": success, "file": result}
    if not success:
        print(f"\n❌ Pipeline halted at Compression")
        return results
    
    # Stage 4: Synthesis
    success, result = stage_synthesis(vault, topic, task_id)
    results["synthesis"] = {"success": success, "file": result}
    if not success:
        print(f"\n❌ Pipeline halted at Synthesis")
        return results
    
    # Stage 5: Validation
    success, result = stage_validation(vault, topic, task_id)
    results["validation"] = {"success": success, "file": result}
    if not success:
        print(f"\n❌ Pipeline halted at Validation")
        return results
    
    # Stage 6: Execution
    success, result = stage_execution(vault, topic, task_id)
    results["execution"] = {"success": success, "file": result}
    if not success:
        print(f"\n❌ Pipeline halted at Execution")
        return results
    
    print(f"\n" + "=" * 60)
    print(f"✅ PIPELINE COMPLETE")
    print(f"📁 Knowledge file: {result}")
    print(f"🎯 All stages executed successfully")
    
    return results


def run_single_stage(vault: Path, topic: str, stage: str) -> Dict:
    """Run a single pipeline stage."""
    task_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    stage_map = {
        "ingestion": stage_ingestion,
        "scouting": stage_scouting,
        "compression": stage_compression,
        "synthesis": stage_synthesis,
        "validation": stage_validation,
        "execution": stage_execution
    }
    
    if stage not in stage_map:
        print(f"❌ Unknown stage: {stage}")
        print(f"Available stages: {', '.join(PIPELINE_STAGES)}")
        return {}
    
    print(f"🔄 Running single stage: {stage.upper()}")
    success, result = stage_map[stage](vault, topic, task_id)
    
    return {stage: {"success": success, "file": result}}


def main():
    parser = argparse.ArgumentParser(description="Cognitive Nexus Pipeline Orchestrator")
    parser.add_argument("--topic", required=True, help="Topic to process through the pipeline")
    parser.add_argument("--stage", choices=PIPELINE_STAGES, help="Run a single stage only")
    parser.add_argument("--auto", action="store_true", help="Auto-mode (for automated runs)")
    parser.add_argument("--vault", help="Vault path (default: env COGNITIVE_NEXUS_VAULT)")
    args = parser.parse_args()
    
    vault = Path(args.vault).expanduser() if args.vault else get_vault_path()
    
    if not vault.exists():
        print(f"❌ Vault not found: {vault}")
        print(f"   Run: python3 init_vault.py --path {vault.parent}")
        sys.exit(1)
    
    if args.stage:
        results = run_single_stage(vault, args.topic, args.stage)
    else:
        results = run_full_pipeline(vault, args.topic, args.auto)
    
    # Save pipeline results
    results_file = vault / "system" / "pipeline_results.json"
    results_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump({
            "last_run": datetime.now().isoformat(),
            "topic": args.topic,
            "stage": args.stage or "full",
            "results": results
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n📊 Results saved: {results_file}")


if __name__ == "__main__":
    main()
