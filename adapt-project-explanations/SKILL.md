---
name: adapt-project-explanations
description: Use a project knowledge map to start explanations at the user's current depth. Infer understanding from ordinary follow-ups and project decisions. The companion Codex hooks load the map and validate updates automatically.
---

# Project Cognition Map

The map lists only what the user can currently be assumed to understand. Each bullet names a reusable knowledge boundary. Nest finer understanding under broader understanding.

## Answer

Read the injected map and current conversation. Start at the nearest relevant known boundary. When the user is missing a causal connection, explain that connection in a few clear steps, then continue the task. Adapt the amount of explanation to the question. Retain the evidence needed to review the work.

An absent entry means the map has no record. Use the question and current dialogue to choose the explanation depth. Keep map maintenance invisible during ordinary answers.

## Update

Use natural interaction. The user may apply an idea, ask a deeper question that demonstrates the broader idea, explicitly say they understand, or move forward through later relevant discussion after an explanation. These can justify adding a narrowly scoped boundary. Stopping questions while continuing the same relevant task can justify treating that part as understood. A topic switch alone provides little evidence.

If repeated follow-ups reveal an entry overstates understanding, narrow or remove that entry. Keep known parent boundaries when the user starts exploring a deeper detail. Add that detail only when subsequent interaction supports understanding it.

Write only short topic headings and nested knowledge labels. Keep definitions, status labels, questions, quotations, dates, explanation instructions, and conversation history out of the map. Preserve the useful tree. Consolidate redundant labels without inferring broader understanding from the presence of several children.

## Persist

The UserPromptSubmit hook supplies the map and a turn-specific candidate path. If an update is warranted, write the full updated map to that candidate. The Stop hook validates its format and checks for concurrent edits before replacing the live map. If no update is warranted, create no candidate.

Honor explicit user corrections. Show the map when asked. See [format and integration](references/map-format.md) for the exact syntax and hook contract. The repository's review cases remain proposals pending user approval.
