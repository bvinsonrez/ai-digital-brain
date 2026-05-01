---
type: weekly
week: <% tp.date.now("YYYY-[W]WW") %>
created: <% tp.date.now("YYYY-MM-DD") %>
tags:
  - weekly-review
---

# Week of <% tp.date.now("MMMM D") %> — <% tp.date.now("YYYY-[W]WW") %>

## This Week

### What I Shipped
- 

### What's Still Moving
- 

### What Got Stuck
- 

---

## Next Week Priorities

1. 
2. 
3. 

---

## Meetings This Week

```dataview
TABLE client, meeting_type
FROM "Meetings"
WHERE date >= date("<% tp.date.now("YYYY-MM-DD", -7) %>")
  AND date <= date("<% tp.date.now("YYYY-MM-DD") %>")
SORT date ASC
```

---

## Loose Ends

- 
