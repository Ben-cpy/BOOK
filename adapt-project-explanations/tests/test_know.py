import importlib.util
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
        self.project = Path(self.temporary.name) / "a project"
        self.project.mkdir()
        subprocess.run(["git", "init", "-q", str(self.project)], check=True)
        install(self.project)
        self.live = self.project / ".know/map.md"

    def event(self, name, turn="t1", **extra):
        return {"hook_event_name": name, "session_id": "s1", "turn_id": turn,
                "cwd": str(self.project), **extra}

    def submit(self, turn="t1"):
        result = run(self.event("UserPromptSubmit", turn), self.project)
        candidates = sorted((self.project / ".know/pending").glob("*/base.md"))
        return result, candidates

    def candidate(self, turn="t1"):
        from know import digest
        key = digest(json.dumps(["s1", turn]).encode())[:32]
        return self.project / ".know/pending" / key / "candidate.md"

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
                                   text=True, capture_output=True, check=True)
        result = json.loads(completed.stdout)
        self.assertIn("# 已掌握", result["hookSpecificOutput"]["additionalContext"])

    def test_load_save_and_cleanup(self):
        result, _ = self.submit()
        self.assertIn("candidate.md", result["hookSpecificOutput"]["additionalContext"])
        self.candidate().write_text(MAP)
        self.assertEqual(run(self.event("Stop"), self.project), {})
        self.assertEqual(self.live.read_text(), MAP)
        self.assertEqual(list((self.project / ".know/pending").iterdir()), [])
        self.assertEqual(run(self.event("Stop"), self.project), {})

    def test_no_update_creates_no_history(self):
        self.submit()
        run(self.event("Stop"), self.project)
        self.assertEqual(self.live.read_text(), EMPTY)
        self.assertEqual(list((self.project / ".know/pending").iterdir()), [])

    def test_invalid_candidate_retries_once_and_preserves_map(self):
        self.submit()
        self.candidate().write_text("bad")
        result = run(self.event("Stop"), self.project)
        self.assertEqual(result["decision"], "block")
        result = run(self.event("Stop", stop_hook_active=True), self.project)
        self.assertIn("systemMessage", result)
        self.assertEqual(self.live.read_text(), EMPTY)

    def test_two_turns_cannot_overwrite_each_other(self):
        self.submit("t1")
        self.submit("t2")
        self.candidate("t1").write_text(MAP)
        self.candidate("t2").write_text(MAP.replace("前缀复用", "块分配"))
        run(self.event("Stop", "t1"), self.project)
        result = run(self.event("Stop", "t2"), self.project)
        self.assertEqual(result["decision"], "block")
        self.assertFalse(self.candidate("t2").exists())
        self.assertEqual(self.live.read_text(), MAP)
        self.candidate("t2").write_text(MAP + "- 块分配\n")
        run(self.event("Stop", "t2", stop_hook_active=True), self.project)
        self.assertEqual(self.live.read_text(), MAP + "- 块分配\n")

    def test_repeated_question_can_remove_overstated_entry(self):
        self.live.write_text(MAP)
        self.submit()
        self.candidate().write_text(EMPTY)
        run(self.event("Stop"), self.project)
        self.assertEqual(self.live.read_text(), EMPTY)

    def test_other_project_is_ignored(self):
        self.assertEqual(run(self.event("UserPromptSubmit", cwd="/tmp"), self.project), {})

    def test_missing_turn_id_is_reported(self):
        event = self.event("UserPromptSubmit")
        del event["turn_id"]
        self.assertIn("systemMessage", run(event, self.project))


if __name__ == "__main__":
    unittest.main()
