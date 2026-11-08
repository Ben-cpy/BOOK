---
name: adapt-project-explanations
description: Use a project knowledge map to start explanations at the user's current depth. Infer understanding from ordinary follow-ups and project decisions. The companion Codex hooks load the map and validate updates automatically.
---

# Project Cognition Map

The map lists only what the user can currently be assumed to understand. Each bullet names a reusable knowledge boundary. Nest finer understanding under broader understanding.

The Skill can be installed globally, but memory belongs to the project identified by the hook. Read and update only that project's `.know/map.md` through its candidate path. Never create a global knowledge map or import another project's understanding boundaries.

## Answer

Read the injected map and current conversation. Start at the nearest relevant known boundary. When the user is missing a causal connection, explain that connection in a few clear steps, then continue the task. Adapt the amount of explanation to the question. Retain the evidence needed to review the work.

For a missing causal link, prefer one compact paragraph with a few sentences in everyday language: connect the cause, the intermediate change and the consequence, then stop at the depth asked. Add an example, equations or lower-level machinery only when requested or needed to resolve the question. Avoid repeating the same connection as a list, a diagram and a formula in one answer.

An absent entry means the map has no record. Use the question and current dialogue to choose the explanation depth. Keep map maintenance invisible during ordinary answers.

## Update

Use natural interaction. The user may apply an idea, ask a deeper question that demonstrates the broader idea, explicitly say they understand, or move forward through later relevant discussion after an explanation. These can justify adding a narrowly scoped boundary. Stopping questions while continuing the same relevant task can justify treating that part as understood. A topic switch alone provides little evidence.

Your own explanation is not evidence that the user understood it. A new question identifies something to explain, not automatically something to record as known.

If repeated follow-ups reveal an entry overstates understanding, narrow or remove that entry. Keep known parent boundaries when the user starts exploring a deeper detail. Add that detail only when subsequent interaction supports understanding it.

Write only short topic headings and nested knowledge labels. Keep definitions, status labels, questions, quotations, dates, explanation instructions, and conversation history out of the map. Preserve the useful tree. Consolidate redundant labels without inferring broader understanding from the presence of several children.

## Persist

The UserPromptSubmit hook supplies the map and a turn-specific candidate path. If an update is warranted, write the full updated map to that candidate. The Stop hook validates its format and checks for concurrent edits before replacing the live map. If no update is warranted, create no candidate.

The first line must be `# 已掌握`. Group bullets under `## Topic` headings; do not put a bullet directly under the first line. Use two spaces per nested level, at most four levels, 80 characters per label, 60 labels and 16 KiB total. Use UTF-8 without BOM, LF newlines and a final newline. An empty map contains only the first line. Topic headings require at least one bullet. Use plain labels without brackets, angle brackets or pipes; avoid duplicate siblings and empty headings.

Write the candidate before your final answer, without announcing routine map maintenance. Do not edit the live map directly. If Stop requests a repair, fix only the candidate and avoid turning the user's answer into a maintenance report.

Honor explicit user corrections. Show the map when asked. See [format and integration](references/map-format.md) for the exact syntax and hook contract. The repository's review cases remain proposals pending user approval.
