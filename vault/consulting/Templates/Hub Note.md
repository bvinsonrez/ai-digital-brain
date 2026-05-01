---
type: hub
client: <% tp.file.folder(true).split("/").pop() %>
status: active
created: <% tp.date.now("YYYY-MM-DD") %>
last_reviewed: <% tp.date.now("YYYY-MM-DD") %>
tags:
  - client
---

# <% tp.file.title %>

## Account Overview

**Industry:** 
**Relationship start:** 
**Key contacts:**
- 

## Active Work

```dataview
TABLE status, file.mtime as "Updated"
FROM "<% tp.file.folder(true) %>"
WHERE type = "project-note" OR type = "meeting-note"
SORT file.mtime DESC
LIMIT 10
```

## Open Items

- [ ] 

## Background

## Notes
