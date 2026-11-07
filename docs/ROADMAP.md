# Roadmap

Long-term goals and ideas. Nothing here has been started.

## Shannon, someday

**Shannon is an idea, not a plan.** Nothing is being built. Theseus and Ariadne stay two separate apps, each with its own package, repository, data and permissions.

### The idea

Shannon would be a character you talk to, named after Claude Shannon, who built a maze-solving mouse. You'd chat with Shannon, and Shannon would know how to use Theseus and Ariadne when they're the right tool.

### What would stay true

- Theseus and Ariadne remain their own Mac apps, and each works without Shannon or the other.
- Shannon reaches them only through their `theseus` and `ariadne` commands, which is already how they meet. It wouldn't need their data folders moved or their apps merged.
- Every promise in `MANIFESTO.md` applies to Shannon too.

### Why not now

In November 2026 we looked at merging both into one Shannon app, then decided it was too much. Both apps need real use first, and a merge would move live data and reset macOS permissions for little immediate gain.

### Before starting

- Both apps have been in steady daily use, and there's still a clear reason to want one voice over them.
- A trademark search on the name, and wording that doesn't imply any tie to Anthropic.

## Theseus on iPhone

**A long-term goal.** Nothing has been started, and it won't hold up other work.

### The goal

A native iOS app for Theseus that shows your list and lets you act on it from anywhere, while your Mac does the work.

Today the phone reaches Theseus through Remote Control in the Claude app, and through the Today and Master List notes.

### Why the Mac still does the work

- **Mac only:** reading Messages and local files, starting Claude Code, and the send guard around it. iOS doesn't let an app do these, so an iPhone app alone couldn't do what Theseus does now.
- **Not a stream of the Mac window:** App Store rule 4.2.7 only allows an app that mirrors one specific program over a local network, so it wouldn't work away from home.

### Planned, not started: an encrypted connection inside the app

Your iPhone and Mac pair once, then talk directly, on Wi-Fi or off it.

- It carries only Theseus traffic.
- It needs no system VPN profile, and leaves the phone's other network use alone.
- It's end-to-end encrypted, with keys that stay on your two devices.
- No accounts, and no server of our own.

### Still open

- **Getting through home and cell networks:** a direct connection won't always work. We haven't decided how the two devices find each other, or whether an end-to-end encrypted relay is needed when they can't connect. A relay can't read the traffic, but it would be run by someone, it would see that the devices are connecting, and it has to fit the manifesto.
- **Pairing and lost keys:** how the devices pair, how you remove a lost phone from the Mac, how you pair again if a key is lost, and whether a restored backup brings the pairing back or you pair again.
- **The Mac has to be awake:** the app can't reach a sleeping Mac, so it needs to show how old its list is and say what it can't do.
- **What the phone can ask for:** a paired phone is a new way into Theseus. It gets the same limits as everything else and can never send anything as you.

### Planned, not started: settings backup

If you lose your Mac or iPhone, you can get your settings back on a new one.

- **The default is your own storage.** Your settings are backed up on your Mac and iPhone. iCloud through Apple Files is the suggested place, and you can choose somewhere else.
- **Not everything counts as a setting.** What goes in the backup still has to be defined. Messages, connector logins and private details don't belong in it unencrypted.

### Proposal, not decided: an optional account

An optional Theseus account could also keep an encrypted copy of your settings on a server, with no telemetry. Backup would work without it.

The manifesto currently rules out accounts and a server of our own, so this can't go ahead unless that changes on purpose, in both apps. It would also need encryption we can't read, a plain answer for a forgotten passphrase, and a decision on who runs and pays for the servers. It may not be needed if an encrypted backup in your own storage is enough.

### What would stay true

- Every promise in `MANIFESTO.md` applies, on every device.
- The Mac app works without the phone app.
- Any new place your data goes gets named in the manifesto first, the way the wall display was.

### Before starting

- A written decision in `docs/adr` covering the open questions above.
- A clear reason Remote Control and the notes aren't enough.
- An Apple Developer account, $99 a year as of November 2026.
