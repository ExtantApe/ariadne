#!/usr/bin/env python3
"""
ariadne: keep your files and Apple Notes filed, with a yes. Never deletes, never overwrites, and every batch can be undone.

  ariadne install                     set up Ariadne's home and put `ariadne` on your PATH (~/.local/bin)
  ariadne init                        set up or refresh Ariadne's home; your config, map and rules are kept
  ariadne doctor [--notes]            what's working and what needs a permission (--notes also tests controlling Notes, which opens it)
  ariadne home                        print Ariadne's home folder
  ariadne rules                       print the operating rules (how Claude runs a filing pass)
  ariadne notes ...                   Apple Notes filing (ariadne notes --help)
  ariadne scan|count|new-plan|plans|show|check|approve|apply|verify|undo|history|dupes|secrets|alias|prune-empty|protect
                                      filing (ariadne --help-files)
"""
import sys

sys.dont_write_bytecode = True  # the app bundle must stay exactly as it was signed

import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
HOME = Path.home()
WS = Path(os.environ.get("ARIADNE_HOME") or HOME / "Library/Application Support/Ariadne")


def find_claude():
    for p in (HOME / ".local/bin/claude", Path("/opt/homebrew/bin/claude"), Path("/usr/local/bin/claude")):
        if p.exists():
            return str(p)
    return shutil.which("claude")


def init():
    """Engine files are refreshed every time. The user's config, map and rules are only created if missing."""
    (WS / "plans").mkdir(parents=True, exist_ok=True)
    (WS / ".claude/commands").mkdir(parents=True, exist_ok=True)
    for name in ("config.json", "filing-map.md", "filing-rules.md"):
        if not (WS / name).exists():
            shutil.copy2(ROOT / "templates" / name, WS / name)
    shutil.copy2(ROOT / "RULES.md", WS / "RULES.md")
    shutil.copy2(ROOT / "templates/settings.json", WS / ".claude/settings.json")
    (WS / "CLAUDE.md").write_text("@RULES.md\n")
    for f in (ROOT / "commands").glob("*.md"):
        shutil.copy2(f, WS / ".claude/commands" / f.name)
    return {"home": str(WS)}


def install():
    res = init()
    bindir = HOME / ".local/bin"
    bindir.mkdir(parents=True, exist_ok=True)
    link = bindir / "ariadne"
    target = ROOT / "bin/ariadne"
    if link.is_symlink() or not link.exists():
        link.unlink(missing_ok=True)
        link.symlink_to(target)
        res["command"] = str(link)
    else:
        res["command"] = f"left alone: {link} already exists and isn't a link"
    if str(bindir) not in os.environ.get("PATH", "").split(":"):
        res["note"] = f"add {bindir} to your PATH"
    return res


def doctor(notes=False):
    checks = []
    def add(name, ok, detail=""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})
    add("Home folder", WS.exists(), str(WS))
    add("Filing map", (WS / "filing-map.md").exists(), "filing-map.md")
    claude = find_claude()
    add("Claude Code", claude, claude or "not found. Suggesting plans needs it; reviewing, moving and undoing don't.")
    cfg = json.loads((WS / "config.json").read_text()) if (WS / "config.json").exists() else {}
    for w in cfg.get("watch", ["~/Desktop", "~/Downloads"]):
        p = Path(os.path.expanduser(w))
        try:
            add(f"Read {w}", True, f"{sum(1 for _ in p.iterdir())} items")
        except OSError as e:
            add(f"Read {w}", False, f"{e.strerror}. Allow it in System Settings → Privacy & Security → Files and Folders.")
    store = HOME / "Library/Group Containers/group.com.apple.notes/NoteStore.sqlite"
    try:
        with open(store, "rb"):
            add("Read the Notes database", True, "needs Full Disk Access")
    except OSError as e:
        add("Read the Notes database", False, f"{e.strerror}. Turn on Full Disk Access for Ariadne to sort Notes; file filing works without it.")
    if notes:  # opens Notes, so only when asked
        p = subprocess.run(["osascript", "-l", "JavaScript", "-e", "Application('Notes').accounts().length"], capture_output=True, text=True, timeout=60)
        add("Control Notes", p.returncode == 0, (p.stderr.strip() or "Automation allowed")[:200])
    return {"checks": checks}


def main():
    argv = sys.argv[1:]
    cmd = argv[0] if argv else ""
    if cmd in ("", "-h", "--help", "help"):
        print(__doc__.strip()); return
    if cmd == "--help-files":
        sys.argv = ["ariadne", "--help"]
    elif cmd == "home":
        print(WS); return
    elif cmd == "rules":
        print((ROOT / "RULES.md").read_text()); return
    elif cmd == "doctor":
        print(json.dumps(doctor("--notes" in argv), indent=1, ensure_ascii=False)); return
    elif cmd in ("init", "install"):
        print(json.dumps({"init": init, "install": install}[cmd](), indent=1, ensure_ascii=False)); return
    elif cmd == "notes":
        import notes
        notes.main(argv[1:]); return
    import files
    files.main()


if __name__ == "__main__":
    main()
