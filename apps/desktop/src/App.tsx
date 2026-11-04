import { useCallback, useEffect, useMemo, useState } from "react";
import { invoke } from "@tauri-apps/api/core";

type Tab = "inbox" | "plans" | "history" | "setup";
type Count = { unfiled: Record<string, number>; total: number };
type PlanInfo = { plan: string; rows: number; approved: number; moved: number; pending: number; modified: string };
type Row = { line: number; approve: string; current_path: string; proposed_path: string; reason: string; state: "moved" | "pending" };
type PlanDetail = { plan: string; rows: Row[]; problems: string[]; warnings: string[]; moved: number };
type Batch = { batch: string; kind: string; moves: number; first: string; last: string; undone_at: string | null };
type Check = { name: string; ok: boolean; detail: string };
type Job = { running: string | null; last_folder: string; last_ok: boolean | null; last_output: string };

async function cli<T>(...args: string[]): Promise<T> {
  return JSON.parse(await invoke<string>("cli", { args })) as T;
}

const errorText = (e: unknown) => {
  const s = String(e);
  try {
    const j = JSON.parse(s);
    if (j.problems) return j.problems.slice(0, 8).join("\n");
  } catch { /* plain text */ }
  return s;
};
const pretty = (p: string) => p.replace(/^\/Users\/[^/]+/, "~");
const parent = (p: string) => p.slice(0, Math.max(p.lastIndexOf("/"), 0));
const base = (p: string) => p.slice(p.lastIndexOf("/") + 1);
const plural = (n: number, one: string) => `${n.toLocaleString()} ${one}${n === 1 ? "" : "s"}`;
const when = (t: string) => t.replace("T", " ").slice(0, 16);

export default function App() {
  const [tab, setTab] = useState<Tab>("inbox");
  const [openPlan, setOpenPlan] = useState<string | null>(null);
  const [error, setError] = useState("");
  const tabs: [Tab, string][] = [["inbox", "To file"], ["plans", "Plans"], ["history", "History"], ["setup", "Setup"]];
  return (
    <div className="app">
      <header>
        <h1>Ariadne</h1>
        <nav>
          {tabs.map(([t, label]) => (
            <button key={t} className={tab === t ? "on" : ""} onClick={() => { setTab(t); setOpenPlan(null); setError(""); }}>{label}</button>
          ))}
        </nav>
      </header>
      {error && <p className="error" onClick={() => setError("")}>{error}</p>}
      <main>
        {tab === "inbox" && <Inbox onError={setError} onPlans={() => setTab("plans")} />}
        {tab === "plans" && !openPlan && <Plans onOpen={setOpenPlan} onError={setError} />}
        {tab === "plans" && openPlan && <Review plan={openPlan} onBack={() => setOpenPlan(null)} onError={setError} onHistory={() => { setOpenPlan(null); setTab("history"); }} />}
        {tab === "history" && <History onError={setError} />}
        {tab === "setup" && <Setup onError={setError} />}
      </main>
    </div>
  );
}

function Inbox({ onError, onPlans }: { onError: (s: string) => void; onPlans: () => void }) {
  const [count, setCount] = useState<Count | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const refresh = useCallback(() => {
    cli<Count>("count").then(setCount).catch((e) => onError(errorText(e)));
  }, [onError]);
  useEffect(refresh, [refresh]);
  useEffect(() => {
    const poll = () => invoke<Job>("job_status").then(setJob);
    poll();
    const t = setInterval(poll, 2000);
    return () => clearInterval(t);
  }, []);
  if (!count) return <p className="muted">Counting…</p>;
  return (
    <section>
      <h2>{count.total ? `${plural(count.total, "item")} waiting` : "All filed"}</h2>
      <p className="muted">Nothing moves until you approve a plan. Ariadne never deletes or overwrites, and every batch can be undone.</p>
      <table className="list"><tbody>
        {Object.entries(count.unfiled).map(([folder, n]) => (
          <tr key={folder}>
            <td>{folder}</td>
            <td className="num">{n.toLocaleString()}</td>
            <td className="act">
              <button disabled={!n || !!job?.running} onClick={() => invoke("suggest", { folder }).catch((e) => onError(String(e)))}>
                {job?.running === folder ? "Working…" : "Suggest a plan"}
              </button>
            </td>
          </tr>
        ))}
      </tbody></table>
      {job?.running && <p className="muted">Claude Code is drafting a plan for {job.running}, using file names only. It can't move anything.</p>}
      {!job?.running && job?.last_ok === true && (
        <div className="card"><pre>{job.last_output.trim()}</pre><button onClick={onPlans}>Review plans</button></div>
      )}
      {!job?.running && job?.last_ok === false && <p className="error">Couldn't draft a plan: {job.last_output.trim().slice(0, 400)}</p>}
    </section>
  );
}

function Plans({ onOpen, onError }: { onOpen: (p: string) => void; onError: (s: string) => void }) {
  const [plans, setPlans] = useState<PlanInfo[] | null>(null);
  useEffect(() => { cli<PlanInfo[]>("plans").then(setPlans).catch((e) => onError(errorText(e))); }, [onError]);
  if (!plans) return <p className="muted">Loading…</p>;
  if (!plans.length) return <p className="muted">No plans yet. Suggest one from To file, or run <code>/tidy</code> in Claude Code.</p>;
  return (
    <table className="list">
      <thead><tr><th>Plan</th><th className="num">Items</th><th>Status</th><th>Changed</th></tr></thead>
      <tbody>
        {plans.map((p) => (
          <tr key={p.plan} className="click" onClick={() => onOpen(p.plan)}>
            <td>{p.plan.replace(/\.csv$/, "")}</td>
            <td className="num">{p.rows.toLocaleString()}</td>
            <td>{!p.moved ? <b>Ready for review</b> : p.pending ? <><b>{p.pending.toLocaleString()} waiting</b> · moved {p.moved.toLocaleString()}</> : `Moved ${p.moved.toLocaleString()}`}</td>
            <td className="muted">{p.modified}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Review({ plan, onBack, onError, onHistory }: { plan: string; onBack: () => void; onError: (s: string) => void; onHistory: () => void }) {
  const [d, setD] = useState<PlanDetail | null>(null);
  const [sel, setSel] = useState<Set<number> | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState<{ moved: number; skipped: unknown[]; batch: string } | null>(null);

  const load = useCallback(() => {
    cli<PlanDetail>("show", "--plan", plan).then((x) => {
      setD(x);
      const waiting = x.rows.filter((r) => r.proposed_path && r.state === "pending").map((r) => r.line);
      // Everything starts ticked once. After that, keep the person's choices: never re-tick what they unticked.
      setSel((old) => (old === null ? new Set(waiting) : new Set(waiting.filter((l) => old.has(l)))));
    }).catch((e) => onError(errorText(e)));
  }, [plan, onError]);
  useEffect(load, [load]);

  const groups = useMemo(() => {
    const m = new Map<string, Row[]>();
    for (const r of d?.rows ?? []) {
      const k = parent(r.proposed_path) || "(no destination)";
      m.set(k, [...(m.get(k) ?? []), r]);
    }
    return [...m.entries()].sort((a, b) => a[0].localeCompare(b[0]));
  }, [d]);

  if (!d || !sel) return <p className="muted">Loading…</p>;
  const waiting = d.rows.filter((r) => r.state === "pending").length;
  const finished = d.moved > 0 && waiting === 0;
  const toggle = (lines: number[], on: boolean) => {
    setConfirming(false);
    setSel((s) => { const n = new Set(s ?? []); lines.forEach((l) => (on ? n.add(l) : n.delete(l))); return n; });
  };
  const apply = async () => {
    setBusy(true); onError("");
    try {
      await cli("approve", "--plan", plan, "--all", "--clear");
      await cli("approve", "--plan", plan, "--lines", [...sel].join(","));
      const r = await cli<{ moved: number; skipped: unknown[]; batch: string }>("apply", "--plan", plan, "--yes");
      setDone(r); load();
    } catch (e) {
      // Plan problems appear in the plan itself after the reload; only anything else needs the banner.
      if (!String(e).includes('"problems"')) onError(errorText(e));
      load();
    }
    setBusy(false); setConfirming(false);
  };

  return (
    <section>
      <div className="bar">
        <button onClick={onBack}>← Plans</button>
        <h2>{plan.replace(/\.csv$/, "")}</h2>
        <span className="grow" />
        {!finished && <>
          <span className="muted">{sel.size.toLocaleString()} of {waiting.toLocaleString()} selected</span>
          {confirming
            ? <><button onClick={() => setConfirming(false)}>Cancel</button><button className="primary" disabled={busy} onClick={apply}>{busy ? "Moving…" : `Yes, move ${plural(sel.size, "item")}`}</button></>
            : <button className="primary" disabled={!sel.size} onClick={() => setConfirming(true)}>Move {plural(sel.size, "item")}…</button>}
        </>}
      </div>
      {done && (
        <div className="card">
          Moved {plural(done.moved, "item")}{done.skipped.length ? `, skipped ${done.skipped.length}` : ""}. Batch <code>{done.batch}</code>.{" "}
          <button onClick={onHistory}>Undo in History</button>
        </div>
      )}
      {finished && !done && <p className="muted">All done: {plural(d.moved, "item")} moved. Undo it from History.</p>}
      {!finished && d.moved > 0 && !done && <p className="muted">{plural(d.moved, "item")} already moved. The rest are still waiting for you.</p>}
      {!finished && d.problems.length > 0 && <div className="error"><b>Fix before moving:</b><pre>{d.problems.slice(0, 12).join("\n")}</pre></div>}
      {!finished && d.warnings.length > 0 && <div className="card"><pre>{d.warnings.slice(0, 8).join("\n")}</pre></div>}
      {groups.map(([dest, rows]) => {
        const lines = rows.filter((r) => r.state === "pending").map((r) => r.line);
        const all = lines.length > 0 && lines.every((l) => sel.has(l));
        return (
          <details key={dest} open={groups.length <= 12}>
            <summary>
              {!finished && lines.length > 0 && <input type="checkbox" checked={all} onClick={(e) => e.stopPropagation()} onChange={() => toggle(lines, !all)} />}
              <span className="dest">{pretty(dest)}</span> <span className="muted">{rows.length.toLocaleString()}</span>
            </summary>
            <table className="rows"><tbody>
              {rows.map((r) => {
                const renamed = base(r.current_path) !== base(r.proposed_path);
                return (
                  <tr key={r.line}>
                    {!finished && <td className="tick">{r.state === "pending" ? <input type="checkbox" checked={sel.has(r.line)} onChange={() => toggle([r.line], !sel.has(r.line))} /> : "✓"}</td>}
                    <td>
                      <div>{base(r.proposed_path)}</div>
                      <div className="muted small">{renamed ? `was ${base(r.current_path)} · ` : ""}from {pretty(parent(r.current_path))}</div>
                    </td>
                    <td className="muted small why">{r.reason}</td>
                  </tr>
                );
              })}
            </tbody></table>
          </details>
        );
      })}
    </section>
  );
}

function History({ onError }: { onError: (s: string) => void }) {
  const [rows, setRows] = useState<Batch[] | null>(null);
  const [preview, setPreview] = useState<{ batch: string; would_restore: number; sample: string[] } | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const load = useCallback(() => { cli<Batch[]>("history").then(setRows).catch((e) => onError(errorText(e))); }, [onError]);
  useEffect(load, [load]);
  if (!rows) return <p className="muted">Loading…</p>;
  if (!rows.length) return <p className="muted">Nothing has been moved yet.</p>;
  const ask = (batch: string) => { setMsg(""); cli<typeof preview>("undo", "--batch", batch).then(setPreview).catch((e) => onError(errorText(e))); };
  const run = async () => {
    if (!preview) return;
    setBusy(true);
    try {
      const r = await cli<{ restored: number; skipped_changed_since?: string[]; failed?: unknown[] }>("undo", "--batch", preview.batch, "--yes");
      const left = (r.skipped_changed_since?.length ?? 0) + (r.failed?.length ?? 0);
      setMsg(`Put back ${plural(r.restored, "item")}${left ? `; ${left} left alone because they changed since` : ""}.`);
      setPreview(null); load();
    } catch (e) { onError(errorText(e)); }
    setBusy(false);
  };
  return (
    <section>
      {msg && <div className="card">{msg}</div>}
      {preview && (
        <div className="card warn">
          <b>Put {plural(preview.would_restore, "item")} back from {preview.batch}?</b>
          <pre>{preview.sample.slice(0, 8).join("\n")}{preview.would_restore > 8 ? "\n…" : ""}</pre>
          <div className="row"><button onClick={() => setPreview(null)}>Cancel</button><button className="primary" disabled={busy} onClick={run}>{busy ? "Putting back…" : "Yes, put them back"}</button></div>
        </div>
      )}
      <table className="list">
        <thead><tr><th>Batch</th><th>Kind</th><th className="num">Moves</th><th>When</th><th /></tr></thead>
        <tbody>
          {rows.map((b) => (
            <tr key={b.batch}>
              <td>{b.batch}</td><td className="muted">{b.kind}</td><td className="num">{b.moves.toLocaleString()}</td><td className="muted">{when(b.last)}</td>
              <td className="act">{b.undone_at ? <span className="muted">Undone</span> : <button onClick={() => ask(b.batch)}>Undo…</button>}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function Setup({ onError }: { onError: (s: string) => void }) {
  const [checks, setChecks] = useState<Check[] | null>(null);
  const load = useCallback(() => {
    setChecks(null);
    cli<{ checks: Check[] }>("doctor").then((d) => setChecks(d.checks)).catch((e) => onError(errorText(e)));
  }, [onError]);
  useEffect(load, [load]);
  return (
    <section>
      <h2>Your filing</h2>
      <div className="row">
        <button onClick={() => invoke("reveal", { what: "map" })}>Edit filing map</button>
        <button onClick={() => invoke("reveal", { what: "rules" })}>Edit filing rules</button>
        <button onClick={() => invoke("reveal", { what: "home" })}>Show Ariadne's folder</button>
      </div>
      <h2>Permissions</h2>
      <p className="muted">Files need access to the folders you file. Sorting Notes also needs Full Disk Access (Ariadne only reads a copy of the database) and Automation for Notes.</p>
      <div className="row">
        <button onClick={() => invoke("open_privacy", { pane: "files" })}>Full Disk Access…</button>
        <button onClick={() => invoke("open_privacy", { pane: "automation" })}>Automation…</button>
        <button onClick={load}>Check again</button>
      </div>
      {!checks ? <p className="muted">Checking…</p> : (
        <ul className="checks">
          {checks.map((c) => <li key={c.name} className={c.ok ? "ok" : "bad"}><b>{c.ok ? "✓" : "✗"} {c.name}</b> <span className="muted small">{c.detail}</span></li>)}
        </ul>
      )}
    </section>
  );
}
