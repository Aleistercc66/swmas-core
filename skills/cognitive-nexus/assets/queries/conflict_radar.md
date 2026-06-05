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