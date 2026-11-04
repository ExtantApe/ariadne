# The Theseus and Ariadne manifesto

Theseus and Ariadne are two apps and one idea. Too much comes in, too much piles up, and the people it happens to, especially ADHD brains, don't need another system to maintain. They need a clear way through.

In the myth, Theseus crossed the sea to the labyrinth, and Ariadne's thread led him back out. Here, Theseus clears the path through what's coming at you, and Ariadne makes sure anything she moves can find its way back.

Either app is complete without the other. Together they should feel like one maker's work: the same promises, the same manners, the same look.

This file is identical in both repositories, and CI fails if it isn't. When an app and this file disagree, either the app has a bug or this file needs changing on purpose, in both places.

## What we believe

1. **You decide. We clear the way.** These apps help you live your life. They don't live it for you. They gather, sort, remember and prepare, then hand you a small, clear choice.
2. **Less to manage, never more.** If a feature gives you a new thing to look after, it has to take away more than it adds.
3. **Your Mac, your data.** Your data stays in plain files on your own computer. The one exception is what Claude Code reads on your own account to do the work, and we say so plainly.
4. **Free and open source, always.** No subscription, no paid tier, no data collection, no selling access to Claude.
5. **Lightly opinionated.** Everything starts blank and adapts to you. The few things that don't bend are the promises below.

## The promises

These are features, not guidelines. Each one is enforced in code and covered by tests wherever that's possible. A promise that's only written down counts as a bug.

| Promise | Theseus | Ariadne |
| --- | --- | --- |
| **Nothing goes out or moves without you** | It never sends anything as you. It drafts; you send. | Nothing moves until you approve it. Background work only counts. |
| **Nothing is destroyed** | Deleting needs you. Personal data is read from copies, never changed. | Nothing is deleted or overwritten. |
| **Mistakes can be taken back** | The list saves as you go, with undo and backups. | Every batch can be undone, even after a crash. |
| **When in doubt, it doesn't happen** | If the send guard can't decide, the call is blocked. | Anything protected is refused, wherever a path really leads. |

If a safety check can't reach a decision, the answer is no.

## What every app does

**Just open it.** Opening the app once is the whole setup. It doesn't need Claude or Terminal open. It opens at login, reopens after a crash, and stays closed if you quit it, until you open it again or restart.

**Asks only when it must.** If it's missing something, its window opens and says what, and what to do. It never fails silently and never leaves you with only a menu bar icon.

**Works in the background, quietly.** It lives in the menu bar, and closing the window only hides it. Unattended work is limited to what's safe with nobody watching.

**Keeps what it's given.** Saved as you go, written whole so a crash can't leave half a file, and never lost because something else was running. Updates keep your macOS permissions.

**Runs on your own Claude Code.** It never sees, stores or handles your Claude login. Anything that doesn't need AI works without it.

**Tells the truth.** It says what happened and what to do next, in plain words. It doesn't say a thing worked unless it did, and the docs don't promise what the code doesn't do.

## How they fit together

Each app stands alone, and neither depends on the other being installed.

- They meet only at the command line. Theseus asks `ariadne count` what's waiting, and uses `ariadne protect` to mark what it owns. When you say yes to filing, it follows `ariadne rules` or opens Ariadne.
- Theseus never moves files. Ariadne knows nothing about your list, your messages or Theseus itself.
- Each keeps its own data folder, permissions, repository and version number.

Anything new that one needs from the other goes through that command line, and stays optional.

## The brand

`brand/README.md` holds the specifics. The short version:

- **One family:** a pastel tile, one continuous deep brown line, warm neutrals. Each app has its own color only: Aegean blue for Theseus, Minoan ochre for Ariadne.
- **Line icons on screen, never emoji.** Green, amber and red only ever mean a status.
- **The same manners:** a sidebar for a few places, one page of cards, saved as you go, undo and redo, the same drag, and a pause before anything is final.
- **The same voice:** warm, plain and brief. It sounds like a capable friend, not a product. It doesn't nag, and it never makes you feel behind.
- **The story stays light.** The myth gives the names and the shapes. Screens use plain words.

## Where they're allowed to differ

Different jobs mean some real differences. These are deliberate:

| | Theseus | Ariadne |
| --- | --- | --- |
| **Rhythm** | Runs all day, reads a lot, and prepares | Occasional, moves real files |
| **Background work** | Hosts briefings, checks and Remote Control, with Claude Code running unattended | Only counts. Claude Code runs only when you ask for a plan |
| **Installed parts** | An engine in your workspace, which the app checks against its own version | The tool ships inside the app |
| **Taking over** | Moves everything into the app once it has its permissions | Has nothing to take over |

Any other difference is a gap to close.

## Keeping them in step

When you change one app, ask: **does the other need this too?**

- **A change to a promise, a behavior above, or the shared look** goes into both apps, or gets a written reason in this file for why not.
- **Shared files** stay identical in both repositories: this file, `brand/README.md`, and the interface files in `apps/desktop/src/ui`. `scripts/check-shared.sh` explains how to update them, and CI fails if they drift.
- **A safety promise** gets a test that tries to break it.
- **Both apps ship** the same way: CI on every push, a release from one tag, and one signing certificate. Their version numbers are their own.
- **Decisions** that change how the apps fit together get an architecture note in `docs/adr`, in each repository they affect.

## What we won't do

- Send, post or reply as you, or add a setting that lets it.
- Delete your files or overwrite them to make something tidier.
- Add accounts, tracking, or a server of our own.
- Charge for this, or make the free version worse.
- Use your data to do anything you didn't ask for.
- Merge the two into one app just because it would be tidier. They stay separate because their jobs and their risks are different.
