"""Self-tests for the part that moves real files. Stdlib only: python3 tests/test_ariadne.py. Everything runs in a throwaway home."""
import csv
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

CLI = Path(__file__).resolve().parents[1] / "tools/cli.py"


class Base(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix="ariadne-test-")).resolve()
        self.addCleanup(shutil.rmtree, self.home, True)
        self.ws = self.home / "ws"
        self.env = {**os.environ, "HOME": str(self.home), "ARIADNE_HOME": str(self.ws)}
        (self.home / "Downloads").mkdir()
        (self.home / "Documents").mkdir()
        self.run_ok("init")

    def run_cli(self, *args):
        return subprocess.run(["/usr/bin/python3", str(CLI), *args], capture_output=True, text=True, env=self.env)

    def run_ok(self, *args):
        p = self.run_cli(*args)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return json.loads(p.stdout) if p.stdout.strip().startswith(("{", "[")) else p.stdout

    def file(self, rel, text="x"):
        p = self.home / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return p

    def plan(self, rows, name="t", approve=True):
        self.run_ok("new-plan", "--name", name)
        path = next((self.ws / "plans").glob(f"*-{name}.csv"))
        with open(path, "a", newline="") as f:
            w = csv.writer(f)
            for src, dst in rows:
                w.writerow(["", str(self.home / src), str(self.home / dst), "test"])
        if approve:
            self.run_ok("approve", "--plan", path.name, "--all")
        return path.name


class Moves(Base):
    def test_unapproved_rows_do_not_move(self):
        a = self.file("Downloads/a.txt")
        plan = self.plan([("Downloads/a.txt", "Documents/a.txt")], approve=False)
        self.assertEqual(self.run_ok("apply", "--plan", plan, "--yes")["moved"], 0)
        self.assertTrue(a.exists())

    def test_apply_requires_yes(self):
        self.file("Downloads/a.txt")
        plan = self.plan([("Downloads/a.txt", "Documents/a.txt")])
        self.assertNotEqual(self.run_cli("apply", "--plan", plan).returncode, 0)
        self.assertTrue((self.home / "Downloads/a.txt").exists())

    def test_apply_then_undo_round_trip(self):
        a = self.file("Downloads/a.txt", "hello")
        plan = self.plan([("Downloads/a.txt", "Documents/sub/b.txt")])
        self.assertEqual(self.run_ok("apply", "--plan", plan, "--yes")["moved"], 1)
        self.assertEqual((self.home / "Documents/sub/b.txt").read_text(), "hello")
        self.assertFalse(a.exists())
        self.assertEqual(self.run_ok("verify", "--plan", plan)["not_in_place"], [])
        self.assertEqual(self.run_ok("undo", "--yes")["restored"], 1)
        self.assertEqual(a.read_text(), "hello")

    def test_undo_without_yes_moves_nothing(self):
        self.file("Downloads/a.txt")
        self.run_ok("apply", "--plan", self.plan([("Downloads/a.txt", "Documents/a.txt")]), "--yes")
        self.assertEqual(self.run_ok("undo")["would_restore"], 1)
        self.assertTrue((self.home / "Documents/a.txt").exists())

    def test_never_overwrites(self):
        self.file("Downloads/a.txt", "new")
        b = self.file("Documents/a.txt", "old")
        plan = self.plan([("Downloads/a.txt", "Documents/a.txt")])
        self.assertEqual(self.run_cli("apply", "--plan", plan, "--yes").returncode, 2)
        self.assertEqual(b.read_text(), "old")
        self.assertTrue((self.home / "Downloads/a.txt").exists())

    def test_folders_merge_without_overwriting(self):
        self.file("Downloads/f/new.txt", "n")
        self.file("Downloads/f/same.txt", "from-source")
        self.file("Documents/f/same.txt", "kept")
        res = self.run_ok("apply", "--plan", self.plan([("Downloads/f", "Documents/f")]), "--yes")
        self.assertEqual(res["moved"], 1)
        self.assertEqual((self.home / "Documents/f/same.txt").read_text(), "kept")
        self.assertEqual((self.home / "Documents/f/new.txt").read_text(), "n")
        self.assertEqual((self.home / "Downloads/f/same.txt").read_text(), "from-source")

    def test_partial_approval(self):
        self.file("Downloads/a.txt"); self.file("Downloads/b.txt")
        plan = self.plan([("Downloads/a.txt", "Documents/a.txt"), ("Downloads/b.txt", "Documents/b.txt")], approve=False)
        self.run_ok("approve", "--plan", plan, "--lines", "3")
        self.assertEqual(self.run_ok("apply", "--plan", plan, "--yes")["moved"], 1)
        self.assertTrue((self.home / "Downloads/a.txt").exists())
        self.assertTrue((self.home / "Documents/b.txt").exists())


class Protection(Base):
    def refused(self, src, dst):
        self.assertTrue((self.home / src).exists() or True)
        plan = self.plan([(src, dst)], name="p" + str(abs(hash((src, dst)))))
        self.assertTrue(self.run_ok("check", "--plan", plan)["problems"], "expected check to refuse")
        self.assertEqual(self.run_cli("apply", "--plan", plan, "--yes").returncode, 2)

    def test_code_folder_with_no_config(self):
        self.file("Code/thing/a.py")
        self.refused("Code/thing/a.py", "Documents/a.py")

    def test_cannot_move_into_code(self):
        self.file("Downloads/a.py")
        self.refused("Downloads/a.py", "Code/a.py")

    def test_git_repository_anywhere(self):
        self.file("projects/repo/.git/HEAD")
        self.file("projects/repo/src/a.py")
        self.refused("projects/repo", "Documents/repo")
        self.refused("projects/repo/src/a.py", "Documents/a.py")

    def test_ariadne_own_folder(self):
        self.refused("ws/config.json", "Documents/config.json")

    def test_app_owned_stays_protected_when_config_adds_more(self):
        cfg = json.loads((self.ws / "config.json").read_text()); cfg["app_owned"] = ["MyApp"]
        (self.ws / "config.json").write_text(json.dumps(cfg))
        self.file("Documents/Zoom/call.mp4"); self.file("Documents/MyApp/d.bin")
        self.refused("Documents/Zoom/call.mp4", "Documents/call.mp4")
        self.refused("Documents/MyApp/d.bin", "Documents/d.bin")

    def test_protect_command(self):
        self.file("Private/a.txt")
        self.run_ok("protect", "--path", "~/Private")
        self.refused("Private/a.txt", "Documents/a.txt")


class Contract(Base):
    def test_count_shape_other_tools_rely_on(self):
        self.file("Downloads/a.txt"); self.file("Downloads/.hidden"); self.file("Downloads/_tray/x")
        res = self.run_ok("count")
        self.assertEqual(res["total"], 1)
        self.assertIn("unfiled", res)

    def test_init_keeps_user_files(self):
        (self.ws / "filing-map.md").write_text("mine")
        self.run_ok("init")
        self.assertEqual((self.ws / "filing-map.md").read_text(), "mine")

    def test_history_includes_note_batches_and_undo_dry_run(self):
        (self.ws / "notes-moves.jsonl").write_text(json.dumps({"batch": "n1", "time": "2026-01-01T00:00:00", "id": "x", "from": "A", "to": "B"}) + "\n")
        self.assertEqual(self.run_ok("history")[0]["kind"], "notes")
        self.assertEqual(self.run_ok("undo", "--batch", "n1")["would_restore"], 1)

    def test_plans_lists_applied_state(self):
        self.file("Downloads/a.txt")
        plan = self.plan([("Downloads/a.txt", "Documents/a.txt")])
        self.run_ok("apply", "--plan", plan, "--yes")
        self.assertEqual(self.run_ok("plans")[0]["moved"], 1)


class PartialPlans(Base):
    def test_rest_of_a_partly_applied_plan_stays_available(self):
        self.file("Downloads/a.txt"); self.file("Downloads/b.txt")
        plan = self.plan([("Downloads/a.txt", "Documents/a.txt"), ("Downloads/b.txt", "Documents/b.txt")], approve=False)
        self.run_ok("approve", "--plan", plan, "--lines", "2")
        self.run_ok("apply", "--plan", plan, "--yes")
        shown = self.run_ok("show", "--plan", plan)
        self.assertEqual([r["state"] for r in shown["rows"]], ["moved", "pending"])
        self.assertEqual(self.run_ok("plans")[0]["pending"], 1)
        # What the app does for the second pass: clear, then approve only what's still waiting.
        self.run_ok("approve", "--plan", plan, "--all", "--clear")
        self.run_ok("approve", "--plan", plan, "--lines", "3")
        self.assertEqual(self.run_ok("apply", "--plan", plan, "--yes")["moved"], 1)
        self.assertTrue((self.home / "Documents/b.txt").exists())

    def test_item_refiled_later_is_not_waiting(self):
        self.file("Downloads/a.txt")
        plan = self.plan([("Downloads/a.txt", "Documents/a.txt")])
        self.run_ok("apply", "--plan", plan, "--yes")
        (self.home / "Documents/a.txt").rename(self.home / "Documents/moved-again.txt")
        self.assertEqual(self.run_ok("show", "--plan", plan)["rows"][0]["state"], "moved")
        self.assertEqual(self.run_ok("plans")[0]["pending"], 0)

    def test_undo_makes_a_plan_ready_again(self):
        self.file("Downloads/a.txt")
        plan = self.plan([("Downloads/a.txt", "Documents/a.txt")])
        self.run_ok("apply", "--plan", plan, "--yes")
        self.run_ok("undo", "--yes")
        self.assertEqual(self.run_ok("plans")[0]["moved"], 0)
        self.assertEqual(self.run_ok("show", "--plan", plan)["rows"][0]["state"], "pending")


class Hardening(Base):
    def raw_plan(self, *lines, name="raw"):
        self.run_ok("new-plan", "--name", name)
        path = next((self.ws / "plans").glob(f"*-{name}.csv"))
        with open(path, "a") as f:
            f.write("".join(l + "\n" for l in lines))
        return path.name

    def test_blank_source_never_means_the_current_folder(self):
        self.file("Downloads/keep.txt")
        plan = self.raw_plan(f"Y,,{self.home}/Documents/x")
        p = subprocess.run(["/usr/bin/python3", str(CLI), "apply", "--plan", plan, "--yes"], capture_output=True, text=True, env=self.env, cwd=self.home / "Downloads")
        self.assertNotEqual(p.returncode, 0, p.stdout)
        self.assertTrue((self.home / "Downloads/keep.txt").exists())

    def test_relative_paths_are_refused(self):
        self.file("Downloads/a.txt")
        plan = self.raw_plan("Y,a.txt,elsewhere/a.txt")
        p = subprocess.run(["/usr/bin/python3", str(CLI), "apply", "--plan", plan, "--yes"], capture_output=True, text=True, env=self.env, cwd=self.home / "Downloads")
        self.assertNotEqual(p.returncode, 0, p.stdout)
        self.assertTrue((self.home / "Downloads/a.txt").exists())

    def test_standard_home_folders_cannot_be_moved(self):
        self.file("Documents/a.txt")
        plan = self.plan([("Documents", "Downloads/Documents")])
        self.assertNotEqual(self.run_cli("apply", "--plan", plan, "--yes").returncode, 0)
        self.assertTrue((self.home / "Documents/a.txt").exists())

    def test_folder_containing_a_repository_cannot_be_moved(self):
        self.file("Downloads/stuff/repo/.git/HEAD")
        plan = self.plan([("Downloads/stuff", "Documents/stuff")])
        self.assertNotEqual(self.run_cli("apply", "--plan", plan, "--yes").returncode, 0)
        self.assertTrue((self.home / "Downloads/stuff/repo/.git/HEAD").exists())

    def test_folder_containing_an_app_folder_cannot_be_moved(self):
        self.file("Downloads/stuff/Zoom/call.mp4")
        plan = self.plan([("Downloads/stuff", "Documents/stuff")])
        self.assertNotEqual(self.run_cli("apply", "--plan", plan, "--yes").returncode, 0)

    def test_paths_outside_home_are_refused(self):
        outside = Path(tempfile.mkdtemp(prefix="ariadne-outside-")).resolve()
        self.addCleanup(shutil.rmtree, outside, True)
        (outside / "a.txt").write_text("x")
        plan = self.raw_plan(f"Y,{outside}/a.txt,{self.home}/Documents/a.txt")
        self.assertNotEqual(self.run_cli("apply", "--plan", plan, "--yes").returncode, 0)
        self.assertTrue((outside / "a.txt").exists())

    def test_secrets_never_prints_a_value(self):
        fake_key = "AKIA" + "ABCDEFGHIJKLMNOP"
        fake_gh = "ghp_" + "abcdefghijklmnopqrst"
        self.file("Downloads/notes.txt", f"{fake_key} {fake_gh} password: hunter2")
        p = self.run_cli("secrets", "--path", str(self.home / "Downloads"))
        self.assertEqual(p.returncode, 0, p.stderr)
        for value in (fake_key, fake_gh, "hunter2", "ABCDEFGH", "abcdefgh"):
            self.assertNotIn(value, p.stdout)
        self.assertEqual(json.loads(p.stdout)["found"], 1)

    def test_unquoted_comma_gives_a_clear_error(self):
        self.file("Downloads/a.txt")
        plan = self.raw_plan(f",{self.home}/Downloads/a.txt,{self.home}/Documents/a.txt,taxes, 2025")
        p = self.run_cli("show", "--plan", plan)
        self.assertNotIn("Traceback", p.stderr)
        self.assertNotEqual(p.returncode, 0)

    def test_missing_plan_gives_a_clear_error(self):
        p = self.run_cli("show", "--plan", "nope.csv")
        self.assertNotIn("Traceback", p.stderr)
        self.assertNotEqual(p.returncode, 0)

    def test_new_plan_twice_gets_a_new_name(self):
        self.run_ok("new-plan", "--name", "dup")
        self.assertNotEqual(self.run_ok("new-plan", "--name", "dup")["plan"], "")
        self.assertEqual(len(list((self.ws / "plans").glob("*dup*.csv"))), 2)

    def test_one_failed_move_does_not_stop_the_rest_or_lose_the_log(self):
        self.file("Downloads/a.txt"); self.file("Downloads/b.txt")
        locked = self.home / "Documents/locked"; locked.mkdir()
        plan = self.plan([("Downloads/a.txt", "Documents/locked/a.txt"), ("Downloads/b.txt", "Documents/b.txt")])
        locked.chmod(0o500)
        self.addCleanup(locked.chmod, 0o700)
        p = self.run_cli("apply", "--plan", plan, "--yes")
        self.assertNotIn("Traceback", p.stderr, p.stderr)
        res = json.loads(p.stdout)
        self.assertEqual(res["moved"], 1)
        self.assertEqual(len(res["skipped"]), 1)
        self.assertTrue((self.home / "Documents/b.txt").exists())
        self.assertTrue(any("moved 1" in l for l in (self.ws / "log.md").read_text().splitlines()))

    def test_case_only_rename(self):
        probe = self.file("Documents/CaseProbe")
        if not (self.home / "Documents/caseprobe").exists():
            self.skipTest("case-sensitive disk")
        self.file("Documents/report.pdf")
        plan = self.plan([("Documents/report.pdf", "Documents/Report.pdf")])
        self.assertEqual(self.run_ok("apply", "--plan", plan, "--yes")["moved"], 1)
        self.assertIn("Report.pdf", os.listdir(self.home / "Documents"))

    def test_undo_can_retry_what_it_skipped(self):
        self.file("Downloads/a.txt", "orig")
        plan = self.plan([("Downloads/a.txt", "Documents/a.txt")])
        self.run_ok("apply", "--plan", plan, "--yes")
        blocker = self.file("Downloads/a.txt", "in the way")
        self.assertEqual(self.run_ok("undo", "--yes")["restored"], 0)
        blocker.unlink()
        self.assertEqual(self.run_ok("undo", "--yes")["restored"], 1)
        self.assertEqual((self.home / "Downloads/a.txt").read_text(), "orig")

    def test_unreadable_watched_folder_does_not_break_count(self):
        (self.home / "Desktop").mkdir(); self.file("Downloads/a.txt")
        (self.home / "Desktop").chmod(0)
        self.addCleanup((self.home / "Desktop").chmod, 0o700)
        p = self.run_cli("count")
        self.assertNotIn("Traceback", p.stderr, p.stderr)
        res = json.loads(p.stdout)
        self.assertEqual(res["total"], 1)
        self.assertEqual(res["unreadable"], ["~/Desktop"])

    def test_default_undo_matches_the_top_of_history(self):
        self.file("Downloads/a.txt"); self.file("Downloads/b.txt")
        self.run_ok("apply", "--plan", self.plan([("Downloads/a.txt", "Documents/a.txt")], name="one"), "--yes")
        (self.ws / "notes-moves.jsonl").write_text(json.dumps({"batch": "later-notes", "time": "2999-01-01T00:00:00", "id": "x", "from": "A", "to": "B"}) + "\n")
        self.assertEqual(self.run_ok("undo")["batch"], self.run_ok("history")[0]["batch"])

    def test_doctor_does_not_open_notes_unless_asked(self):
        checks = self.run_ok("doctor")["checks"]
        self.assertFalse(any(c["name"] == "Control Notes" for c in checks))


if __name__ == "__main__":
    unittest.main(verbosity=1)
