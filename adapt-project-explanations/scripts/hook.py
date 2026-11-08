#!/usr/bin/env python3
"""Codex UserPromptSubmit/Stop hooks for a project cognition map."""
import argparse
import fcntl
import json
from pathlib import Path
import sys

from know import atomic_write, digest, validate

SKILL = Path(__file__).resolve().parents[1] / "SKILL.md"


def run(event, project):
    root = project.resolve()
    cwd = Path(event.get("cwd", "")).resolve()
    if not cwd.is_relative_to(root):
        return {}
    name = event.get("hook_event_name")
    if name not in {"UserPromptSubmit", "Stop"}:
        return {}
    session, turn = event.get("session_id"), event.get("turn_id")
    if not session or not turn:
        return {"systemMessage": "Cognition map requires session_id and turn_id. Update skipped."}
    directory = root / ".know"
    token = digest(json.dumps([session, turn]).encode())[:32]
    pending = directory / "pending" / token
    live = directory / "map.md"
    with (directory / "map.lock").open("a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        current = live.read_bytes()
        if name == "UserPromptSubmit":
            try:
                text = validate(current)
            except ValueError as error:
                return {"systemMessage": f"Cognition map needs correction: {error}"}
            pending.mkdir(parents=True, exist_ok=True)
            base = pending / "base.md"
            if not base.exists():
                atomic_write(base, current)
            candidate = pending / "candidate.md"
            context = (
                SKILL.read_text(encoding="utf-8")
                + "\n\nCurrent project map\n" + text
                + "\n\nIf this user turn changes what can be assumed understood, write the complete "
                + "updated Markdown to " + str(candidate)
                + ". Otherwise create no candidate. The Stop hook validates and saves the candidate. "
                + "Use ordinary dialogue as evidence. Do not ask for a quiz or learning confirmation."
            )
            return {"hookSpecificOutput": {"hookEventName": name, "additionalContext": context}}
        candidate = pending / "candidate.md"
        if not candidate.exists():
            if pending.exists():
                (pending / "base.md").unlink(missing_ok=True)
                pending.rmdir()
            return {}
        try:
            proposed = candidate.read_bytes()
            validate(proposed)
            base = (pending / "base.md").read_bytes()
            if current != base and proposed != current:
                atomic_write(pending / "base.md", current)
                candidate.unlink()
                raise ValueError("map changed in another session. Reconcile your candidate with "
                                 + str(live) + " before retrying")
            atomic_write(live, proposed)
            candidate.unlink()
            (pending / "base.md").unlink()
            pending.rmdir()
            return {}
        except ValueError as error:
            if event.get("stop_hook_active"):
                return {"systemMessage": f"Cognition update was not saved: {error}"}
            return {"decision": "block", "reason": f"Correct only the cognition candidate at {candidate}: {error}"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path)
    args = parser.parse_args()
    try:
        event = json.load(sys.stdin)
        if not isinstance(event, dict):
            raise ValueError("hook payload must be an object")
        result = run(event, args.project)
    except (OSError, ValueError, TypeError) as error:
        result = {"systemMessage": f"Cognition hook could not run: {error}"}
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
