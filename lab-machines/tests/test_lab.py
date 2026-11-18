"""Tests for scripts/lab.py in temporary repositories. Two clones of one bare remote stand in for two machines."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

LAB = Path(__file__).resolve().parent.parent / "scripts" / "lab.py"


def run(*args, machine=None, cwd=None, hub=None, home=None):
    env = {**os.environ}
    env.pop("LAB_HUB", None)
    env["HOME"] = str(home or tempfile.gettempdir())  # keeps the real ~/.config/lab out of the tests
    if machine:
        env["LAB_MACHINE"] = machine
    if hub:
        env["LAB_HUB"] = str(hub)
    return subprocess.run([sys.executable, str(LAB), *args], capture_output=True, text=True, env=env, cwd=cwd)


def sh(cwd, *cmd):
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return result.stdout


def identity(repo):
    for key, value in (("user.email", "lab@example.com"), ("user.name", "lab"), ("commit.gpgsign", "false")):
        sh(repo, "git", "config", key, value)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.base = base
        self.root, self.remote, self.other = base / "mac" / "proj", base / "remote.git", base / "pc" / "proj"
        self.root.mkdir(parents=True)
        sh(base, "git", "init", "-q", "--bare", str(self.remote))
        sh(self.root, "git", "init", "-q")
        identity(self.root)
        (self.root / ".gitignore").write_text("/runs/\n", encoding="utf-8")
        (self.root / "train.py").write_text("print('hi')\n", encoding="utf-8")
        (self.root / "STATE.md").write_text("state\n", encoding="utf-8")
        sh(self.root, "git", "add", "-A")
        sh(self.root, "git", "commit", "-q", "-m", "init")
        sh(self.root, "git", "remote", "add", "origin", str(self.remote))
        sh(self.root, "git", "push", "-q", "-u", "origin", "HEAD")
        sh(base, "git", "clone", "-q", str(self.remote), str(self.other))
        identity(self.other)

    def tearDown(self):
        self.tmp.cleanup()

    def lab(self, *args, **kw):
        return run(*args, cwd=self.root, **kw)

    def push_from_other(self, message, path=None, text=None):
        sh(self.other, "git", "pull", "-q", "--rebase")
        if path:
            (self.other / path).write_text(text, encoding="utf-8")
            sh(self.other, "git", "add", path)
        sh(self.other, "git", "commit", "-q", "--allow-empty", "-m", message)
        sh(self.other, "git", "push", "-q")


class RunTest(Base):
    def test_run_start_end_runs_and_journal(self):
        (self.root / "train.py").write_text("print('changed')\n", encoding="utf-8")
        refused = self.lab("run", "start", "E1", "--no-push", "--", "python", "train.py", machine="pc")
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn("未提交", refused.stderr)
        (self.root / "STATE.md").write_text("only docs changed\n", encoding="utf-8")  # Markdown never blocks
        sh(self.root, "git", "commit", "-q", "-am", "code")
        started = self.lab("run", "start", "E1", "--", "python", "train.py", machine="pc")
        self.assertEqual(started.returncode, 0, started.stdout + started.stderr)
        self.assertNotIn("WARN", started.stdout)
        records = list((self.root / ".lab" / "runs").glob("*.json"))
        self.assertEqual(len(records), 1)
        record = json.loads(records[0].read_text(encoding="utf-8"))
        self.assertEqual((record["machine"], record["status"], record["exp"], record["command"]),
                         ("pc", "running", "E1", "python train.py"))
        self.assertEqual((Path(record["code_dir"]) / "train.py").read_text(encoding="utf-8"), "print('changed')\n")
        self.assertTrue(Path(record["code_dir"]).is_relative_to((self.root / "runs").resolve()))
        self.assertIn(record["run_id"], self.lab("runs", "--active").stdout)
        self.assertIn(record["run_id"], self.lab("status").stdout)
        ended = self.lab("run", "end", record["run_id"], "--status", "done", "--outputs", "/data/x", machine="pc")
        self.assertEqual(ended.returncode, 0, ended.stderr)
        record = json.loads(records[0].read_text(encoding="utf-8"))
        self.assertEqual((record["status"], record["outputs"]), ("done", "/data/x"))
        self.assertEqual(self.lab("runs", "--active").stdout.count(record["run_id"]), 0)
        self.assertEqual(self.lab("log", "downloaded", "dinov2", machine="cluster").returncode, 0)
        journal = self.lab("journal").stdout
        self.assertIn(f"run[pc](E1): start {record['run_id']}", journal)
        self.assertIn("log[cluster]: downloaded dinov2", journal)
        self.assertEqual(self.lab("journal", "--machine", "cluster").stdout.count("\n"), 1)

    def test_unknown_machine_and_bad_exp_are_rejected(self):
        self.assertIn("不知道本机", self.lab("run", "start", "E1", "--", "echo", machine="").stderr)
        self.assertNotEqual(self.lab("run", "start", "../x", "--", "echo", machine="pc").returncode, 0)

    def test_untracked_code_blocks_a_run_and_unignored_runs_warns(self):
        (self.root / "new_model.py").write_text("x = 1\n", encoding="utf-8")
        self.assertIn("未提交", self.lab("run", "start", "E1", "--no-push", "--", "echo", machine="pc").stderr)
        (self.root / "new_model.py").unlink()
        (self.root / ".gitignore").write_text("", encoding="utf-8")
        sh(self.root, "git", "commit", "-q", "-am", "stop ignoring runs")
        result = self.lab("run", "start", "E2", "--no-push", "--", "echo", machine="pc")
        self.assertIn("没有被 git 忽略", result.stdout)

    def test_runs_root_can_be_moved_outside_the_repo(self):
        outside = self.base / "runs_root"
        env_run = subprocess.run([sys.executable, str(LAB), "run", "start", "E1", "--no-push", "--", "echo", "x"],
                                 cwd=self.root, capture_output=True, text=True,
                                 env={**os.environ, "LAB_MACHINE": "pc", "LAB_RUNS_ROOT": str(outside), "HOME": self.tmp.name})
        self.assertEqual(env_run.returncode, 0, env_run.stderr)
        self.assertNotIn("WARN", env_run.stdout)
        self.assertEqual(len(list((outside / "E1").glob("E1-*-pc/code/train.py"))), 1)

    def test_log_refuses_when_changes_are_staged(self):
        (self.root / "STATE.md").write_text("staged\n", encoding="utf-8")
        sh(self.root, "git", "add", "STATE.md")
        result = self.lab("log", "note", "--no-push", machine="mac")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("已暂存", result.stderr)


class SyncTest(Base):
    def test_push_rebases_when_another_machine_pushed_first(self):
        self.push_from_other("log[pc]: from pc")
        result = self.lab("log", "from", "mac", machine="mac")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("已拉取其他机器的更新并推送", result.stdout)
        subjects = sh(self.remote, "git", "log", "--format=%s")
        self.assertIn("log[pc]: from pc", subjects)
        self.assertIn("log[mac]: from mac", subjects)

    def test_read_commands_pull_first(self):
        self.push_from_other("log[cluster]: downloaded weights")
        self.assertIn("log[cluster]: downloaded weights", self.lab("journal").stdout)
        sh(self.root, "git", "reset", "-q", "--hard", "HEAD~1")
        self.assertNotIn("downloaded weights", self.lab("journal", "--no-pull").stdout)

    def test_sync_pushes_local_commits_and_aborts_on_conflict(self):
        sh(self.root, "git", "commit", "-q", "--allow-empty", "-m", "log[mac]: local only")
        self.assertEqual(self.lab("sync").returncode, 0)
        self.assertIn("log[mac]: local only", sh(self.remote, "git", "log", "--format=%s"))
        self.push_from_other("docs[pc]: edit", "STATE.md", "pc version\n")
        (self.root / "STATE.md").write_text("mac version\n", encoding="utf-8")
        sh(self.root, "git", "commit", "-q", "-am", "docs[mac]: edit")
        result = self.lab("sync")
        self.assertEqual(result.returncode, 1)
        self.assertIn("自动 rebase 失败", result.stdout)
        self.assertEqual((self.root / "STATE.md").read_text(encoding="utf-8"), "mac version\n")
        self.assertFalse((self.root / ".git" / "rebase-merge").exists() or (self.root / ".git" / "rebase-apply").exists())

    def test_sync_refuses_with_uncommitted_changes(self):
        (self.root / "STATE.md").write_text("dirty\n", encoding="utf-8")
        result = self.lab("sync")
        self.assertEqual(result.returncode, 1)
        self.assertIn("未提交", result.stdout)


class HubTest(Base):
    def test_outside_a_repo_falls_back_to_the_hub(self):
        elsewhere = self.base / "not-a-repo"
        elsewhere.mkdir()
        result = run("log", "installed", "uv", "--no-push", machine="pc", cwd=elsewhere, hub=self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("log[pc]: installed uv", sh(self.root, "git", "log", "-1", "--format=%s"))
        self.assertIn("installed uv", run("journal", "--no-pull", cwd=elsewhere, hub=self.root).stdout)

    def test_inside_a_repo_the_repo_wins_and_hub_flag_overrides(self):
        hub = self.base / "hub"
        hub.mkdir()
        sh(hub, "git", "init", "-q")
        identity(hub)
        result = run("log", "in project", "--no-push", machine="mac", cwd=self.root, hub=hub)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("in project", sh(self.root, "git", "log", "-1", "--format=%s"))
        result = run("log", "in hub", "--hub", "--no-push", machine="mac", cwd=self.root, hub=hub)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("in hub", sh(hub, "git", "log", "-1", "--format=%s"))

    def test_no_repo_and_no_hub_is_an_error(self):
        elsewhere = self.base / "nowhere"
        elsewhere.mkdir()
        result = run("journal", cwd=elsewhere)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("总台", result.stderr)


if __name__ == "__main__":
    unittest.main()
