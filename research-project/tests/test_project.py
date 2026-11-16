"""Tests for scripts/project.py in temporary projects."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
TOOL = SKILL / "scripts" / "project.py"
DATE = "2026-11-16"


def run(*args):
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True)


class ProjectTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "proj"
        result = run("init", str(self.root), "--name", "demo", "--date", DATE)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for key, value in (("user.email", "t@example.com"), ("user.name", "t"), ("commit.gpgsign", "false")):
            self.git("config", key, value)
        self.commit("init")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        result = subprocess.run(["git", *args], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def check(self):
        return run("check", "--root", str(self.root))

    def new(self, slug="lr", kind="ablation"):
        result = run("new", slug, "--type", kind, "--date", DATE, "--root", str(self.root))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return self.root / "experiments" / "{}-{}".format(DATE, slug)

    def edit(self, relative, old, new):
        path = self.root / relative
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new), encoding="utf-8")

    def assert_error(self, fragment):
        result = self.check()
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn(fragment, result.stdout)

    def test_init_creates_layout_and_fills_placeholders(self):
        for relative in ("AGENTS.md", "CLAUDE.md", "STATE.md", "EXPERIMENTS.md", ".gitignore",
                         "docs/PROJECT.md", "docs/DATA.md", "docs/PIPELINE.md", "docs/DECISIONS.md",
                         "configs/trunk.yaml", "src/demo/__init__.py", "tools/project.py"):
            self.assertTrue((self.root / relative).is_file(), relative)
        agents = (self.root / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("src/demo/", agents)
        self.assertNotIn("{{", agents)
        self.assertIn(DATE, (self.root / "STATE.md").read_text(encoding="utf-8"))

    def test_init_never_overwrites(self):
        (self.root / "STATE.md").write_text("mine\n", encoding="utf-8")
        result = run("init", str(self.root), "--name", "demo")
        self.assertEqual(result.returncode, 0)
        self.assertIn("跳过：STATE.md", result.stdout)
        self.assertEqual((self.root / "STATE.md").read_text(encoding="utf-8"), "mine\n")

    def test_fresh_project_passes_with_warnings(self):
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("主干未锁定", result.stdout)

    def test_templates_fit_their_line_limits(self):
        self.assertNotIn("上限", self.check().stdout.replace("上限 5 项", ""))

    def test_copied_tool_works_inside_project(self):
        result = subprocess.run([sys.executable, "tools/project.py", "check"], cwd=self.root,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_new_creates_card_and_row(self):
        directory = self.new()
        self.assertTrue((directory / "CARD.md").is_file())
        registry = (self.root / "EXPERIMENTS.md").read_text(encoding="utf-8")
        self.assertIn("| {}-lr | ablation |".format(DATE), registry)
        self.commit("card")
        self.assertEqual(self.check().returncode, 0, self.check().stdout)
        self.assertNotEqual(run("new", "lr", "--type", "ablation", "--date", DATE,
                                "--root", str(self.root)).returncode, 0)

    def test_extra_markdown_is_error(self):
        (self.root / "NOTES.md").write_text("x\n", encoding="utf-8")
        self.assert_error("多余的 Markdown 文件：NOTES.md")

    def test_ignored_and_scratch_markdown_are_allowed(self):
        (self.root / "scratch" / "notes.md").write_text("x\n", encoding="utf-8")
        self.assertEqual(self.check().returncode, 0)

    def test_line_limit_is_error(self):
        with open(self.root / "STATE.md", "a", encoding="utf-8") as handle:
            handle.write("x\n" * 40)
        self.assert_error("STATE.md 有")

    def test_uncommitted_code_is_error(self):
        (self.root / "src" / "demo" / "model.py").write_text("x = 1\n", encoding="utf-8")
        self.assert_error("未提交或未跟踪")
        self.commit("code")
        self.assertEqual(self.check().returncode, 0)

    def test_trunk_commit_must_exist(self):
        self.edit("STATE.md", "- commit：【待填】", "- commit：deadbeef")
        self.commit("state")
        self.assert_error("主干 commit deadbeef 不存在")
        head = self.git("rev-parse", "--short", "HEAD").strip()
        self.edit("STATE.md", "deadbeef", head)
        self.commit("state")
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("主干未锁定", result.stdout)

    def test_stale_state_is_warning(self):
        self.edit("STATE.md", "更新：" + DATE, "更新：2020-01-01")
        self.commit("old state")
        result = self.check()
        self.assertEqual(result.returncode, 0)
        self.assertIn("早于最近一次提交", result.stdout)

    def test_queue_limit(self):
        self.edit("STATE.md", "## 排队（最多 5 项）\n\n（暂无）",
                  "## 排队（最多 5 项）\n\n" + "".join("- q{}\n".format(i) for i in range(6)))
        self.assert_error("排队有 6 项")

    def test_experiment_needs_card_row_and_result(self):
        (self.root / "experiments" / "orphan").mkdir()
        (self.root / "experiments" / "orphan" / "x.txt").write_text("x\n", encoding="utf-8")
        result = self.check()
        self.assertIn("experiments/orphan 没有 CARD.md", result.stdout)
        self.assertIn("experiments/orphan 没有登记", result.stdout)
        self.assertEqual(result.returncode, 1)

    def test_done_requires_result_json(self):
        directory = self.new()
        self.edit("EXPERIMENTS.md", "| queued |", "| done |")
        self.assert_error("没有 result.json")
        (directory / "result.json").write_text("{}\n", encoding="utf-8")
        self.assertEqual(self.check().returncode, 0)

    def test_two_running_is_warning(self):
        self.new("a")
        self.new("b")
        text = (self.root / "EXPERIMENTS.md").read_text(encoding="utf-8").replace("| queued |", "| running |")
        (self.root / "EXPERIMENTS.md").write_text(text, encoding="utf-8")
        self.assertIn("同时是 running", self.check().stdout)

    def test_large_tracked_file_is_error(self):
        (self.root / "experiments" / "big.bin").write_bytes(b"0" * (1024 * 1024 + 1))
        self.commit("big")
        self.assert_error("超过 1024 KB")


if __name__ == "__main__":
    unittest.main()
