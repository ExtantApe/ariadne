# Ariadne

**Keep your Mac's files and Apple Notes filed, with a yes.** Free and open source. For Macs.

Your Desktop, Downloads and Notes pile up. Ariadne suggests where every item belongs, shows you the plan, and moves only what you approve.
In the myth, Ariadne's thread led Theseus back out of the labyrinth. Here the thread is the move log: anything Ariadne moves can be put back.

## The promises
- **Nothing moves without your yes.** Background runs only count.
- **Nothing is deleted or overwritten.** A clash is skipped and reported. Duplicates go to a tray for you to empty.
- **Every batch can be undone**, files and notes alike.
- **Some things stay put, always.** `~/Code`, anything in a git repository, any folder containing one, app-owned folders, your standard folders themselves (Desktop, Documents and so on), anything outside your home folder or an external drive, and Ariadne's own folder are refused. Your config can only add to that list.

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
Scanning, reviewing, moving and undoing need no AI at all. Only *suggesting* a plan uses [Claude Code](https://code.claude.com), with your own account, and it reads file names (contents only if you allow it in `read_contents`). When the app asks for a plan, Claude may draft one, and approving, applying, undoing and web access are denied.

## Install
### The app
1. Download the `.dmg` from [Releases](https://github.com/mgilardi/ariadne/releases/latest) and drag Ariadne to Applications.
2. Ariadne is free and unsigned (Apple charges for signing), so macOS blocks the first launch. Allow it one of two ways:

   **Terminal (quickest):**

   ```bash
   xattr -dr com.apple.quarantine "/Applications/Ariadne.app"
   ```

   **Or System Settings:** open the app and dismiss the warning, then go to **System Settings → Privacy & Security**, scroll down, and choose **Open Anyway**.

Requires macOS 14 or later, on Apple silicon or Intel, and Apple's command line tools (`xcode-select --install`).

Open it and it lives in your menu bar. Sorting Notes also needs Full Disk Access (Setup tab). To use `ariadne` from Terminal, Claude Code or Theseus, click **Install the command** in the Setup tab.

### Just the command
```bash
git clone https://github.com/mgilardi/ariadne ~/ariadne
~/ariadne/bin/ariadne install
```

For `/tidy`, `/file` and `/undo` in any Claude Code session, also run `/plugin marketplace add mgilardi/ariadne`, then `/plugin install ariadne@ariadne`.

### Build it yourself
Needs Rust, Node 22+ and pnpm.
```bash
pnpm install
pnpm app:build     # apps/desktop/src-tauri/target/release/bundle/macos/Ariadne.app
pnpm test          # tests for the part that moves files; runs in a throwaway home
```

Macs identify an unsigned app by its exact build, so a new version may ask for its permissions again.

## Your data
Everything is in `~/Library/Application Support/Ariadne` (or `$ARIADNE_HOME`): `config.json`, `filing-map.md`, `filing-rules.md`, `plans/`, and the move logs. It never leaves your Mac except what Claude Code reads when drafting a plan.

## Works with Theseus, doesn't need it
[Theseus](https://github.com/mgilardi/theseus) is a personal assistant that can offer a filing pass when things pile up. It calls `ariadne count`, and that's the whole connection. To protect what another tool owns, it runs `ariadne protect`.

## Not yet
Apple signing, automatic updates, a Notes review screen and a filing map editor in the app, and watching folders live.

MIT License. Independent project, not affiliated with Anthropic or Apple.
