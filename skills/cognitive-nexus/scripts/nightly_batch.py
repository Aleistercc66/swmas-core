#!/usr/bin/env python3
"""
Cognitive Nightly Batch - Self-Improving Loop
Runs every night at 02:00 to scan the vault, find orphans, propose connections, and archive old data.
"""

import os
import json
import yaml
import shutil
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Set, Tuple


def get_vault_path() -> Path:
    """Get vault path from environment or default."""
    return Path(os.environ.get("COGNITIVE_NEXUS_VAULT", "~/obsidian-vault/Cognitive-Nexus")).expanduser()


def find_orphan_notes(vault: Path) -> List[Path]:
    """Find all markdown files without any backlinks."""
    orphans = []
    
    for md_file in vault.rglob("*.md"):
        # Skip system files, READMEs, and templates
        if any(skip in str(md_file) for skip in [".obsidian", "README", "template"]):
            continue
        
        content = md_file.read_text(encoding="utf-8")
        
        # Check for backlinks (Wikilinks [[...]] or Markdown links [...](...))
        has_wikilinks = "[[" in content
        has_md_links = "][" in content or "](" in content
        
        if not has_wikilinks and not has_md_links:
            orphans.append(md_file)
    
    return orphans


def find_broken_links(vault: Path) -> List[Tuple[Path, str]]:
    """Find all wikilinks that point to non-existent files."""
    broken = []
    
    for md_file in vault.rglob("*.md"):
        if ".obsidian" in str(md_file):
            continue
        
        content = md_file.read_text(encoding="utf-8")
        
        # Find all wikilinks
        import re
        wikilinks = re.findall(r'\[\[(.*?)\]\]', content)
        
        for link in wikilinks:
            # Check if target exists
            target = vault / f"{link}.md"
            if not target.exists():
                broken.append((md_file, link))
    
    return broken


def find_missing_metadata(vault: Path) -> List[Path]:
    """Find files without YAML frontmatter."""
    missing = []
    
    for md_file in vault.rglob("*.md"):
        if ".obsidian" in str(md_file):
            continue
        
        content = md_file.read_text(encoding="utf-8")
        
        if not content.startswith("---"):
            missing.append(md_file)
    
    return missing


def archive_old_files(vault: Path, days: int = 30) -> Dict:
    """Archive old files from inbox and ai_outputs."""
    archive_dir = vault / "system" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    archived = {
        "inbox": [],
        "ai_outputs": []
    }
    
    cutoff = datetime.now() - timedelta(days=days)
    
    # Archive old inbox files (processed only)
    inbox = vault / "inbox"
    if inbox.exists():
        for md_file in inbox.rglob("*.md"):
            if md_file.stat().st_mtime < cutoff.timestamp():
                # Check if marked as processed
                content = md_file.read_text(encoding="utf-8")
                if "status: processed" in content or "status: archived" in content:
                    target = archive_dir / "inbox" / md_file.name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(md_file), str(target))
                    archived["inbox"].append(str(md_file))
    
    # Archive old AI outputs
    ai_outputs = vault / "ai_outputs"
    if ai_outputs.exists():
        for md_file in ai_outputs.rglob("*.md"):
            if md_file.stat().st_mtime < cutoff.timestamp():
                # Determine agent subfolder
                agent = md_file.parent.name
                target = archive_dir / "ai_outputs" / agent / md_file.name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(md_file), str(target))
                archived["ai_outputs"].append(str(md_file))
    
    return archived


def generate_hermes_proposals(vault: Path, orphans: List[Path]) -> str:
    """Generate Hermes analysis for orphan notes."""
    proposals = []
    
    for orphan in orphans:
        content = orphan.read_text(encoding="utf-8")
        
        # Extract title
        title = orphan.stem
        if content.startswith("---"):
            try:
                _, yaml_part, _ = content.split("---", 2)
                metadata = yaml.safe_load(yaml_part)
                title = metadata.get("title", title)
            except:
                pass
        
        # Find potential connections based on content similarity
        related = find_related_notes(vault, orphan, content)
        
        proposals.append({
            "file": str(orphan.relative_to(vault)),
            "title": title,
            "potential_connections": related[:5]  # Top 5
        })
    
    # Write proposals to dashboard
    proposals_file = vault / "00_nexus" / "nightly_proposals.md"
    
    content = f"""---
title: "Nightly Proposals"
type: system
status: active
created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
---

# 🌙 Nightly Proposals ({datetime.now().strftime("%Y-%m-%d")})

## Orphan Notes Found: {len(orphans)}

### Proposed Connections

"""
    
    for proposal in proposals:
        content += f"""#### {proposal['title']}

- **File**: `{proposal['file']}`
- **Suggested Connections**:
"""
        for related in proposal['potential_connections']:
            content += f"  - [[{related['file']}|{related['title']}]] (similarity: {related['score']:.2f})\n"
        
        content += "\n"
    
    content += f"""
## Actions Required

1. Review each proposal in Hermes
2. Accept or reject connections
3. Update orphan notes with approved backlinks
4. Run: `python3 scripts/conflict_resolver.py --vault {vault}`

## Next Nightly Batch

Scheduled: {(datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d 02:00:00")}
"""
    
    proposals_file.write_text(content, encoding="utf-8")
    
    return str(proposals_file)


def find_related_notes(vault: Path, target: Path, content: str) -> List[Dict]:
    """Find potentially related notes based on content similarity."""
    related = []
    
    # Extract keywords from target content (simple approach)
    import re
    words = set(re.findall(r'\b\w+\b', content.lower()))
    
    for md_file in vault.rglob("*.md"):
        if md_file == target or ".obsidian" in str(md_file):
            continue
        
        other_content = md_file.read_text(encoding="utf-8")
        other_words = set(re.findall(r'\b\w+\b', other_content.lower()))
        
        # Calculate Jaccard similarity
        intersection = words & other_words
        union = words | other_words
        
        if union:
            score = len(intersection) / len(union)
            if score > 0.1:  # Threshold
                title = md_file.stem
                if other_content.startswith("---"):
                    try:
                        _, yaml_part, _ = other_content.split("---", 2)
                        metadata = yaml.safe_load(yaml_part)
                        title = metadata.get("title", title)
                    except:
                        pass
                
                related.append({
                    "file": str(md_file.relative_to(vault)),
                    "title": title,
                    "score": score
                })
    
    # Sort by score descending
    related.sort(key=lambda x: x['score'], reverse=True)
    
    return related


def run_nightly_batch(vault: Path, days: int = 30) -> Dict:
    """Execute the full nightly batch."""
    print(f"\n🌙 NIGHTLY BATCH STARTING")
    print(f"📁 Vault: {vault}")
    print(f"=" * 60)
    
    results = {}
    
    # 1. Find orphans
    print(f"\n🔍 Scanning for orphan notes...")
    orphans = find_orphan_notes(vault)
    results["orphans"] = {
        "count": len(orphans),
        "files": [str(o.relative_to(vault)) for o in orphans]
    }
    print(f"   Found {len(orphans)} orphan notes")
    
    # 2. Find broken links
    print(f"\n🔗 Checking for broken links...")
    broken = find_broken_links(vault)
    results["broken_links"] = {
        "count": len(broken),
        "links": [{"file": str(f.relative_to(vault)), "link": l} for f, l in broken]
    }
    print(f"   Found {len(broken)} broken links")
    
    # 3. Find missing metadata
    print(f"\n📋 Checking for missing metadata...")
    missing = find_missing_metadata(vault)
    results["missing_metadata"] = {
        "count": len(missing),
        "files": [str(m.relative_to(vault)) for m in missing]
    }
    print(f"   Found {len(missing)} files without metadata")
    
    # 4. Archive old files
    print(f"\n📦 Archiving files older than {days} days...")
    archived = archive_old_files(vault, days)
    results["archived"] = archived
    total_archived = len(archived["inbox"]) + len(archived["ai_outputs"])
    print(f"   Archived {total_archived} files")
    
    # 5. Generate Hermes proposals
    print(f"\n🧠 Generating Hermes connection proposals...")
    if orphans:
        proposals_file = generate_hermes_proposals(vault, orphans)
        results["proposals_file"] = proposals_file
        print(f"   Proposals saved: {proposals_file}")
    else:
        print(f"   No orphans to process")
    
    # 6. Update dashboard
    print(f"\n📊 Updating dashboard...")
    dashboard_file = vault / "00_nexus" / "00_NEXUS_DASHBOARD.md"
    if dashboard_file.exists():
        update_dashboard_stats(dashboard_file, results)
        print(f"   Dashboard updated")
    
    # 7. Save batch report
    report_file = vault / "daily" / f"nightly_{datetime.now().strftime('%Y%m%d')}.md"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    
    report_content = f"""---
title: "Nightly Batch Report: {datetime.now().strftime('%Y-%m-%d')}"
type: daily
status: complete
batch_date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
---

# Nightly Batch Report: {datetime.now().strftime('%Y-%m-%d')}

## Summary

| Metric | Count |
|--------|-------|
| Orphan Notes | {len(orphans)} |
| Broken Links | {len(broken)} |
| Missing Metadata | {len(missing)} |
| Archived Files | {total_archived} |

## Orphan Notes

{chr(10).join(f"- `{str(o.relative_to(vault))}`" for o in orphans) if orphans else "_None found_"}

## Broken Links

{chr(10).join(f"- `{str(f.relative_to(vault))}` → `[[{l}]]`" for f, l in broken) if broken else "_None found_"}

## Missing Metadata

{chr(10).join(f"- `{str(m.relative_to(vault))}`" for m in missing) if missing else "_None found_"}

## Archived Files

### Inbox
{chr(10).join(f"- `{f}`" for f in archived['inbox']) if archived['inbox'] else "_None archived_"}

### AI Outputs
{chr(10).join(f"- `{f}`" for f in archived['ai_outputs']) if archived['ai_outputs'] else "_None archived_"}

## Proposals

{results.get('proposals_file', 'No proposals generated')}

## Next Batch

{(datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d 02:00:00')}
"""
    
    report_file.write_text(report_content, encoding="utf-8")
    results["report_file"] = str(report_file)
    
    print(f"\n" + "=" * 60)
    print(f"✅ NIGHTLY BATCH COMPLETE")
    print(f"📄 Report: {report_file}")
    print(f"📊 Orphans: {len(orphans)} | Broken: {len(broken)} | Missing: {len(missing)} | Archived: {total_archived}")
    
    return results


def update_dashboard_stats(dashboard_file: Path, results: Dict) -> None:
    """Update the dashboard with latest stats."""
    content = dashboard_file.read_text(encoding="utf-8")
    
    # Update stats section
    stats_line = f"\n- **Last Nightly Batch**: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    if "## 📝 QUICK LOG" in content:
        content = content.replace(
            "## 📝 QUICK LOG",
            f"## 📝 QUICK LOG\n\n{stats_line}"
        )
    
    dashboard_file.write_text(content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Cognitive Nightly Batch - Self-Improving Loop")
    parser.add_argument("--vault", help="Vault path (default: env COGNITIVE_NEXUS_VAULT)")
    parser.add_argument("--days", type=int, default=30, help="Archive files older than N days (default: 30)")
    parser.add_argument("--output", help="Output JSON file for results")
    args = parser.parse_args()
    
    vault = Path(args.vault).expanduser() if args.vault else get_vault_path()
    
    if not vault.exists():
        print(f"❌ Vault not found: {vault}")
        print(f"   Run: python3 scripts/init_vault.py --path {vault.parent}")
        sys.exit(1)
    
    results = run_nightly_batch(vault, args.days)
    
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Results saved: {args.output}")


if __name__ == "__main__":
    import sys
    main()
