"""Tests for scripts/project.py in temporary projects."""
import os
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
        self.assertIn("早于本项目最近一次提交", result.stdout)

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


    def test_trunk_tag_must_exist_and_match_commit(self):
        head = self.git("rev-parse", "--short", "HEAD").strip()
        self.edit("STATE.md", "- tag：【待填，例如 trunk-v1】", "- tag：trunk-v1")
        self.edit("STATE.md", "- commit：【待填】", "- commit：" + head)
        self.assert_error("主干 tag trunk-v1 不存在")
        self.git("tag", "trunk-v1", head)
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.commit("state")
        self.edit("STATE.md", "- commit：" + head, "- commit：" + self.git("rev-parse", "--short", "HEAD").strip())
        self.assert_error("不一致")

    def test_single_project_needs_no_tag_prefix(self):
        self.assertIn("例如 trunk-v1】", (self.root / "STATE.md").read_text(encoding="utf-8"))
        self.assertIn("打 tag `trunk-v<N>`", (self.root / "AGENTS.md").read_text(encoding="utf-8"))


class SubProjectTest(unittest.TestCase):
    """Several projects share one repository, e.g. reproduce_idea/paper_repro/{repa,rae}."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "reproduce_idea"
        self.repo.mkdir()
        self.git("init", "-q")
        for key, value in (("user.email", "t@example.com"), ("user.name", "t"), ("commit.gpgsign", "false")):
            self.git("config", key, value)
        (self.repo / "AGENTS.md").write_text("# 总规则\n", encoding="utf-8")
        for name in ("repa", "rae"):
            result = run("init", str(self.repo / "paper_repro" / name), "--name", name, "--date", DATE)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("paper_repro/{}/trunk-v<N>".format(name), result.stdout)
        self.repa = self.repo / "paper_repro" / "repa"
        self.commit("init", "{} 12:00:00".format(DATE))

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args, date=None):
        env = dict(os.environ, GIT_COMMITTER_DATE=date, GIT_AUTHOR_DATE=date) if date else None
        result = subprocess.run(["git", *args], cwd=self.repo, capture_output=True, text=True, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def commit(self, message, date):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message, date=date)

    def check(self, project):
        return run("check", "--root", str(project))

    def edit(self, path, old, new):
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new), encoding="utf-8")

    def test_init_reuses_outer_repo_and_writes_prefix(self):
        self.assertFalse((self.repa / ".git").exists())
        self.assertIn("例如 paper_repro/repa/trunk-v1】", (self.repa / "STATE.md").read_text(encoding="utf-8"))
        self.assertIn("`paper_repro/repa/trunk-v<N>`", (self.repa / "AGENTS.md").read_text(encoding="utf-8"))

    def test_check_scope_is_the_sub_project(self):
        (self.repo / "NOTES.md").write_text("x\n", encoding="utf-8")
        (self.repo / "paper_repro" / "rae" / "src" / "rae" / "model.py").write_text("x = 1\n", encoding="utf-8")
        result = self.check(self.repa)
        self.assertEqual(result.returncode, 0, result.stdout)
        copied = subprocess.run([sys.executable, "tools/project.py", "check"], cwd=self.repa,
                                capture_output=True, text=True)
        self.assertEqual(copied.returncode, 0, copied.stdout + copied.stderr)

    def test_sibling_commit_does_not_make_state_stale(self):
        rae = self.repo / "paper_repro" / "rae"
        (rae / "src" / "rae" / "model.py").write_text("x = 1\n", encoding="utf-8")
        self.commit("rae work", "2026-11-25 12:00:00")
        self.assertNotIn("早于", self.check(self.repa).stdout)
        self.assertIn("早于本项目最近一次提交 2026-11-25", self.check(rae).stdout)

    def test_sub_project_tag_needs_prefix(self):
        head = self.git("rev-parse", "--short", "HEAD").strip()
        state = self.repa / "STATE.md"
        self.edit(state, "- commit：【待填】", "- commit：" + head)
        self.edit(state, "- tag：【待填，例如 paper_repro/repa/trunk-v1】", "- tag：trunk-v1")
        self.git("tag", "trunk-v1", head)
        result = self.check(self.repa)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("应以 paper_repro/repa/ 开头", result.stdout)
        self.edit(state, "- tag：trunk-v1", "- tag：paper_repro/repa/trunk-v1")
        self.git("tag", "paper_repro/repa/trunk-v1", head)
        result = self.check(self.repa)
        self.assertEqual(result.returncode, 0, result.stdout)


if __name__ == "__main__":
    unittest.main()
