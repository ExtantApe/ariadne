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


class NotesCrash(Base):
    """A pretend Notes, so these never touch the real one. It moves what it's told to, and can fail on cue."""

    def setUp(self):
        super().setUp()
        self.state = self.ws / "fake-notes.json"
        self.state.write_text(json.dumps({"a": "Inbox", "b": "Inbox"}))
        fake = self.ws / "fake-bin"
        fake.mkdir()
        (fake / "osascript").write_text(f"""#!/usr/bin/python3
import json, os, sys
state_file = {str(self.state)!r}
notes = json.load(open(state_file))
r = json.loads(sys.argv[-1])
if r["cmd"] == "folders":
    print(json.dumps([dict(id=n, name=n, path=n, account=r["account"]) for n in ("Inbox", "Filed", "Elsewhere")]))
elif r["cmd"] == "locate":
    print(json.dumps([dict(id=i, title="note " + i, **{{"from": notes[i], "fromId": notes[i]}}) for i in r["ids"] if i in notes]))
elif r["cmd"] == "move":
    moved, failed, skipped = [], [], []
    for i in r["ids"]:
        if r.get("only_in") and notes[i] != r["only_in"]:
            skipped.append(i)
        elif os.environ.get("FAKE_FAIL") == i:
            failed.append(dict(id=i, error="locked"))
        else:
            moved.append(dict(id=i, **{{"from": notes[i], "fromId": notes[i]}}))
            notes[i] = r["to"]
            json.dump(notes, open(state_file, "w"))
            if os.environ.get("FAKE_CRASH_AFTER") == i:
                sys.exit("Notes crashed")
    print(json.dumps(dict(moved=moved, failed=failed, skipped=skipped, to=r["to"])))
""")
        (fake / "osascript").chmod(0o755)
        self.env = {**self.env, "PATH": f"{fake}:{self.env.get('PATH', '/usr/bin:/bin')}"}

    def notes(self):
        return json.loads(self.state.read_text())

    def move(self, **env):
        return subprocess.run(["/usr/bin/python3", str(CLI), "notes", "move", "--id", "a", "--id", "b", "--to", "Filed", "--batch", "n1"],
                              capture_output=True, text=True, env={**self.env, **env})

    def test_a_crash_partway_can_still_be_undone(self):
        self.assertNotEqual(self.move(FAKE_CRASH_AFTER="a").returncode, 0)
        self.assertEqual(self.notes(), {"a": "Filed", "b": "Inbox"})
        result = self.run_ok("notes", "undo", "--batch", "n1", "--yes")
        self.assertEqual((result["restored"], result["left_alone"]), (1, 1))
        self.assertEqual(self.notes(), {"a": "Inbox", "b": "Inbox"})

    def test_a_note_that_could_not_move_is_not_counted(self):
        self.assertEqual(self.move(FAKE_FAIL="b").returncode, 0)
        self.assertEqual(self.notes(), {"a": "Filed", "b": "Inbox"})
        self.assertEqual(next(h for h in self.run_ok("history") if h["batch"] == "n1")["moves"], 1)
        self.assertEqual([r["name"] for r in self.run_ok("where", "note")], ["note a"])
        self.assertEqual(self.run_ok("notes", "undo", "--batch", "n1", "--yes")["restored"], 1)

    def test_undo_leaves_a_note_you_moved_since_alone(self):
        self.assertEqual(self.move().returncode, 0)
        self.state.write_text(json.dumps({"a": "Elsewhere", "b": "Filed"}))
        result = self.run_ok("notes", "undo", "--batch", "n1", "--yes")
        self.assertEqual((result["restored"], result["left_alone"]), (1, 1))
        self.assertEqual(self.notes(), {"a": "Elsewhere", "b": "Inbox"})

    def test_home_is_private(self):
        self.assertEqual(self.ws.stat().st_mode & 0o777, 0o700)


class CommandList(unittest.TestCase):
    def test_every_command_is_listed_and_none_clashes_with_claude_code(self):
        result = subprocess.run(["/usr/bin/python3", str(CLI), "help"], capture_output=True, text=True, check=True)
        names = {p.stem for p in (CLI.parents[1] / "commands").glob("*.md")}
        for name in names:
            self.assertIn(f"  /{name}", result.stdout)
        self.assertFalse(names & {"undo", "help", "doctor", "status", "review", "update"})


class Where(Base):
    def test_finds_a_moved_file_and_says_when_it_was_put_back(self):
        self.file("Downloads/taxes.pdf")
        self.file("Downloads/other.txt")
        plan = self.plan([("Downloads/taxes.pdf", "Documents/Money/taxes-2025.pdf"), ("Downloads/other.txt", "Documents/other.txt")])
        self.run_ok("apply", "--plan", plan, "--yes")
        rows = self.run_ok("where", "TAXES")
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0]["undone"])
        self.assertTrue(rows[0]["to"].endswith("Documents/Money/taxes-2025.pdf"))
        self.assertIn("now in: ~/Documents/Money", self.run_ok("where", "taxes", "--text"))
        self.run_ok("undo", "--yes")
        self.assertTrue(self.run_ok("where", "taxes")[0]["undone"])
        self.assertIn("now in: ~/Downloads/taxes.pdf", self.run_ok("where", "taxes", "--text"))

    def test_finds_a_filed_note_by_title(self):
        (self.ws / "notes-moves.jsonl").write_text(json.dumps({"batch": "n1", "time": "2026-01-01T00:00:00", "id": "x", "title": "Lake house plans", "from": "Inbox", "to": "Home/Projects"}) + "\n")
        rows = self.run_ok("where", "lake")
        self.assertEqual((rows[0]["kind"], rows[0]["to"], rows[0]["undone"]), ("note", "Home/Projects", False))

    def test_nothing_found(self):
        self.assertEqual(self.run_ok("where", "nothing"), [])
        self.assertIn("Nothing filed", self.run_ok("where", "nothing", "--text"))


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


class Bypasses(Base):
    """Every way past a protected path the 2026-11 review found. All of these used to move the file."""

    def raw(self, src, dst, name):
        self.run_ok("new-plan", "--name", name)
        path = next((self.ws / "plans").glob(f"*-{name}.csv"))
        with open(path, "a", newline="") as f:
            csv.writer(f).writerow(["Y", src, dst, "test"])
        return path.name

    def assert_refused(self, src, dst, name):
        plan = self.raw(src, dst, name)
        self.assertTrue(self.run_ok("check", "--plan", plan)["problems"], "check should refuse")
        self.assertEqual(self.run_cli("apply", "--plan", plan, "--yes").returncode, 2)

    def test_dot_dot_out_of_code(self):
        a = self.file("Code/thing/a.py")
        self.assert_refused(f"{self.home}/Downloads/../Code/thing/a.py", f"{self.home}/Documents/a.py", "dotdot")
        self.assertTrue(a.exists())

    def test_dot_dot_into_code(self):
        a = self.file("Downloads/a.py"); (self.home / "Code").mkdir()
        self.assert_refused(str(a), f"{self.home}/Downloads/../Code/a.py", "dotinto")
        self.assertFalse((self.home / "Code/a.py").exists())

    def test_wrong_capitalization(self):
        a = self.file("Code/thing/a.py")
        if not (self.home / "code").exists():
            self.skipTest("case-sensitive disk")
        self.assert_refused(f"{self.home}/code/thing/a.py", f"{self.home}/Documents/a.py", "caps")
        self.assertTrue(a.exists())

    def test_symlink_into_code_as_source(self):
        a = self.file("Code/thing/a.py")
        (self.home / "Downloads/link").symlink_to(self.home / "Code")
        self.assert_refused(f"{self.home}/Downloads/link/thing/a.py", f"{self.home}/Documents/a.py", "linksrc")
        self.assertTrue(a.exists())

    def test_symlink_into_code_as_destination(self):
        a = self.file("Downloads/a.py"); (self.home / "Code").mkdir()
        (self.home / "Documents/link").symlink_to(self.home / "Code")
        self.assert_refused(str(a), f"{self.home}/Documents/link/a.py", "linkdst")
        self.assertFalse((self.home / "Code/a.py").exists())

    def test_app_owned_any_capitalization(self):
        a = self.file("Documents/zoom/call.mp4")
        self.assert_refused(str(a), f"{self.home}/Documents/call.mp4", "zoom")
        self.assertTrue(a.exists())

    def test_folder_with_differently_capitalized_app_folder_inside(self):
        self.file("Downloads/stuff/zoom/call.mp4")
        self.assert_refused(f"{self.home}/Downloads/stuff", f"{self.home}/Documents/stuff", "zoomin")

    def test_standard_folder_any_capitalization(self):
        self.file("Documents/a.txt")
        if not (self.home / "documents").exists():
            self.skipTest("case-sensitive disk")
        self.assert_refused(f"{self.home}/documents", f"{self.home}/Downloads/documents", "stdcaps")

    def test_merge_through_a_symlink_cannot_reach_code(self):
        (self.home / "Code/thing").mkdir(parents=True)
        self.file("Downloads/f/a.py")
        (self.home / "Documents/f").symlink_to(self.home / "Code/thing")
        self.assert_refused(f"{self.home}/Downloads/f", f"{self.home}/Documents/f", "merge")
        self.assertFalse((self.home / "Code/thing/a.py").exists())

    def test_nested_mobile_documents_does_not_open_the_library(self):
        a = self.file("Library/Stuff/Mobile Documents/a.txt")
        self.assert_refused(str(a), f"{self.home}/Documents/a.txt", "lib")
        self.assertTrue(a.exists())

    def test_the_move_itself_checks_again(self):
        sys_path = str(CLI.parent)
        code = (
            "import sys; sys.path.insert(0, %r); import files; from pathlib import Path\n"
            "m, s = [], []\n"
            "files.move_one(Path(sys.argv[1]), Path(sys.argv[2]), 'b', 'r', m, s)\n"
            "print(len(m), len(s))" % sys_path
        )
        a = self.file("Downloads/a.py"); (self.home / "Code").mkdir()
        p = subprocess.run(["/usr/bin/python3", "-c", code, str(a), str(self.home / "Code/a.py")], capture_output=True, text=True, env=self.env)
        self.assertEqual(p.stdout.split(), ["0", "1"], p.stderr)
        self.assertTrue(a.exists())

    def test_undo_can_still_put_back_what_an_old_build_moved_out_of_code(self):
        moved = self.file("Documents/a.py", "rescued"); (self.home / "Code").mkdir()
        (self.ws / "moves.log.jsonl").write_text(json.dumps({"batch": "old", "time": "2026-01-01T00:00:00", "from": "~/Code/a.py", "to": "~/Documents/a.py"}) + "\n")
        self.assertEqual(self.run_ok("undo", "--batch", "old", "--yes")["restored"], 1)
        self.assertEqual((self.home / "Code/a.py").read_text(), "rescued")
        self.assertFalse(moved.exists())


class CrashSafety(Base):
    def test_log_is_written_before_the_move(self):
        a = self.file("Downloads/a.txt")
        plan = self.plan([("Downloads/a.txt", "Documents/a.txt")])
        code = (
            "import sys, json, os; sys.path.insert(0, %r); sys.argv = ['files', 'apply', '--plan', %r, '--yes']; import files, shutil\n"
            "def die(s, d):\n"
            "    assert any(e.get('to', '').endswith('Documents/a.txt') for e in files.load_log()), 'not logged first'\n"
            "    shutil.real_move(s, d); os._exit(9)\n"
            "shutil.real_move = shutil.move; shutil.move = die\n"
            "files.main()" % (str(CLI.parent), plan)
        )
        p = subprocess.run(["/usr/bin/python3", "-c", code], capture_output=True, text=True, env=self.env)
        self.assertEqual(p.returncode, 9, p.stderr)
        self.assertEqual(self.run_ok("undo", "--yes")["restored"], 1)
        self.assertTrue(a.exists())

    def test_a_failed_move_is_not_in_history(self):
        self.file("Downloads/a.txt")
        locked = self.home / "Documents/locked"; locked.mkdir()
        plan = self.plan([("Downloads/a.txt", "Documents/locked/a.txt")])
        locked.chmod(0o500)
        self.addCleanup(locked.chmod, 0o700)
        self.assertEqual(self.run_ok("apply", "--plan", plan, "--yes")["moved"], 0)
        self.assertEqual(self.run_ok("history"), [])

    def test_torn_log_line_is_survivable(self):
        self.file("Downloads/a.txt")
        self.run_ok("apply", "--plan", self.plan([("Downloads/a.txt", "Documents/a.txt")]), "--yes")
        with open(self.ws / "moves.log.jsonl", "a") as f:
            f.write('{"batch": "torn", "ti')
        self.assertEqual(len(self.run_ok("history")), 1)

    def test_undo_that_finds_it_already_back_is_not_a_failure(self):
        a = self.file("Downloads/a.txt")
        self.run_ok("apply", "--plan", self.plan([("Downloads/a.txt", "Documents/a.txt")]), "--yes")
        (self.home / "Documents/a.txt").rename(a)
        self.assertEqual(self.run_ok("undo", "--yes")["skipped_total"], 0)


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

    def test_one_broken_plan_does_not_hide_the_others(self):
        self.file("Downloads/a.txt")
        self.plan([("Downloads/a.txt", "Documents/a.txt")], name="good", approve=False)
        self.run_ok("new-plan", "--name", "bad")
        bad = next((self.ws / "plans").glob("*-bad.csv"))
        with open(bad, "a") as f:
            f.write('Y,a,b,c,too,many,columns\n')
        (self.ws / "plans" / "2026-01-01-binary.csv").write_bytes(b"\xff\xfe\x00\x01")
        rows = {r["plan"]: r for r in self.run_ok("plans")}
        self.assertEqual(len(rows), 3)
        self.assertIn("error", rows[bad.name])
        self.assertIn("error", rows["2026-01-01-binary.csv"])
        self.assertTrue(any(k.endswith("-good.csv") and "error" not in v for k, v in rows.items()))

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


class MoveRow(Base):
    def test_moves_a_row_and_learns(self):
        self.file("Downloads/a.txt")
        plan = self.plan([("Downloads/a.txt", "Documents/x/a.txt")], approve=False)
        self.run_ok("move-row", "--plan", plan, "--line", "2", "--to", str(self.home / "Documents/y"))
        self.assertTrue(self.run_ok("show", "--plan", plan)["rows"][0]["proposed_path"].endswith("Documents/y/a.txt"))
        self.assertIn("a.txt →", (self.ws / "filing-rules.md").read_text())
        self.run_ok("approve", "--plan", plan, "--all")
        self.assertEqual(self.run_ok("apply", "--plan", plan, "--yes")["moved"], 1)
        self.assertTrue((self.home / "Documents/y/a.txt").exists())

    def test_undoing_a_row_move_teaches_nothing(self):
        self.file("Downloads/a.txt")
        plan = self.plan([("Downloads/a.txt", "Documents/x/a.txt")], approve=False)
        before = (self.ws / "filing-rules.md").read_text()
        self.run_ok("move-row", "--plan", plan, "--line", "2", "--to", str(self.home / "Documents/y"), "--no-learn")
        self.assertEqual((self.ws / "filing-rules.md").read_text(), before)

    def test_undoing_a_drag_takes_the_correction_back_out(self):
        self.file("Downloads/a.txt")
        plan = self.plan([("Downloads/a.txt", "Documents/x/a.txt")], approve=False)
        before = (self.ws / "filing-rules.md").read_text()
        self.run_ok("move-row", "--plan", plan, "--line", "2", "--to", str(self.home / "Documents/y"))
        self.assertNotEqual((self.ws / "filing-rules.md").read_text(), before)
        self.run_ok("move-row", "--plan", plan, "--line", "2", "--to", str(self.home / "Documents/x"), "--unlearn")
        self.assertEqual((self.ws / "filing-rules.md").read_text(), before)
        self.assertTrue(self.run_ok("show", "--plan", plan)["rows"][0]["proposed_path"].endswith("Documents/x/a.txt"))

    def test_unlearn_leaves_other_corrections_alone(self):
        self.file("Downloads/a.txt"); self.file("Downloads/b.txt")
        plan = self.plan([("Downloads/a.txt", "Documents/x/a.txt"), ("Downloads/b.txt", "Documents/x/b.txt")], approve=False)
        self.run_ok("move-row", "--plan", plan, "--line", "2", "--to", str(self.home / "Documents/y"))
        self.run_ok("move-row", "--plan", plan, "--line", "3", "--to", str(self.home / "Documents/y"))
        self.run_ok("move-row", "--plan", plan, "--line", "3", "--to", str(self.home / "Documents/x"), "--unlearn")
        rules = (self.ws / "filing-rules.md").read_text()
        self.assertIn("a.txt →", rules)
        self.assertNotIn("b.txt →", rules)

    def test_protected_destination_is_still_refused(self):
        self.file("Downloads/a.txt")
        plan = self.plan([("Downloads/a.txt", "Documents/a.txt")], approve=False)
        self.run_ok("move-row", "--plan", plan, "--line", "2", "--to", str(self.home / "Code/z"))
        self.run_ok("approve", "--plan", plan, "--all")
        self.assertEqual(self.run_cli("apply", "--plan", plan, "--yes").returncode, 2)
        self.assertTrue((self.home / "Downloads/a.txt").exists())

    def test_unknown_line_gives_a_clear_error(self):
        plan = self.plan([], approve=False)
        p = self.run_cli("move-row", "--plan", plan, "--line", "9", "--to", "~/x")
        self.assertNotEqual(p.returncode, 0)
        self.assertNotIn("Traceback", p.stderr)


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
