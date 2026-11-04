#!/usr/bin/env python3
"""
files.py: the filing engine of Ariadne (macOS).

Plans moves, shows them, applies only what was approved, logs every move and can undo any batch.
It never deletes a file and never overwrites one. Config, plans and logs live in Ariadne's home:
~/Library/Application Support/Ariadne, or $ARIADNE_HOME.

Commands (JSON output unless --text)
  scan  [--path P ...] [--deep]       read-only inventory of the watched folders (config.filing.watch) or the given paths.
                                      --deep walks subfolders. Never downloads cloud-only files.
  count                               unfiled items per watched folder (cheap; used by check-in offers)
  new-plan --name NAME                create plans/<date>-<name>.csv with the header, for Claude to fill in
  plans                               every plan: row counts, how many are approved, whether it has been applied
  show --plan FILE                    one plan's rows plus its check results
  approve --plan FILE (--all | --lines 2,3) [--clear]
                                      set (or clear) approve=Y on rows. Only do this after the user said yes.
  protect [--path P] [--notes-folder F] [--note-id ID]
                                      add to the never-touch lists (other tools use this to protect what they own)
  check --plan FILE                   validate a plan: sources exist, destinations are free, nothing is moved twice,
                                      no app-owned or never-touch paths; prints the dry run
  apply --plan FILE [--batch NAME] --yes
                                      move every row with approve=Y. Folders whose destination already exists are merged
                                      child by child. A clash is skipped and reported, never overwritten.
  verify --plan FILE                  report every approved row that is not where the plan put it
  undo  [--batch NAME] [--yes]        reverse a batch from the move log (default: the most recent)
  history                             batches in the move log, newest first
  dupes [--path P ...] [--hash]       same name+size groups (and same content with --hash, local files only)
  secrets [--path P ...]              files that look like they hold passwords, keys or recovery codes.
                                      Reports where and what kind, NEVER the values.
  alias --target T --at DIR [--name N] --yes
                                      a Finder alias (iCloud syncs aliases; it does not sync symlinks)
  prune-empty --path P --yes          remove folders under P that are empty (only .DS_Store inside). The one delete it does.

Paths in plans may start with ~ . Plan columns: approve, current_path, proposed_path, reason.
Config: config.json in Ariadne's home; see templates/config.json.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

HOME = Path.home()
WS = Path(os.environ.get("ARIADNE_HOME") or HOME / "Library/Application Support/Ariadne")
CFG = json.loads((WS / "config.json").read_text()) if (WS / "config.json").exists() else {}
FCFG = CFG
ICLOUD = HOME / "Library/Mobile Documents/com~apple~CloudDocs"
DATA = WS
PLANS = WS / "plans"
MOVELOG = WS / "moves.log.jsonl"
NOTESLOG = WS / "notes-moves.jsonl"
LOG_MD = WS / "log.md"
# Always protected, whatever the config says. Config can only add to these.
NEVER_TOUCH_ALWAYS = ["~/Code"]
STANDARD_FOLDERS = ["Desktop", "Documents", "Downloads", "Pictures", "Movies", "Music", "Applications", "Public"]
PLAN_COLS = ["approve", "current_path", "proposed_path", "reason"]
SKIP_NAMES = {".DS_Store", ".localized", "Icon\r"}

# Folders that apps write to. Moving them breaks the app. Matched against any path component.
APP_OWNED_DEFAULT = ["Adobe", "TimeBoltData", "TimeBoltScratchPath", "Zoom", "Codex", "Aftershoot Projects",
                     "Photos Library.photoslibrary", "Lightroom Library.lrlibrary", "Photo Booth Library",
                     "Family Tree Maker", "Microsoft User Data", "node_modules", ".git"]
SECRET_NAME = re.compile(r"(password|passcode|recovery[ _-]?codes?|backup[ _-]?codes?|credential|secret|api[ _-]?key|"
                         r"\.env$|\.pem$|\.key$|2fa|seed[ _-]?phrase|wp-config\.php$)", re.I)
SECRET_TEXT = re.compile(r"(password\s*[:=]|passwd|api[_ -]?key\s*[:=]|secret[_ -]?key|token\s*[:=]|recovery code|"
                         r"backup code|BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY|sk_live_[0-9A-Za-z]{8}|ghp_[0-9A-Za-z]{20}|"
                         r"AKIA[0-9A-Z]{16}|DB_PASSWORD)", re.I)
TEXT_EXT = {".txt", ".md", ".csv", ".json", ".env", ".conf", ".ini", ".yml", ".yaml", ".pem", ".key", ".php", ".rtf"}


# ------------------------------------------------------------------ helpers

def out(obj, text=False):
    if text and isinstance(obj, (list, dict)):
        print(json.dumps(obj, indent=1, ensure_ascii=False))
    else:
        print(json.dumps(obj, indent=1, ensure_ascii=False, default=str))


def expand(p: str) -> Path:
    return Path(os.path.expanduser(p.strip())).absolute()


def tilde(p: Path) -> str:
    s = str(p)
    return "~" + s[len(str(HOME)):] if s.startswith(str(HOME)) else s


def app_owned() -> list[str]:
    return APP_OWNED_DEFAULT + [n for n in FCFG.get("app_owned", []) if n not in APP_OWNED_DEFAULT]


def never_touch() -> list[Path]:
    return [expand(p) for p in NEVER_TOUCH_ALWAYS + FCFG.get("never_touch", [])]


def in_git_repo(p: Path) -> Path | None:
    """The repository p is in or is, if any. Moving code around breaks it."""
    for d in [p, *p.parents]:
        if d == HOME or d == d.parent:
            return None
        if os.path.lexists(d / ".git"):
            return d
    return None


def blocked(p: Path) -> str | None:
    parts = set(p.parts)
    for name in app_owned():
        if name in parts:
            return f"app-owned folder '{name}'"
    for nt in never_touch():
        if p == nt or nt in p.parents:
            return f"never-touch path {tilde(nt)}"
    if p == HOME or p in (HOME / "Library", ICLOUD):
        return "a root folder"
    if p.parent == HOME and p.name in STANDARD_FOLDERS:
        return "a standard folder"
    if HOME not in p.parents and p.parts[:2] != ("/", "Volumes"):
        return "somewhere outside your home folder"
    if p == WS or WS in p.parents:
        return "Ariadne's own folder"
    if HOME / "Library" in p.parents and "Mobile Documents" not in p.parts:
        return "the Library folder"
    repo = in_git_repo(p)
    if repo:
        return f"git repository {tilde(repo)}"
    return None


def contains_protected(folder: Path) -> str | None:
    """What protected thing is inside this folder, if any. Moving the folder would move it too."""
    owned, nt = set(app_owned()), set(never_touch())
    for dp, dns, fns in os.walk(folder):
        if ".git" in dns or ".git" in fns:
            return f"a git repository ({tilde(Path(dp))})"
        for d in dns:
            if d in owned:
                return f"an app-owned folder ({d})"
            if Path(dp) / d in nt:
                return f"a never-touch folder ({d})"
    return None


def same_item(a: Path, b: Path) -> bool:
    """True when two paths are one item: a case-only rename on a case-insensitive disk."""
    try:
        return os.path.samestat(os.lstat(a), os.lstat(b))
    except OSError:
        return False


def plain_path(p: str) -> bool:
    return p.startswith("/") or p.startswith("~/")


def cloud_only(p: Path, st: os.stat_result | None = None) -> bool:
    """Heuristic: dataless iCloud files report a size but allocate no blocks. Never reads the file."""
    if p.name.startswith(".") and p.name.endswith(".icloud"):
        return True
    try:
        st = st or os.lstat(p)
    except OSError:
        return False
    return getattr(st, "st_blocks", 1) == 0 and st.st_size > 0


def same_volume(a: Path, b: Path) -> bool:
    try:
        b_exist = b
        while not b_exist.exists():
            b_exist = b_exist.parent
        return os.lstat(a).st_dev == os.lstat(b_exist).st_dev
    except OSError:
        return True


def now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def log_md(line: str):
    LOG_MD.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_MD, "a") as f:
        f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M} · {line}\n")


def watched() -> list[Path]:
    return [expand(p) for p in FCFG.get("watch", ["~/Desktop", "~/Downloads"])]


def plan_path(path: str) -> Path:
    p = expand(path)
    if not p.is_absolute() or (not p.exists() and (PLANS / path).exists()):
        return PLANS / path
    return p


def read_plan(path: str) -> list[dict]:
    rows = []
    with open(plan_path(path), newline="") as f:
        for i, r in enumerate(csv.DictReader(f), start=2):
            if None in r:
                sys.exit(f"{plan_path(path).name} line {i} has too many columns. Put quotes around any field with a comma in it.")
            r = {k: (v or "").strip() for k, v in r.items()}
            r["line"] = i
            rows.append(r)
    return rows


def approved(rows):
    return [r for r in rows if r.get("approve", "").upper() in ("Y", "YES") and r.get("proposed_path")]


def walk_files(root: Path, deep: bool):
    if root.is_file():
        yield root
        return
    if not deep:
        for c in sorted(root.iterdir()):
            if c.name not in SKIP_NAMES and not c.name.startswith("."):
                yield c
        return
    for dp, dns, fns in os.walk(root):
        dpp = Path(dp)
        dns[:] = sorted(d for d in dns if not d.startswith(".") and not blocked(dpp / d))
        for f in sorted(fns):
            if f in SKIP_NAMES or (f.startswith(".") and not f.endswith(".icloud")):
                continue
            yield dpp / f


def item_info(p: Path) -> dict:
    try:
        st = os.lstat(p)
    except OSError as e:
        return {"path": tilde(p), "error": str(e)}
    is_dir = p.is_dir() and not p.is_symlink()
    info = {"path": tilde(p), "name": p.name, "kind": "folder" if is_dir else "file",
            "modified": dt.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d"),
            "ext": "" if is_dir else p.suffix.lower().lstrip(".")}
    if is_dir:
        n = s = c = 0
        for dp, dns, fns in os.walk(p):
            for f in fns:
                if f in SKIP_NAMES:
                    continue
                try:
                    fst = os.lstat(os.path.join(dp, f))
                except OSError:
                    continue
                n += 1; s += fst.st_size
                c += cloud_only(Path(dp) / f, fst)
        info.update(files=n, bytes=s, cloud_only_files=c)
    else:
        info.update(bytes=st.st_size, cloud_only=cloud_only(p, st))
    b = blocked(p)
    if b:
        info["skip"] = b
    return info


# ------------------------------------------------------------------ commands

def cmd_scan(a):
    roots = [expand(p) for p in a.path] if a.path else watched()
    items = []
    for r in roots:
        if not r.exists():
            items.append({"path": tilde(r), "error": "missing"}); continue
        try:
            for p in walk_files(r, a.deep):
                items.append(item_info(p))
        except OSError as e:
            items.append({"path": tilde(r), "error": e.strerror})
    (DATA / "scans").mkdir(parents=True, exist_ok=True)
    for old in sorted((DATA / "scans").glob("scan-*.json"))[:-19]:   # our own working files; keep the recent ones
        old.unlink()
    snap = DATA / "scans" / f"scan-{dt.datetime.now():%Y%m%d-%H%M%S}.json"
    snap.write_text(json.dumps(items, indent=1, ensure_ascii=False))
    summary = Counter((i.get("kind"), "cloud" if i.get("cloud_only") else "local") for i in items if "kind" in i)
    out({"items": len(items), "saved": tilde(snap),
         "summary": {f"{k[0]}s ({k[1]})": v for k, v in summary.items()},
         "skipped": [i["path"] for i in items if i.get("skip")][:20],
         "sample": items[:40]})


def cmd_count(a):
    res, unreadable = {}, []
    for r in watched():
        try:
            res[tilde(r)] = sum(1 for c in r.iterdir() if c.name not in SKIP_NAMES and not c.name.startswith(".")
                                and not c.name.startswith("_") and not blocked(c))
        except FileNotFoundError:
            continue
        except OSError:
            unreadable.append(tilde(r))
    out({"unfiled": res, "total": sum(res.values()), "unreadable": unreadable})


def cmd_new_plan(a):
    PLANS.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", a.name).strip("-") or "plan"
    p = PLANS / f"{dt.date.today():%Y-%m-%d}-{slug}.csv"
    n = 2
    while p.exists():
        p = PLANS / f"{dt.date.today():%Y-%m-%d}-{slug}-{n}.csv"; n += 1
    with open(p, "w", newline="") as f:
        csv.writer(f).writerow(PLAN_COLS)
    out({"plan": tilde(p), "columns": PLAN_COLS,
         "note": "one row per item; approve=Y only after the user says yes; paths may start with ~"})


def live_moves(batch: str, log=None) -> list[dict]:
    """Moves in a batch that are still in effect: an undo cancels what it put back, but not what it had to skip."""
    log = load_log() if log is None else log
    undos = [(i, e) for i, e in enumerate(log) if e.get("undo_of") == batch]
    last, skipped = (undos[-1][0], set(undos[-1][1].get("skipped", []))) if undos else (-1, set())
    return [e for i, e in enumerate(log) if e.get("batch") == batch and "from" in e and (i > last or e["to"] in skipped)]


def moved_count(batch: str, log=None) -> int:
    return len(live_moves(batch, log))


def row_state(r: dict) -> str:
    """After a plan has been applied, a row is only still waiting if its source is still there. Where it went since is the user's business."""
    if not plain_path(r.get("current_path", "")):
        return "pending"
    s = expand(r["current_path"])
    if r.get("proposed_path") and plain_path(r["proposed_path"]):
        d = expand(r["proposed_path"])
        if s != d and str(s).lower() == str(d).lower() and same_item(s, d):
            return "moved" if d.name in os.listdir(d.parent) else "pending"
    return "pending" if os.path.lexists(s) else "moved"


def cmd_plans(a):
    log = load_log()
    res = []
    for p in sorted(PLANS.glob("*.csv"), key=lambda x: x.stat().st_mtime, reverse=True) if PLANS.exists() else []:
        rows = read_plan(str(p))
        moved = moved_count(p.stem, log)
        res.append({"plan": p.name, "rows": len(rows), "approved": len(approved(rows)), "moved": moved,
                    "pending": sum(1 for r in rows if row_state(r) == "pending") if moved else len(rows),
                    "modified": dt.datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")})
    out(res)


def cmd_show(a):
    rows = read_plan(a.plan)
    probs, warns = analyse(rows)
    moved = moved_count(plan_path(a.plan).stem)
    for r in rows:
        r["state"] = row_state(r) if moved else "pending"
    out({"plan": plan_path(a.plan).name, "rows": rows, "problems": probs, "warnings": warns, "moved": moved})


def cmd_approve(a):
    if not a.all and not a.lines:
        sys.exit("approve needs --all or --lines")
    want = None if a.all else {int(x) for x in a.lines.split(",") if x.strip()}
    p = plan_path(a.plan)
    rows = read_plan(str(p))
    changed = 0
    for r in rows:
        if want is None or r["line"] in want:
            new = "" if a.clear else "Y"
            changed += r.get("approve", "") != new
            r["approve"] = new
    tmp = p.with_suffix(".csv.tmp")
    cols = [c for c in rows[0] if c != "line"] if rows else PLAN_COLS
    with open(tmp, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader(); w.writerows(rows)
    os.replace(tmp, p)
    out({"plan": p.name, "changed": changed, "approved": len(approved(rows))})


def cmd_protect(a):
    cfg_path = WS / "config.json"
    cfg = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
    for key, vals in (("never_touch", a.path), ("notes_never_touch", a.notes_folder), ("notes_never_touch_ids", a.note_id)):
        cur = cfg.setdefault(key, [])
        cur.extend(v for v in (vals or []) if v not in cur)
    WS.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")
    out({k: cfg.get(k, []) for k in ("never_touch", "notes_never_touch", "notes_never_touch_ids")})


def analyse(rows):
    """Problems and warnings for a plan, without touching anything."""
    probs, warns = [], []
    rows = approved(rows)
    for r in rows:
        if not (plain_path(r.get("current_path", "")) and plain_path(r["proposed_path"])):
            probs.append(f"line {r['line']}: paths must be full paths starting with / or ~/")
    rows = [r for r in rows if plain_path(r.get("current_path", "")) and plain_path(r["proposed_path"])]
    srcs = [expand(r["current_path"]) for r in rows]
    dsts = [expand(r["proposed_path"]) for r in rows]
    seen_dst = Counter(dsts)
    src_set = set(srcs)
    for r, s, d in zip(rows, srcs, dsts):
        where = f"line {r['line']}"
        if not os.path.lexists(s):
            probs.append(f"{where}: source missing: {tilde(s)}"); continue
        for p, label in ((s, "source"), (d, "destination")):
            b = blocked(p)
            if b:
                probs.append(f"{where}: {label} is in a {b}: {tilde(p)}")
        if s.is_dir() and not s.is_symlink():
            inner = contains_protected(s)
            if inner:
                probs.append(f"{where}: this folder contains {inner}, which has to stay where it is: {tilde(s)}")
        if seen_dst[d] > 1:
            probs.append(f"{where}: two rows move to the same place: {tilde(d)}")
        if any(x != s and x in s.parents for x in src_set):
            probs.append(f"{where}: its parent folder is also moved in this plan; drop one of the two rows")
        if d == s or (s in d.parents):
            probs.append(f"{where}: destination is inside the source")
        if os.path.lexists(d) and not same_item(s, d):
            if s.is_dir() and d.is_dir():
                warns.append(f"{where}: {tilde(d)} exists; contents will be merged child by child")
            else:
                probs.append(f"{where}: destination exists and would be overwritten: {tilde(d)}")
        if not same_volume(s, d.parent):
            if (s.is_file() and cloud_only(s)) or s.is_dir():
                warns.append(f"{where}: crosses volumes, so it copies (and downloads if cloud-only): {tilde(s)}")
    return probs, warns


def cmd_check(a):
    rows = read_plan(a.plan)
    probs, warns = analyse(rows)
    ap = approved(rows)
    dest_areas = Counter(tilde(expand(r["proposed_path"]).parent) for r in ap)
    out({"rows": len(rows), "approved": len(ap), "problems": probs, "warnings": warns,
         "by_destination": dict(dest_areas.most_common(30)),
         "dry_run": [f"{r['current_path']}  →  {r['proposed_path']}" for r in ap[:60]],
         "ok_to_apply": not probs})


def move_one(src: Path, dst: Path, batch: str, reason: str, moved: list, skipped: list):
    """Move src to dst. Merge into an existing folder child by child; never overwrite. A failure skips this item and carries on."""
    try:
        if os.path.lexists(dst) and not same_item(src, dst):
            if src.is_dir() and not src.is_symlink() and dst.is_dir():
                for c in sorted(src.iterdir()):
                    if c.name in SKIP_NAMES:
                        continue
                    move_one(c, dst / c.name, batch, reason, moved, skipped)
                return
            skipped.append({"from": tilde(src), "to": tilde(dst), "why": "destination exists"})
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
    except OSError as e:
        skipped.append({"from": tilde(src), "to": tilde(dst), "why": e.strerror or str(e)})
        return
    rec = {"batch": batch, "time": now(), "from": tilde(src), "to": tilde(dst), "reason": reason}
    with open(MOVELOG, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n"); f.flush(); os.fsync(f.fileno())
    moved.append(rec)


def cmd_apply(a):
    if not a.yes:
        sys.exit("apply needs --yes (only after the user approved this plan)")
    rows = read_plan(a.plan)
    probs, _ = analyse(rows)
    if probs and not a.skip_problems:
        out({"applied": False, "problems": probs, "hint": "fix the plan, or rerun with --skip-problems"}); sys.exit(2)
    bad_lines = {int(re.match(r"line (\d+)", p).group(1)) for p in probs if p.startswith("line ")}
    batch = a.batch or plan_path(a.plan).stem
    DATA.mkdir(parents=True, exist_ok=True)
    moved, skipped = [], []
    for r in approved(rows):
        if r["line"] in bad_lines:
            skipped.append({"from": r["current_path"], "why": "problem in check"}); continue
        move_one(expand(r["current_path"]), expand(r["proposed_path"]), batch, r.get("reason", ""), moved, skipped)
    log_md(f"filing · batch {batch}: moved {len(moved)}, skipped {len(skipped)} · plan {tilde(plan_path(a.plan))}")
    out({"batch": batch, "moved": len(moved), "skipped": skipped, "log": tilde(MOVELOG)})


def cmd_verify(a):
    bad = []
    for r in approved(read_plan(a.plan)):
        s, d = expand(r["current_path"]), expand(r["proposed_path"])
        if not os.path.lexists(d):
            bad.append({"line": r["line"], "missing_at": r["proposed_path"]})
        elif s != d and same_item(s, d):
            continue
        elif os.path.lexists(s) and not (s.is_dir() and not has_files(s)):
            bad.append({"line": r["line"], "still_at_source": r["current_path"]})
    out({"checked": len(approved(read_plan(a.plan))), "not_in_place": bad})


def has_files(p: Path) -> bool:
    return any(f not in SKIP_NAMES for _, _, fs in os.walk(p) for f in fs)


def load_log(path: Path = MOVELOG):
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def history_rows() -> list[dict]:
    log = load_log()
    by = {}
    for e in log:
        if "from" in e and not e.get("undo_of"):
            b = by.setdefault(e["batch"], {"batch": e["batch"], "kind": "files", "moves": 0, "first": e["time"], "last": e["time"], "undone_at": None})
            b["moves"] += 1; b["last"] = e["time"]
    for b in by.values():
        if not live_moves(b["batch"], log):
            b["undone_at"] = max(e["time"] for e in log if e.get("undo_of") == b["batch"])
    for e in load_log(NOTESLOG):
        if e.get("undo_of"):
            if e["undo_of"] in by: by[e["undo_of"]]["undone_at"] = e["time"]
            continue
        b = by.setdefault(e["batch"], {"batch": e["batch"], "kind": "notes", "moves": 0, "first": e["time"], "last": e["time"], "undone_at": None})
        b["moves"] += 1; b["last"] = e["time"]
    return sorted(by.values(), key=lambda b: b["last"], reverse=True)


def cmd_history(a):
    out(history_rows())


def cmd_undo(a):
    batch = a.batch
    if not batch:
        rows = [b for b in history_rows() if not b["undone_at"]]
        if not rows:
            sys.exit("nothing to undo")
        batch = rows[0]["batch"]
    log = load_log()
    if not any(e.get("batch") == batch for e in log) and any(e.get("batch") == batch for e in load_log(NOTESLOG)):
        import notes
        out(notes.undo(batch, a.yes)); return
    plan = list(reversed(live_moves(batch, log)))
    if not plan:
        sys.exit(f"batch {batch} has nothing left to undo")
    if not a.yes:
        out({"batch": batch, "would_restore": len(plan), "sample": [f"{e['to']} → {e['from']}" for e in plan[:20]],
             "hint": "rerun with --yes"}); return
    restored, skipped = 0, []
    for e in plan:
        s, d = expand(e["to"]), expand(e["from"])
        if not os.path.lexists(s) or (os.path.lexists(d) and not same_item(s, d)):
            skipped.append(e["to"]); continue
        try:
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(s), str(d))
            restored += 1
        except OSError:
            skipped.append(e["to"])
    with open(MOVELOG, "a") as f:
        f.write(json.dumps({"batch": f"undo-{batch}", "undo_of": batch, "time": now(), "restored": restored,
                            "skipped": skipped}, ensure_ascii=False) + "\n")
    log_md(f"filing · undo {batch}: restored {restored}, skipped {len(skipped)}")
    out({"batch": batch, "restored": restored, "skipped_changed_since": skipped[:20], "skipped_total": len(skipped)})


def cmd_dupes(a):
    roots = [expand(p) for p in a.path] if a.path else watched()
    groups = defaultdict(list)
    for r in roots:
        for p in walk_files(r, True):
            try:
                st = os.lstat(p)
            except OSError:
                continue
            if st.st_size > 0 and p.is_file():
                groups[(p.name.lower(), st.st_size)].append(p)
    # same base name ("x (1).jpg", "x 2.jpg") in the same folder with the same size
    def base(n):
        b, e = os.path.splitext(n); return re.sub(r"( \(\d+\)|\(\d+\)| copy| [2-9])$", "", b) + e
    folder_groups = defaultdict(list)
    for (n, s), ps in list(groups.items()):
        for p in ps:
            folder_groups[(p.parent, base(p.name).lower(), s)].append(p)
    found = []
    for ps in list(groups.values()) + list(folder_groups.values()):
        ps = sorted(set(ps), key=lambda p: (len(str(p)), str(p)))
        if len(ps) < 2:
            continue
        if a.hash:
            local = [p for p in ps if not cloud_only(p)]
            hs = defaultdict(list)
            for p in local:
                h = hashlib.sha256()
                try:
                    with open(p, "rb") as f:
                        for ch in iter(lambda: f.read(1 << 20), b""):
                            h.update(ch)
                except OSError:
                    continue
                hs[h.hexdigest()].append(p)
            for same in hs.values():
                if len(same) > 1:
                    found.append({"keep": tilde(same[0]), "copies": [tilde(x) for x in same[1:]], "match": "content"})
        else:
            found.append({"keep": tilde(ps[0]), "copies": [tilde(x) for x in ps[1:]], "match": "name+size"})
    uniq, seen = [], set()
    for g in found:
        k = tuple(g["copies"])
        if k not in seen:
            seen.add(k); uniq.append(g)
    out({"groups": len(uniq), "extra_copies": sum(len(g["copies"]) for g in uniq), "list": uniq[:200]})


def secret_kind(found: str) -> str:
    """A label for what matched. Never any part of the match itself: some patterns match the key."""
    t = found.lower()
    for start, label in (("sk_live", "Stripe key"), ("ghp_", "GitHub token"), ("akia", "AWS key"), ("begin", "private key"), ("db_password", "database password"),
                         ("pass", "password"), ("api", "API key"), ("secret", "secret key"), ("token", "token"), ("recovery", "recovery code"), ("backup", "backup code")):
        if t.startswith(start):
            return label
    return "possible secret"


def cmd_secrets(a):
    roots = [expand(p) for p in a.path] if a.path else [expand(p) for p in FCFG.get("secret_scan", ["~/Desktop", "~/Downloads", "~/Documents"])]
    hits, unreadable = [], 0
    for r in roots:
        for p in walk_files(r, True):
            kinds = set()
            if SECRET_NAME.search(p.name):
                kinds.add("file name")
            if p.suffix.lower() in TEXT_EXT:
                try:
                    if cloud_only(p):
                        unreadable += 1
                    elif os.lstat(p).st_size <= 200_000:
                        for m in SECRET_TEXT.finditer(p.read_text(errors="ignore")):
                            kinds.add(secret_kind(m.group(1)))
                except OSError:
                    unreadable += 1
            if kinds:
                hits.append({"path": tilde(p), "looks_like": sorted(kinds)})
    out({"found": len(hits), "files": hits[:200], "not_checked_cloud_only": unreadable,
         "note": "values are never printed. Offer to copy them into one note in the Notes Secrets folder for the user to lock, "
                 "then (only with their yes) delete the plain-text originals."})


def cmd_alias(a):
    if not a.yes:
        sys.exit("alias needs --yes")
    t, at = expand(a.target), expand(a.at)
    if blocked(at):
        sys.exit(f"refusing to put an alias in {blocked(at)}")
    if not t.exists():
        sys.exit(f"target missing: {tilde(t)}")
    at.mkdir(parents=True, exist_ok=True)
    name = a.name or t.name
    if os.path.lexists(at / name):
        out({"created": False, "why": "already exists", "path": tilde(at / name)}); return
    js = ("function run(a){const F=Application('Finder');"
          "const x=F.make({new:'aliasFile',to:Path(a[0]),at:Path(a[1])});x.name=a[2];return x.name();}")
    p = subprocess.run(["osascript", "-l", "JavaScript", "-e", js, str(t), str(at), name], capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit(f"Finder error: {p.stderr.strip()} (System Settings → Privacy & Security → Automation → allow Finder)")
    with open(MOVELOG, "a") as f:
        f.write(json.dumps({"batch": f"alias-{dt.date.today()}", "time": now(), "alias": tilde(at / name), "target": tilde(t)}) + "\n")
    log_md(f"filing · alias {tilde(at / name)} → {tilde(t)}")
    out({"created": True, "alias": tilde(at / name), "target": tilde(t)})


def cmd_prune(a):
    if not a.yes:
        sys.exit("prune-empty needs --yes (it removes empty folders)")
    root = expand(a.path)
    if blocked(root) and root != ICLOUD:
        sys.exit(f"refusing: {blocked(root)}")
    removed = []
    for dp, dns, fns in os.walk(root, topdown=False):
        p = Path(dp)
        if p == root or blocked(p):
            continue
        rest = [f for f in os.listdir(p) if f not in SKIP_NAMES]
        if not rest:
            for f in os.listdir(p):
                (p / f).unlink()
            p.rmdir(); removed.append(tilde(p))
    if removed:
        log_md(f"filing · removed {len(removed)} empty folders under {tilde(root)}")
    out({"removed": removed})


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = ap.add_subparsers(dest="cmd", required=True)
    x = s.add_parser("scan"); x.add_argument("--path", action="append"); x.add_argument("--deep", action="store_true"); x.set_defaults(fn=cmd_scan)
    x = s.add_parser("count"); x.set_defaults(fn=cmd_count)
    x = s.add_parser("new-plan"); x.add_argument("--name", required=True); x.set_defaults(fn=cmd_new_plan)
    x = s.add_parser("plans"); x.set_defaults(fn=cmd_plans)
    x = s.add_parser("show"); x.add_argument("--plan", required=True); x.set_defaults(fn=cmd_show)
    x = s.add_parser("approve"); x.add_argument("--plan", required=True); x.add_argument("--all", action="store_true"); x.add_argument("--lines")
    x.add_argument("--clear", action="store_true"); x.set_defaults(fn=cmd_approve)
    x = s.add_parser("protect"); x.add_argument("--path", action="append"); x.add_argument("--notes-folder", action="append")
    x.add_argument("--note-id", action="append"); x.set_defaults(fn=cmd_protect)
    x = s.add_parser("check"); x.add_argument("--plan", required=True); x.set_defaults(fn=cmd_check)
    x = s.add_parser("apply"); x.add_argument("--plan", required=True); x.add_argument("--batch"); x.add_argument("--yes", action="store_true")
    x.add_argument("--skip-problems", action="store_true"); x.set_defaults(fn=cmd_apply)
    x = s.add_parser("verify"); x.add_argument("--plan", required=True); x.set_defaults(fn=cmd_verify)
    x = s.add_parser("undo"); x.add_argument("--batch"); x.add_argument("--yes", action="store_true"); x.set_defaults(fn=cmd_undo)
    x = s.add_parser("history"); x.set_defaults(fn=cmd_history)
    x = s.add_parser("dupes"); x.add_argument("--path", action="append"); x.add_argument("--hash", action="store_true"); x.set_defaults(fn=cmd_dupes)
    x = s.add_parser("secrets"); x.add_argument("--path", action="append"); x.set_defaults(fn=cmd_secrets)
    x = s.add_parser("alias"); x.add_argument("--target", required=True); x.add_argument("--at", required=True)
    x.add_argument("--name"); x.add_argument("--yes", action="store_true"); x.set_defaults(fn=cmd_alias)
    x = s.add_parser("prune-empty"); x.add_argument("--path", required=True); x.add_argument("--yes", action="store_true"); x.set_defaults(fn=cmd_prune)
    a = ap.parse_args()
    try:
        a.fn(a)
    except OSError as e:
        sys.exit(f"{e.strerror or e}: {tilde(Path(e.filename)) if e.filename else ''}")
    except csv.Error as e:
        sys.exit(f"That plan isn't a readable CSV: {e}")


if __name__ == "__main__":
    main()
