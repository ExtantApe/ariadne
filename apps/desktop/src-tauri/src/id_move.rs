//! The move from the old bundle identifier to `com.extantape.ariadne` (K724, D280).
//!
//! Tauri and macOS keep some of an app's files in folders named after its identifier. On the first launch of the new identifier this copies
//! those folders across, once. It never moves or deletes the old ones, so the previous version still works if someone goes back, and it never
//! writes into a new folder that already has something in it. Nothing here touches the Keychain: neither app has an item named after its identifier.

use std::fs;
use std::path::{Path, PathBuf};

pub const OLD_ID: &str = "io.github.mgilardi.ariadne";
pub const NEW_ID: &str = "com.extantape.ariadne";

/// Folders under the home folder whose name is the identifier.
const FOLDERS: [&str; 2] = ["Library/Application Support", "Library/WebKit"];
const MARKER: &str = "id-move.json";

#[derive(Debug, Default, PartialEq)]
pub struct Outcome {
    pub already_done: bool,
    pub copied: Vec<String>,
    pub failed: Vec<String>,
}

impl Outcome {
    /// One plain sentence for the log. Never contains file contents.
    pub fn summary(&self) -> String {
        if self.already_done {
            return String::new();
        }
        let mut s = if self.copied.is_empty() { "No data under the old identifier needed copying.".to_string() } else { format!("Copied from the old identifier: {}. The old folders were left as they are.", self.copied.join(", ")) };
        for f in &self.failed {
            s.push_str(&format!(" Could not copy {f}; it will try again next time you open the app."));
        }
        s
    }
}

fn is_empty_dir(p: &Path) -> bool {
    fs::read_dir(p).map(|mut d| d.next().is_none()).unwrap_or(false)
}

/// Copies files and folders. Symlinks are skipped: they could point outside the folder being copied.
fn copy_tree(from: &Path, to: &Path) -> std::io::Result<()> {
    fs::create_dir_all(to)?;
    for entry in fs::read_dir(from)? {
        let entry = entry?;
        let kind = entry.file_type()?;
        let dest = to.join(entry.file_name());
        if kind.is_dir() {
            copy_tree(&entry.path(), &dest)?;
        } else if kind.is_file() {
            fs::copy(entry.path(), &dest)?;
        }
    }
    Ok(())
}

/// Copy the old identifier's folders to the new one's if the new one's are missing or empty. Runs once: a marker file records it, and is only
/// written when nothing failed.
pub fn migrate(home: &Path, old_id: &str, new_id: &str) -> Outcome {
    let marker = home.join(FOLDERS[0]).join(new_id).join(MARKER);
    if marker.exists() {
        return Outcome { already_done: true, ..Default::default() };
    }
    let mut out = Outcome::default();
    for base in FOLDERS {
        let (old, new) = (home.join(base).join(old_id), home.join(base).join(new_id));
        if !old.is_dir() || (new.exists() && !is_empty_dir(&new)) {
            continue;
        }
        let tmp: PathBuf = home.join(base).join(format!("{new_id}.copying"));
        let _ = fs::remove_dir_all(&tmp);
        let done = copy_tree(&old, &tmp).and_then(|_| {
            if new.exists() {
                fs::remove_dir(&new)?; // only ever an empty folder
            }
            fs::rename(&tmp, &new)
        });
        match done {
            Ok(()) => out.copied.push(base.rsplit('/').next().unwrap_or(base).to_string()),
            Err(_) => {
                let _ = fs::remove_dir_all(&tmp);
                out.failed.push(base.rsplit('/').next().unwrap_or(base).to_string());
            }
        }
    }
    if out.failed.is_empty() {
        let dir = marker.parent().unwrap();
        let text = format!("{{\"from\":\"{old_id}\",\"to\":\"{new_id}\",\"copied\":{}}}\n", out.copied.len());
        if fs::create_dir_all(dir).and_then(|_| fs::write(&marker, text)).is_err() {
            out.failed.push("the record that this was done".into());
        }
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::os::unix::fs::PermissionsExt;

    /// A home folder made for one test, removed (and only it) when the test ends, pass or fail.
    struct Home(PathBuf);
    impl Home {
        fn new(name: &str) -> Home {
            let p = std::env::temp_dir().join(format!("k724-{}-{name}", std::process::id()));
            let _ = fs::remove_dir_all(&p);
            fs::create_dir_all(&p).unwrap();
            Home(p)
        }
        fn put(&self, base: &str, id: &str, file: &str, text: &str) {
            let p = self.0.join(base).join(id).join(file);
            fs::create_dir_all(p.parent().unwrap()).unwrap();
            fs::write(p, text).unwrap();
        }
        fn read(&self, base: &str, id: &str, file: &str) -> Option<String> {
            fs::read_to_string(self.0.join(base).join(id).join(file)).ok()
        }
    }
    impl Drop for Home {
        fn drop(&mut self) {
            let _ = fs::remove_dir_all(&self.0);
        }
    }
    const APP: &str = "Library/Application Support";
    const WEB: &str = "Library/WebKit";

    #[test]
    fn copies_the_old_folders_once_and_leaves_the_old_ones_alone() {
        let h = Home::new("copy");
        h.put(APP, OLD_ID, "a/b.txt", "one");
        h.put(WEB, OLD_ID, "WebsiteData/ls.db", "prefs");
        let out = migrate(&h.0, OLD_ID, NEW_ID);
        assert!(out.failed.is_empty() && !out.already_done);
        assert_eq!(h.read(APP, NEW_ID, "a/b.txt").as_deref(), Some("one"));
        assert_eq!(h.read(WEB, NEW_ID, "WebsiteData/ls.db").as_deref(), Some("prefs"));
        assert_eq!(h.read(APP, OLD_ID, "a/b.txt").as_deref(), Some("one"), "old data stays");
        assert_eq!(h.read(WEB, OLD_ID, "WebsiteData/ls.db").as_deref(), Some("prefs"));
        assert!(!h.0.join(APP).join(format!("{NEW_ID}.copying")).exists(), "no temporary folder is left");
        // The second launch does nothing, even after the old folder changes and the new one is edited.
        h.put(APP, OLD_ID, "later.txt", "x");
        h.put(APP, NEW_ID, "a/b.txt", "edited");
        let again = migrate(&h.0, OLD_ID, NEW_ID);
        assert!(again.already_done && again.summary().is_empty());
        assert_eq!(h.read(APP, NEW_ID, "a/b.txt").as_deref(), Some("edited"));
        assert_eq!(h.read(APP, NEW_ID, "later.txt"), None);
    }

    #[test]
    fn never_overwrites_a_new_folder_that_has_something_in_it() {
        let h = Home::new("keep");
        h.put(APP, OLD_ID, "a.txt", "old");
        h.put(APP, NEW_ID, "a.txt", "new");
        h.put(WEB, OLD_ID, "w.db", "old web");
        let out = migrate(&h.0, OLD_ID, NEW_ID);
        assert_eq!(h.read(APP, NEW_ID, "a.txt").as_deref(), Some("new"));
        assert_eq!(h.read(WEB, NEW_ID, "w.db").as_deref(), Some("old web"), "a folder that was missing is still filled");
        assert_eq!(out.copied, ["WebKit"]);
        assert_eq!(h.read(APP, OLD_ID, "a.txt").as_deref(), Some("old"));
    }

    #[test]
    fn an_empty_new_folder_counts_as_missing() {
        let h = Home::new("empty");
        h.put(APP, OLD_ID, "a.txt", "old");
        fs::create_dir_all(h.0.join(APP).join(NEW_ID)).unwrap();
        migrate(&h.0, OLD_ID, NEW_ID);
        assert_eq!(h.read(APP, NEW_ID, "a.txt").as_deref(), Some("old"));
    }

    #[test]
    fn a_missing_old_folder_is_fine_and_creates_nothing_but_the_record() {
        let h = Home::new("none");
        let out = migrate(&h.0, OLD_ID, NEW_ID);
        assert!(out.copied.is_empty() && out.failed.is_empty());
        assert!(!h.0.join(WEB).exists());
        let names: Vec<_> = fs::read_dir(h.0.join(APP).join(NEW_ID)).unwrap().map(|e| e.unwrap().file_name()).collect();
        assert_eq!(names, [MARKER]);
    }

    #[test]
    fn a_file_that_cannot_be_read_is_reported_and_tried_again_next_time() {
        let h = Home::new("fail");
        h.put(APP, OLD_ID, "ok.txt", "fine");
        h.put(APP, OLD_ID, "locked.txt", "secret");
        let locked = h.0.join(APP).join(OLD_ID).join("locked.txt");
        fs::set_permissions(&locked, fs::Permissions::from_mode(0o000)).unwrap();
        if fs::read(&locked).is_ok() {
            return; // running as a user who can read anything: the case can't be made
        }
        let out = migrate(&h.0, OLD_ID, NEW_ID);
        assert_eq!(out.failed, ["Application Support"]);
        assert!(out.summary().contains("try again"));
        assert!(!h.0.join(APP).join(NEW_ID).exists(), "a half copy is not left behind, so it can't pass for real data");
        assert!(!h.0.join(APP).join(format!("{NEW_ID}.copying")).exists());
        fs::set_permissions(&locked, fs::Permissions::from_mode(0o600)).unwrap();
        let retry = migrate(&h.0, OLD_ID, NEW_ID);
        assert!(retry.failed.is_empty());
        assert_eq!(h.read(APP, NEW_ID, "locked.txt").as_deref(), Some("secret"));
    }

    #[test]
    fn symlinks_are_not_followed() {
        let h = Home::new("link");
        h.put(APP, OLD_ID, "a.txt", "x");
        std::os::unix::fs::symlink("/etc/hosts", h.0.join(APP).join(OLD_ID).join("link")).unwrap();
        migrate(&h.0, OLD_ID, NEW_ID);
        assert!(h.0.join(APP).join(NEW_ID).join("a.txt").exists());
        assert!(!h.0.join(APP).join(NEW_ID).join("link").exists());
    }

    #[test]
    fn the_app_config_uses_the_new_identifier() {
        let conf = include_str!("../tauri.conf.json");
        assert!(conf.contains(&format!("\"identifier\": \"{NEW_ID}\"")));
        assert!(!conf.contains(OLD_ID));
    }
}
