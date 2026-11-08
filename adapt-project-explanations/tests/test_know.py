import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
from know import EMPTY, validate
from hook import run
from install import install

MAP = "# 已掌握\n\n## KV cache\n- 前缀复用\n  - 相同文本在不同前文下的 KV 可能不同\n"


class CognitionTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name) / "a project 中文"
        self.project.mkdir()
        subprocess.run(["git", "init", "-q", str(self.project)], check=True)
        install(self.project)
        self.live = self.project / ".know/map.md"

    def event(self, name, turn="t1", **extra):
        return {"hook_event_name": name, "session_id": "s2" if turn == "t2" else "s1", "turn_id": turn,
                "cwd": str(self.project), **extra}

    def submit(self, turn="t1"):
        result = run(self.event("UserPromptSubmit", turn), self.project)
        candidates = sorted((self.project / ".know/pending").glob("*/*/base.md"))
        return result, candidates

    def candidate(self, turn="t1"):
        from know import digest
        session = "s2" if turn == "t2" else "s1"
        return self.project / ".know/pending" / digest(session.encode())[:32] / digest(turn.encode())[:32] / "candidate.md"

    def test_format(self):
        self.assertEqual(validate(MAP.encode()), MAP)
        self.assertEqual(validate(EMPTY.encode()), EMPTY)
        for text in (
            MAP.replace("- 前缀复用", "- [可直接讲] 前缀复用"),
            MAP + "解释段落\n",
            MAP.replace("  -", "   -"),
            MAP.replace("- 前缀复用\n", ""),
            MAP + "- 前缀复用\n",
            MAP.replace("\n", "\r\n"),
            MAP + "\n## 空主题\n",
        ):
            with self.subTest(text=text), self.assertRaises(ValueError):
                validate(text.encode())

    def test_install_preserves_existing_hooks_and_is_idempotent(self):
        path = self.project / ".codex/hooks.json"
        config = json.loads(path.read_text())
        other = {"hooks": [{"type": "command", "command": "echo existing"}]}
        config["hooks"]["UserPromptSubmit"].insert(0, other)
        path.write_text(json.dumps(config))
        install(self.project)
        install(self.project)
        actual = json.loads(path.read_text())
        self.assertEqual(len(actual["hooks"]["UserPromptSubmit"]), 2)
        self.assertEqual(actual["hooks"]["UserPromptSubmit"][0], other)
        self.assertEqual(len(actual["hooks"]["Stop"]), 1)
        self.assertIn("/.know/", (self.project / ".git/info/exclude").read_text())

    def test_installed_command_runs_with_spaces_and_in_subdirectory(self):
        config = json.loads((self.project / ".codex/hooks.json").read_text())
        command = config["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
        sub = self.project / "sub"
        sub.mkdir()
        event = self.event("UserPromptSubmit", cwd=str(sub))
        completed = subprocess.run(command, shell=True, cwd=sub, input=json.dumps(event),
                                   text=True, encoding="utf-8", capture_output=True, check=True)
        result = json.loads(completed.stdout)
        self.assertIn("# 已掌握", result["hookSpecificOutput"]["additionalContext"])

    def test_load_save_and_cleanup(self):
        result, _ = self.submit()
        self.assertIn("candidate.md", result["hookSpecificOutput"]["additionalContext"])
        self.candidate().write_bytes(MAP.encode())
        self.assertEqual(run(self.event("Stop"), self.project), {})
        self.assertEqual(self.live.read_text(encoding="utf-8"), MAP)
        self.assertEqual(list((self.project / ".know/pending").iterdir()), [])
        self.assertEqual(run(self.event("Stop"), self.project), {})

    def test_no_update_creates_no_history(self):
        self.submit()
        run(self.event("Stop"), self.project)
        self.assertEqual(self.live.read_text(encoding="utf-8"), EMPTY)
        self.assertEqual(list((self.project / ".know/pending").iterdir()), [])

    def test_invalid_candidate_retries_once_and_preserves_map(self):
        self.submit()
        self.candidate().write_text("bad")
        result = run(self.event("Stop"), self.project)
        self.assertEqual(result["decision"], "block")
        result = run(self.event("Stop", stop_hook_active=True), self.project)
        self.assertIn("systemMessage", result)
        self.assertEqual(self.live.read_text(encoding="utf-8"), EMPTY)

    def test_two_turns_cannot_overwrite_each_other(self):
        self.submit("t1")
        self.submit("t2")
        self.candidate("t1").write_bytes(MAP.encode())
        self.candidate("t2").write_bytes(MAP.replace("前缀复用", "块分配").encode())
        run(self.event("Stop", "t1"), self.project)
        result = run(self.event("Stop", "t2"), self.project)
        self.assertEqual(result["decision"], "block")
        self.assertFalse(self.candidate("t2").exists())
        self.assertEqual(self.live.read_text(encoding="utf-8"), MAP)
        self.candidate("t2").write_bytes((MAP + "- 块分配\n").encode())
        run(self.event("Stop", "t2", stop_hook_active=True), self.project)
        self.assertEqual(self.live.read_text(encoding="utf-8"), MAP + "- 块分配\n")

    def test_repeated_question_can_remove_overstated_entry(self):
        self.live.write_bytes(MAP.encode())
        self.submit()
        self.candidate().write_bytes(EMPTY.encode())
        run(self.event("Stop"), self.project)
        self.assertEqual(self.live.read_text(encoding="utf-8"), EMPTY)

    def test_other_project_is_ignored(self):
        self.assertEqual(run(self.event("UserPromptSubmit", cwd="/tmp"), self.project), {})

    def test_missing_turn_id_is_reported(self):
        event = self.event("UserPromptSubmit")
        del event["turn_id"]
        self.assertIn("systemMessage", run(event, self.project))

    def test_install_keeps_other_handlers_in_same_group(self):
        path = self.project / ".codex/hooks.json"
        config = json.loads(path.read_text())
        other = {"type": "command", "command": "echo unrelated"}
        config["hooks"]["Stop"][0]["hooks"].append(other)
        config["hooks"]["Stop"][0]["matcher"] = "preserved"
        path.write_text(json.dumps(config))
        install(self.project)
        first = path.read_bytes()
        install(self.project)
        self.assertEqual(path.read_bytes(), first)
        self.assertEqual(json.loads(first)["hooks"]["Stop"][0],
                         {"matcher": "preserved", "hooks": [other]})

    def test_interrupted_session_cleans_only_its_previous_turn(self):
        self.submit("t1")
        self.submit("t2")  # Another session is still active.
        self.candidate("t1").write_bytes(MAP.encode())
        run(self.event("UserPromptSubmit", "resumed"), self.project)
        self.assertFalse(self.candidate("t1").parent.exists())
        self.assertTrue(self.candidate("t2").with_name("base.md").exists())
        self.assertEqual(self.live.read_bytes(), EMPTY.encode())
        run(self.event("Stop", "t1"), self.project)  # Delayed old event is harmless.
        self.assertEqual(self.live.read_bytes(), EMPTY.encode())

    def test_duplicate_submit_preserves_original_base(self):
        self.submit()
        self.live.write_bytes(MAP.encode())
        self.submit()
        self.assertEqual(self.candidate().with_name("base.md").read_bytes(), EMPTY.encode())
        self.candidate().write_bytes((MAP + "- 块分配\n").encode())
        self.assertEqual(run(self.event("Stop"), self.project)["decision"], "block")
        self.assertEqual(self.live.read_bytes(), MAP.encode())

    def test_identical_candidate_does_not_rewrite_live_map(self):
        self.submit()
        before = self.live.stat().st_mtime_ns
        self.candidate().write_bytes(EMPTY.encode())
        self.assertEqual(run(self.event("Stop"), self.project), {})
        self.assertEqual(self.live.stat().st_mtime_ns, before)

    def test_second_failure_cleans_staging(self):
        self.submit()
        self.candidate().write_bytes(b"bad")
        run(self.event("Stop"), self.project)
        run(self.event("Stop", stop_hook_active=True), self.project)
        self.assertFalse(self.candidate().parent.exists())
        self.assertEqual(self.live.read_bytes(), EMPTY.encode())

    def test_nested_project_does_not_load_parent_map(self):
        nested = self.project / "nested"
        nested.mkdir()
        install(nested)
        event = self.event("UserPromptSubmit", cwd=str(nested))
        self.assertEqual(run(event, self.project), {})
        self.assertIn("hookSpecificOutput", run(event, nested))

    def test_parallel_stop_processes_do_not_lose_updates(self):
        self.submit("t1")
        self.submit("t2")
        one = MAP.encode()
        two = MAP.replace("前缀复用", "块分配").encode()
        self.candidate("t1").write_bytes(one)
        self.candidate("t2").write_bytes(two)
        processes = []
        for turn in ("t1", "t2"):
            p = subprocess.Popen([sys.executable, "-X", "utf8", str(SCRIPTS / "hook.py"),
                                  "--project", str(self.project)], stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 text=True, encoding="utf-8")
            p.stdin.write(json.dumps(self.event("Stop", turn)))
            p.stdin.close()
            p.stdin = None
            processes.append(p)
        outputs = []
        for p in processes:
            stdout, stderr = p.communicate(timeout=10)
            self.assertEqual(p.returncode, 0, stderr)
            outputs.append(json.loads(stdout))
        self.assertEqual(sum(o.get("decision") == "block" for o in outputs), 1)
        self.assertIn(self.live.read_bytes(), (one, two))

    def test_missing_cwd_does_not_use_process_working_directory(self):
        event = self.event("UserPromptSubmit")
        del event["cwd"]
        self.assertEqual(run(event, self.project), {})


if __name__ == "__main__":
    unittest.main()
