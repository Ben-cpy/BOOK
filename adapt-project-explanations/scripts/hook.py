#!/usr/bin/env python3
"""Codex UserPromptSubmit/Stop hooks for a project cognition map."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from know import EMPTY, atomic_write, digest, file_lock, ignore_runtime, validate

SKILL = Path(__file__).resolve().parents[1] / "SKILL.md"


def cleanup(pending):
    for name in ("candidate.md", "base.md", "retry"):
        (pending / name).unlink(missing_ok=True)
    pending.rmdir()


def project_root(cwd):
    git = subprocess.run(["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True, encoding="utf-8")
    if git.returncode == 0:
        return Path(git.stdout.strip()).resolve()
    # Non-Git projects are anchored by the first map, not by a global store.
    for parent in (cwd, *cwd.parents):
        if parent == Path.home() or parent == parent.parent:
            break
        if (parent / ".know/map.md").exists():
            return parent
    return None if cwd in (Path.home(), Path(cwd.anchor)) else cwd


def run(event, project=None):
    if not isinstance(event.get("cwd"), str) or not event["cwd"]:
        return {}
    cwd = Path(event["cwd"]).resolve()
    name = event.get("hook_event_name")
    if name not in {"UserPromptSubmit", "Stop"} or not cwd.is_dir():
        return {}
    root = project.resolve() if project is not None else project_root(cwd)
    if root is None:
        return {}
    if not cwd.is_relative_to(root):
        return {}
    # A parent's hook may be inherited by Codex in a nested project.
    for parent in (cwd, *cwd.parents):
        if parent == root:
            break
        if (parent / ".git").exists() or (parent / ".know/map.md").exists():
            return {}
    session, turn = event.get("session_id"), event.get("turn_id")
    if not session or not turn:
        return {"systemMessage": "Cognition map requires session_id and turn_id. Update skipped."}
    directory = root / ".know"
    if name == "Stop" and not directory.exists():
        return {}
    directory.mkdir(exist_ok=True)
    session_dir = directory / "pending" / digest(str(session).encode())[:32]
    pending = session_dir / digest(str(turn).encode())[:32]
    live = directory / "map.md"
    with file_lock(directory / "map.lock"):
        if not live.exists():
            if name != "UserPromptSubmit":
                return {}
            atomic_write(live, EMPTY.encode())
            ignore_runtime(root)
        current = live.read_bytes()
        if name == "UserPromptSubmit":
            try:
                text = validate(current)
            except ValueError as error:
                return {"systemMessage": f"Cognition map needs correction: {error}"}
            # A resumed session starts a new turn after interruption. Discard its
            # unfinished candidates, never another session's active update.
            if session_dir.exists():
                for old in session_dir.iterdir():
                    if old != pending and old.is_dir():
                        cleanup(old)
            pending.mkdir(parents=True, exist_ok=True)
            base = pending / "base.md"
            if base.exists():
                # Global and project hooks may both be enabled. Under the same
                # map lock, only the first handler injects this turn's context.
                return {}
            atomic_write(base, current)
            candidate = pending / "candidate.md"
            context = (
                SKILL.read_text(encoding="utf-8").replace(
                    "references/map-format.md", str(SKILL.parent / "references/map-format.md"))
                + "\n\nCurrent project map\n" + text
                + "\nProject scope: " + str(root) + ". Use only this project's map; "
                + "do not import knowledge from other projects."
                + "\n\nIf this user turn changes what can be assumed understood, write the complete "
                + "updated Markdown to " + str(candidate)
                + ". Otherwise create no candidate. The Stop hook validates and saves the candidate. "
                + "Write UTF-8 without BOM, LF newlines and a final newline. "
                + "Do not write map.md directly. Complete candidate writes before your final answer. "
                + "Use ordinary dialogue as evidence. Do not ask for a quiz or learning confirmation."
            )
            return {"hookSpecificOutput": {"hookEventName": name, "additionalContext": context}}
        candidate = pending / "candidate.md"
        if not candidate.exists():
            if (pending / "retry").exists() and not event.get("stop_hook_active"):
                # Another enabled Stop handler may run after the first requests
                # a conflict repair. Keep its refreshed baseline for the model.
                return {}
            if pending.exists():
                cleanup(pending)
            if session_dir.exists() and not any(session_dir.iterdir()):
                session_dir.rmdir()
            return {}
        try:
            proposed = candidate.read_bytes()
            validate(proposed)
            base = (pending / "base.md").read_bytes()
            if current != base and proposed != current:
                candidate.unlink()
                atomic_write(pending / "retry", b"")
                atomic_write(pending / "base.md", current)
                raise ValueError("map changed in another session. Reconcile your candidate with "
                                 + str(live) + " before retrying")
            if proposed != current:
                atomic_write(live, proposed)
            cleanup(pending)
            session_dir.rmdir()
            return {}
        except ValueError as error:
            if event.get("stop_hook_active"):
                cleanup(pending)
                session_dir.rmdir()
                return {"systemMessage": f"Cognition update was not saved: {error}"}
            return {"decision": "block", "reason": (
                f"Repair only the cognition candidate at {candidate}: {error}. "
                "Use # 已掌握, then ## topic headings and plain nested bullets; UTF-8 and LF. "
                "Do not announce maintenance or replace the substantive answer with a repair report."
            )}


def main():
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, help="Omit to discover the project from the event cwd")
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
