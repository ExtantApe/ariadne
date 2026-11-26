# Releasing Ariadne for Mac

Every push and pull request runs CI, including a full app build. A release is one tag:

1. Set the new version in `apps/desktop/src-tauri/tauri.conf.json`, `apps/desktop/src-tauri/Cargo.toml` and `apps/desktop/package.json`, and update `CHANGELOG.md`.
2. Commit and push to `main`, and wait for CI to pass.
3. Tag it: `git tag desktop-v1.2.3 && git push origin desktop-v1.2.3`

GitHub Actions then builds a universal app and publishes the `.dmg` on the Releases page. The build fails if the tag doesn't match the version.

**Before the next release (held 2026-11-25):** Dependabot's tauri-action 1.0.0 update (PR #8) is held until then. Merge it first, release as usual, then download the new `.dmg` and check the signature with `codesign -dvv "/Applications/Ariadne.app"`. Its `Authority` line must name the same self-signed certificate as the last release. If it doesn't, don't publish: revert the PR and release again. Remove this note once it's done.

## Signing

Releases are signed with a self-signed certificate kept in the `APP_SIGNING_P12` and `APP_SIGNING_PASSWORD` repository secrets. macOS ties an app's permissions to its certificate, so they survive updates. Without those secrets (a fork, say) the build is signed ad hoc and each version asks for permissions again.

The same certificate signs Theseus and Ariadne, and it must not change: a new one means everyone grants permissions once more. It doesn't remove the first-launch warning; only Apple's paid Developer ID does.
