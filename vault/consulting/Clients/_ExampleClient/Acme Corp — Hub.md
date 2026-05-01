---
type: hub
client: Acme Corp
status: active
created: 2026-01-15
last_reviewed: 2026-01-15
tags:
  - client
---

# Acme Corp — Hub

## Account Overview

**Industry:** Manufacturing
**Relationship start:** January 2026
**Key contacts:**
- Jane Smith, VP Operations — primary contact for this engagement
- Tom Lee, IT Director — technical stakeholder on data infrastructure

## Active Work

```dataview
TABLE status, file.mtime as "Updated"
FROM "Clients/_ExampleClient"
WHERE type = "project-note" OR type = "meeting-note"
SORT file.mtime DESC
LIMIT 10
```

## Open Items

- [ ] Confirm data access for Phase 1 pilot
- [ ] Schedule follow-up with Tom Lee on infrastructure review

## Background

Acme Corp is a mid-size manufacturer exploring how to consolidate their operational data across three facilities. They have legacy ERP data in separate systems and want a unified view for planning and reporting.

The engagement started with a discovery call in January 2026. This hub note tracks all related work.

## Notes

_Use this section for anything that doesn't fit elsewhere: relationship dynamics, stakeholder sensitivities, account history._
