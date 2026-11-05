# Changelog

## 0.3.0
- **Notes batches can be undone after a crash.** Ariadne now writes the log before moving anything. Undo moves a note back only if it's still where the batch put it, so a note you've moved since stays put.
- **Locked notes can be found by name.** `ariadne where` now finds them too.
- **Your Ariadne folder is private to your account.**
- **`/undo` is now `/restore`.** Claude Code uses `/undo` for its own command. `ariadne undo` in Terminal stays the same.
- **`ariadne where <name>`.** Find where a filed file or note went, instantly and without Claude.
- **A list of every command.** Run `/commands` in a session, or `ariadne help` in Terminal.

## 0.2.2
- **A new icon and color.** Ariadne is now a spool of thread on rose, with a deep rose accent inside the app. Theseus gets a matching change.

## 0.2.1
- **Just open the app, once.** Ariadne now opens at login and reopens after a crash, the same way Theseus does, with no Login Items step. Quitting from the menu bar is respected. If it can't read a folder it watches, its window opens to say so.

## 0.2.0
- **Protected folders can no longer be bypassed.** 0.1.0 compared path text, so `~/Downloads/../Code/x`, `~/code/x`, a symlink into `~/Code`, and `Documents/zoom` all got through. Ariadne now checks where a path really leads, ignoring capitalization, and checks again at the moment of each move, including inside folder merges. Undo can still put back anything an older version moved out.
- **Every move can be undone, even after a crash.** The log entry is written before the move, not after.
- Undoing a drag takes the correction back out of `filing-rules.md`.
- One unreadable plan no longer blanks the Plans page. It's listed on its own.
- Plans, rules and config are written whole, so a crash can't leave half a file.
- Releases are signed with a stable certificate, so updates keep your macOS permissions. This release asks for them one last time.
- A drag released outside the window ends.
- New: browser tests of the window in `apps/desktop/e2e`, run by CI, plus a check that files shared with Theseus stay identical.

## 0.1.0
- Drag a file to a different folder in a plan, with undo. Ariadne records the correction in `filing-rules.md` so it can learn from it. New `ariadne move-row`.
- Softer, pastel app icon.
- New interface on the shared design system with Theseus (`brand/README.md`): a sidebar, plans split into to-review and done, a clearer review screen. Built without Apple's hardened runtime, which can silently block macOS permission dialogs on unsigned apps.
- New identity: the Cretan labyrinth in ivory on Minoan red ochre, a monochrome menu bar icon that follows light and dark mode, and matching colors in the app.
- First standalone version, split out of Theseus: the `ariadne` command, `/tidy` `/file` `/undo`, and Ariadne for Mac (plan review, history with undo, permissions).
- Protection is now built in rather than config-only: `~/Code`, git repositories, the Library folder and Ariadne's own folder are always refused, and config can only add to the protected lists.
- A partly applied plan keeps its remaining rows available, and undoing a batch makes its plan ready again.
- Note batches appear in `history` and undo with `ariadne undo`.
- Safety: a plan row with a blank or relative path is refused (a blank source used to mean the current folder). Folders containing a git repository or app folder, standard folders like Documents, and anything outside your home folder or an external drive can't be moved.
- `ariadne secrets` never prints any part of a value. It used to include matched key text in its labels.
- One failed move no longer stops a batch, and undo can retry what it had to skip. Case-only renames work.
- Clear messages instead of crashes for unreadable folders, missing plans and unquoted commas in plans. `new-plan` picks a fresh name instead of failing.
- App: can install the `ariadne` command, stops a stuck plan draft after 15 minutes, gives Claude no file access beyond Ariadne's folder and no web access while drafting, and has a content security policy. `ariadne doctor` no longer opens Notes unless asked.
