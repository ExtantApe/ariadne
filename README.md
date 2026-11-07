<img src="brand/icon-1024.png" width="96" alt="">

# Ariadne

**Keeps your Mac's files and Apple Notes filed, with your OK.** Free and open source, for Macs.

Your Desktop, Downloads and Notes pile up. Ariadne suggests where everything should go, shows you the plan, and only moves what you approve.

The name comes from the myth, where Ariadne's thread led Theseus back out of the labyrinth. Here the thread is the move log, so anything Ariadne moves can be put back.

Ariadne has a sister app, [Theseus](https://github.com/ExtantApe/theseus), a personal assistant for when too much is coming at you. [The manifesto](MANIFESTO.md) is what they both promise.

## The promises
- **Nothing moves until you say yes.** Background runs only count.
- **Nothing gets deleted or overwritten.** If there's a clash, it's skipped and reported. Duplicates go to a tray for you to empty.
- **Every batch can be undone**, files and notes alike.
- **Some things never move.** That's `~/Code`, anything in a git repository, any folder containing one, app-owned folders, your standard folders themselves (Desktop, Documents and so on), anything outside your home folder or an external drive, and Ariadne's own folder. It checks where a path really leads, so `..`, capitalization and symlinks don't get around it, and it checks again right before each move. Your config can add to that list but can't take anything off it.

## Two ways to use it
**The Mac app.** It lives in your menu bar and counts what's waiting. You review a plan row by row, tick what moves, and can undo any batch. The tool ships inside it.

**The command**, from Terminal or Claude Code:

| Command | What it does |
|---|---|
| `ariadne count` | what's waiting in your watched folders |
| `ariadne scan --path ~/Downloads` | read-only inventory |
| `ariadne plans`, `ariadne show --plan NAME` | your plans and their rows |
| `ariadne check --plan NAME` | dry run: missing files, clashes, protected paths |
| `ariadne approve`, `ariadne apply --plan NAME --yes` | approve rows, then move them |
| `ariadne where NAME --text` | where a filed file or note went |
| `ariadne history`, `ariadne undo [--batch NAME]` | see batches, and put one back (add `--yes`) |
| `ariadne dupes`, `ariadne secrets` | find duplicates, and files that look like they hold passwords (never prints the values) |
| `ariadne notes …` | the same for Apple Notes |
| `ariadne doctor` | what's working and what needs a permission |

In Claude Code, `/tidy`, `/file` and `/restore` run a whole pass in plain language. To see every command, run `/commands`, or `ariadne help` in Terminal.

## Where Claude comes in
Scanning, reviewing, moving and undoing don't use AI at all. The only part that does is *suggesting* a plan, which uses [Claude Code](https://code.claude.com) on your own account. It reads file names, and contents only if you allow it in `read_contents`. When the app asks for a plan, Claude can draft one, but it can't approve, apply or undo anything, and it can't use the web.

## What it costs
Ariadne is free. You'd only pay for Claude, and only if you want it suggesting plans.

| What | Cost | Needed for |
|---|---|---|
| A Mac | the one you own | Everything |
| [Claude Pro, Max or Ultra](https://claude.com/pricing) | $20, $100 or $200 a month | Only for having Claude suggest a plan |

## Install
### The app
1. Download the `.dmg` from [Releases](https://github.com/ExtantApe/ariadne/releases/latest) and drag Ariadne to Applications.
2. Apple charges for notarizing and Ariadne is free, so it isn't notarized and macOS blocks the first launch. There are two ways to allow it:

   **Terminal (quickest):**

   ```bash
   xattr -dr com.apple.quarantine "/Applications/Ariadne.app"
   ```

   **Or System Settings:** open the app and dismiss the warning, then go to **System Settings → Privacy & Security**, scroll down, and choose **Open Anyway**.

Requires macOS 14 or later, on Apple silicon or Intel, and Apple's command line tools (`xcode-select --install`).

Open it once and it lives in your menu bar. After that it opens at login and reopens after a crash, and you don't need Claude or Terminal open. If you quit it from the menu bar, it stays closed until you open it or restart. To turn that off, set `"open_at_login": false` in its config.

Sorting Notes also needs Full Disk Access (Setup tab). To use `ariadne` from Terminal, Claude Code or Theseus, click **Install the command** in the Setup tab.

### Just the command
```bash
git clone https://github.com/ExtantApe/ariadne ~/ariadne
~/ariadne/bin/ariadne install
```

For `/tidy`, `/file` and `/restore` in any Claude Code session, also run `/plugin marketplace add ExtantApe/ariadne`, then `/plugin install ariadne@ariadne`.

### Build it yourself
Needs Rust, Node 22+ and pnpm.
```bash
pnpm install
pnpm app:build     # apps/desktop/src-tauri/target/release/bundle/macos/Ariadne.app
pnpm test          # tests for the part that moves files; runs in a throwaway home
```

Your own builds are signed ad hoc, so each one asks for permissions again. Releases don't have that problem.

## Your data
Everything is in `~/Library/Application Support/Ariadne` (or `$ARIADNE_HOME`): `config.json`, `filing-map.md`, `filing-rules.md`, `plans/`, and the move logs. The only thing that leaves your Mac is what Claude Code reads when it drafts a plan. Notes you file stay in the account they're in.

## Works with Theseus, doesn't need it
[Theseus](https://github.com/ExtantApe/theseus) can offer a filing pass when things pile up. It calls `ariadne count` to see what's waiting and `ariadne protect` to mark what it owns, and that's the whole connection.

## Not yet
Apple signing, automatic updates, a Notes review screen and a filing map editor in the app, and watching folders live.

Questions and ideas: [open an issue](https://github.com/ExtantApe/ariadne/issues).

MIT License. Independent project, not affiliated with Anthropic or Apple.
