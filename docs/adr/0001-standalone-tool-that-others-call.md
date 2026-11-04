# ADR 0001: Ariadne is its own tool, and other apps call it
**Status:** accepted · 2026-11-03

**Context:** Ariadne began as a module inside Theseus. Filing is occasional and moves real files, while an assistant runs constantly and mostly reads. Its rules loaded on every Theseus run, including background syncs that only ever counted. It's also useful to someone who doesn't want an assistant.

**Decision:** Separate repo, own data folder (`~/Library/Application Support/Ariadne`, because `~/Ariadne` is the same path as this repo's `~/ariadne` on a default Mac), own Mac app. Ariadne knows nothing about any other tool. The public contract is the command line: `ariadne count` for what's waiting, and `ariadne protect` for another tool to mark what it owns.

**Why not rely on separate permissions:** that was the earlier reason for a second app, but Theseus.app needs Full Disk Access anyway, so a second app isolates nothing. The reasons are purpose and risk.

**Consequences:** the app bundles the tool, so it doesn't depend on this repo being on disk. Two apps means two permission grants for people who use both.
