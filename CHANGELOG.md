# Changelog

## Unreleased
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
