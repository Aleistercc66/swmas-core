#!/usr/bin/env python3
"""
Cognitive Nexus Conflict Resolver
Interactive resolution of conflicts between AI agents, with Hermes having veto power.
"""

import os
import json
import yaml
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple


def get_vault_path() -> Path:
    """Get vault path from environment or default."""
    return Path(os.environ.get("COGNITIVE_NEXUS_VAULT", "~/obsidian-vault/Cognitive-Nexus")).expanduser()


def list_conflicts(vault: Path) -> List[Dict]:
    """List all unresolved conflicts in the vault."""
    conflicts = []
    
    conflicts_dir = vault / "conflicts"
    if not conflicts_dir.exists():
        return conflicts
    
    for md_file in conflicts_dir.rglob("*.md"):
        if "README" in str(md_file):
            continue
        
        content = md_file.read_text(encoding="utf-8")
        
        # Extract metadata
        metadata = {}
        if content.startswith("---"):
            try:
                _, yaml_part, _ = content.split("---", 2)
                metadata = yaml.safe_load(yaml_part) or {}
            except:
                pass
        
        resolution_status = metadata.get("resolution_status", "pending")
        
        if resolution_status != "resolved":
            conflicts.append({
                "file": str(md_file.relative_to(vault)),
                "title": metadata.get("title", md_file.stem),
                "agents": metadata.get("agents_involved", "unknown"),
                "type": metadata.get("conflict_type", "unknown"),
                "severity": metadata.get("severity", "medium"),
                "status": resolution_status,
                "path": md_file
            })
    
    # Sort by severity (critical > high > medium > low)
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "pending": 4}
    conflicts.sort(key=lambda x: severity_order.get(x["severity"], 5))
    
    return conflicts


def show_conflict(conflict: Dict) -> None:
    """Display a conflict for review."""
    print(f"\n{'='*60}")
    print(f"⚠️  CONFLICT: {conflict['title']}")
    print(f"{'='*60}")
    print(f"📁 File: {conflict['file']}")
    print(f"🤖 Agents: {conflict['agents']}")
    print(f"📊 Type: {conflict['type']}")
    print(f"🔥 Severity: {conflict['severity'].upper()}")
    print(f"⏳ Status: {conflict['status']}")
    print(f"\n{'-'*60}")
    
    content = conflict['path'].read_text(encoding="utf-8")
    
    # Show content after frontmatter
    if "---" in content:
        parts = content.split("---")
        if len(parts) >= 3:
            body = parts[2].strip()
            print(body[:1000])  # Show first 1000 chars
            if len(body) > 1000:
                print(f"\n... ({len(body) - 1000} more characters)")


def resolve_conflict(conflict: Dict, resolution: str, rationale: str) -> bool:
    """Resolve a conflict with a decision."""
    try:
        content = conflict['path'].read_text(encoding="utf-8")
        
        # Update metadata
        if content.startswith("---"):
            try:
                _, yaml_part, body = content.split("---", 2)
                metadata = yaml.safe_load(yaml_part) or {}
                
                metadata["resolution_status"] = "resolved"
                metadata["resolution_method"] = resolution
                metadata["resolution_rationale"] = rationale
                metadata["resolution_date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                metadata["resolution_by"] = "human" if resolution == "human_override" else "hermes"
                
                new_yaml = yaml.dump(metadata, allow_unicode=True, sort_keys=False)
                new_content = f"---\n{new_yaml}---{body}"
                
                conflict['path'].write_text(new_content, encoding="utf-8")
                
                # Move to decisions folder
                decisions_dir = Path(conflict['path']).parent.parent / ".." / "decisions" / "approved"
                decisions_dir = decisions_dir.resolve()
                decisions_dir.mkdir(parents=True, exist_ok=True)
                
                decision_file = decisions_dir / f"resolution_{conflict['path'].stem}.md"
                
                decision_content = f"""---
title: "Conflict Resolution: {conflict['title']}"
type: decision
status: approved
decision_type: conflict_resolution
original_conflict: "{conflict['file']}"
agents_involved: "{conflict['agents']}"
resolution_date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
resolution_by: "{'human' if resolution == 'human_override' else 'hermes'}"
---

# Conflict Resolution: {conflict['title']}

## Original Conflict

- **File**: `{conflict['file']}`
- **Agents**: {conflict['agents']}
- **Type**: {conflict['type']}
- **Severity**: {conflict['severity']}

## Resolution

**Method**: {resolution}

**Rationale**:

{rationale}

## Decision

- **Date**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- **Decided by**: {'Human override' if resolution == 'human_override' else 'Hermes validation'}
- **Status**: ✅ APPROVED

## Consequences

<!-- Document the impact of this resolution -->

## Related Decisions

<!-- Link to related decisions -->
"""
                
                decision_file.write_text(decision_content, encoding="utf-8")
                
                print(f"\n✅ Conflict resolved!")
                print(f"📄 Decision saved: {decision_file}")
                
                return True
                
            except Exception as e:
                print(f"❌ Error parsing metadata: {e}")
                return False
    except Exception as e:
        print(f"❌ Error resolving conflict: {e}")
        return False


def interactive_resolution(vault: Path) -> None:
    """Interactive conflict resolution session."""
    conflicts = list_conflicts(vault)
    
    if not conflicts:
        print(f"\n✅ No unresolved conflicts found!")
        print(f"   The system is in harmony. 🧘")
        return
    
    print(f"\n⚠️  {len(conflicts)} UNRESOLVED CONFLICTS FOUND")
    print(f"{'='*60}")
    
    for i, conflict in enumerate(conflicts, 1):
        print(f"\n[{i}/{len(conflicts)}] {conflict['title']}")
        print(f"     Severity: {conflict['severity'].upper()} | Agents: {conflict['agents']}")
    
    print(f"\n{'='*60}")
    
    for i, conflict in enumerate(conflicts, 1):
        show_conflict(conflict)
        
        print(f"\n{'='*60}")
        print(f"RESOLUTION OPTIONS:")
        print(f"  [1] Approve Hermes critique (reject original)")
        print(f"  [2] Override Hermes (approve original)")
        print(f"  [3] Compromise (merge both perspectives)")
        print(f"  [4] Escalate (multi-agent review)")
        print(f"  [5] Skip (keep unresolved)")
        print(f"{'='*60}")
        
        choice = input(f"\nConflict [{i}/{len(conflicts)}] — Choose resolution (1-5): ").strip()
        
        if choice == "1":
            rationale = input("Rationale for accepting Hermes: ").strip()
            resolve_conflict(conflict, "hermes_approved", rationale)
        elif choice == "2":
            rationale = input("Rationale for overriding Hermes: ").strip()
            resolve_conflict(conflict, "human_override", rationale)
        elif choice == "3":
            rationale = input("Describe the compromise: ").strip()
            resolve_conflict(conflict, "compromise", rationale)
        elif choice == "4":
            rationale = input("Escalation reason: ").strip()
            # Move to multi-agent
            multi_dir = vault / "conflicts" / "multi-agent"
            multi_dir.mkdir(parents=True, exist_ok=True)
            new_path = multi_dir / conflict['path'].name
            conflict['path'].rename(new_path)
            print(f"   Escalated to: {new_path}")
        elif choice == "5":
            print(f"   Skipped (remains unresolved)")
        else:
            print(f"   Invalid choice, skipping...")


def auto_resolve(vault: Path) -> None:
    """Auto-resolve all low-severity conflicts (Hermes wins)."""
    conflicts = list_conflicts(vault)
    
    low_severity = [c for c in conflicts if c['severity'] in ['low', 'medium']]
    
    if not low_severity:
        print(f"\n✅ No auto-resolvable conflicts found")
        return
    
    print(f"\n🤖 AUTO-RESOLVING {len(low_severity)} LOW/MEDIUM CONFLICTS")
    
    for conflict in low_severity:
        print(f"   Resolving: {conflict['title']}...")
        resolve_conflict(
            conflict,
            "hermes_approved",
            "Auto-resolved: Hermes critique accepted for low/medium severity conflict"
        )
    
    print(f"\n✅ Auto-resolved {len(low_severity)} conflicts")


def generate_conflict_report(vault: Path) -> str:
    """Generate a comprehensive conflict report."""
    conflicts = list_conflicts(vault)
    
    report_file = vault / "00_nexus" / "conflict_report.md"
    
    content = f"""---
title: "Conflict Report"
type: dashboard
status: active
updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
---

# ⚠️ Conflict Report

**Generated**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Summary

| Status | Count |
|--------|-------|
| Critical | {len([c for c in conflicts if c['severity'] == 'critical'])} |
| High | {len([c for c in conflicts if c['severity'] == 'high'])} |
| Medium | {len([c for c in conflicts if c['severity'] == 'medium'])} |
| Low | {len([c for c in conflicts if c['severity'] == 'low'])} |
| **Total Unresolved** | **{len(conflicts)}** |

## Unresolved Conflicts

"""
    
    for conflict in conflicts:
        content += f"""### {conflict['title']}

- **File**: `{conflict['file']}`
- **Agents**: {conflict['agents']}
- **Type**: {conflict['type']}
- **Severity**: {conflict['severity']}
- **Status**: {conflict['status']}

"""
    
    content += f"""
## Resolution Actions

```shell
# Interactive resolution
python3 scripts/conflict_resolver.py --interactive

# Auto-resolve low/medium
python3 scripts/conflict_resolver.py --auto

# Show details
python3 scripts/conflict_resolver.py --show {conflicts[0]['file'] if conflicts else 'none'}
```

## Resolution History

<!-- Link to /decisions/ for past resolutions -->
"""
    
    report_file.write_text(content, encoding="utf-8")
    
    return str(report_file)


def main():
    parser = argparse.ArgumentParser(description="Cognitive Nexus Conflict Resolver")
    parser.add_argument("--vault", help="Vault path (default: env COGNITIVE_NEXUS_VAULT)")
    parser.add_argument("--interactive", action="store_true", help="Interactive resolution mode")
    parser.add_argument("--auto", action="store_true", help="Auto-resolve low/medium conflicts")
    parser.add_argument("--show", help="Show details of a specific conflict file")
    parser.add_argument("--report", action="store_true", help="Generate conflict report")
    args = parser.parse_args()
    
    vault = Path(args.vault).expanduser() if args.vault else get_vault_path()
    
    if not vault.exists():
        print(f"❌ Vault not found: {vault}")
        sys.exit(1)
    
    if args.show:
        # Show specific conflict
        conflict_path = vault / args.show
        if conflict_path.exists():
            conflict = {
                "file": args.show,
                "title": conflict_path.stem,
                "agents": "unknown",
                "type": "unknown",
                "severity": "unknown",
                "status": "pending",
                "path": conflict_path
            }
            show_conflict(conflict)
        else:
            print(f"❌ Conflict file not found: {args.show}")
    elif args.interactive:
        interactive_resolution(vault)
    elif args.auto:
        auto_resolve(vault)
    elif args.report:
        report = generate_conflict_report(vault)
        print(f"📄 Report generated: {report}")
    else:
        # Default: list conflicts
        conflicts = list_conflicts(vault)
        
        if not conflicts:
            print(f"\n✅ No unresolved conflicts! The system is in harmony.")
        else:
            print(f"\n⚠️  {len(conflicts)} UNRESOLVED CONFLICTS:")
            print(f"{'='*60}")
            for conflict in conflicts:
                print(f"  [{conflict['severity'].upper():^8}] {conflict['title']}")
                print(f"           Agents: {conflict['agents']} | Type: {conflict['type']}")
            print(f"{'='*60}")
            print(f"\nRun with --interactive to resolve")
            print(f"Run with --auto to auto-resolve low/medium")


if __name__ == "__main__":
    import sys
    main()
