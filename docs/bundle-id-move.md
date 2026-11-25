# Bundle identifier move: Ariadne

Decided D280 (owner, 2026-11-23): apps under the ExtantApe org use `com.extantape.<name>`. Ariadne moves from `io.github.mgilardi.ariadne` to `com.extantape.ariadne` in its next release. Task K724. This overrides the old line that kept the personal-account io.github IDs. The shared self-signed certificate does not change.

## Every place the identifier is used

| Where | Old | What happens |
| --- | --- | --- |
| `apps/desktop/src-tauri/tauri.conf.json` `identifier` | `io.github.mgilardi.ariadne` | Changed. A test checks it matches `NEW_ID` in `id_move.rs`. |
| Web view storage, `~/Library/WebKit/<id>` | old id | Copied once. The window stores nothing of its own in `localStorage`, so this is usually empty. |
| `~/Library/Application Support/<id>` | old id | Copied once if it exists. Ariadne's own data is in `~/Library/Application Support/Ariadne` (or `$ARIADNE_HOME`), which never used the identifier. |
| Caches, HTTPStorages, Preferences plist, Saved Application State | old id | Not copied. macOS rebuilds them. |
| Data folder `~/Library/Application Support/Ariadne`: `config.json`, `filing-map.md`, `filing-rules.md`, `plans/`, move logs | product name | Nothing to do. Same path under the new id. |
| Launch agent `com.ariadne.watchdog` | own label | Nothing to do. It opens the app by path. |
| Keychain | none | Ariadne has no Keychain items, so no Keychain copy is needed. |
| CI (`.github/workflows`) | no mention | Nothing to do. |
| `scripts/leak-allow.txt` | lists the old id | Kept on purpose, for the same reason as in Theseus: the old id still appears in `id_move.rs`, this plan and the changelog. |

## The migration (`apps/desktop/src-tauri/src/id_move.rs`)

Same code as Theseus. It runs at the start of `run()`, copies each id-named folder once if the new one is missing or empty, through a temporary sibling renamed into place. It never overwrites a new folder with content in it, never touches the old folder, skips symbolic links, and writes `id-move.json` only when nothing failed, so a failure is retried next launch. The result goes to `logs/app.log` in the Ariadne folder in plain words.

## What users grant again

macOS ties privacy permissions to the app's identifier, so the new Ariadne starts with none. After updating, open **System Settings > Privacy & Security** and grant Ariadne again under:

1. **Files and Folders**: Desktop, Documents and Downloads (macOS asks again the first time Ariadne counts or files from each).
2. **Full Disk Access**, needed for sorting Notes. You add it yourself with the plus button.
3. **Automation**: the Notes entry under Ariadne (macOS asks again on first use).

The old Ariadne entries stay in those lists and do nothing. They can be removed with the minus button. If you use the `ariadne` command from Terminal, Claude Code or Theseus, those keep their own permissions.

## Tested and not tested

Tested: the migration with made-up home folders (copies once, never overwrites, leaves the old data, missing old folder, empty new folder, unreadable file then retry, symbolic links, config matches). Not tested: a real Tauri build and launch, and the permission prompts on a real Mac.
