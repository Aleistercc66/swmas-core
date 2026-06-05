#!/usr/bin/env python3
"""
Cognitive Nexus Vault Health Check
Diagnostic tool for the vault: broken links, orphan notes, missing metadata, structural issues.
"""

import os
import yaml
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set, Tuple


def get_vault_path() -> Path:
    """Get vault path from environment or default."""
    return Path(os.environ.get("COGNITIVE_NEXUS_VAULT", "~/obsidian-vault/Cognitive-Nexus")).expanduser()


def check_vault_health(vault: Path) -> Dict:
    """Run comprehensive health check on the vault."""
    print(f"\n🏥 VAULT HEALTH CHECK")
    print(f"📁 Vault: {vault}")
    print(f"=" * 60)
    
    health = {
        "vault_exists": vault.exists(),
        "structure": {},
        "orphans": 0,
        "broken_links": 0,
        "missing_metadata": 0,
        "total_files": 0,
        "total_size": 0,
        "errors": []
    }
    
    if not vault.exists():
        health["errors"].append("Vault directory does not exist")
        return health
    
    # Check structure
    required_folders = [
        "00_nexus", "inbox", "daily", "projects", "knowledge",
        "decisions", "ai_outputs", "conflicts", "system"
    ]
    
    for folder in required_folders:
        folder_path = vault / folder
        exists = folder_path.exists()
        health["structure"][folder] = exists
        if not exists:
            health["errors"].append(f"Missing folder: {folder}")
    
    # Count files and size
    for md_file in vault.rglob("*.md"):
        if ".obsidian" in str(md_file):
            continue
        health["total_files"] += 1
        health["total_size"] += md_file.stat().st_size
    
    # Find orphans
    orphans = []
    for md_file in vault.rglob("*.md"):
        if ".obsidian" in str(md_file) or "README" in str(md_file):
            continue
        
        content = md_file.read_text(encoding="utf-8")
        has_links = "[[" in content or ("](" in content and "][" in content)
        
        if not has_links:
            orphans.append(str(md_file.relative_to(vault)))
    
    health["orphans"] = len(orphans)
    health["orphan_files"] = orphans
    
    # Find broken links
    import re
    broken = []
    for md_file in vault.rglob("*.md"):
        if ".obsidian" in str(md_file):
            continue
        
        content = md_file.read_text(encoding="utf-8")
        wikilinks = re.findall(r'\[\[(.*?)\]\]', content)
        
        for link in wikilinks:
            target = vault / f"{link}.md"
            if not target.exists():
                broken.append({
                    "file": str(md_file.relative_to(vault)),
                    "link": link
                })
    
    health["broken_links"] = len(broken)
    health["broken_link_details"] = broken
    
    # Find missing metadata
    missing_meta = []
    for md_file in vault.rglob("*.md"):
        if ".obsidian" in str(md_file):
            continue
        
        content = md_file.read_text(encoding="utf-8")
        if not content.startswith("---"):
            missing_meta.append(str(md_file.relative_to(vault)))
    
    health["missing_metadata"] = len(missing_meta)
    health["missing_metadata_files"] = missing_meta
    
    # Check dashboard
    dashboard = vault / "00_nexus" / "00_NEXUS_DASHBOARD.md"
    health["dashboard_exists"] = dashboard.exists()
    if not dashboard.exists():
        health["errors"].append("Dashboard file missing")
    
    # Check system rules
    rules = vault / "system" / "SYSTEM_RULES.md"
    health["rules_exist"] = rules.exists()
    if not rules.exists():
        health["errors"].append("System rules file missing")
    
    return health


def print_health_report(health: Dict) -> None:
    """Print formatted health report."""
    print(f"\n📊 HEALTH REPORT")
    print(f"{'='*60}")
    
    # Structure
    print(f"\n🏗️  VAULT STRUCTURE:")
    for folder, exists in health["structure"].items():
        status = "✅" if exists else "❌"
        print(f"   {status} {folder}")
    
    # Files
    print(f"\n📁 FILES:")
    print(f"   Total .md files: {health['total_files']}")
    print(f"   Total size: {health['total_size'] / 1024:.1f} KB")
    
    # Issues
    print(f"\n⚠️  ISSUES:")
    print(f"   Orphan notes: {health['orphans']}")
    print(f"   Broken links: {health['broken_links']}")
    print(f"   Missing metadata: {health['missing_metadata']}")
    
    # Errors
    if health["errors"]:
        print(f"\n🔴 ERRORS:")
        for error in health["errors"]:
            print(f"   ❌ {error}")
    else:
        print(f"\n✅ No critical errors found!")
    
    # Score
    score = 100
    score -= health["orphans"] * 2
    score -= health["broken_links"] * 3
    score -= health["missing_metadata"] * 1
    score -= len(health["errors"]) * 10
    score = max(0, score)
    
    print(f"\n🏆 HEALTH SCORE: {score}/100")
    
    if score >= 90:
        print(f"   🟢 EXCELLENT - Vault is in great shape!")
    elif score >= 70:
        print(f"   🟡 GOOD - Minor issues to address")
    elif score >= 50:
        print(f"   🟠 FAIR - Needs attention")
    else:
        print(f"   🔴 POOR - Critical issues require immediate action")
    
    print(f"{'='*60}")


def save_health_report(vault: Path, health: Dict) -> str:
    """Save health report to daily log."""
    report_file = vault / "daily" / f"health_{datetime.now().strftime('%Y%m%d')}.md"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    
    content = f"""---
title: "Vault Health Report: {datetime.now().strftime('%Y-%m-%d')}"
type: health-check
status: complete
check_date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
health_score: {max(0, 100 - health['orphans']*2 - health['broken_links']*3 - health['missing_metadata']*1 - len(health['errors'])*10)}
---

# Vault Health Report

**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Structure Status

| Folder | Status |
|--------|--------|
{chr(10).join(f"| {folder} | {'✅' if exists else '❌'} |" for folder, exists in health['structure'].items())}

## File Statistics

- **Total .md files**: {health['total_files']}
- **Total size**: {health['total_size'] / 1024:.1f} KB

## Issues Found

### Orphan Notes ({health['orphans']})

{chr(10).join(f"- `{f}`" for f in health.get('orphan_files', [])) if health.get('orphan_files') else "_None found_"}

### Broken Links ({health['broken_links']})

{chr(10).join(f"- `{b['file']}` → `[[{b['link']}]]`" for b in health.get('broken_link_details', [])) if health.get('broken_link_details') else "_None found_"}

### Missing Metadata ({health['missing_metadata']})

{chr(10).join(f"- `{f}`" for f in health.get('missing_metadata_files', [])) if health.get('missing_metadata_files') else "_None found_"}

## Errors

{chr(10).join(f"- ❌ {e}" for e in health['errors']) if health['errors'] else "_None found_"}

## Recommendations

{generate_recommendations(health)}

"""
    
    report_file.write_text(content, encoding="utf-8")
    
    return str(report_file)


def generate_recommendations(health: Dict) -> str:
    """Generate recommendations based on health issues."""
    recs = []
    
    if health["orphans"] > 0:
        recs.append(f"- **Fix Orphans**: Run `python3 scripts/nightly_batch.py --vault {health.get('vault_path', '')}` to generate connection proposals")
    
    if health["broken_links"] > 0:
        recs.append("- **Fix Broken Links**: Check all [[...]] links and create missing target files or fix the links")
    
    if health["missing_metadata"] > 0:
        recs.append("- **Add Metadata**: Add YAML frontmatter to all files: `---\\ntitle: ...\\ntype: ...\\nstatus: ...\\n---`")
    
    if not all(health["structure"].values()):
        recs.append("- **Fix Structure**: Run `python3 scripts/init_vault.py` to recreate missing folders")
    
    if not recs:
        recs.append("- **Maintain**: Schedule regular health checks with cron")
    
    return chr(10).join(recs)


def main():
    parser = argparse.ArgumentParser(description="Cognitive Nexus Vault Health Check")
    parser.add_argument("--vault", help="Vault path (default: env COGNITIVE_NEXUS_VAULT)")
    parser.add_argument("--save", action="store_true", help="Save report to daily log")
    parser.add_argument("--fix", action="store_true", help="Attempt auto-fix of minor issues")
    args = parser.parse_args()
    
    vault = Path(args.vault).expanduser() if args.vault else get_vault_path()
    
    health = check_vault_health(vault)
    health["vault_path"] = str(vault)
    
    print_health_report(health)
    
    if args.save:
        report = save_health_report(vault, health)
        print(f"\n💾 Report saved: {report}")
    
    if args.fix:
        print(f"\n🔧 AUTO-FIX MODE")
        # Fix missing metadata with templates
        # Fix broken links by creating placeholder files
        # This is a simplified version - full implementation would be more complex
        print(f"   (Auto-fix feature requires manual review)")


if __name__ == "__main__":
    main()
