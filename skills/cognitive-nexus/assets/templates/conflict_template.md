---
title: "Conflict: {{title}}"
type: conflict
status: pending
agents_involved: "{{agent1}}, {{agent2}}"
conflict_type: "{{type}}"
severity: "{{severity}}"
resolution_status: "pending"
resolution_method: ""
resolution_rationale: ""
resolution_date: ""
resolution_by: ""
---

# Conflict: {{title}}

## Conflicting Views

### {{agent1}} Position

<!-- {{agent1}} output or reasoning -->

### {{agent2}} Position

<!-- {{agent2}} critique or rejection -->

## Validation Report

### Critique

<!-- Detailed critique from Hermes -->

### Findings

| Issue | Severity | Location | Recommendation |
|-------|----------|----------|----------------|
<!-- Issues table -->

## Verdict

**Status**: `PENDING`

**Rationale**:

<!-- Explanation for the verdict -->

## Next Steps

- If APPROVED: Pass to OpenClaw for execution
- If REJECTED: Move to `/conflicts/` for human resolution
