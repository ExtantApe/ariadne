# Ariadne

**Keep your Mac's files and Apple Notes filed, with a yes.** Free and open source. For Macs.

Your Desktop, Downloads and Notes pile up. Ariadne suggests where every item belongs, shows you the plan, and moves only what you approve.
In the myth, Ariadne's thread led Theseus back out of the labyrinth. Here the thread is the move log: anything Ariadne moves can be put back.

## The promises
- **Nothing moves without your yes.** Background runs only count.
- **Nothing is deleted or overwritten.** A clash is skipped and reported. Duplicates go to a tray for you to empty.
- **Every batch can be undone**, files and notes alike.
- **Code stays put.** `~/Code`, anything in a git repository, app-owned folders and Ariadne's own folder are always refused. Your config can only add to that list.

## Two ways to use it
**The Mac app.** A menu bar app that counts what's waiting, lets you review a plan row by row, tick what moves, and undo any batch. The tool ships inside it.

**The command**, from Terminal or Claude Code:

| Command | What it does |
|---|---|
| `ariadne count` | what's waiting in your watched folders |
| `ariadne scan --path ~/Downloads` | read-only inventory |
| `ariadne plans`, `ariadne show --plan NAME` | your plans and their rows |
| `ariadne check --plan NAME` | dry run: missing files, clashes, protected paths |
| `ariadne approve`, `ariadne apply --plan NAME --yes` | approve rows, then move them |
| `ariadne history`, `ariadne undo [--batch NAME]` | see batches, and put one back (add `--yes`) |
| `ariadne dupes`, `ariadne secrets` | find duplicates, and files that look like they hold passwords (never prints the values) |
| `ariadne notes …` | the same for Apple Notes |
| `ariadne doctor` | what's working and what needs a permission |

In Claude Code, `/tidy`, `/file` and `/undo` run a whole pass in plain language.

## Where Claude comes in
Scanning, reviewing, moving and undoing need no AI at all. Only *suggesting* a plan uses [Claude Code](https://code.claude.com), with your own account, and it reads file names (contents only if you allow it in `read_contents`). When the app asks for a plan, Claude may draft one, and approving, applying and undoing are denied.

## Install
**App:** build it (below), drag `Ariadne.app` to Applications, and open it. It's ad hoc signed, so right-click → Open the first time. Full Disk Access is only needed to sort Notes.

**Command:**
```bash
git clone https://github.com/mgilardi/ariadne ~/ariadne
~/ariadne/bin/ariadne install
```

## Build the app
Needs Rust, Node 22+, pnpm and the Xcode Command Line Tools.
```bash
pnpm install
pnpm --filter ariadne-desktop icons
pnpm app:build     # apps/desktop/src-tauri/target/release/bundle/macos/Ariadne.app
pnpm test          # tests for the part that moves files; runs in a throwaway home
```

## Your data
Everything is in `~/Library/Application Support/Ariadne` (or `$ARIADNE_HOME`): `config.json`, `filing-map.md`, `filing-rules.md`, `plans/`, and the move logs. It never leaves your Mac except what Claude Code reads when drafting a plan.

## Works with Theseus, doesn't need it
[Theseus](https://github.com/mgilardi/theseus) is a personal assistant that can offer a filing pass when things pile up. It calls `ariadne count`, and that's the whole connection. To protect what another tool owns, it runs `ariadne protect`.

## Not yet
Signing and notarization, automatic updates, a Notes review screen and a filing map editor in the app, and watching folders live.

MIT License. Independent project, not affiliated with Anthropic or Apple.
