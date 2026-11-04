---
description: Undo a filing batch (the last one, or one you name)
argument-hint: [batch name, or nothing for the most recent]
---
Run `ariadne history` and show the last few batches. Show what `ariadne undo --batch "$ARGUMENTS"` would restore (no `--yes`; leave `--batch`
off when no name was given), and ask once. On yes, run it with `--yes` and report how many came back and any skipped because they changed since.
