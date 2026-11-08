"""Opt-in real Codex trial; uses your configured provider and model quota.

Run with --scenario scenarios/kv-cache.json. Artifacts remain in a new temporary
project. No user configuration or existing project is changed. Review hook.py
before running: the trial bypasses hook trust only for this invocation.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from install import hook_command, install


def codex_executable():
    executable = shutil.which("codex")
    if not executable:
        raise ValueError("Codex CLI is not on PATH; pass --codex /path/to/codex")
    if os.name == "nt":
        # The npm launcher is a .cmd file. Prefer the native binary so timeout
        # handling owns the actual CLI process rather than a wrapper shell.
        package = Path(executable).parent / "node_modules/@openai/codex"
        native = list(package.glob("node_modules/@openai/codex-win32-*/vendor/*/bin/codex.exe"))
        if len(native) == 1:
            return str(native[0])
    return executable


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", required=True, type=Path)
    parser.add_argument("--codex", help="Path to a native Codex executable")
    args = parser.parse_args()
    scenario = json.loads(args.scenario.read_text(encoding="utf-8"))
    executable = args.codex or codex_executable()
    root = Path(tempfile.mkdtemp(prefix="cognition-live-"))
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    install(root)
    # Observe only synthetic trial data; production hooks never write this log.
    observer = root / "observe.py"
    observer.write_text('''import json, subprocess, sys
from pathlib import Path
root = Path(__file__).parent
event = json.load(sys.stdin)
live = root / '.know/map.md'
before = live.read_text(encoding='utf-8')
p = subprocess.run([sys.executable, '-X', 'utf8', HOOK, '--project', str(root)],
    input=json.dumps(event), text=True, encoding='utf-8', capture_output=True)
record = {k: event.get(k) for k in ('hook_event_name','session_id','turn_id','model','stop_hook_active')}
record.update(before=before, after=live.read_text(encoding='utf-8'),
    output=json.loads(p.stdout), exit_code=p.returncode, stderr=p.stderr)
with (root / 'hook-events.jsonl').open('a', encoding='utf-8') as f:
    f.write(json.dumps(record, ensure_ascii=False) + '\\n')
print(p.stdout, end='')
'''.replace("HOOK", repr(str(SCRIPTS / "hook.py"))), encoding="utf-8")
    path = root / ".codex/hooks.json"
    config = json.loads(path.read_text(encoding="utf-8"))
    for event in ("UserPromptSubmit", "Stop"):
        config["hooks"][event][0]["hooks"][0]["command"] = hook_command(observer, root)
    path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    (root / "scenario.json").write_text(json.dumps(scenario, ensure_ascii=False, indent=2), encoding="utf-8")
    version = subprocess.check_output([executable, "--version"], text=True).strip()
    print(f"{version}; evidence: {root}", flush=True)
    session = None
    summaries = []
    for number, step in enumerate(scenario, 1):
        if step.get("new_session"):
            session = None
        command = [executable, "-a", "never", "-s", "workspace-write",
                   "-c", "model_reasoning_effort=\"low\"",
                   "-c", "projects." + json.dumps(str(root)) + '.trust_level="trusted"',
                   "--disable", "plugins", "--disable", "apps", "--disable", "multi_agent", "exec"]
        if session:
            command += ["resume", session]
        command += ["--json", "--dangerously-bypass-hook-trust", "-"]
        with (root / f"turn-{number}.jsonl").open("w", encoding="utf-8") as out, \
                (root / f"turn-{number}.stderr").open("w", encoding="utf-8") as err:
            subprocess.run(command, cwd=root, input=step["prompt"], text=True,
                           encoding="utf-8", stdout=out, stderr=err, check=True, timeout=240)
        events = [json.loads(line) for line in (root / f"turn-{number}.jsonl").read_text(encoding="utf-8").splitlines()]
        session = next(e["thread_id"] for e in events if e["type"] == "thread.started")
        summary = {"turn": number, "session_id": session, "prompt": step["prompt"],
                   "messages": [e["item"]["text"] for e in events if e.get("item", {}).get("type") == "agent_message"],
                   "map": (root / ".know/map.md").read_text(encoding="utf-8")}
        summaries.append(summary)
        (root / "summary.json").write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(summary, ensure_ascii=False), flush=True)
    print("Inspect answers AND hook-events.jsonl; successful commands do not prove semantic correctness.")


if __name__ == "__main__":
    main()
