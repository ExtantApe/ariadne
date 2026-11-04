import { invoke } from '@tauri-apps/api/core'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { Icon, type IconName } from './ui/Icon'

type Tab = 'inbox' | 'plans' | 'history' | 'setup'
type Count = { unfiled: Record<string, number>; total: number; unreadable?: string[] }
type PlanInfo = { plan: string; rows: number; approved: number; moved: number; pending: number; modified: string }
type Row = { line: number; approve: string; current_path: string; proposed_path: string; reason: string; state: 'moved' | 'pending' }
type PlanDetail = { plan: string; rows: Row[]; problems: string[]; warnings: string[]; moved: number }
type Batch = { batch: string; kind: string; moves: number; first: string; last: string; undone_at: string | null }
type Check = { name: string; ok: boolean; detail: string }
type Job = { running: string | null; last_folder: string; last_ok: boolean | null; last_output: string }

async function cli<T>(...args: string[]): Promise<T> {
  return JSON.parse(await invoke<string>('cli', { args })) as T
}

const errorText = (e: unknown) => {
  const s = String(e)
  try {
    const j = JSON.parse(s)
    if (j.problems) return j.problems.slice(0, 8).join('\n')
  } catch { /* plain text */ }
  return s
}
const pretty = (p: string) => p.replace(/^\/Users\/[^/]+/, '~')
const parent = (p: string) => p.slice(0, Math.max(p.lastIndexOf('/'), 0))
const base = (p: string) => p.slice(p.lastIndexOf('/') + 1)
const plural = (n: number, one: string) => `${n.toLocaleString()} ${one}${n === 1 ? '' : 's'}`
const when = (t: string) => t.replace('T', ' ').slice(0, 16)
const planName = (p: string) => p.replace(/\.csv$/, '').replace(/^\d{4}-\d{2}-\d{2}-/, '').replace(/-/g, ' ')
const planDate = (p: string) => p.match(/^\d{4}-\d{2}-\d{2}/)?.[0] ?? ''

const NAV: [Tab, string, IconName][] = [
  ['inbox', 'To file', 'inbox'],
  ['plans', 'Plans', 'plans'],
  ['history', 'History', 'history'],
  ['setup', 'Setup', 'setup'],
]

function Problem({ text, onClose }: { text: string; onClose: () => void }) {
  return (
    <div className="notice bad">
      <Icon name="alert" />
      <div className="grow" style={{ whiteSpace: 'pre-wrap' }}>{text}</div>
      <button className="btn quiet icon" onClick={onClose} aria-label="Dismiss" style={{ height: 22, width: 22 }}><Icon name="close" size={14} /></button>
    </div>
  )
}

export default function App() {
  const [tab, setTab] = useState<Tab>('inbox')
  const [openPlan, setOpenPlan] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [waiting, setWaiting] = useState<number | null>(null)
  const go = (t: Tab) => { setTab(t); setOpenPlan(null); setError('') }
  useEffect(() => {
    const load = () => cli<Count>('count').then((c) => setWaiting(c.total)).catch(() => {})
    void load()
    window.addEventListener('focus', load)
    return () => window.removeEventListener('focus', load)
  }, [tab])
  return (
    <div className="shell">
      <aside className="side">
        <div className="brand"><img src="/icon.svg" alt="" />Ariadne</div>
        <nav className="nav">
          {NAV.map(([t, label, icon]) => (
            <button key={t} aria-current={tab === t ? 'page' : undefined} onClick={() => go(t)}>
              <Icon name={icon} />
              {label}
              {t === 'inbox' && !!waiting && <span className="count">{waiting.toLocaleString()}</span>}
            </button>
          ))}
        </nav>
      </aside>
      <div className="main">
        {tab === 'inbox' && <Inbox onError={setError} error={error} onPlans={() => go('plans')} />}
        {tab === 'plans' && !openPlan && <Plans onOpen={setOpenPlan} onError={setError} error={error} />}
        {tab === 'plans' && openPlan && <Review plan={openPlan} onBack={() => setOpenPlan(null)} onError={setError} error={error} onHistory={() => go('history')} />}
        {tab === 'history' && <History onError={setError} error={error} />}
        {tab === 'setup' && <Setup onError={setError} error={error} />}
      </div>
    </div>
  )
}

type Common = { error: string; onError: (s: string) => void }

function Inbox({ error, onError, onPlans }: Common & { onPlans: () => void }) {
  const [count, setCount] = useState<Count | null>(null)
  const [job, setJob] = useState<Job | null>(null)
  const refresh = useCallback(() => { cli<Count>('count').then(setCount).catch((e) => onError(errorText(e))) }, [onError])
  useEffect(refresh, [refresh])
  useEffect(() => {
    window.addEventListener('focus', refresh)
    return () => window.removeEventListener('focus', refresh)
  }, [refresh])
  useEffect(() => {
    const poll = () => invoke<Job>('job_status').then(setJob)
    void poll()
    const t = setInterval(poll, 2000)
    return () => clearInterval(t)
  }, [])
  if (!count) return <div className="page"><p className="muted">Counting…</p></div>
  return (
    <div className="page">
      <div className="head">
        <div className="grow">
          <div className="big-count">{count.total.toLocaleString()}</div>
          <div className="sub">{count.total === 1 ? 'item waiting to be filed' : 'items waiting to be filed'}</div>
        </div>
      </div>
      {error && <Problem text={error} onClose={() => onError('')} />}
      {!!count.unreadable?.length && (
        <div className="notice"><Icon name="alert" /><div>Ariadne can't read {count.unreadable.join(' and ')} yet. Allow it in System Settings → Privacy &amp; Security → Files and Folders.</div></div>
      )}
      <div className="card">
        {Object.entries(count.unfiled).map(([folder, n]) => (
          <div className="item" key={folder}>
            <Icon name="folder" />
            <div className="grow title">{folder}</div>
            <span className="muted num">{n.toLocaleString()}</span>
            <button className="btn" disabled={!n || !!job?.running} onClick={() => invoke('suggest', { folder }).catch((e) => onError(String(e)))}>
              {job?.running === folder ? <><Icon name="refresh" className="spin" />Working…</> : <><Icon name="sparkle" />Suggest a plan</>}
            </button>
          </div>
        ))}
      </div>
      {job?.running && <div className="muted small">Claude Code is drafting a plan for {job.running} from file names. It can't move anything.</div>}
      {!job?.running && job?.last_ok === true && (
        <div className="card pad"><pre className="selectable">{job.last_output.trim()}</pre><div className="row" style={{ marginTop: 10 }}><button className="btn primary" onClick={onPlans}>Review the plan<Icon name="arrowRight" /></button></div></div>
      )}
      {!job?.running && job?.last_ok === false && <Problem text={`Couldn't draft a plan. ${job.last_output.trim().slice(0, 400)}`} onClose={() => setJob({ ...job, last_ok: null })} />}
      <div className="promise muted small">
        <div><Icon name="check" size={15} />Nothing moves until you approve it.</div>
        <div><Icon name="check" size={15} />Nothing is ever deleted or overwritten.</div>
        <div><Icon name="check" size={15} />Every batch can be put back.</div>
      </div>
    </div>
  )
}

function Plans({ onOpen, error, onError }: Common & { onOpen: (p: string) => void }) {
  const [plans, setPlans] = useState<PlanInfo[] | null>(null)
  useEffect(() => { cli<PlanInfo[]>('plans').then(setPlans).catch((e) => onError(errorText(e))) }, [onError])
  const waiting = plans?.filter((p) => !p.moved || p.pending) ?? []
  const done = plans?.filter((p) => p.moved && !p.pending) ?? []
  const row = (p: PlanInfo) => (
    <button className="item click" key={p.plan} onClick={() => onOpen(p.plan)}>
      <Icon name="file" />
      <div className="grow">
        <div className="title" style={{ textTransform: 'capitalize' }}>{planName(p.plan)}</div>
        <div className="muted small">{planDate(p.plan)} · {plural(p.rows, 'item')}</div>
      </div>
      {!p.moved ? <span className="pill warn">Ready to review</span> : p.pending ? <span className="pill warn">{p.pending.toLocaleString()} waiting</span> : <span className="pill ok">Moved {p.moved.toLocaleString()}</span>}
      <Icon name="chevron" className="chev" />
    </button>
  )
  return (
    <div className="page">
      <div className="head"><div className="grow"><h1>Plans</h1><div className="sub">Where everything would go. Nothing moves until you say so.</div></div></div>
      {error && <Problem text={error} onClose={() => onError('')} />}
      {plans && !plans.length && <div className="card empty"><Icon name="plans" size={28} /><h2>No plans yet</h2><div>Suggest one from To file, or run <code>/tidy</code> in Claude Code.</div></div>}
      {waiting.length > 0 && <div className="card"><div className="card-title">To review</div>{waiting.map(row)}</div>}
      {done.length > 0 && <div className="card"><div className="card-title">Done</div>{done.map(row)}</div>}
    </div>
  )
}

function Review({ plan, onBack, error, onError, onHistory }: Common & { plan: string; onBack: () => void; onHistory: () => void }) {
  const [d, setD] = useState<PlanDetail | null>(null)
  const [sel, setSel] = useState<Set<number> | null>(null)
  const [confirming, setConfirming] = useState(false)
  const [busy, setBusy] = useState(false)
  const [done, setDone] = useState<{ moved: number; skipped: unknown[]; batch: string } | null>(null)

  const load = useCallback(() => {
    cli<PlanDetail>('show', '--plan', plan).then((x) => {
      setD(x)
      const waiting = x.rows.filter((r) => r.proposed_path && r.state === 'pending').map((r) => r.line)
      // Everything starts ticked once. After that, keep the person's choices: never re-tick what they unticked.
      setSel((old) => (old === null ? new Set(waiting) : new Set(waiting.filter((l) => old.has(l)))))
    }).catch((e) => onError(errorText(e)))
  }, [plan, onError])
  useEffect(load, [load])

  const groups = useMemo(() => {
    const m = new Map<string, Row[]>()
    for (const r of d?.rows ?? []) {
      const k = parent(r.proposed_path) || '(no destination)'
      m.set(k, [...(m.get(k) ?? []), r])
    }
    return [...m.entries()].sort((a, b) => a[0].localeCompare(b[0]))
  }, [d])

  if (!d || !sel) return <div className="page"><p className="muted">Loading…</p></div>
  const waiting = d.rows.filter((r) => r.state === 'pending').length
  const finished = d.moved > 0 && waiting === 0
  const toggle = (lines: number[], on: boolean) => {
    setConfirming(false)
    setSel((s) => {
      const n = new Set(s ?? [])
      lines.forEach((l) => (on ? n.add(l) : n.delete(l)))
      return n
    })
  }
  const apply = async () => {
    setBusy(true)
    onError('')
    try {
      await cli('approve', '--plan', plan, '--all', '--clear')
      await cli('approve', '--plan', plan, '--lines', [...sel].join(','))
      const r = await cli<{ moved: number; skipped: unknown[]; batch: string }>('apply', '--plan', plan, '--yes')
      setDone(r)
      load()
    } catch (e) {
      // Plan problems appear in the plan itself after the reload; only anything else needs the banner.
      if (!String(e).includes('"problems"')) onError(errorText(e))
      load()
    }
    setBusy(false)
    setConfirming(false)
  }

  return (
    <div className="page wide">
      <div className="head bar">
        <button className="btn icon" onClick={onBack} aria-label="Back to plans"><Icon name="back" /></button>
        <div className="grow">
          <h1 style={{ textTransform: 'capitalize' }}>{planName(plan)}</h1>
          <div className="sub">{finished ? `${plural(d.moved, 'item')} moved` : `${sel.size.toLocaleString()} of ${waiting.toLocaleString()} selected · ${plural(groups.length, 'destination')}`}</div>
        </div>
        {!finished && (confirming ? (
          <>
            <button className="btn" onClick={() => setConfirming(false)}>Cancel</button>
            <button className="btn primary" disabled={busy} onClick={apply}>{busy ? 'Moving…' : `Yes, move ${plural(sel.size, 'item')}`}</button>
          </>
        ) : (
          <button className="btn primary" disabled={!sel.size} onClick={() => setConfirming(true)}>Move {plural(sel.size, 'item')}…</button>
        ))}
      </div>
      {error && <Problem text={error} onClose={() => onError('')} />}
      {done && (
        <div className="notice">
          <Icon name="check" />
          <div className="grow">Moved {plural(done.moved, 'item')}{done.skipped.length ? `, skipped ${done.skipped.length}` : ''}.</div>
          <button className="btn" onClick={onHistory}><Icon name="undo" />Undo in History</button>
        </div>
      )}
      {!finished && d.moved > 0 && !done && <div className="muted small">{plural(d.moved, 'item')} already moved. The rest are still waiting for you.</div>}
      {!finished && d.problems.length > 0 && (
        <div className="notice bad"><Icon name="alert" /><div><b>Fix these before moving</b><pre style={{ marginTop: 4 }}>{d.problems.slice(0, 12).join('\n')}</pre></div></div>
      )}
      {!finished && d.warnings.length > 0 && <div className="notice"><Icon name="info" /><pre>{d.warnings.slice(0, 8).join('\n')}</pre></div>}
      {groups.map(([dest, rows]) => {
        const lines = rows.filter((r) => r.state === 'pending').map((r) => r.line)
        const all = lines.length > 0 && lines.every((l) => sel.has(l))
        return (
          <details className="card group" key={dest} open={groups.length <= 12}>
            <summary>
              <Icon name="chevron" className="chev" />
              {!finished && lines.length > 0 && <input type="checkbox" aria-label={`Select all going to ${pretty(dest)}`} checked={all} onClick={(e) => e.stopPropagation()} onChange={() => toggle(lines, !all)} />}
              <Icon name="folder" />
              <span className="dest grow">{pretty(dest)}</span>
              <span className="muted num">{rows.length.toLocaleString()}</span>
            </summary>
            {rows.map((r) => {
              const renamed = base(r.current_path) !== base(r.proposed_path)
              const pending = r.state === 'pending'
              return (
                <div className={`line ${pending ? '' : 'done'}`} key={r.line}>
                  <span className="tick">
                    {pending
                      ? (!finished && <input type="checkbox" aria-label={base(r.proposed_path)} checked={sel.has(r.line)} onChange={() => toggle([r.line], !sel.has(r.line))} />)
                      : <Icon name="check" size={14} />}
                  </span>
                  <div>
                    <div className="name">{base(r.proposed_path)}</div>
                    <div className="from">{renamed ? `was ${base(r.current_path)} · ` : ''}from {pretty(parent(r.current_path))}</div>
                  </div>
                  <div className="why">{r.reason}</div>
                </div>
              )
            })}
          </details>
        )
      })}
    </div>
  )
}

function History({ error, onError }: Common) {
  const [rows, setRows] = useState<Batch[] | null>(null)
  const [preview, setPreview] = useState<{ batch: string; would_restore: number; sample: string[] } | null>(null)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState('')
  const load = useCallback(() => { cli<Batch[]>('history').then(setRows).catch((e) => onError(errorText(e))) }, [onError])
  useEffect(load, [load])
  const ask = (batch: string) => {
    setMsg('')
    cli<NonNullable<typeof preview>>('undo', '--batch', batch).then(setPreview).catch((e) => onError(errorText(e)))
  }
  const run = async () => {
    if (!preview) return
    setBusy(true)
    try {
      const r = await cli<{ restored: number; skipped_total?: number; failed?: unknown[] }>('undo', '--batch', preview.batch, '--yes')
      const left = (r.skipped_total ?? 0) + (r.failed?.length ?? 0)
      setMsg(`Put back ${plural(r.restored, 'item')}${left ? `. ${left} couldn't go back because something changed since; try Undo again once that's sorted.` : '.'}`)
      setPreview(null)
      load()
    } catch (e) {
      onError(errorText(e))
    }
    setBusy(false)
  }
  return (
    <div className="page">
      <div className="head"><div className="grow"><h1>History</h1><div className="sub">Everything Ariadne has moved. Any batch can be put back.</div></div></div>
      {error && <Problem text={error} onClose={() => onError('')} />}
      {msg && <div className="notice"><Icon name="check" /><div>{msg}</div></div>}
      {preview && (
        <div className="card pad" style={{ borderColor: 'var(--warn)' }}>
          <b>Put {plural(preview.would_restore, 'item')} back from {planName(preview.batch)}?</b>
          <pre className="muted" style={{ margin: '8px 0 12px' }}>{preview.sample.slice(0, 6).join('\n')}{preview.would_restore > 6 ? '\n…' : ''}</pre>
          <div className="row">
            <button className="btn primary" disabled={busy} onClick={run}>{busy ? 'Putting back…' : 'Yes, put them back'}</button>
            <button className="btn" onClick={() => setPreview(null)}>Cancel</button>
          </div>
        </div>
      )}
      {rows && !rows.length && <div className="card empty"><Icon name="history" size={28} /><h2>Nothing moved yet</h2></div>}
      {rows && rows.length > 0 && (
        <div className="card">
          {rows.map((b) => (
            <div className="item" key={b.batch}>
              <Icon name={b.kind === 'notes' ? 'file' : 'folder'} />
              <div className="grow">
                <div className="title" style={{ textTransform: 'capitalize' }}>{planName(b.batch)}</div>
                <div className="muted small">{plural(b.moves, b.kind === 'notes' ? 'note' : 'item')} · {when(b.last)}</div>
              </div>
              {b.undone_at ? <span className="pill">Put back</span> : <button className="btn" onClick={() => ask(b.batch)}><Icon name="undo" />Undo…</button>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function Setup({ error, onError }: Common) {
  const [checks, setChecks] = useState<Check[] | null>(null)
  const [cmd, setCmd] = useState('')
  const load = useCallback((withNotes = false) => {
    setChecks(null)
    cli<{ checks: Check[] }>(...(withNotes ? ['doctor', '--notes'] : ['doctor'])).then((d) => setChecks(d.checks)).catch((e) => onError(errorText(e)))
  }, [onError])
  useEffect(() => {
    load()
    const again = () => load()
    window.addEventListener('focus', again)
    return () => window.removeEventListener('focus', again)
  }, [load])
  const installCommand = () => cli<{ command: string; note?: string }>('install')
    .then((r) => setCmd(`${r.command}${r.note ? `. ${r.note}.` : ''}`)).catch((e) => onError(errorText(e)))
  return (
    <div className="page">
      <div className="head"><div className="grow"><h1>Setup</h1><div className="sub">Your filing structure, permissions and tools.</div></div></div>
      {error && <Problem text={error} onClose={() => onError('')} />}
      <div className="card">
        <div className="card-title">Your filing</div>
        <div className="item"><Icon name="map" /><div className="grow"><div className="title">Filing map</div><div className="muted small">The folders everything files into, and how things are named.</div></div><button className="btn" onClick={() => invoke('reveal', { what: 'map' })}>Edit</button></div>
        <div className="item"><Icon name="plans" /><div className="grow"><div className="title">Filing rules</div><div className="muted small">What Ariadne has learned from your corrections.</div></div><button className="btn" onClick={() => invoke('reveal', { what: 'rules' })}>Edit</button></div>
        <div className="item"><Icon name="folder" /><div className="grow"><div className="title">Ariadne's folder</div><div className="muted small">Your plans and move logs.</div></div><button className="btn" onClick={() => invoke('reveal', { what: 'home' })}>Show</button></div>
      </div>
      <div className="card">
        <div className="card-title">Status</div>
        {!checks && <div className="item muted">Checking…</div>}
        {checks?.map((c) => (
          <div className="item perm" key={c.name}>
            <div className="grow"><div className="title">{c.name}</div><div className="muted small">{c.detail}</div></div>
            {c.ok ? <span className="pill ok state"><Icon name="check" size={12} />OK</span> : <span className="pill warn state">Needs access</span>}
          </div>
        ))}
        <div className="item">
          <div className="row grow">
            <button className="btn" onClick={() => invoke('open_privacy', { pane: 'files' })}><Icon name="open" />Full Disk Access</button>
            <button className="btn" onClick={() => invoke('open_privacy', { pane: 'automation' })}><Icon name="open" />Automation</button>
          </div>
          <button className="btn quiet" onClick={() => load(true)}>Test Notes (opens Notes)</button>
        </div>
      </div>
      <div className="card">
        <div className="card-title">The ariadne command</div>
        <div className="item"><Icon name="terminal" /><div className="grow"><div className="title">Use Ariadne from Terminal, Claude Code and Theseus</div><div className="muted small">{cmd || 'Adds ariadne to your command line.'}</div></div><button className="btn" onClick={installCommand}>Install</button></div>
      </div>
    </div>
  )
}
