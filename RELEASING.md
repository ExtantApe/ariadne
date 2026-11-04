# Releasing Ariadne for Mac

Every push and pull request runs CI, including a full app build. A release is one tag:

1. Set the new version in `apps/desktop/src-tauri/tauri.conf.json`, `apps/desktop/src-tauri/Cargo.toml` and `apps/desktop/package.json`, and update `CHANGELOG.md`.
2. Commit and push to `main`, and wait for CI to pass.
3. Tag it: `git tag desktop-v1.2.3 && git push origin desktop-v1.2.3`

GitHub Actions then builds a universal app and publishes the `.dmg` on the Releases page. The build fails if the tag doesn't match the version.

## Signing

Releases are signed with a self-signed certificate kept in the `APP_SIGNING_P12` and `APP_SIGNING_PASSWORD` repository secrets. macOS ties an app's permissions to its certificate, so they survive updates. Without those secrets (a fork, say) the build is signed ad hoc and each version asks for permissions again.

The same certificate signs Theseus and Ariadne, and it must not change: a new one means everyone grants permissions once more. It doesn't remove the first-launch warning; only Apple's paid Developer ID does.
