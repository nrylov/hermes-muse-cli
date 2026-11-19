import importlib.util
import json
import os
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = importlib.util.spec_from_file_location(
    "muse_run", os.path.join(HERE, "..", "skills", "muse-cli", "scripts", "muse_run.py"))
muse_run = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(muse_run)

FIXTURE = os.path.join(HERE, "fixtures", "exec_sample.jsonl")


def fixture_text():
    with open(FIXTURE) as f:
        return f.read()


class BuildCommand(unittest.TestCase):
    def test_flags(self):
        cmd = muse_run.build_command("/tmp/p.txt", "never", 7)
        self.assertEqual(cmd[:2], ["muse", "exec"])
        self.assertIn("--json", cmd)
        self.assertEqual(cmd[cmd.index("--prompt-file") + 1], "/tmp/p.txt")
        self.assertEqual(cmd[cmd.index("--approval-mode") + 1], "never")
        self.assertEqual(cmd[cmd.index("--max-model-steps") + 1], "7")
        self.assertNotIn("--model", cmd)


class Summarize(unittest.TestCase):
    def test_fixture(self):
        s = muse_run.summarize(fixture_text())
        self.assertEqual(s["terminal"], "completed")
        self.assertIn("a+b", s["text"])
        self.assertEqual(s["calls"], 6)
        self.assertEqual(s["failed_calls"], 0)
        self.assertEqual(s["models"][0]["model"], "muse-spark-1.3")
        self.assertEqual(s["session_id"], "01a1f3fc-b285-7942-ba2f-1e9a342e72b7")

    def test_missing_terminal_raises(self):
        with self.assertRaises(ValueError):
            muse_run.summarize('{"payload_type": "run.usage", "payload": {}}')

    def test_malformed_line_raises(self):
        with self.assertRaises(ValueError):
            muse_run.summarize("not json")


class Run(unittest.TestCase):
    def test_rejects_non_repo(self):
        with tempfile.TemporaryDirectory() as d:
            res = muse_run.run("/tmp/x", d)
            self.assertFalse(res["ok"])
            self.assertIn("not a git repo", res["error"])

    def test_non_completed_terminal_is_not_ok(self):
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, ".git"))
            cancelled = fixture_text().replace('"terminal": "completed"', '"terminal": "cancelled"')
            orig = muse_run.subprocess.run
            orig_which = muse_run.shutil.which

            class P:
                returncode = 0
                stdout = cancelled
                stderr = ""

            muse_run.subprocess.run = lambda *a, **k: P() if a[0][0] == "muse" else orig(*a, **k)
            muse_run.shutil.which = lambda name: "/bin/muse"  # stub: CI has no muse binary
            try:
                res = muse_run.run("/tmp/x", d)
            finally:
                muse_run.subprocess.run = orig
                muse_run.shutil.which = orig_which
            self.assertFalse(res["ok"])
            self.assertEqual(res["terminal"], "cancelled")


if __name__ == "__main__":
    unittest.main()
