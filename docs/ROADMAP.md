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

### Still open

- **Getting through home and cell networks:** a direct connection won't always work. We haven't decided how the two devices find each other, or whether an end-to-end encrypted relay is needed when they can't connect. A relay can't read the traffic, but it would be run by someone, it would see that the devices are connecting, and it has to fit the manifesto.
- **Pairing and lost keys:** how the devices pair, how you remove a lost phone from the Mac, how you pair again if a key is lost, and whether restoring a backup brings the pairing back.
- **The Mac has to be awake:** the app can't reach a sleeping Mac, so it needs to show how old its list is and say what it can't do.
- **What the phone can ask for:** a paired phone is a new way into Theseus. It gets the same limits as everything else and can never send anything as you.

### Planned, not started: an encrypted iCloud backup

Your Theseus folder only lives on your Mac today. It isn't in iCloud Drive. All Theseus has in iCloud now is the Today and Master List notes in Apple Notes, and the optional alarm file from your iPhone.

The plan is an encrypted backup in iCloud Drive, so you can restore after losing one device or both.

- **You choose at setup, and a switch changes it later.** The first-run prompt suggests iCloud, and says you can stay fully offline, but that nothing can restore your data if both devices are lost.
- **Real encryption, not hidden files.** The backup is encrypted on your device before it reaches iCloud. Without the key, Apple or someone in your Apple account sees only an encrypted file, its size and when it changed.
- **You keep the recovery key.** Theseus suggests saving it in Apple's Passwords, or you can keep it somewhere else. Someone with your Apple account and device passcode could reach it in Passwords. If you lose the key and your devices, the backup can't be opened.
- **What goes in it:** your settings, your profile and your `data` folder, which holds your list, drafts and prep notes. Scratch files, logs and temporary copies of your messages stay out.
- **What encryption can't do:** someone with an unlocked device can read what's on that device.

### Planned, not started: a lockdown button

A button for when a device is stolen, with no accounts or servers. A device you still have would send a signed signal to your other devices, directly or through iCloud Drive. The signal has to come from one of your paired devices, after Face ID or the device passcode.

Lockdown locks the app and stops pairing, runs, Remote Control, backups and wall display updates. It also hides what it can. It deletes nothing, and your recovery key undoes it. Erasing a device stays with Apple's Find My.

| Where | What lockdown does | What it can't do |
| --- | --- | --- |
| Mac app | Shows a locked screen | Hide the plain files on disk |
| iPhone app | Shows a locked screen, and drops its copy of your list, which the Mac can send again | Act on the signal if the phone is offline |
| Wall display | Clears the screen | Reach the Pi unless the Mac can. Unplugging the Pi clears it too |
| Notifications | Stops any Theseus sends | Hide what Messages, Mail and other apps show |
| Today and Master List notes | The Mac reads back your edits, then replaces the notes with a short placeholder. Your list stays on the Mac and returns when you unlock | Change the notes if the Mac is the stolen device, or if it's offline. You'd do that by hand in Notes |
| Alarm file | Theseus stops reading it | Change it. Your iPhone's Shortcut owns it, and it holds only alarm times and labels |

**Hiding isn't encryption.** Lockdown keeps your list off the screens Theseus controls. Someone who can get into an unlocked Mac can still open the plain files, and Messages, Mail and Notes themselves. FileVault, a locked device and Find My's Lost Mode are what protect against that, so Theseus should check that FileVault is on and say so if it isn't.

Still open:

- **Encrypting your files during lockdown:** this would only cover the Theseus folder, and only on a device that hears the signal. It isn't planned unless there's a good reason.
- **Asking for Face ID:** the iPhone app could ask each time it opens, which works even if the signal never arrives.
- **With no device left,** Find My is the only option, and only if it was already on.

### What would stay true

- Every promise in `MANIFESTO.md` applies, on every device.
- The Mac app works without the phone app.
- No accounts, and no server of our own.
- Any new place your data goes, including iCloud backup, gets named in the manifesto first, the way the wall display was.

### Before starting

- A written decision in `docs/adr` covering the open questions above.
- A clear reason Remote Control and the notes aren't enough.
- An Apple Developer account, $99 a year as of November 2026.
