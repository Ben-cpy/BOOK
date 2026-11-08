#!/usr/bin/env python3
"""Enable the cognition hooks in one Codex project (Linux/macOS, Python 3.10+)."""
import argparse
import fcntl
import json
from pathlib import Path
import shlex
import subprocess
import sys

from know import EMPTY, atomic_write, validate


def install(root):
    root = root.resolve()
    if not root.is_dir():
        raise ValueError("project directory does not exist")
    codex = root / ".codex"
    codex.mkdir(exist_ok=True)
    with (codex / "cognition-install.lock").open("a") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        path = codex / "hooks.json"
        raw = path.read_bytes() if path.exists() else b"{}"
        config = json.loads(raw)
        if not isinstance(config, dict) or not isinstance(config.get("hooks", {}), dict):
            raise ValueError("invalid hooks.json")
        hooks = config.setdefault("hooks", {})
        script = Path(__file__).resolve().with_name("hook.py")
        command = " ".join(shlex.quote(str(item)) for item in (sys.executable, script, "--project", root))
        for event in ("UserPromptSubmit", "Stop"):
            entries = hooks.setdefault(event, [])
            if not isinstance(entries, list):
                raise ValueError(f"invalid {event} hook list")
            entries[:] = [item for item in entries if not any(
                hook.get("statusMessage") == "Project Cognition Map" for hook in item.get("hooks", [])
            )]
            entries.append({"hooks": [{"type": "command", "command": command, "timeout": 10,
                                      "statusMessage": "Project Cognition Map"}]})
        knowledge = root / ".know"
        knowledge.mkdir(exist_ok=True)
        live = knowledge / "map.md"
        if live.exists():
            validate(live.read_bytes())
        else:
            atomic_write(live, EMPTY.encode())
        if path.exists() and not path.with_name("hooks.before-cognition.json").exists():
            atomic_write(path.with_name("hooks.before-cognition.json"), raw)
        atomic_write(path, (json.dumps(config, indent=2, ensure_ascii=False) + "\n").encode())
        git = subprocess.run(["git", "-C", str(root), "rev-parse", "--path-format=absolute", "--git-path", "info/exclude"],
                             capture_output=True, text=True)
        if git.returncode == 0:
            exclude = Path(git.stdout.strip())
            exclude.parent.mkdir(parents=True, exist_ok=True)
            existing = exclude.read_text() if exclude.exists() else ""
            lines = existing.splitlines()
            for rule in ("/.know/", "/.codex/hooks.before-cognition.json", "/.codex/cognition-install.lock"):
                if rule not in lines:
                    lines.append(rule)
            atomic_write(exclude, ("\n".join(lines) + "\n").encode())
    return root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path)
    args = parser.parse_args()
    try:
        root = install(args.project)
        print(f"Configured {root / '.codex/hooks.json'}")
        print("In Codex, use /hooks to review and trust the two command hooks.")
    except (OSError, ValueError, TypeError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
