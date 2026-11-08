# Map and hook contract

The [sample map](map.example.md) is illustrative. Installation creates an empty map.

The first line is exactly `# 已掌握`. Topic headings start with `## `. Knowledge labels are plain Markdown bullets, using two spaces per nested level. A parent must exist before a child. Labels are at most 80 characters, depth at most four levels, and the entire map at most 60 entries and 16 KiB. These are size limits, not a learning model. Duplicate siblings, state tags, inline metadata, empty topics, and broken indentation are rejected.

The project root determines scope. Runtime files stay in `.know/`.

- `map.md` contains the current understanding tree.
- `pending/<turn hash>/` contains a base snapshot and an optional candidate. Completed turns are cleaned up. Interrupted or failed turns may leave staging files, which can be deleted when that session has ended.
- `map.lock` serializes updates made through the hook.

`UserPromptSubmit` injects the skill and current map. It captures a snapshot for that session and turn. `Stop` validates an optional candidate and atomically replaces the map if the base still matches. A concurrent change causes a retry against the new map. Repeated validation failure leaves the live map untouched and reports the problem.

The installer merges these two command hooks into project `.codex/hooks.json` and backs up the original configuration once. Keep the cloned repository at its installed path, or rerun the installer after moving it. Codex requires trust for local hook commands through `/hooks`.

The adapter targets Codex CLI hook events with `session_id`, `turn_id`, `cwd`, and `hook_event_name`. It uses Python 3.10+ and POSIX file locks on Linux/macOS. The validator checks structure and safe writes. The model remains responsible for the meaning and scope of an update. Filesystem writes outside this adapter are governed by the host's permissions.

[Codex hook reference](https://learn.chatgpt.com/docs/hooks)
