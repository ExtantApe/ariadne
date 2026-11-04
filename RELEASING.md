# Releasing Ariadne for Mac

Every push and pull request runs CI, including a full app build. A release is one tag:

1. Set the new version in `apps/desktop/src-tauri/tauri.conf.json`, `apps/desktop/src-tauri/Cargo.toml` and `apps/desktop/package.json`, and update `CHANGELOG.md`.
2. Commit and push to `main`, and wait for CI to pass.
3. Tag it: `git tag desktop-v1.2.3 && git push origin desktop-v1.2.3`

GitHub Actions then builds a universal app and publishes the `.dmg` on the Releases page. The build fails if the tag doesn't match the version.

Macs identify an unsigned app by its exact build, so each new version may ask for its macOS permissions again. A paid Apple Developer ID would fix that, and would remove the first-launch warning.
