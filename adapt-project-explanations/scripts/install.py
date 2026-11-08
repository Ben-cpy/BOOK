#!/usr/bin/env python3
"""Install globally with project-local memory, or in one project (Python 3.9+)."""
import argparse
import base64
import json
import os
from pathlib import Path
import shlex
import shutil
import sys

from know import EMPTY, atomic_write, file_lock, ignore_runtime, validate


def hook_command(script, root=None):
    args = [sys.executable, "-X", "utf8", str(script)]
    if root is not None:
        args += ["--project", str(root)]
    if os.name == "nt":
        # Explicit PowerShell invocation also works when the caller uses cmd.exe.
        quoted = "& " + " ".join("'" + arg.replace("'", "''") + "'" for arg in args)
        encoded = base64.b64encode(quoted.encode("utf-16-le")).decode("ascii")
        return "powershell.exe -NoProfile -NonInteractive -EncodedCommand " + encoded
    return " ".join(shlex.quote(arg) for arg in args)


def configure_hooks(codex, command):
    """Caller holds the install lock; preserve unrelated handlers and metadata."""
    path = codex / "hooks.json"
    raw = path.read_bytes() if path.exists() else b"{}"
    config = json.loads(raw)
    if not isinstance(config, dict) or not isinstance(config.get("hooks", {}), dict):
        raise ValueError("invalid hooks.json")
    hooks = config.setdefault("hooks", {})
    for event in ("UserPromptSubmit", "Stop"):
        entries = hooks.setdefault(event, [])
        if not isinstance(entries, list):
            raise ValueError(f"invalid {event} hook list")
        kept = []
        for item in entries:
            if (not isinstance(item, dict) or not isinstance(item.get("hooks"), list)
                    or not all(isinstance(hook, dict) for hook in item["hooks"])):
                raise ValueError(f"invalid {event} hook group")
            remaining = [hook for hook in item["hooks"]
                         if hook.get("statusMessage") != "Project Cognition Map"]
            if remaining:
                kept.append({**item, "hooks": remaining})
        handler = {"type": "command", "command": command, "timeout": 10,
                   "statusMessage": "Project Cognition Map"}
        if event == "UserPromptSubmit":
            handler["additionalContextLimit"] = 0  # Map is bounded to 16 KiB.
        entries[:] = kept + [{"hooks": [handler]}]
    if path.exists() and not path.with_name("hooks.before-cognition.json").exists():
        atomic_write(path.with_name("hooks.before-cognition.json"), raw)
    atomic_write(path, (json.dumps(config, indent=2, ensure_ascii=False) + "\n").encode())


def install(root):
    root = root.resolve()
    if not root.is_dir():
        raise ValueError("project directory does not exist")
    codex = root / ".codex"
    codex.mkdir(exist_ok=True)
    with file_lock(codex / "cognition-install.lock"):
        knowledge = root / ".know"
        knowledge.mkdir(exist_ok=True)
        with file_lock(knowledge / "map.lock"):
            live = knowledge / "map.md"
            if live.exists():
                validate(live.read_bytes())
            else:
                atomic_write(live, EMPTY.encode())
            ignore_runtime(root)
        configure_hooks(codex, hook_command(Path(__file__).resolve().with_name("hook.py"), root))
    return root


def install_global(codex_home=None, skills_dir=None):
    codex = Path(codex_home or os.environ.get("CODEX_HOME", Path.home() / ".codex")).resolve()
    # Hooks inject the complete Skill every turn. Keeping the runtime outside
    # skill discovery avoids a second automatic invocation and its UI narration.
    skills = Path(skills_dir or codex / "cognition-runtime").resolve()
    codex.mkdir(parents=True, exist_ok=True)
    destination = skills / "adapt-project-explanations"
    source = Path(__file__).resolve().parents[1]
    with file_lock(codex / "cognition-install.lock"):
        if source != destination:
            backup = codex / "cognition-skill.before-install"
            if destination.exists() and not backup.exists():
                shutil.copytree(destination, backup, ignore=shutil.ignore_patterns("__pycache__"))
            for relative in [Path("SKILL.md"), *[p.relative_to(source) for folder in ("scripts", "references")
                                              for p in (source / folder).rglob("*")
                                              if p.is_file() and "__pycache__" not in p.parts]]:
                target = destination / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                atomic_write(target, (source / relative).read_bytes())
        configure_hooks(codex, hook_command(destination / "scripts/hook.py"))
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--project", type=Path)
    mode.add_argument("--global", dest="global_install", action="store_true")
    parser.add_argument("--codex-home", type=Path, help="Global hook configuration directory (for testing/custom installs)")
    parser.add_argument("--runtime-dir", "--skills-dir", dest="skills_dir", type=Path,
                        help="Global runtime parent (default: <codex-home>/cognition-runtime)")
    args = parser.parse_args()
    try:
        if args.global_install:
            destination = install_global(args.codex_home, args.skills_dir)
            print(f"Installed global skill: {destination}")
            print("Maps are created per project at <project>/.know/map.md on first use.")
        else:
            if args.codex_home or args.skills_dir:
                parser.error("--codex-home and --skills-dir require --global")
            root = install(args.project)
            print(f"Configured {root / '.codex/hooks.json'}")
        print("In Codex, use /hooks to review and trust the two command hooks.")
    except (OSError, ValueError, TypeError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
