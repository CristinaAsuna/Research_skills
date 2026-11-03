"""Tests for scripts/lab.py and scripts/figstyle.py in temporary workspaces."""
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
LAB = SKILL / "scripts" / "lab.py"
PLACEHOLDER = re.compile(r"【待填[^】]*】")
DATE = "2026-11-03"


def run(*args):
    return subprocess.run([sys.executable, str(LAB), *args], capture_output=True, text=True)


class LabTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "ws"
        result = run("init", str(self.root))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for key, value in (("user.email", "lab@example.com"), ("user.name", "lab"), ("commit.gpgsign", "false")):
            self.git("config", key, value)

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        result = subprocess.run(["git", "-C", str(self.root), *args], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def lab(self, *args):
        return run(*args, "--root", str(self.root))

    def new(self, slug="toy"):
        result = self.lab("new", slug, "--paper", "Toy Paper", "--date", DATE)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return self.root / "topics" / f"{DATE}-{slug}"

    def set_cell(self, topic_id, index, value):
        path = self.root / "EXPERIMENTS.md"
        lines = path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines):
            cells = line.split("|")
            if len(cells) > 7 and cells[2].strip() == topic_id:
                cells[index + 1] = f" {value} "
                lines[i] = "|".join(cells)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def fill(self, topic, *names):
        for name in names:
            path = topic / name
            path.write_text(PLACEHOLDER.sub("x", path.read_text(encoding="utf-8")), encoding="utf-8")

    def plan_topic(self, slug="toy"):
        topic = self.new(slug)
        self.fill(topic, "DISCOVERY.md", "PLAN.md")
        self.set_cell(topic.name, 3, "推到极限")
        self.set_cell(topic.name, 4, "planned")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", f"plan({topic.name}): freeze predictions")
        return topic

    def check(self, topic=None, phase=None):
        args = ["check"] + ([str(topic)] if topic else []) + (["--phase", phase] if phase else [])
        return self.lab(*args)

    def test_init_creates_rendered_files_and_never_overwrites(self):
        for rel in (".gitignore", "lab.toml", "CLAUDE.md", "tools/lab.py", "tools/figstyle.py", "templates/PLAN.md"):
            self.assertTrue((self.root / rel).is_file(), rel)
        self.assertTrue((self.root / ".git").exists())
        for rel in ("AGENTS.md", "lab.toml", "README.md", "HARNESS_LOG.md"):
            self.assertNotIn("{{", (self.root / rel).read_text(encoding="utf-8"), rel)
        (self.root / "AGENTS.md").write_text("custom\n", encoding="utf-8")
        self.assertEqual(run("init", str(self.root)).returncode, 0)
        self.assertEqual((self.root / "AGENTS.md").read_text(encoding="utf-8"), "custom\n")
        upgrade = run("init", str(self.root), "--upgrade")
        self.assertIn("skill/AGENTS.md", upgrade.stdout)
        self.assertEqual((self.root / "AGENTS.md").read_text(encoding="utf-8"), "custom\n")

    def test_clean_workspace_passes(self):
        result = self.check()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("0 个错误", result.stdout)
        self.assertIn("学习阶段：S1", self.lab("status").stdout)

    def test_new_creates_topic_row_and_suffix(self):
        topic = self.new()
        for name in ("DISCOVERY.md", "PLAN.md", "SUMMARY.md", "REFLECTION.md"):
            text = (topic / name).read_text(encoding="utf-8")
            self.assertNotIn("{{", text)
            self.assertIn(topic.name, text)
        for name in ("code", "figures", "results", "runs"):
            self.assertTrue((topic / name).is_dir())
        index = (self.root / "EXPERIMENTS.md").read_text(encoding="utf-8")
        self.assertIn(f"| {topic.name} | Toy Paper |", index)
        self.assertIn("| discovery |", index)
        second = self.lab("new", "toy", "--paper", "Toy Paper", "--date", DATE)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertTrue((self.root / "topics" / f"{DATE}-toy-2").is_dir())
        self.assertIn(topic.name, self.lab("status").stdout)
        self.assertEqual(self.check().returncode, 0)

    def test_planned_requires_filled_discovery_and_plan(self):
        topic = self.new()
        self.set_cell(topic.name, 4, "planned")
        result = self.check(topic)
        self.assertEqual(result.returncode, 1)
        self.assertIn("DISCOVERY.md 还有", result.stdout)
        self.assertIn("发现原型未填写", result.stdout)
        self.fill(topic, "DISCOVERY.md", "PLAN.md")
        self.set_cell(topic.name, 3, "推到极限")
        result = self.check(topic)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn(f"plan({topic.name})", result.stdout)

    def test_extra_markdown_is_rejected(self):
        topic = self.new()
        (topic / "NOTES.md").write_text("x\n", encoding="utf-8")
        (topic / "results" / "REPORT.md").write_text("x\n", encoding="utf-8")
        (topic / "runs" / "log.md").write_text("x\n", encoding="utf-8")
        result = self.check(topic)
        self.assertEqual(result.returncode, 1)
        self.assertIn("NOTES.md", result.stdout)
        self.assertIn("results/REPORT.md", result.stdout)
        self.assertNotIn("log.md", result.stdout)

    def test_agents_line_budget_is_hard(self):
        path = self.root / "AGENTS.md"
        path.write_text(path.read_text(encoding="utf-8") + "rule\n" * 200, encoding="utf-8")
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("AGENTS.md 有", result.stdout)

    def test_executed_requires_figures_and_results(self):
        topic = self.plan_topic()
        self.fill(topic, "SUMMARY.md")
        self.set_cell(topic.name, 4, "executed")
        result = self.check(topic)
        self.assertEqual(result.returncode, 1)
        self.assertIn("figures/E1_main.png", result.stdout)
        self.assertIn("没有 E*.json", result.stdout)
        (topic / "figures" / "E1_main.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        (topic / "results" / "E1.json").write_text(json.dumps({"exp": "E1", "status": "done"}), encoding="utf-8")
        result = self.check(topic)
        self.assertEqual(result.returncode, 0, result.stdout)
        result = self.check(topic, phase="reviewed")
        self.assertEqual(result.returncode, 1)
        self.assertIn("REFLECTION.md 还有", result.stdout)

    def test_invalid_results_json_is_rejected(self):
        topic = self.new()
        (topic / "results" / "E1.json").write_text("{}", encoding="utf-8")
        (topic / "results" / "E2.json").write_text("not json", encoding="utf-8")
        result = self.check(topic)
        self.assertEqual(result.returncode, 1)
        self.assertIn("results/E1.json 需要包含 exp", result.stdout)
        self.assertIn("results/E2.json 不是合法 JSON", result.stdout)

    def test_frozen_predictions_cannot_change(self):
        topic = self.plan_topic()
        self.assertEqual(self.check(topic).returncode, 0)
        plan = topic / "PLAN.md"
        original = plan.read_text(encoding="utf-8")
        plan.write_text(original.replace("| E1 | x | x | x |", "| E1 | changed | x | x |"), encoding="utf-8")
        result = self.check(topic)
        self.assertEqual(result.returncode, 1)
        self.assertIn("冻结预测", result.stdout)
        plan.write_text(original + "\n## 计划修订\n\n2026-11-04：E2 改为 4 个 seed。\n", encoding="utf-8")
        self.assertEqual(self.check(topic).returncode, 0)

    def test_running_without_plan_commit_is_rejected(self):
        topic = self.new()
        self.fill(topic, "DISCOVERY.md", "PLAN.md")
        self.set_cell(topic.name, 3, "推到极限")
        self.set_cell(topic.name, 4, "running")
        result = self.check(topic)
        self.assertEqual(result.returncode, 1)
        self.assertIn("预测未冻结", result.stdout)

    def test_runs_must_be_git_ignored(self):
        topic = self.new()
        gitignore = self.root / ".gitignore"
        gitignore.write_text(gitignore.read_text(encoding="utf-8").replace("topics/*/runs/\n", ""), encoding="utf-8")
        result = self.check(topic)
        self.assertEqual(result.returncode, 1)
        self.assertIn("runs/ 没有被 git 忽略", result.stdout)

    def test_index_and_directories_must_match(self):
        (self.root / "topics" / f"{DATE}-orphan").mkdir()
        result = self.check()
        self.assertEqual(result.returncode, 1)
        self.assertIn("没有登记在 EXPERIMENTS.md", result.stdout)


@unittest.skipUnless(importlib.util.find_spec("matplotlib") and importlib.util.find_spec("numpy"), "needs matplotlib")
class FigstyleTest(unittest.TestCase):
    def test_seed_lines_representative_seed_and_save(self):
        sys.path.insert(0, str(SKILL / "scripts"))
        import figstyle
        import matplotlib.pyplot as plt

        figstyle.setup()
        fig, ax = plt.subplots(figsize=(4, 3))
        line = figstyle.seed_lines(ax, [1, 2, 3], [[1, 2, 3], [2, 3, 4], [3, 4, 5]], label="a", naive=[2, 2, 2])
        self.assertEqual(len(ax.lines), 5)
        self.assertEqual(list(line.get_ydata()), [2, 3, 4])
        self.assertEqual(figstyle.representative_seed([0.1, 0.5, 0.9], seeds=[7, 8, 9]), 8)
        with tempfile.TemporaryDirectory() as tmp:
            path = figstyle.save_fig(fig, Path(tmp) / "f.png")
            self.assertTrue(path.is_file())
            fig, _ = plt.subplots()
            with self.assertRaises(ValueError):
                figstyle.save_fig(fig, Path(tmp) / "g.png", max_bytes=10)


if __name__ == "__main__":
    unittest.main()
