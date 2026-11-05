#!/usr/bin/env python3
"""
notes.py: Apple Notes filing for Ariadne (through JavaScript for Automation and a read-only copy of the Notes database).

  ariadne notes folders                     every folder (account/path) with note counts
  ariadne notes find --query TEXT           notes whose title contains text
  ariadne notes snapshot [--text] [--folder PATH]
                                            read-only list of every note from a COPY of the database (needs Full Disk Access).
                                            --text adds each unlocked, unprotected note's plain text.
  ariadne notes move --id ID [--id ID] --to "Area/Sub" [--batch NAME]
                                            move notes (the folder is created if missing), logging where each came from
  ariadne notes undo --batch NAME [--yes]   put a batch back

Nothing is ever deleted. Locked notes are never unlocked. Protected folders and notes (config: notes_never_touch,
notes_never_touch_ids) are refused.
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

HOME = Path.home()
WS = Path(os.environ.get("ARIADNE_HOME") or HOME / "Library/Application Support/Ariadne")
CFG = json.loads((WS / "config.json").read_text()) if (WS / "config.json").exists() else {}
ACCOUNT = CFG.get("notes_account", "iCloud")
NOTESLOG = WS / "notes-moves.jsonl"
NOTESTORE = HOME / "Library/Group Containers/group.com.apple.notes/NoteStore.sqlite"

JXA = r"""
function run(argv) {
  const r = JSON.parse(argv[0]);
  const Notes = Application('Notes');
  function account() {
    try { const a = Notes.accounts.byName(r.account); a.name(); return a; }
    catch (e) { return Notes.defaultAccount(); }
  }
  function child(container, name) {
    try { const f = container.folders.byName(name); f.name(); return f; } catch (e) { return null; }
  }
  function folderAt(path) {
    let cur = account();
    for (const part of path.split('/').filter(Boolean)) {
      let f = child(cur, part);
      if (!f) { Notes.make({ new: 'folder', withProperties: { name: part }, at: cur }); f = child(cur, part); }
      cur = f;
    }
    return cur;
  }
  function walk(container, prefix, out) {
    for (const f of container.folders()) {
      const p = prefix ? prefix + '/' + f.name() : f.name();
      let c = 0; try { c = f.notes.length; } catch (e) {}
      out.push({ path: p, notes: c, id: f.id() });
      walk(f, p, out);
    }
    return out;
  }
  switch (r.cmd) {
    case 'folders': {
      const out = [];
      for (const a of Notes.accounts()) { const rows = walk(a, '', []); rows.forEach(x => x.account = a.name()); out.push(...rows); }
      return JSON.stringify(out);
    }
    case 'find': {
      const q = r.query.toLowerCase(); const out = [];
      const ns = Notes.notes(); const names = Notes.notes.name();
      for (let i = 0; i < names.length; i++) if ((names[i] || '').toLowerCase().includes(q)) {
        const o = { id: ns[i].id(), title: names[i] }; try { o.folder = ns[i].container().name(); } catch (e) {}
        out.push(o);
      }
      return JSON.stringify(out);
    }
    case 'move': {
      const dest = folderAt(r.to); const moved = []; const failed = [];
      for (const id of r.ids) {
        let from = '', fromId = '';
        try {
          const n = Notes.notes.byId(id); n.name();
          try { const c = n.container(); from = c.name(); fromId = c.id(); } catch (e) {}
          if ((r.protect || []).indexOf(from) >= 0) { failed.push({ id: id, error: 'in a protected folder: ' + from }); continue; }
          const title = n.name(); Notes.move(n, { to: dest }); moved.push({ id: id, from: from, fromId: fromId, title: title });
        }
        catch (e) {
          // Locked notes move but Notes reports an error; check where the note is now.
          try { const n = Notes.notes.byId(id); if (n.container().id() === dest.id()) { moved.push({ id: id, from: from, fromId: fromId, locked_error: true }); continue; } } catch (e2) {}
          failed.push({ id: id, error: String(e) });
        }
      }
      return JSON.stringify({ moved: moved, failed: failed, to: r.to });
    }
  }
  throw new Error('unknown command');
}
"""


def jxa(req: dict):
    req = {"account": ACCOUNT, **req}
    p = subprocess.run(["osascript", "-l", "JavaScript", "-e", JXA, json.dumps(req, ensure_ascii=False)], capture_output=True, text=True)
    if p.returncode != 0:
        sys.exit(f"Notes error: {p.stderr.strip()} (System Settings → Privacy & Security → Automation → allow Notes)")
    return json.loads(p.stdout)


def protected_folder(path: str) -> bool:
    return any(path == k or path.startswith(k + "/") for k in CFG.get("notes_never_touch", []) if k)


def note_text(blob):
    """Plain text of a note from its gzipped protobuf body (document → note → text)."""
    def varint(b, i):
        r = s = 0
        while True:
            x = b[i]; i += 1; r |= (x & 0x7f) << s; s += 7
            if x < 0x80:
                return r, i
    def field(b, want):
        i = 0
        while i < len(b):
            k, i = varint(b, i); f, t = k >> 3, k & 7
            if t == 0: _, i = varint(b, i)
            elif t == 2:
                l, i = varint(b, i); v = b[i:i + l]; i += l
                if f == want: return v
            elif t == 5: i += 4
            elif t == 1: i += 8
            else: return None
        return None
    try:
        return field(field(field(gzip.decompress(blob), 2), 3), 2).decode("utf-8", "replace").replace("￼", "[attachment]")
    except Exception:
        return None


def snapshot(with_text: bool, only_folder: str | None):
    if not NOTESTORE.parent.exists():
        sys.exit("Notes database not found.")
    tmp = Path(tempfile.mkdtemp(prefix="ariadne-notes-"))
    try:
        try:
            for suffix in ("", "-wal", "-shm"):
                src = Path(str(NOTESTORE) + suffix)
                if src.exists():
                    shutil.copy2(src, tmp / src.name)
        except PermissionError:
            sys.exit("Reading the Notes database needs Full Disk Access: System Settings → Privacy & Security → Full Disk Access → "
                     "turn on Ariadne (or the app running this command). Nothing is changed in Notes.")
        c = sqlite3.connect(f"file:{tmp / NOTESTORE.name}?mode=ro", uri=True)
        uuid = c.execute("select Z_UUID from Z_METADATA").fetchone()[0]
        folders = {pk: (t, par) for pk, t, par in c.execute(
            "select Z_PK, ZTITLE2, ZPARENT from ZICCLOUDSYNCINGOBJECT where ZTITLE2 is not null "
            "and (ZMARKEDFORDELETION is null or ZMARKEDFORDELETION = 0)")}
        def path(pk):
            parts = []
            while pk in folders:
                t, pk = folders[pk]; parts.append(t)
            return "/".join(reversed(parts))
        rows = c.execute(
            "select n.Z_PK, n.ZTITLE1, n.ZFOLDER, n.ZISPASSWORDPROTECTED, n.ZCREATIONDATE3, n.ZMODIFICATIONDATE1, d.ZDATA "
            "from ZICCLOUDSYNCINGOBJECT n left join ZICNOTEDATA d on d.ZNOTE = n.Z_PK "
            "where n.ZTITLE1 is not null and (n.ZMARKEDFORDELETION is null or n.ZMARKEDFORDELETION = 0)").fetchall()
        c.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    ep = dt.datetime(2001, 1, 1, tzinfo=dt.timezone.utc)
    iso = lambda x: (ep + dt.timedelta(seconds=x)).isoformat(timespec="seconds") if x else None
    ids = set(CFG.get("notes_never_touch_ids", []))
    no_text = CFG.get("notes_no_text", ["Secrets"])
    out = []
    for pk, title, f, locked, cre, mod, data in rows:
        fp = path(f)
        if fp == "Recently Deleted" or (only_folder and fp != only_folder):
            continue
        nid = f"x-coredata://{uuid}/ICNote/p{pk}"
        o = {"id": nid, "title": title, "folder": fp, "locked": bool(locked), "created": iso(cre), "modified": iso(mod),
             "protected": protected_folder(fp) or nid in ids}
        if with_text and not locked and data and not o["protected"] and not any(k.lower() in fp.lower() for k in no_text):
            o["text"] = note_text(data)
        out.append(o)
    return out


def log_line(line: str):
    WS.mkdir(parents=True, exist_ok=True)
    with open(WS / "log.md", "a") as f:
        f.write(f"{dt.datetime.now():%Y-%m-%d %H:%M} · {line}\n")


def move(ids: list[str], to: str, batch: str):
    if protected_folder(to):
        sys.exit(f"Refusing: '{to}' is a never-touch folder.")
    guarded = set(CFG.get("notes_never_touch_ids", []))
    keep = [i for i in ids if i not in guarded]
    protect = [p.split("/")[-1] for p in CFG.get("notes_never_touch", [])]
    res = jxa({"cmd": "move", "ids": keep, "to": to, "protect": protect})
    res["refused_protected"] = [i for i in ids if i in guarded]
    paths = {f["id"]: f["path"] for f in jxa({"cmd": "folders"}) if f.get("account") == ACCOUNT}
    batch = batch or f"notes-{dt.date.today()}"
    WS.mkdir(parents=True, exist_ok=True)
    with open(NOTESLOG, "a") as f:
        for m in res["moved"]:
            f.write(json.dumps({"batch": batch, "time": dt.datetime.now().isoformat(timespec="seconds"), "id": m["id"], "title": m.get("title"),
                                "from": paths.get(m.get("fromId"), m.get("from")), "to": to}, ensure_ascii=False) + "\n")
    log_line(f"notes move · {len(res['moved'])} note(s) → {to} · batch {batch}")
    return res


def undo(batch: str, yes: bool):
    log = [json.loads(l) for l in NOTESLOG.read_text().splitlines() if l.strip()] if NOTESLOG.exists() else []
    last = max([i for i, e in enumerate(log) if e.get("undo_of") == batch], default=-1)
    plan = [e for i, e in enumerate(log) if e.get("batch") == batch and "id" in e and i > last]
    if not plan:
        sys.exit(f"batch {batch} has nothing left to undo")
    if not yes:
        return {"batch": batch, "would_restore": len(plan), "sample": [f"{e['to']} → {e['from']}" for e in plan[:20]], "hint": "rerun with --yes"}
    restored, failed = 0, []
    by_from: dict[str, list[str]] = {}
    for e in plan:
        by_from.setdefault(e["from"], []).append(e["id"])
    for dest, ids in by_from.items():
        res = jxa({"cmd": "move", "ids": ids, "to": dest, "protect": []})
        restored += len(res["moved"]); failed += res["failed"]
    with open(NOTESLOG, "a") as f:
        f.write(json.dumps({"batch": f"undo-{batch}", "undo_of": batch, "time": dt.datetime.now().isoformat(timespec="seconds"),
                            "restored": restored}, ensure_ascii=False) + "\n")
    log_line(f"notes undo {batch}: restored {restored}, failed {len(failed)}")
    return {"batch": batch, "restored": restored, "failed": failed[:20]}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ariadne notes", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    s = ap.add_subparsers(dest="cmd", required=True)
    s.add_parser("folders")
    x = s.add_parser("find"); x.add_argument("--query", required=True)
    x = s.add_parser("snapshot"); x.add_argument("--text", action="store_true"); x.add_argument("--folder")
    x = s.add_parser("move"); x.add_argument("--id", action="append", required=True); x.add_argument("--to", required=True); x.add_argument("--batch", default="")
    x = s.add_parser("undo"); x.add_argument("--batch", required=True); x.add_argument("--yes", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "folders": res = jxa({"cmd": "folders"})
    elif a.cmd == "find": res = jxa({"cmd": "find", "query": a.query})
    elif a.cmd == "snapshot": res = snapshot(a.text, a.folder)
    elif a.cmd == "move": res = move(a.id, a.to, a.batch)
    else: res = undo(a.batch, a.yes)
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
