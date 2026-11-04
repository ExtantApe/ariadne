# Changelog

## Unreleased
- First standalone version, split out of Theseus: the `ariadne` command, `/tidy` `/file` `/undo`, and Ariadne for Mac (plan review, history with undo, permissions).
- Protection is now built in rather than config-only: `~/Code`, git repositories, the Library folder and Ariadne's own folder are always refused, and config can only add to the protected lists.
- A partly applied plan keeps its remaining rows available, and undoing a batch makes its plan ready again.
- Note batches appear in `history` and undo with `ariadne undo`.
