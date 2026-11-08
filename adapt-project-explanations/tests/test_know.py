import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "know.py"
PROJECT = "vllm-kv"
EMPTY = "# Project Cognition Map\nProject: vllm-kv\n"
TOPIC = EMPTY + "\n## 前缀复用\n"
DIRECT = "- [可直接讲] 前缀一致性与连续命中 <!-- prefix-match | used | s01:t02 -->\n"
FRONTIER = "  - [待厘清] 未填满的块能否跨请求复用 <!-- partial-block | frontier | s01:t04 -->\n"
BRIDGE = "- [补桥] 命中对首 token 与后续生成延迟的影响 <!-- latency-scope | repeated | s01:t06, s01:t08 -->\n"
CONTINUED = BRIDGE.replace("[补桥]", "[可直接讲]").replace(
    "repeated | s01:t06, s01:t08", "continued | s01:t10, s01:t12"
)
REOPENED = BRIDGE.replace("repeated | s01:t06, s01:t08", "reopened | s02:t01")
TURN_IDS = [f"s01:t{i:02d}" for i in (2, 4, 6, 8, 10, 12)] + ["s02:t01"]


class KnowCliTest(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        self.map = root / "map.md"
        self.candidate = root / "candidate.md"
        self.index = root / "user-turns.json"
        self.set_map(EMPTY)
        self.write_index(PROJECT, TURN_IDS)

    def set_map(self, text):
        self.map.write_bytes(text.encode("utf-8"))

    def write_index(self, project, turns):
        self.index.write_text(json.dumps({"project": project, "user_turns": turns}), encoding="utf-8")

    def run_cli(self, *args):
        return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True)

    def validate(self, project=PROJECT):
        return self.run_cli("validate", self.map, "--project", project)

    def apply(self, proposed, snapshot=None):
        self.candidate.write_bytes(proposed.encode("utf-8"))
        if snapshot is None:
            snapshot = self.map.read_bytes()
        return self.run_cli(
            "apply", self.map, "--project", PROJECT, "--candidate", self.candidate,
            "--expected-sha256", hashlib.sha256(snapshot).hexdigest(), "--user-turns", self.index,
        )

    def assert_refused(self, proposed, message, snapshot=None):
        before = self.map.read_bytes()
        result = self.apply(proposed, snapshot)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn(message, result.stderr)
        self.assertEqual(self.map.read_bytes(), before)

    def test_valid_sample_and_empty_map(self):
        sample = (ROOT / "references" / "map.example.md").read_text(encoding="utf-8")
        self.assertEqual(sample, TOPIC + DIRECT + FRONTIER + BRIDGE)
        for text in (EMPTY, sample):
            self.set_map(text)
            result = self.validate()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), hashlib.sha256(text.encode()).hexdigest())

    def test_rejects_malformed_maps(self):
        active = TOPIC + BRIDGE
        rows = {
            "line ending": active.replace("\n", "\r\n"),
            "final newline": active[:-1],
            "metadata": TOPIC + "- [补桥] 项目边界\n",
            "bad state": active.replace("[补桥]", "[待厘清]"),
            "missing evidence": active.replace(", s01:t08", ""),
            "duplicate evidence": active.replace("s01:t08", "s01:t06"),
            "duplicate entry": active + BRIDGE,
            "duplicate topic": active + "\n## 前缀复用\n" + BRIDGE,
            "empty topic": active + "\n## 空主题\n",
            "oversized label": active.replace("命中对首", "x" * 57),
            "orphan": TOPIC + FRONTIER,
            "odd indent": TOPIC + DIRECT + FRONTIER[1:],
            "skipped level": TOPIC + DIRECT + "  " + FRONTIER,
            "excessive depth": TOPIC + DIRECT + "".join("  " * i + DIRECT for i in range(1, 5)),
            "too many boundaries": TOPIC + "".join(
                DIRECT.replace("prefix-match", f"topic-{i}") for i in range(25)
            ),
        }
        for name, text in rows.items():
            with self.subTest(name=name):
                self.set_map(text)
                result = self.validate()
                self.assertEqual(result.returncode, 1, result.stderr)

    def test_rejects_wrong_project(self):
        self.assertIn("project mismatch", self.validate("other-project").stderr)

    def test_full_reminder_lifecycle(self):
        for entry in (BRIDGE, CONTINUED, REOPENED):
            proposed = TOPIC + entry
            result = self.apply(proposed)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(self.map.read_bytes(), proposed.encode())

    def test_direct_after_independent_use(self):
        self.set_map(TOPIC + BRIDGE)
        proposed = TOPIC + BRIDGE.replace("[补桥]", "[可直接讲]").replace(
            "repeated | s01:t06, s01:t08", "used | s01:t10"
        )
        result = self.apply(proposed)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_adds_child_without_changing_parent(self):
        self.set_map(TOPIC + DIRECT)
        result = self.apply(TOPIC + DIRECT + FRONTIER)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.map.read_bytes(), (TOPIC + DIRECT + FRONTIER).encode())

    def test_requires_an_established_direct_parent(self):
        self.assert_refused(TOPIC + FRONTIER.lstrip(), "requires a direct parent")
        self.set_map(TOPIC + BRIDGE)
        child = FRONTIER.replace("s01:t04", "s01:t10")
        self.assert_refused(TOPIC + BRIDGE + child, "requires a direct parent")
        self.set_map(TOPIC + DIRECT)
        self.assert_refused(TOPIC + DIRECT + FRONTIER.replace("s01:t04", "s01:t02"), "chronological")

    def test_promotes_child_after_second_question(self):
        self.set_map(TOPIC + DIRECT + FRONTIER)
        repeated = FRONTIER.replace("[待厘清]", "[补桥]").replace(
            "frontier | s01:t04", "repeated | s01:t04, s01:t06"
        )
        result = self.apply(TOPIC + DIRECT + repeated)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_rejects_fake_or_cross_project_evidence(self):
        self.assert_refused(TOPIC + BRIDGE.replace("s01:t08", "s01:t99"), "evidence missing")
        self.write_index("other-project", ["s01:t06", "s01:t08"])
        self.assert_refused(TOPIC + BRIDGE, "index project mismatch")

    def test_rejects_stale_or_reused_evidence(self):
        self.set_map(TOPIC + BRIDGE)
        self.assert_refused(TOPIC + CONTINUED, "map changed since validation", EMPTY.encode())
        self.assert_refused(TOPIC + CONTINUED.replace("s01:t10", "s01:t08"), "chronological")

    def test_rejects_unsupported_changes(self):
        self.assert_refused(TOPIC + CONTINUED, "invalid reason for a new boundary")
        self.assert_refused(TOPIC + DIRECT + BRIDGE, "exactly one")
        self.set_map(TOPIC + BRIDGE)
        self.assert_refused(EMPTY, "cannot remove")
        self.assert_refused(TOPIC + CONTINUED.replace("token", "tokens"), "cannot rewrite")
        self.set_map(TOPIC + DIRECT + BRIDGE)
        self.assert_refused(TOPIC + CONTINUED + DIRECT, "cannot reorder")

    def test_repeat_application_is_idempotent(self):
        self.set_map(TOPIC + BRIDGE)
        result = self.apply(TOPIC + BRIDGE, EMPTY.encode())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "unchanged")


if __name__ == "__main__":
    unittest.main()
