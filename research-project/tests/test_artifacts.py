"""Tests for the template's src/<pkg>/artifacts.py, imported from a freshly initialized project."""
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
TOOL = SKILL / "scripts" / "project.py"


class ArtifactsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "proj"
        result = subprocess.run([sys.executable, str(TOOL), "init", str(self.root), "--name", "demo"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.root = self.root.resolve()
        os.environ.pop("PROJECT_RUNS_ROOT", None)
        spec = importlib.util.spec_from_file_location("artifacts", self.root / "src" / "demo" / "artifacts.py")
        self.art = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.art)

    def tearDown(self):
        os.environ.pop("PROJECT_RUNS_ROOT", None)
        self.tmp.cleanup()

    def names(self, run):
        return sorted(p.name for p in (run / "checkpoints").iterdir())

    def test_only_best_and_last_are_kept(self):
        run = self.art.run_dir("exp1")
        self.assertEqual(run, self.root / "runs" / "exp1")
        improved = [self.art.save_checkpoint(run, {"step": step}, metric)
                    for step, metric in ((1, 3.0), (2, 1.0), (3, 2.0))]
        self.assertEqual(improved, [True, True, False])
        self.assertEqual(self.names(run), ["best.json", "best.pt", "last.pt"])
        self.assertEqual(self.art.load_checkpoint(run, "best"), {"step": 2})
        self.assertEqual(self.art.load_checkpoint(run, "last"), {"step": 3})

    def test_higher_is_better_and_no_metric(self):
        run = self.art.run_dir("exp2")
        self.assertTrue(self.art.save_checkpoint(run, {"step": 1}, 0.5, lower_is_better=False))
        self.assertTrue(self.art.save_checkpoint(run, {"step": 2}, 0.9, lower_is_better=False))
        self.assertFalse(self.art.save_checkpoint(run, {"step": 3}))
        self.assertEqual(self.art.load_checkpoint(run, "best"), {"step": 2})
        self.assertEqual(self.art.load_checkpoint(run, "last"), {"step": 3})

    def test_named_best_needs_a_valid_name(self):
        run = self.art.run_dir("exp3")
        self.art.save_checkpoint(run, {"step": 1}, 1.0, name="ssim")
        self.assertIn("best_ssim.pt", self.names(run))
        with self.assertRaises(ValueError):
            self.art.save_checkpoint(run, {}, 1.0, name="../x")

    def test_smoke_runs_go_to_scratch(self):
        self.assertEqual(self.art.run_dir("exp4", smoke=True), self.root / "scratch" / "smoke" / "exp4")
        self.assertFalse((self.root / "runs" / "exp4").exists())

    def test_cache_dir_is_one_directory_per_key(self):
        first = self.art.cache_dir("latents", data="val", vae="mse", size=256)
        again = self.art.cache_dir("latents", size=256, vae="mse", data="val")
        other = self.art.cache_dir("latents", data="val", vae="ema", size=256)
        self.assertEqual(first, again)
        self.assertNotEqual(first, other)
        self.assertEqual(first.parent, self.root / "runs" / "_cache" / "latents")
        self.assertFalse(self.art.is_complete(first))
        self.art.mark_complete(first)
        self.assertTrue(self.art.is_complete(again))
        with self.assertRaises(ValueError):
            self.art.cache_dir("latents")

    def test_runs_root_can_move(self):
        elsewhere = Path(self.tmp.name) / "big_disk"
        os.environ["PROJECT_RUNS_ROOT"] = str(elsewhere)
        self.assertEqual(self.art.run_dir("exp5"), elsewhere / "exp5")
        self.assertEqual(self.art.cache_dir("feat", model="m").parent, elsewhere / "_cache" / "feat")

    def test_env_sh_points_tool_caches_to_temp(self):
        script = 'export TMPDIR="{}"; unset SLURM_TMPDIR LAB_MODELS_DIR; . tools/env.sh 2>/dev/null; ' \
                 'echo "$MPLCONFIGDIR|$TRITON_CACHE_DIR|$PIP_CACHE_DIR|${{HF_HOME:-none}}"'.format(self.tmp.name)
        out = subprocess.run(["bash", "-c", script], cwd=self.root, capture_output=True, text=True).stdout.strip()
        mpl, triton, pip, hf = out.split("|")
        for path in (mpl, triton, pip):
            self.assertTrue(path.startswith(self.tmp.name), out)
            self.assertNotIn(str(self.root), path)
        self.assertEqual(hf, "none")
        warned = subprocess.run(["bash", "-c", "unset LAB_MODELS_DIR; . tools/env.sh"], cwd=self.root,
                                capture_output=True, text=True).stderr
        self.assertIn("LAB_MODELS_DIR", warned)
        script = 'export LAB_MODELS_DIR=/models; . tools/env.sh; echo "$HF_HOME|$TORCH_HOME"'
        out = subprocess.run(["bash", "-c", script], cwd=self.root, capture_output=True, text=True).stdout.strip()
        self.assertEqual(out, "/models/huggingface|/models/torch")


if __name__ == "__main__":
    unittest.main()
