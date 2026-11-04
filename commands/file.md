---
description: File one thing (a file, folder or note) where it belongs, with your OK
argument-hint: <path or note title> [optional hint, e.g. "for the podcast" or "taxes 2025"]
---
Run `ariadne rules` if the rules aren't already loaded. File "$ARGUMENTS": find it (a path, or `ariadne notes find --query` for a note), propose
ONE destination and name from `filing-map.md` and `filing-rules.md` (plus the hint, if given), and ask "File it there?" with up to two
alternatives as ① ② ③ quick picks. On yes, write a one-row plan, `ariadne check`, `ariadne approve --all`, then `ariadne apply --yes` (or
`ariadne notes move` for a note). If they picked something else, offer to make it a rule.
