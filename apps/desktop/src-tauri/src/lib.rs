//! Ariadne for Mac: a thin screen over the `ariadne` command, which ships inside the app.
//!
//! Every action runs the same tool people can run from Terminal, so the app and the command never disagree. Scanning, reviewing, moving
//! and undoing need no AI. Only "Suggest a plan" uses Claude Code, and it can draft a plan but never approve or apply one.

use serde::Serialize;
use serde_json::Value;
use std::fs;
use std::path::PathBuf;
use std::process::{Command, Stdio};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};
use tauri::image::Image;
use tauri::menu::{Menu, MenuItem, PredefinedMenuItem};
use tauri::tray::TrayIconBuilder;
use tauri::{AppHandle, Manager, RunEvent, State, WindowEvent};

const PY: &str = "/usr/bin/python3";
// What the window may ask the tool to do. Aliases and pruning stay in Terminal/chat for now.
const ALLOWED: &[&str] = &["count", "plans", "show", "check", "approve", "move-row", "apply", "verify", "history", "undo", "doctor", "home", "install"];
const DRAFT_TIME_LIMIT: Duration = Duration::from_secs(15 * 60);

// Passed on every run: Claude Code ignores a folder's own settings until someone has trusted that folder, and nobody opens Ariadne's home
// interactively. Drafting is allowed; anything that moves or approves is explicitly denied.
const DRAFT_ALLOW: &str = "Edit(plans/**),Bash(ariadne rules:*),Bash(ariadne scan:*),Bash(ariadne count:*),Bash(ariadne new-plan:*),\
Bash(ariadne plans:*),Bash(ariadne show:*),Bash(ariadne check:*),Bash(ariadne dupes:*),Bash(ariadne history:*)";
const DRAFT_DENY: &str = "Bash(ariadne approve:*),Bash(ariadne apply:*),Bash(ariadne undo:*),Bash(ariadne alias:*),Bash(ariadne prune-empty:*),\
Bash(ariadne protect:*),Bash(ariadne notes:*),Bash(rm:*),Bash(mv:*),Bash(cp:*),Bash(python3:*),Bash(/usr/bin/python3:*),WebFetch,WebSearch";

#[derive(Clone, Serialize, Default)]
struct Job {
    running: Option<String>,
    last_folder: String,
    last_ok: Option<bool>,
    last_output: String,
}

struct Shared {
    root: PathBuf, // where the tool lives: inside the app, or the repo in development
    job: Mutex<Job>,
}

type S = Arc<Shared>;

fn home() -> PathBuf {
    PathBuf::from(std::env::var("HOME").unwrap_or_else(|_| "/Users/Shared".into()))
}

fn ariadne_home() -> PathBuf {
    std::env::var("ARIADNE_HOME").map(PathBuf::from).unwrap_or_else(|_| home().join("Library/Application Support/Ariadne"))
}

fn uid() -> String {
    Command::new("/usr/bin/id").arg("-u").output().map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string()).unwrap_or_default()
}

fn quit_flag() -> PathBuf {
    // /tmp empties on restart, so quitting Ariadne lasts until the next restart or until you open it again.
    PathBuf::from(format!("/tmp/ariadne-quit-{}", uid()))
}

fn xml_escape(s: &str) -> String {
    s.replace('&', "&amp;").replace('<', "&lt;").replace('>', "&gt;")
}

/// Opening the app once is all it takes: a small launch agent opens it at login and reopens it after a crash, the same way Theseus does.
/// Quitting from the menu is respected. `"open_at_login": false` in config.json turns this off. Development builds have no bundle, so they don't get one.
fn keep_open() {
    const LABEL: &str = "com.ariadne.watchdog";
    let path = home().join("Library/LaunchAgents").join(format!("{LABEL}.plist"));
    let domain = format!("gui/{}", uid());
    let cfg: Value = fs::read_to_string(ariadne_home().join("config.json")).ok().and_then(|t| serde_json::from_str(&t).ok()).unwrap_or(Value::Null);
    if cfg["open_at_login"].as_bool() == Some(false) {
        if path.exists() {
            let _ = Command::new("/bin/launchctl").args(["bootout", &domain, path.to_str().unwrap_or("")]).output();
            let _ = fs::remove_file(&path);
        }
        return;
    }
    let Some(app) = std::env::current_exe().ok().and_then(|e| e.ancestors().find(|p| p.extension().map(|x| x == "app").unwrap_or(false)).map(PathBuf::from)) else { return };
    let quoted = format!("'{}'", app.display().to_string().replace('\'', "'\\''"));
    let script = format!("pgrep -xq ariadne || [ -e {} ] || open -g -j {quoted}", quit_flag().display());
    let plist = format!(
        r#"<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>{LABEL}</string>
<key>ProgramArguments</key><array><string>/bin/sh</string><string>-c</string><string>{}</string></array>
<key>RunAtLoad</key><true/>
<key>StartInterval</key><integer>300</integer>
</dict></plist>
"#,
        xml_escape(&script)
    );
    if fs::read_to_string(&path).map(|t| t == plist).unwrap_or(false) {
        return;
    }
    let _ = fs::create_dir_all(path.parent().unwrap());
    let _ = Command::new("/bin/launchctl").args(["bootout", &domain, path.to_str().unwrap_or("")]).output();
    if fs::write(&path, plist).is_ok() {
        let _ = Command::new("/bin/launchctl").args(["bootstrap", &domain, path.to_str().unwrap_or("")]).output();
    }
}

/// True if it can't read a folder it watches, so the window should say so instead of leaving only a menu bar icon.
fn needs_setup(root: &PathBuf) -> bool {
    match tool(root, &["count".to_string()]) {
        Ok(t) => serde_json::from_str::<Value>(&t).ok().map(|v| v["unreadable"].as_array().map(|a| !a.is_empty()).unwrap_or(false)).unwrap_or(true),
        Err(_) => true,
    }
}

fn find_claude() -> Option<PathBuf> {
    let h = home();
    [h.join(".local/bin/claude"), PathBuf::from("/opt/homebrew/bin/claude"), PathBuf::from("/usr/local/bin/claude")]
        .into_iter()
        .find(|p| p.exists())
}

fn path_env(root: &PathBuf) -> String {
    format!("{}:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:{}/.local/bin", root.join("bin").display(), home().display())
}

fn tool(root: &PathBuf, args: &[String]) -> Result<String, String> {
    // /usr/bin/python3 is a stub until Apple's developer tools are installed.
    let has_tools = Command::new("/usr/bin/xcode-select").arg("-p").output().map(|o| o.status.success()).unwrap_or(false);
    if !has_tools {
        return Err("Ariadne needs Apple's command line tools. In Terminal, run: xcode-select --install".into());
    }
    let out = Command::new(PY)
        .arg(root.join("tools/cli.py"))
        .args(args)
        .env("PATH", path_env(root))
        .stdin(Stdio::null())
        .output()
        .map_err(|e| e.to_string())?;
    let stdout = String::from_utf8_lossy(&out.stdout).to_string();
    if out.status.success() {
        Ok(stdout)
    } else {
        let err = String::from_utf8_lossy(&out.stderr).trim().to_string();
        Err(if stdout.trim().is_empty() { err } else { stdout })
    }
}

fn unfiled(root: &PathBuf) -> Option<u64> {
    let v: Value = serde_json::from_str(&tool(root, &["count".to_string()]).ok()?).ok()?;
    v["total"].as_u64()
}

// ---------- commands ----------

#[tauri::command(async)]
fn cli(s: State<'_, S>, args: Vec<String>) -> Result<String, String> {
    match args.first() {
        Some(c) if ALLOWED.contains(&c.as_str()) => tool(&s.root, &args),
        _ => Err("That command isn't available in the app.".into()),
    }
}

#[tauri::command]
fn job_status(s: State<'_, S>) -> Job {
    s.job.lock().unwrap().clone()
}

/// Ask Claude Code to draft a plan for a folder. It can write a plan but can't approve or apply one.
#[tauri::command]
fn suggest(s: State<'_, S>, folder: String) -> Result<(), String> {
    let claude = find_claude().ok_or("Claude Code isn't installed. You can still review, move and undo plans here.")?;
    {
        let mut j = s.job.lock().unwrap();
        if j.running.is_some() {
            return Err("Already working on a plan.".into());
        }
        j.running = Some(folder.clone());
    }
    let shared = s.inner().clone();
    thread::spawn(move || {
        let prompt = format!(
            "Run a filing pass for {folder} as far as the Check step in RULES.md: scan it, classify by file name only (don't open file \
             contents), write the plan and run the check until it has no problems. Leave the approve column blank. Don't approve, apply or move \
             anything. End with the plan's file name and a two-line summary."
        );
        let (ok, text) = draft(&claude, &prompt, &shared.root);
        let mut j = shared.job.lock().unwrap();
        *j = Job { running: None, last_folder: folder, last_ok: Some(ok), last_output: text };
    });
    Ok(())
}

fn draft(claude: &PathBuf, prompt: &str, root: &PathBuf) -> (bool, String) {
    let h = ariadne_home();
    let _ = fs::create_dir_all(h.join("logs"));
    let log = h.join("logs/last-draft.txt");
    let file = match fs::File::create(&log) {
        Ok(f) => f,
        Err(e) => return (false, e.to_string()),
    };
    let err = match file.try_clone() {
        Ok(f) => f,
        Err(e) => return (false, e.to_string()),
    };
    let child = Command::new(claude)
        .args(["-p", prompt, "--allowedTools", DRAFT_ALLOW, "--disallowedTools", DRAFT_DENY])
        .current_dir(&h)
        .env("PATH", path_env(root))
        .stdin(Stdio::null())
        .stdout(file)
        .stderr(err)
        .spawn();
    let mut child = match child {
        Ok(c) => c,
        Err(e) => return (false, e.to_string()),
    };
    let started = Instant::now();
    let ok = loop {
        match child.try_wait() {
            Ok(Some(status)) => break status.success(),
            Ok(None) if started.elapsed() > DRAFT_TIME_LIMIT => {
                let _ = child.kill();
                let _ = child.wait();
                return (false, "Claude Code took longer than 15 minutes, so Ariadne stopped it. Nothing was moved.".into());
            }
            Ok(None) => thread::sleep(Duration::from_secs(1)),
            Err(e) => return (false, e.to_string()),
        }
    };
    let text = fs::read_to_string(&log).unwrap_or_default();
    // Claude Code's own notice about untrusted folders is noise here: the tools are passed explicitly.
    let text = text.lines().filter(|l| !l.starts_with("Ignoring ")).collect::<Vec<_>>().join("\n");
    (ok, text)
}

#[tauri::command]
fn open_privacy(pane: String) {
    let anchor = match pane.as_str() {
        "files" => "Privacy_AllFiles",
        "automation" => "Privacy_Automation",
        _ => "Privacy",
    };
    let _ = Command::new("/usr/bin/open").arg(format!("x-apple.systempreferences:com.apple.preference.security?{anchor}")).spawn();
}

#[tauri::command]
fn reveal(what: String) -> Result<(), String> {
    let h = ariadne_home();
    let (flag, path) = match what.as_str() {
        "home" => ("-R", h.join("config.json")),
        "map" => ("-t", h.join("filing-map.md")),
        "rules" => ("-t", h.join("filing-rules.md")),
        _ => return Err("unknown".into()),
    };
    Command::new("/usr/bin/open").arg(flag).arg(path).spawn().map(|_| ()).map_err(|e| e.to_string())
}

fn show_main(app: &AppHandle) {
    if let Some(w) = app.get_webview_window("main") {
        let _ = w.show();
        let _ = w.set_focus();
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![cli, job_status, suggest, open_privacy, reveal])
        .setup(|app| {
            #[cfg(target_os = "macos")]
            app.set_activation_policy(tauri::ActivationPolicy::Accessory);

            // The tool ships inside the app; in development it's the repo.
            let bundled = app.path().resource_dir()?.join("engine");
            let root = if bundled.join("tools/cli.py").exists() {
                bundled
            } else {
                PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("../../..")
            };
            let shared: S = Arc::new(Shared { root: root.clone(), job: Mutex::new(Job::default()) });
            app.manage(shared.clone());
            let _ = tool(&root, &["init".to_string()]);

            // Opening the app undoes "Quit": from here on, the launch agent looks after it again.
            let _ = fs::remove_file(quit_flag());
            keep_open();

            // Open on the very first launch, and whenever it can't do its job yet, so nobody is left with only a menu bar icon.
            let seen = ariadne_home().join(".opened");
            if !seen.exists() || needs_setup(&root) {
                let _ = fs::write(&seen, "");
                show_main(app.handle());
            }

            let status = MenuItem::with_id(app, "status", "Counting…", false, None::<&str>)?;
            let open = MenuItem::with_id(app, "open", "Open Ariadne", true, None::<&str>)?;
            let quit = MenuItem::with_id(app, "quit", "Quit Ariadne", true, None::<&str>)?;
            let sep = PredefinedMenuItem::separator(app)?;
            let menu = Menu::with_items(app, &[&status, &sep, &open, &quit])?;
            TrayIconBuilder::with_id("ariadne")
                .icon(Image::from_bytes(include_bytes!("../icons/tray.png"))?)
                .icon_as_template(true)
                .tooltip("Ariadne")
                .menu(&menu)
                .show_menu_on_left_click(true)
                .on_menu_event(|app: &AppHandle, event| match event.id.as_ref() {
                    "open" => show_main(app),
                    "quit" => {
                        let _ = fs::write(quit_flag(), "");
                        app.exit(0);
                    }
                    _ => {}
                })
                .build(app)?;

            // Only ever counts. Nothing moves in the background.
            thread::spawn(move || loop {
                let line = match unfiled(&root) {
                    Some(0) => "All filed".to_string(),
                    Some(1) => "1 item to file".to_string(),
                    Some(n) => format!("{n} items to file"),
                    None => "Couldn't count".to_string(),
                };
                let _ = status.set_text(line);
                thread::sleep(Duration::from_secs(300));
            });
            Ok(())
        })
        .on_window_event(|window, event| {
            // Closing the window just hides it; Ariadne stays in the menu bar.
            if let WindowEvent::CloseRequested { api, .. } = event {
                api.prevent_close();
                let _ = window.hide();
            }
        })
        .build(tauri::generate_context!())
        .expect("error while starting Ariadne");
    app.run(|handle, event| {
        // Opening the app again (Finder, Spotlight) brings the window back.
        if let RunEvent::Reopen { .. } = event {
            show_main(handle);
        }
    });
}
