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
                         "configs/trunk.yaml", "src/demo/__init__.py", "src/demo/artifacts.py",
                         "tools/project.py", "tools/env.sh"):
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


    def run_files(self, exp, names):
        folder = self.root / "runs" / exp / "checkpoints"
        folder.mkdir(parents=True, exist_ok=True)
        for name in names:
            (folder / name).write_bytes(b"x" * 1024)
        return folder

    def audit(self, *extra):
        result = run("audit", "--root", str(self.root), *extra)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def prune_list(self):
        listings = sorted((self.root / "scratch").glob("prune-*.txt"))
        self.assertEqual(len(listings), 1)
        return listings[0], listings[0].read_text(encoding="utf-8")

    def test_new_card_asks_for_storage_budget(self):
        card = (self.new() / "CARD.md").read_text(encoding="utf-8")
        self.assertIn("## 计算和存储预算", card)
        self.assertIn("checkpoints/best.pt", card)

    def test_audit_lists_redundant_checkpoints_and_misplaced_caches(self):
        exp = self.new().name
        self.run_files(exp, ["best.pt", "last.pt", "step_010000.pt", "smoke.pt", "best_ssim.pt"])
        (self.root / "runs" / exp / "matplotlib_cache").mkdir()
        deps = self.root / "experiments" / exp / "exports" / "python_dependencies" / "site-packages"
        deps.mkdir(parents=True)
        (deps / "lib.so").write_bytes(b"x")
        out = self.audit()
        listing, text = self.prune_list()
        for name in ("step_010000.pt", "smoke.pt", "best_ssim.pt", "matplotlib_cache", "python_dependencies"):
            self.assertIn(name, text)
        self.assertNotIn("best.pt\n", text.replace("best_ssim.pt", ""))
        self.assertNotIn("last.pt", text)
        self.assertIn("可回收", out)

    def test_card_keeps_listed_files_and_done_drops_last(self):
        directory = self.new()
        self.edit("experiments/{}/CARD.md".format(directory.name),
                  "result.json；checkpoints/best.pt；", "result.json；checkpoints/best.pt；checkpoints/best_ssim.pt；")
        self.run_files(directory.name, ["best.pt", "last.pt", "best_ssim.pt"])
        self.edit("EXPERIMENTS.md", "| queued |", "| done |")
        (directory / "result.json").write_text("{}\n", encoding="utf-8")
        self.audit("--exp", directory.name)
        _, text = self.prune_list()
        self.assertEqual([Path(line).name for line in text.splitlines()], ["last.pt"])

    def test_clean_run_has_nothing_to_prune(self):
        exp = self.new().name
        self.run_files(exp, ["best.pt", "last.pt"])
        self.assertIn("可回收 0G", self.audit())
        self.assertEqual(list((self.root / "scratch").glob("prune-*.txt")), [])

    def test_over_budget_and_unregistered_runs(self):
        directory = self.new()
        self.edit("experiments/{}/CARD.md".format(directory.name),
                  "存储上限 N GB", "存储上限 0.000001 GB")
        self.run_files(directory.name, ["best.pt", "last.pt"])
        self.run_files("someone-elses-run", ["best.pt"])
        out = self.audit()
        self.assertIn("超出存储预算", out)
        self.assertIn("没有登记在 EXPERIMENTS.md 的 run 目录", out)
        self.assertIn("超出卡片的存储预算", self.check().stdout)

    def test_audit_reports_identical_large_files(self):
        for exp in ("a", "b"):
            folder = self.root / "runs" / "_cache" / exp
            folder.mkdir(parents=True)
            with open(folder / "latents.bin", "wb") as handle:
                handle.truncate(101 * 1024 ** 2)
        out = self.audit()
        self.assertIn("内容相同的大文件", out)
        self.assertIn("可回收 0G", out)

    def test_prune_previews_then_deletes_only_with_yes(self):
        exp = self.new().name
        folder = self.run_files(exp, ["best.pt", "step_1.pt"])
        self.audit()
        listing, _ = self.prune_list()
        preview = run("prune", str(listing), "--root", str(self.root))
        self.assertEqual(preview.returncode, 0, preview.stdout)
        self.assertTrue((folder / "step_1.pt").exists())
        done = run("prune", str(listing), "--yes", "--root", str(self.root))
        self.assertEqual(done.returncode, 0, done.stdout)
        self.assertIn("已删除 1 项", done.stdout)
        self.assertFalse((folder / "step_1.pt").exists())
        self.assertTrue((folder / "best.pt").exists())

    def test_prune_refuses_paths_outside_artifact_dirs(self):
        exp = self.new().name
        folder = self.run_files(exp, ["step_1.pt"])
        outside = self.root / "src" / "demo" / "__init__.py"
        listing = self.root / "scratch" / "manual.txt"
        listing.write_text("{}\n{}\n{}\n".format(folder / "step_1.pt", outside,
                                                   self.root / "experiments" / exp / "CARD.md"), encoding="utf-8")
        result = run("prune", str(listing), "--yes", "--root", str(self.root))
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertIn("什么也没删", result.stdout)
        self.assertTrue((folder / "step_1.pt").exists())
        self.assertTrue(outside.exists())

    def test_extra_root_directory_is_error(self):
        (self.root / "sd15_fulltrain").mkdir()
        (self.root / "sd15_fulltrain" / "core.py").write_text("x = 1\n", encoding="utf-8")
        self.assert_error("根目录多出 sd15_fulltrain/")

    def test_direct_torch_save_is_warning(self):
        (self.root / "src" / "demo" / "train.py").write_text("import torch\ntorch.save({}, 'x.pt')\n", encoding="utf-8")
        self.commit("train")
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("src/demo/train.py 直接调用了 torch.save", result.stdout)
        self.assertNotIn("artifacts.py 直接调用", result.stdout)

    def test_check_warns_when_much_is_reclaimable(self):
        exp = self.new().name
        folder = self.root / "runs" / exp / "checkpoints"
        folder.mkdir(parents=True)
        with open(folder / "step_1.pt", "wb") as handle:
            handle.truncate(11 * 1024 ** 3)
        self.assertIn("冗余产物：运行 tools/project.py audit", self.check().stdout)
        self.assertNotIn("冗余产物", run("check", "--skip-audit", "--root", str(self.root)).stdout)


    def test_check_warns_about_data_inside_the_project(self):
        big = self.root / "data" / "imagenet"
        big.mkdir(parents=True)
        with open(big / "train.tar", "wb") as handle:
            handle.truncate(2 * 1024 ** 3)
        out = run("check", "--skip-audit", "--root", str(self.root)).stdout
        self.assertIn("data/ 是普通目录", out)
        self.assertIn("data 有 2.0G", out)

    def test_check_allows_data_link_and_big_runs(self):
        target = Path(self.tmp.name) / "shared" / "imagenet"
        target.mkdir(parents=True)
        with open(target / "train.tar", "wb") as handle:
            handle.truncate(2 * 1024 ** 3)
        (self.root / "data").symlink_to(target)
        (self.root / "runs" / "x").mkdir(parents=True)
        with open(self.root / "runs" / "x" / "best.pt", "wb") as handle:
            handle.truncate(2 * 1024 ** 3)
        out = run("check", "--skip-audit", "--root", str(self.root)).stdout
        self.assertNotIn("data/ 是普通目录", out)
        self.assertNotIn("G：数据集放", out)


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
