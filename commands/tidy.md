---
description: Tidy files or Notes: plan where everything goes, you approve, then it moves, logs and can be undone
argument-hint: [a folder like Downloads, "notes", "dupes", "secrets", "setup", or nothing for your watched folders]
---
Run `ariadne rules` if the rules aren't already loaded, and follow them. Target: "$ARGUMENTS" (empty = the folders in `watch`).

- **setup** → the setup interview, then stop.
- **a folder** (or empty) → a filing pass for files.
- **notes** → the same loop for Apple Notes.
- **dupes** → `ariadne dupes`; propose moving extra copies to `00 Inbox/_Duplicates`, never deleting them.
- **secrets** → `ariadne secrets`. Never print a value.

Always show the plan and wait for the user's yes before moving anything.
