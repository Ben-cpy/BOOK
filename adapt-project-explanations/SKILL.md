---
name: adapt-project-explanations
description: Adapt explanations and experiment reviews using an opt-in Project Cognition Map. Use when a user asks to understand a project mechanism, interpret results, or inspect or correct the map. Track the depth of the user's understanding from ordinary project conversations.
---

# Project Cognition Map

Answer the user's project question. Use the map to decide where to start, whether a short causal bridge is needed, and which finer boundary the user is exploring.

## Read the boundary tree

- Use the active project's .know/map.md only after opt-in. Initialize it only on request. See [map format](references/map-format.md).
- A heading names a topic. An indented node names a finer distinction within the parent. Read each state at its own depth.
- **可直接讲**: take that exact boundary as the starting point. **待厘清**: focus on the precise subquestion when relevant, without treating the parent as a gap. **补桥**: give one short causal bridge where it matters to the user's decision.
- Use at most one proactive bridge. It may take two or three short sentences. Start with a mechanism the user can follow, show how it leads to the outcome, then continue the task. For a requested explanation, match the requested depth. Always deliver the measurements, assumptions, and limitations needed to audit the result.

## Observe and adapt

| Signal from ordinary conversation | Map change |
| --- | --- |
| The user repeatedly gets stuck at the same boundary in two distinct turns | Add or promote the specific boundary to **补桥**. |
| The user isolates a narrower, reusable question under an established **可直接讲** boundary | Add that question as a **待厘清** child. Use this only if tracking the distinction will change a future explanation or review. Preserve the parent. |
| The user correctly applies a boundary in a fresh decision | Mark that specific boundary **可直接讲** if it is useful across sessions. |
| A bridge was given and the user later advances through two relevant opportunities without revisiting that gap | Mark that specific boundary **可直接讲** as a reversible explanation default. |
| The same gap returns after the default was set | Restore **补桥** at that exact depth. |
| A routine question, paraphrase, silence, or topic switch | Answer the present task. Keep the map as it is. |

A deeper question can show progress at the parent and uncertainty at the child. Ask no questions solely to generate evidence. Record a short boundary label only. Keep definitions, explanation text, user quotes, and session narratives out of the map. Keep evidence references in the inline Markdown comment.

## Save and correct

- Propose at most one boundary change per turn. When a trusted host supplies the ordered project user-turn index, validate and apply the candidate through scripts/know.py. Without the index, adapt within the conversation. Never fabricate the index.
- When the user explicitly corrects the map, use the correction immediately in the answer. On request, show the exact local entry and let the user confirm any manual label, structure, or state change outside the automatic transition rules.
- When asked to show the map, render its headings, nested boundaries, and states. Include source references on request.
