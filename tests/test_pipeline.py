"""Offline contract and regression tests; all written inputs are synthetic."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import ablate
import common
import decid3
import extract
import goaldesc
import mock_server
import review_runner
import sample
import scrub
from decidability import build_user, first_token_top_logprobs, top_letter


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="test-work-", dir=ROOT)
        cls.work = Path(cls.temp.name)
        cls.env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "COOKBOOK_MOCK_MODE": "clean"}
        result = subprocess.run([sys.executable, "scripts/demo.py", "--work-dir", str(cls.work / "demo")],
                                cwd=ROOT, env=cls.env, capture_output=True, text=True)
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        cls.demo_output = result.stdout
        cls.raw = common.read_rows(cls.work / "demo/raw.jsonl")
        cls.usable = common.read_rows(cls.work / "demo/usable.jsonl")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def run_script(self, script, *args, mode="clean"):
        return subprocess.run([sys.executable, str(ROOT / "scripts" / script), *map(str, args)],
                              cwd=ROOT, env={**self.env, "COOKBOOK_MOCK_MODE": mode},
                              capture_output=True, text=True)

    def test_full_pipeline_fixture_counts(self):
        self.assertEqual(len(self.raw), 84)
        self.assertEqual(len(self.usable), 84)
        self.assertEqual({g: sum(r["gate"] == g for r in self.raw)
                          for g in ("ROUTE", "REVIEW", "ARCH")},
                         {"ROUTE": 36, "REVIEW": 40, "ARCH": 8})
        self.assertEqual(sum(r["extra"].get("task_enriched", False) for r in self.raw), 6)
        self.assertTrue(all(not r.get("scrub_failed") for r in self.usable))
        self.assertIn("PIPELINE COMPLETE; AUDIT NOT RUN", self.demo_output)

    def test_recorded_synthetic_repair_counts(self):
        before = common.read_rows(self.work / "demo/map-repaired.jsonl")
        after = common.read_rows(self.work / "demo/repaired.jsonl")
        fields = ("state", "options", "label")
        self.assertEqual(sum(any(a[f] != b[f] for f in fields) for a, b in zip(before, after)), 76)
        self.assertEqual(len(json.loads((self.work / "demo/codes.json").read_text())), 12)
        self.assertEqual(len(json.loads((self.work / "demo/map.json").read_text())), 6)

    def test_schema_and_no_change_column_in_review(self):
        required = {"id", "source", "gate", "state", "question", "options", "label", "extra", "provenance"}
        for row in self.raw:
            self.assertTrue(required <= row.keys())
            self.assertIn(row["label"], row["options"])
            if row["gate"] == "REVIEW":
                self.assertNotIn("edited README", row["state"] + json.dumps(row["extra"]))

    def test_task_backfill_uses_only_what(self):
        result = extract.lookup_task_what(ROOT / "fixtures/goals", "zephyr-migration", "t2")
        self.assertEqual(result, "Migrate Zephyr batch 2")
        self.assertNotIn("done", result)

    def test_generic_lane_normalizer(self):
        for lane in common.load_config()["lanes"]:
            self.assertEqual(extract.norm_lane(lane), lane)
        self.assertEqual(extract.norm_lane(None), "other")

    def test_extraction_label_overlap(self):
        self.assertTrue(extract.label_leaks("The team decided to keep logs on local disk", "keep logs on local disk"))
        self.assertFalse(extract.label_leaks("Cost and latency differ.", "keep logs on local disk"))

    def test_patterns_fail_closed_and_case_insensitive(self):
        p = self.work / "patterns-test.txt"
        p.write_text("# comment\nfictionalperson\n")
        self.assertTrue(common.load_patterns(p)[0].search("FictionalPerson"))
        p.write_text("[\n")
        with self.assertRaises(Exception):
            common.load_patterns(p)
        p.write_text("# empty\n")
        with self.assertRaises(ValueError):
            common.load_patterns(p)
        with self.assertRaises(FileNotFoundError):
            common.load_patterns(self.work / "missing.txt")

    def test_secret_shape_patterns_match_constructed_synthetic_strings(self):
        pats = common.load_patterns(ROOT / "configs/patterns.example.txt")
        strings = ["s" + "k-" + "x" * 20, "A" + "KIA" + "X" * 16,
                   "g" + "hp_" + "x" * 30, "B" + "earer " + "x" * 20,
                   "-" * 5 + "BEGIN PRIVATE KEY" + "-" * 5]
        for text in strings:
            self.assertTrue(any(p.search(text) for p in pats))

    def test_scrub_checks_options_and_fixed_labels(self):
        row = copy.deepcopy(self.raw[-1])
        row["options"] = ["SAFE", "FictionalPerson"]
        row["label"] = "FictionalPerson"
        inp, out = self.work / "bad-input.jsonl", self.work / "bad-output.jsonl"
        common.write_rows(inp, [row])
        with patch.object(scrub, "scrub_text", side_effect=lambda base, model, text, mapping: (text, mapping, True, "")):
            with contextlib.redirect_stderr(io.StringIO()):
                scrub.main(["--in", str(inp), "--out", str(out), "--map", str(self.work / "bad-map.json"),
                            "--patterns", str(ROOT / "configs/patterns.example.txt")])
        self.assertTrue(common.read_rows(out)[0]["scrub_failed"])

    def test_scrub_option_failure_is_not_accepted(self):
        row = copy.deepcopy(self.raw[-1])
        inp, out = self.work / "option-in.jsonl", self.work / "option-out.jsonl"
        common.write_rows(inp, [row])
        responses = [(row["state"], {}, True, "")] + [(o, {}, False, "") for o in row["options"]]
        with patch.object(scrub, "scrub_text", side_effect=responses):
            with contextlib.redirect_stderr(io.StringIO()):
                scrub.main(["--in", str(inp), "--out", str(out), "--map", str(self.work / "option-map.json"),
                            "--patterns", str(ROOT / "configs/patterns.example.txt")])
        self.assertEqual(common.read_rows(out)[0]["scrub_error"], "option_model_failure")

    def test_map_repair_drops_poison_and_keeps_shared_placeholder(self):
        mapping = {"SyntheticProject": "project_1", "project_5": "project_1",
                   "vllm": "vendor_2", "bot": "bot_2", "BrokenName": "project_N"}
        mapfile = self.work / "poison.json"
        mapfile.write_text(json.dumps(mapping))
        row = {**self.usable[-1], "state": "project_1 vendor_2 project_N"}
        common.write_rows(self.work / "poison-row.jsonl", [row])
        result = self.run_script("mapclean.py", "--map", mapfile, "--in", self.work / "poison-row.jsonl",
                                 "--out", self.work / "poison-fixed.jsonl", "--map-out", self.work / "clean-map.json",
                                 "--keep", ROOT / "configs/keep.example.txt")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((self.work / "clean-map.json").read_text()), {"SyntheticProject": "project_1"})
        self.assertEqual(common.read_rows(self.work / "poison-fixed.jsonl")[0]["state"], "project_1 vllm project_0")
        self.assertNotIn("SyntheticProject", result.stderr)

    def test_postpass_handles_spaces_dates_options_and_case(self):
        row = {**self.usable[0], "state": "Task: ordinary work\nShape: small\nGoal: synthetic project with spaces month-YYYY-MM-18"}
        bad = {**self.usable[-1], "id": "bad-option", "options": ["safe", "FICTIONALPERSON"], "label": "safe"}
        common.write_rows(self.work / "post-in.jsonl", [row, bad])
        (self.work / "post-map.json").write_text("{}")
        result = self.run_script("postscrub.py", "--in", self.work / "post-in.jsonl", "--out", self.work / "post-out.jsonl",
                                 "--map", self.work / "post-map.json", "--patterns", ROOT / "configs/patterns.example.txt")
        self.assertEqual(result.returncode, 0, result.stderr)
        fixed, failed = common.read_rows(self.work / "post-out.jsonl")
        self.assertRegex(fixed["state"], r"Goal: project_\d+$")
        self.assertTrue(failed["scrub_failed"])

    def test_repair_restores_severity_and_drops_context(self):
        raw = {**self.usable[36], "state": "Reviewer finding: SEV-MAJOR: check limit\nContext: revised"}
        s = {**raw, "state": "Reviewer finding: project_0: check limit\nContext: revised"}
        common.write_rows(self.work / "align-raw.jsonl", [raw])
        common.write_rows(self.work / "align-in.jsonl", [s])
        (self.work / "align-map.json").write_text("{}")
        result = self.run_script("postscrub2.py", "--in", self.work / "align-in.jsonl", "--raw", self.work / "align-raw.jsonl",
                                 "--out", self.work / "align-out.jsonl", "--map", self.work / "align-map.json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(common.read_rows(self.work / "align-out.jsonl")[0]["state"], "Reviewer finding: SEV-MAJOR: check limit")

    def test_leak_filter_detects_planted_decision(self):
        row = {**self.usable[-1], "state": "The team decided to keep the logs."}
        common.write_rows(self.work / "leak-in.jsonl", [row])
        result = self.run_script("leakcheck.py", "--in", self.work / "leak-in.jsonl", "--out", self.work / "leak-out.jsonl",
                                 "--dropped", self.work / "leak-dropped.jsonl")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(common.read_rows(self.work / "leak-out.jsonl"), [])
        self.assertTrue(common.read_rows(self.work / "leak-dropped.jsonl")[0]["leak"])

    def test_goal_description_validator_only(self):
        pats = common.load_patterns(ROOT / "configs/patterns.example.txt")
        lane = common.load_config()["lane_words"]
        self.assertIsNone(goaldesc.valid("log storage migration", pats, [], lane))
        for text, reason in [("", "shape"), ("migration in 2026", "year"),
                             ("cheap cloud task", "lane"), ("Zephyr migration", "mechanical"),
                             ("forbidden migration", "token")]:
            self.assertEqual(goaldesc.valid(text, pats, ["forbidden"], lane), reason)

    def gate_on(self, raw, scrubbed, *flags, mode="clean"):
        common.write_rows(self.work / "gate-raw.jsonl", raw)
        common.write_rows(self.work / "gate-scrubbed.jsonl", scrubbed)
        return self.run_script("decid3.py", "--raw", self.work / "gate-raw.jsonl",
                               "--scrubbed", self.work / "gate-scrubbed.jsonl", "--out", self.work / "test-reads.jsonl",
                               "--summary", self.work / "test-summary.json", *flags, mode=mode)

    def test_new_delivered_options_flag_detects_option_only_bias(self):
        options = ["first storage plan", "second storage plan"]
        state = next("Shape: " + x for x in ("small", "batch", "risky", "cost")
                     if mock_server.pick(build_user("Shape: " + x, "Choose", options))[0] == "A")
        raw = {"id": "synthetic", "gate": "ARCH", "state": state, "question": "Choose", "options": options, "label": options[0]}
        changed = {**raw, "options": ["code_7 storage plan", options[1]]}
        self.assertEqual(self.gate_on([raw], [changed], mode="bias").returncode, 0)
        self.assertEqual(self.gate_on([raw], [changed], "--scrubbed-options", mode="bias").returncode, 2)

    def test_new_mean_pairs_and_stability_on_seeded_noise(self):
        result = self.gate_on(self.raw, self.usable, "--per-gate", "30", "--floor-estimator", "mean-pairs",
                              "--stability-report", mode="noise")
        self.assertIn(result.returncode, (0, 2))
        reports = json.loads((self.work / "test-summary.json").read_text())["classes"]
        self.assertTrue(any(0 < r["floor"] < 1 for r in reports.values()))
        self.assertTrue(any(r["stability"]["split"]["n"] > 0 for r in reports.values()))
        self.assertIn("stability=", result.stdout)
        self.assertTrue(all(r["floor"] == r["mean_pairs_floor"] for r in reports.values()))

    def test_estimator_and_empty_strata_contract(self):
        row = {"raw_maj": "A", "scrub_maj": "B", "agree": False,
               "self_floor_pair": True, "self_floor_mean_pairs": 1/3,
               "raw_unanimous": False, "classes": ["ref_1", "id_1"]}
        result = decid3.summarize([row], "mean-pairs")
        self.assertEqual(result["floor"], 1/3)
        self.assertEqual(result["pair_floor"], 1)
        self.assertEqual(result["stability"]["unanimous"], {"n": 0, "agreement": None})
        self.assertEqual(result["chance_agreement"], 0)
        self.assertEqual(result["flips_by_class"], {"ref_1": 1, "id_1": 1})

    def test_placeholder_attribution_includes_refs_and_ids(self):
        self.assertEqual(decid3.PLACEHOLDER_RE.findall("ref_7 id_8 project_1"), ["ref_7", "id_8", "project_1"])

    def test_empty_or_missing_reads_cannot_pass(self):
        self.assertEqual(self.gate_on([], []).returncode, 2)
        with patch.object(decid3, "chat_logprobs", return_value=({}, True)):
            common.write_rows(self.work / "missing-raw.jsonl", self.raw[:1])
            common.write_rows(self.work / "missing-scrubbed.jsonl", self.usable[:1])
            with self.assertRaises(ValueError):
                decid3.main(["--raw", str(self.work / "missing-raw.jsonl"), "--scrubbed",
                             str(self.work / "missing-scrubbed.jsonl"), "--out", str(self.work / "missing-reads.jsonl")])

    def test_synthetic_neutral_refs_pass_and_code_bias_fails(self):
        self.assertEqual(self.gate_on(self.raw, self.usable, mode="bias").returncode, 0)
        biased = [{**r, "state": r["state"].replace("ref_", "code_")} for r in self.usable]
        self.assertEqual(self.gate_on(self.raw, biased, mode="bias").returncode, 2)

    def test_stratified_sample_is_seeded_and_minimal(self):
        selected = sample.select(self.usable)
        self.assertEqual(len(selected), 50)
        self.assertEqual(selected, sample.select(self.usable))
        self.assertTrue(all(set(r) == set(sample.FIELDS) for r in selected))
        self.assertTrue(any(r["gate"] == "REVIEW" and r["label"] == "REJECT" for r in selected))

    def test_egress_scans_prompt_and_sample_before_command(self):
        prompt, rows, output = self.work / "audit-prompt.txt", self.work / "audit-sample.jsonl", self.work / "audit-test.txt"
        for bad_role in ("prompt", "sample"):
            prompt.write_text("FictionalPerson" if bad_role == "prompt" else "Review the sample")
            rows.write_text("FictionalPerson" if bad_role == "sample" else "[]")
            with patch.object(review_runner.subprocess, "run") as command:
                with contextlib.redirect_stdout(io.StringIO()):
                    rc = review_runner.main(["--prompt", str(prompt), "--sample", str(rows),
                                             "--patterns", str(ROOT / "configs/patterns.example.txt"),
                                             "--out", str(output), "--command", "unused"])
                self.assertEqual(rc, 9)
                command.assert_not_called()

    def test_noop_reviewer_is_not_clean(self):
        result = self.run_script("review_runner.py", "--prompt", ROOT / "configs/p-audit-scrub-v2.txt",
                                 "--sample", self.work / "demo/sample50.jsonl", "--patterns", ROOT / "configs/patterns.example.txt",
                                 "--out", self.work / "noop-review.txt", "--command", sys.executable, "-c", "pass")
        self.assertEqual(result.returncode, 2)
        self.assertIn("AUDIT: INVALID RESPONSE", result.stdout)

    def test_ablation_changes_only_named_fields(self):
        outputs = ablate.variants(self.raw, {r["id"]: r for r in self.usable}, common.load_config()["code_pattern"])
        self.assertEqual(len(outputs["v1"]), 36)
        self.assertTrue(all("Goal: project_" in r["state"] for r in outputs["v1"]))
        self.assertTrue(any("ref_" in r["state"] for r in outputs["v2"]))
        for variant in outputs.values():
            self.assertEqual([r["id"] for r in variant], [r["id"] for r in self.raw if r["gate"] == "ROUTE"])

    def test_logprob_contract_and_escalation(self):
        payload = {"choices": [{"logprobs": {"content": [{"top_logprobs": [
            {"token": " A", "logprob": -3}, {"token": "C", "logprob": -0.1}]}]}}]}
        self.assertEqual(top_letter(first_token_top_logprobs(payload), {"A", "B", "C"}), "C")
        self.assertIn("C. None of these; escalate", build_user("state", "question", ["one", "two"]))

    def test_shell_wrappers_run_offline(self):
        result = subprocess.run(["sh", "scripts/run_gates.sh", "--work-dir", str(self.work / "shell-demo")],
                                cwd=ROOT, env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run(["sh", "scripts/review_runner.sh", "--prompt", "configs/p-audit-scrub-v2.txt",
                                 "--sample", str(self.work / "shell-demo/sample50.jsonl"),
                                 "--patterns", "configs/patterns.example.txt", "--out", str(self.work / "shell-review.txt")],
                                cwd=ROOT, env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("AUDIT NOT RUN", result.stdout)

    def test_dry_scrub_writes_nothing(self):
        out, mapping = self.work / "dry-out.jsonl", self.work / "dry-map.json"
        result = self.run_script("scrub.py", "--in", self.work / "demo/raw.jsonl", "--out", out,
                                 "--map", mapping, "--patterns", ROOT / "configs/patterns.example.txt", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(out.exists())
        self.assertFalse(mapping.exists())
        self.assertNotIn("FictionalPerson", result.stderr)

    def test_ablation_cli(self):
        result = self.run_script("ablate.py", "--raw", self.work / "demo/raw.jsonl",
                                 "--scrubbed", self.work / "demo/usable.jsonl", "--out-dir", self.work / "variants")
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ("v1", "v2", "v3"):
            self.assertEqual(len(common.read_rows(self.work / "variants" / (name + ".jsonl"))), 36)


if __name__ == "__main__":
    unittest.main()
