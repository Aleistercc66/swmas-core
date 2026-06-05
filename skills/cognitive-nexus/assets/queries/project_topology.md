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