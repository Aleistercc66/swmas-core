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