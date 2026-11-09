# Test audit

How the tests line up with what Ariadne promises. Redo it after every feature or fix, and at least every 14 days while the repo has commits.

## 2026-11-09 · first audit

What exists: `tests/test_ariadne.py` (71 tests, stdlib, everything in a throwaway home), run in CI with the leak check, the shared-file check, the desktop build and its end-to-end run.

### Always covered (approval, data loss, protection, secrets)

| Promise (RULES.md, "The rules that never bend") | Proved by |
| --- | --- |
| Nothing moves until the user approves the plan | `test_apply_requires_yes`, `test_unapproved_rows_do_not_move`, `test_partial_approval`, `test_undo_without_yes_moves_nothing` |
| Nothing is overwritten or lost | `test_never_overwrites`, `test_folders_merge_without_overwriting`, `test_case_only_rename`, `CrashSafety` (log written before the move, a failed move isn't in history, a torn log line is survivable), `NotesCrash` |
| Everything can be undone | `test_apply_then_undo_round_trip`, `test_a_crash_partway_can_still_be_undone`, `test_undo_can_retry_what_it_skipped`, `test_default_undo_matches_the_top_of_history` |
| Code folders, repositories, app folders and protected paths are never touched | `Protection` and `Bypasses` (`..` in and out, symlinks either way, capitalization, merges through symlinks, the move itself checks again), `Hardening` (standard home folders, folders holding a repository or app folder, paths outside home, relative and blank paths) |
| The one delete, `prune-empty`, removes only empty folders and only with a yes | **new** `PruneEmpty`: without `--yes` nothing is removed; only folders empty but for Finder's files go; files, the named folder and anything inside a repository stay; a protected folder is refused |
| Notes are read from a copy, read-only | **new** `NotesReadOnly` |
| Secret values never appear | `test_secrets_never_prints_a_value` |
| Other tools can rely on `count` | `test_count_shape_other_tools_rely_on`, `test_unreadable_watched_folder_does_not_break_count` |

### Gaps added in this audit
- `prune-empty` is the only command that deletes and had no tests. Added `PruneEmpty` (3 tests).
- The Notes snapshot being read-only was true in the code but unproven. Added `NotesReadOnly` (1 test).

### Gaps skipped, and why
- Moving notes through Notes itself (AppleScript) can't run in CI; the crash and partial-failure paths are covered with a fake (`NotesCrash`).
- `alias` creation goes through Finder and needs Automation permission; it creates, never moves or deletes.
- Desktop app framework internals; the end-to-end run covers the screens.

### Next audit
By 2026-11-23, or with the next feature or fix, whichever comes first.
