"""Global installation must never turn project knowledge into global memory."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from hook import run
from install import install, install_global
from know import EMPTY


class GlobalCognitionTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.codex_home = self.directory / "user config 中文" / ".codex"
        self.skills_dir = self.directory / "user skills 中文" / ".agents" / "skills"

    def project(self, name, git=True):
        root = self.directory / name
        root.mkdir(parents=True)
        if git:
            subprocess.run(["git", "init", "-q", str(root)], check=True)
        return root

    def event(self, cwd, name="UserPromptSubmit", session="session-a", turn="turn-a"):
        return {"hook_event_name": name, "session_id": session,
                "turn_id": turn, "cwd": str(cwd)}

    def context(self, event):
        return run(event)["hookSpecificOutput"]["additionalContext"]

    def handlers(self, config, event):
        return [handler for group in config["hooks"][event]
                for handler in group["hooks"]]

    def test_global_install_is_self_contained_and_creates_no_memory(self):
        installed = install_global(self.codex_home, self.skills_dir)
        self.assertEqual(installed, self.skills_dir / "adapt-project-explanations")
        for relative in ("SKILL.md", "scripts/hook.py", "scripts/know.py", "references/map-format.md"):
            self.assertEqual((installed / relative).read_bytes(), (ROOT / relative).read_bytes())
        config = json.loads((self.codex_home / "hooks.json").read_text(encoding="utf-8"))
        for event in ("UserPromptSubmit", "Stop"):
            ours = [h for h in self.handlers(config, event)
                    if h.get("statusMessage") == "Project Cognition Map"]
            self.assertEqual(len(ours), 1)
        self.assertEqual(list(self.directory.rglob("map.md")), [])
        self.assertEqual(list(self.directory.rglob("pending")), [])

    def test_default_global_runtime_stays_outside_skill_discovery(self):
        fake_home = self.directory / "isolated user home"
        fake_home.mkdir()
        with patch("install.Path.home", return_value=fake_home):
            installed = install_global(self.codex_home)
        self.assertEqual(installed, self.codex_home / "cognition-runtime" / "adapt-project-explanations")
        self.assertEqual((installed / "SKILL.md").read_bytes(), (ROOT / "SKILL.md").read_bytes())
        self.assertTrue((installed / "scripts/hook.py").is_file())
        self.assertFalse((fake_home / ".agents").exists())
        self.assertFalse((fake_home / ".codex").exists())
        self.assertFalse((self.codex_home / "skills").exists())
        self.assertEqual(list(self.directory.rglob("map.md")), [])
        self.assertEqual(list(self.directory.rglob("pending")), [])

    def test_reinstall_keeps_other_hooks_and_original_backup(self):
        self.codex_home.mkdir(parents=True)
        other = {"type": "command", "command": "echo unrelated", "statusMessage": "Other tool"}
        config = {"description": "existing user configuration", "hooks": {
            "UserPromptSubmit": [{"hooks": [other]}],
            "SessionStart": [{"hooks": [other]}],
        }}
        raw = (json.dumps(config) + "\n").encode()
        path = self.codex_home / "hooks.json"
        path.write_bytes(raw)
        install_global(self.codex_home, self.skills_dir)
        actual = json.loads(path.read_text(encoding="utf-8"))
        # Exercise coexisting handlers within the same matcher group as ours.
        actual["hooks"]["Stop"][0]["hooks"].append(other)
        path.write_text(json.dumps(actual), encoding="utf-8")
        install_global(self.codex_home, self.skills_dir)
        first = path.read_bytes()
        install_global(self.codex_home, self.skills_dir)
        self.assertEqual(path.read_bytes(), first)
        actual = json.loads(first)
        self.assertEqual(actual["description"], config["description"])
        self.assertEqual(actual["hooks"]["SessionStart"], config["hooks"]["SessionStart"])
        for event in ("UserPromptSubmit", "Stop"):
            handlers = self.handlers(actual, event)
            self.assertIn(other, handlers)
            self.assertEqual(sum(h.get("statusMessage") == "Project Cognition Map" for h in handlers), 1)
        self.assertEqual((self.codex_home / "hooks.before-cognition.json").read_bytes(), raw)
        self.assertEqual(list(self.directory.rglob("map.md")), [])

    def test_reinstall_refreshes_installed_skill(self):
        installed = install_global(self.codex_home, self.skills_dir)
        (installed / "SKILL.md").write_text("old installed version", encoding="utf-8")
        install_global(self.codex_home, self.skills_dir)
        self.assertEqual((installed / "SKILL.md").read_bytes(), (ROOT / "SKILL.md").read_bytes())

    def test_first_message_initializes_empty_map_at_git_root(self):
        project = self.project("new project 中文")
        child = project / "src" / "module"
        child.mkdir(parents=True)
        self.assertFalse((project / ".know").exists())
        self.context(self.event(child))
        self.assertEqual((project / ".know/map.md").read_bytes(), EMPTY.encode())
        self.assertFalse((child / ".know").exists())
        self.assertFalse((self.directory / ".know").exists())
        self.assertEqual(run(self.event(child, "Stop")), {})
        self.assertEqual(list((project / ".know/pending").iterdir()), [])

    def test_two_git_projects_keep_reads_and_writes_separate(self):
        project_a = self.project("project A")
        project_b = self.project("project B")
        child_a, child_b = project_a / "src", project_b / "src"
        child_a.mkdir()
        child_b.mkdir()
        self.context(self.event(child_a))
        self.context(self.event(child_b))
        # Identical session and turn IDs still must not cross the project boundary.
        a_map = "# 已掌握\n\n## Project A\n- Alpha-only knowledge\n"
        b_map = "# 已掌握\n\n## Project B\n- Beta-only knowledge\n"
        for project, text in ((project_a, a_map), (project_b, b_map)):
            base = list((project / ".know/pending").rglob("base.md"))
            self.assertEqual(len(base), 1)
            base[0].with_name("candidate.md").write_bytes(text.encode())
        self.assertEqual(run(self.event(child_a, "Stop")), {})
        self.assertEqual((project_a / ".know/map.md").read_text(encoding="utf-8"), a_map)
        self.assertEqual((project_b / ".know/map.md").read_bytes(), EMPTY.encode())
        self.assertEqual(run(self.event(child_b, "Stop")), {})
        a_context = self.context(self.event(child_a, turn="next-a"))
        b_context = self.context(self.event(child_b, turn="next-b"))
        self.assertIn("Alpha-only knowledge", a_context)
        self.assertNotIn("Beta-only knowledge", a_context)
        self.assertIn("Beta-only knowledge", b_context)
        self.assertNotIn("Alpha-only knowledge", b_context)

    def test_nested_git_project_does_not_inherit_parent_map(self):
        parent = self.project("parent")
        child = self.project("parent/child")
        self.context(self.event(parent))
        (parent / ".know/map.md").write_bytes("# 已掌握\n\n## Parent\n- Parent-only knowledge\n".encode())
        context = self.context(self.event(child))
        self.assertNotIn("Parent-only knowledge", context)
        self.assertEqual((child / ".know/map.md").read_bytes(), EMPTY.encode())

    def test_non_git_first_use_and_subdirectory_reuse(self):
        project = self.project("notes project", git=False)
        self.context(self.event(project))
        known = "# 已掌握\n\n## Notes\n- Notes-only knowledge\n"
        (project / ".know/map.md").write_bytes(known.encode())
        child = project / "chapters" / "one"
        child.mkdir(parents=True)
        context = self.context(self.event(child, turn="next"))
        self.assertIn("Notes-only knowledge", context)
        self.assertFalse((child / ".know").exists())
        self.assertFalse((child.parent / ".know").exists())

    def test_global_and_local_hooks_inject_and_save_once_in_either_order(self):
        install_global(self.codex_home, self.skills_dir)
        for first in ("global", "local"):
            with self.subTest(first=first):
                project = self.project(first + " runs first")
                install(project)
                child = project / "src"
                child.mkdir()
                order = (None, project) if first == "global" else (project, None)
                outputs = [run(self.event(child), scope) for scope in order]
                self.assertEqual(sum("hookSpecificOutput" in output for output in outputs), 1)
                self.assertIn("hookSpecificOutput", outputs[0])
                self.assertEqual(outputs[1], {})
                bases = list((project / ".know/pending").rglob("base.md"))
                self.assertEqual(len(bases), 1)
                proposed = "# 已掌握\n\n## Shared\n- Same project knowledge\n".encode()
                bases[0].with_name("candidate.md").write_bytes(proposed)
                # Either hook can save the candidate created after the other injected.
                live = project / ".know/map.md"
                self.assertEqual(run(self.event(child, "Stop"), order[1]), {})
                self.assertEqual(live.read_bytes(), proposed)
                saved_at = live.stat().st_mtime_ns
                self.assertEqual(run(self.event(child, "Stop"), order[0]), {})
                self.assertEqual(live.read_bytes(), proposed)
                self.assertEqual(live.stat().st_mtime_ns, saved_at)
                self.assertEqual(list((project / ".know/pending").iterdir()), [])

    def test_global_still_runs_when_configured_local_hook_does_not_execute(self):
        project = self.project("local hook not executed")
        install(project)
        install_global(self.codex_home, self.skills_dir)
        self.assertIn("hookSpecificOutput", run(self.event(project)))
        base = list((project / ".know/pending").rglob("base.md"))
        self.assertEqual(len(base), 1)
        proposed = "# 已掌握\n\n## Global hook\n- Project knowledge\n".encode()
        base[0].with_name("candidate.md").write_bytes(proposed)
        self.assertEqual(run(self.event(project, "Stop")), {})
        self.assertEqual((project / ".know/map.md").read_bytes(), proposed)
        self.assertEqual(list((project / ".know/pending").iterdir()), [])

    def test_global_and_local_concurrent_processes_inject_once(self):
        project = self.project("concurrent hook sources")
        install(project)
        installed = install_global(self.codex_home, self.skills_dir)

        def invoke_both(name):
            commands = [
                [sys.executable, "-X", "utf8", str(installed / "scripts/hook.py")],
                [sys.executable, "-X", "utf8", str(ROOT / "scripts/hook.py"), "--project", str(project)],
            ]
            processes = []
            for command in commands:
                process = subprocess.Popen(command, cwd=project, stdin=subprocess.PIPE,
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                           text=True, encoding="utf-8")
                process.stdin.write(json.dumps(self.event(project, name)))
                process.stdin.close()
                process.stdin = None
                processes.append(process)
            outputs = []
            for process in processes:
                stdout, stderr = process.communicate(timeout=10)
                self.assertEqual(process.returncode, 0, stderr)
                outputs.append(json.loads(stdout))
            return outputs

        submitted = invoke_both("UserPromptSubmit")
        self.assertEqual(sum("hookSpecificOutput" in output for output in submitted), 1)
        self.assertEqual(sum(output == {} for output in submitted), 1)
        bases = list((project / ".know/pending").rglob("base.md"))
        self.assertEqual(len(bases), 1)
        proposed = "# 已掌握\n\n## Concurrent\n- Project-local understanding\n".encode()
        bases[0].with_name("candidate.md").write_bytes(proposed)
        self.assertEqual(invoke_both("Stop"), [{}, {}])
        self.assertEqual((project / ".know/map.md").read_bytes(), proposed)
        self.assertEqual(list((project / ".know/pending").iterdir()), [])

    def test_duplicate_stop_preserves_conflict_baseline_until_repair(self):
        install_global(self.codex_home, self.skills_dir)
        for first in ("global", "local"):
            with self.subTest(first=first):
                project = self.project(first + " conflict repair")
                install(project)
                scopes = (None, project) if first == "global" else (project, None)
                event = self.event(project)
                for scope in scopes:
                    run(event, scope)
                base = next((project / ".know/pending").rglob("base.md"))
                candidate = base.with_name("candidate.md")
                original_change = "# 已掌握\n\n## Topic\n- This turn's knowledge\n".encode()
                other_change = "# 已掌握\n\n## Topic\n- Other session's knowledge\n".encode()
                candidate.write_bytes(original_change)
                live = project / ".know/map.md"
                live.write_bytes(other_change)
                stop = self.event(project, "Stop")
                self.assertEqual(run(stop, scopes[0])["decision"], "block")
                self.assertFalse(candidate.exists())
                self.assertEqual(run(stop, scopes[1]), {})
                self.assertEqual(base.read_bytes(), other_change)
                self.assertTrue(base.with_name("retry").exists())
                self.assertEqual(live.read_bytes(), other_change)
                reconciled = ("# 已掌握\n\n## Topic\n- Other session's knowledge\n"
                              "- This turn's knowledge\n").encode()
                candidate.write_bytes(reconciled)
                stop["stop_hook_active"] = True
                for scope in reversed(scopes):
                    self.assertEqual(run(stop, scope), {})
                self.assertEqual(live.read_bytes(), reconciled)
                self.assertFalse(base.with_name("retry").exists())
                self.assertEqual(list((project / ".know/pending").iterdir()), [])

    def test_conflict_continuation_without_candidate_cleans_staging(self):
        install_global(self.codex_home, self.skills_dir)
        for first in ("global", "local"):
            with self.subTest(first=first):
                project = self.project(first + " abandoned repair")
                install(project)
                scopes = (None, project) if first == "global" else (project, None)
                for scope in scopes:
                    run(self.event(project), scope)
                base = next((project / ".know/pending").rglob("base.md"))
                base.with_name("candidate.md").write_bytes(
                    "# 已掌握\n\n## Topic\n- Unreconciled knowledge\n".encode())
                other_change = "# 已掌握\n\n## Topic\n- Already saved knowledge\n".encode()
                live = project / ".know/map.md"
                live.write_bytes(other_change)
                stop = self.event(project, "Stop")
                self.assertEqual(run(stop, scopes[0])["decision"], "block")
                self.assertEqual(run(stop, scopes[1]), {})
                self.assertTrue(base.with_name("retry").exists())
                stop["stop_hook_active"] = True
                for scope in scopes:
                    self.assertEqual(run(stop, scope), {})
                self.assertEqual(live.read_bytes(), other_change)
                self.assertFalse(base.with_name("retry").exists())
                self.assertEqual(list((project / ".know/pending").iterdir()), [])

    def test_unrelated_project_hooks_do_not_disable_global_cognition(self):
        project = self.project("other tools")
        (project / ".codex").mkdir()
        (project / ".codex/hooks.json").write_text(json.dumps({"hooks": {
            "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "echo other"}]}]
        }}), encoding="utf-8")
        self.context(self.event(project))
        self.assertEqual((project / ".know/map.md").read_bytes(), EMPTY.encode())

    def test_installed_global_command_runs_from_unseen_project(self):
        install_global(self.codex_home, self.skills_dir)
        config = json.loads((self.codex_home / "hooks.json").read_text(encoding="utf-8"))
        project = self.project("unseen project 中文")
        child = project / "nested folder"
        child.mkdir()
        for name in ("UserPromptSubmit", "Stop"):
            command = next(h["command"] for h in self.handlers(config, name)
                           if h.get("statusMessage") == "Project Cognition Map")
            completed = subprocess.run(command, shell=True, cwd=child,
                                       input=json.dumps(self.event(child, name)), text=True,
                                       encoding="utf-8", capture_output=True, check=True)
            output = json.loads(completed.stdout)
            if name == "UserPromptSubmit":
                self.assertIn("hookSpecificOutput", output)
            else:
                self.assertEqual(output, {})
        self.assertEqual((project / ".know/map.md").read_bytes(), EMPTY.encode())
        self.assertFalse((self.codex_home / ".know").exists())
        self.assertFalse((self.skills_dir / "adapt-project-explanations/.know").exists())
        self.assertEqual(list((project / ".know/pending").iterdir()), [])

    def test_missing_or_invalid_cwd_creates_no_map(self):
        missing = self.directory / "does not exist"
        file = self.directory / "not a directory.txt"
        file.write_text("ordinary file", encoding="utf-8")
        for cwd in (None, "", str(missing), str(file)):
            with self.subTest(cwd=cwd):
                event = self.event(self.directory)
                if cwd is None:
                    del event["cwd"]
                else:
                    event["cwd"] = cwd
                self.assertEqual(run(event), {})
        self.assertFalse(missing.exists())
        self.assertEqual(list(self.directory.rglob("map.md")), [])

    def test_home_without_project_does_not_become_global_memory(self):
        fake_home = self.project("home without project", git=False)
        with patch("hook.Path.home", return_value=fake_home):
            self.assertEqual(run(self.event(fake_home)), {})
            self.assertEqual(run(self.event(fake_home, "Stop")), {})
        self.assertFalse((fake_home / ".know").exists())

    def test_stop_before_first_message_creates_no_map(self):
        project = self.project("not used yet")
        self.assertEqual(run(self.event(project, "Stop")), {})
        self.assertFalse((project / ".know").exists())


if __name__ == "__main__":
    unittest.main()
