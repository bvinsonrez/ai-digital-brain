---
type: hub
project: <% tp.file.folder(true).split("/").pop() %>
status: active
created: <% tp.date.now("YYYY-MM-DD") %>
last_reviewed: <% tp.date.now("YYYY-MM-DD") %>
tags:
  - project
---

# <% tp.file.title %>

## Overview

**Goal:** 
**Started:** <% tp.date.now("YYYY-MM-DD") %>
**Status:** Active

## Related Notes

```dataview
TABLE file.mtime as "Updated"
FROM "<% tp.file.folder(true) %>"
WHERE file.name != this.file.name
SORT file.mtime DESC
```

## Open Items

- [ ] 

## Notes
