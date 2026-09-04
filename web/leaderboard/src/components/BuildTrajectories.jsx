import { useState, useEffect, useMemo } from 'react'
import './Leaderboard.css'
import './BuildTrajectories.css'

// Build-trajectory visualizer: one sample build per release task, drawn from
// a mixture of the six developer configurations (coding harness × builder
// model), showing how a coding agent constructs the customer-service agent —
// client dialogue, tool calls, local test runs, and the final evaluation
// outcome. Data is distilled from the sealed-runner recordings into
// public/build-trajectories/ (truncated + scrubbed offline; this component
// only renders what ships there). Tool names arrive pre-normalized across
// harnesses (bash/read/write/edit/task + the hyper-tau MCP tools).
//
// A second tab shows the output kit for the same build: the final submitted
// workspace, distilled per slot into relNNN.kit.json alongside the
// trajectory (same scrubbing + `full`-truncation conventions).

import { repoUrl } from '../routes'

const BASE = `${import.meta.env.BASE_URL}build-trajectories`
const NO_CACHE = { cache: 'no-cache' }

const DOMAINS = [
  { key: 'airline', label: 'Airline', icon: '✈️' },
  { key: 'retail', label: 'Retail', icon: '🛍️' },
  { key: 'telecom', label: 'Telecom', icon: '📱' },
  { key: 'banking', label: 'Banking', icon: '🏦' },
]

const domainOf = (raw) => DOMAINS.find((d) => (raw || '').startsWith(d.key)) || { label: raw, icon: '📦' }

const TOOL_META = {
  bash: { icon: '❯', cls: 'bash', label: 'Bash' },
  read: { icon: '📄', cls: 'read', label: 'Read' },
  edit: { icon: '✏️', cls: 'edit', label: 'Edit' },
  write: { icon: '✏️', cls: 'edit', label: 'Write' },
  task: { icon: '🤖', cls: 'other', label: 'Subagent task' },
  run_local_test: { icon: '🧪', cls: 'test', label: 'run local test' },
  run_live_experiment: { icon: '🌐', cls: 'live', label: 'run live experiment' },
  submit: { icon: '📦', cls: 'submit', label: 'submit' },
}
const toolMeta = (name) => TOOL_META[name] || { icon: '🔧', cls: 'other', label: name.replace(/_/g, ' ') }
const toolLabel = (name) => toolMeta(name).label

const fmtPct = (x) => `${(x * 100).toFixed(1)}%`

// Collapsible long text block. `full` is the original length when the
// distiller truncated the text for shipping.
function Clamp({ text, full, mono = true, collapsedChars = 600 }) {
  const [open, setOpen] = useState(false)
  const needsClamp = text.length > collapsedChars
  const shown = open || !needsClamp ? text : `${text.slice(0, collapsedChars)}…`
  return (
    <div className="bt-clamp">
      <pre className={mono ? 'bt-pre' : 'bt-pre bt-pre-prose'}>{shown}</pre>
      {(needsClamp || full) && (
        <div className="bt-clamp-foot">
          {needsClamp && (
            <button type="button" className="bt-clamp-btn" onClick={() => setOpen(!open)}>
              {open ? 'Show less' : 'Show more'}
            </button>
          )}
          {full && <span className="bt-trunc-note">truncated for display ({full.toLocaleString()} chars)</span>}
        </div>
      )}
    </div>
  )
}

function CallCard({ item }) {
  const meta = toolMeta(item.tool)
  const args = item.args || {}
  const extraKeys = Object.keys(args).filter((k) => !k.endsWith('__full'))
  return (
    <div className={`bt-item bt-call bt-tool-${meta.cls}`}>
      <div className="bt-item-head">
        <span className="bt-tool-chip">
          <span className="bt-tool-icon">{meta.icon}</span> {toolLabel(item.tool)}
        </span>
        <span className="bt-step-num">step {item.s}</span>
      </div>
      {item.tool === 'Bash' && args.command != null ? (
        <Clamp text={args.command} full={args.command__full} />
      ) : extraKeys.length > 0 ? (
        <div className="bt-args">
          {extraKeys.map((k) => (
            <div key={k} className="bt-arg">
              <span className="bt-arg-key">{k}</span>
              <Clamp text={String(args[k])} full={args[`${k}__full`]} collapsedChars={300} />
            </div>
          ))}
        </div>
      ) : null}
    </div>
  )
}

function ResultCard({ item }) {
  const meta = toolMeta(item.tool)
  return (
    <div className={`bt-item bt-result bt-tool-${meta.cls}`}>
      <div className="bt-item-head">
        <span className="bt-result-label">↳ {toolLabel(item.tool)} output</span>
        <span className="bt-step-num">step {item.s}</span>
      </div>
      <Clamp text={item.text} full={item.full} collapsedChars={400} />
    </div>
  )
}

function TrajectoryItem({ item }) {
  switch (item.k) {
    case 'phase':
      return (
        <div className="bt-divider">
          <span>{item.detail || item.phase}</span>
        </div>
      )
    case 'client':
      return (
        <div className="bt-item bt-msg bt-msg-client">
          <div className="bt-msg-label">💼 Client</div>
          <Clamp text={item.text} full={item.full} mono={false} collapsedChars={900} />
        </div>
      )
    case 'dev_msg':
      return (
        <div className="bt-item bt-msg bt-msg-dev">
          <div className="bt-msg-label">🛠️ Builder → client</div>
          <Clamp text={item.text} full={item.full} mono={false} collapsedChars={900} />
        </div>
      )
    case 'text':
      return (
        <div className="bt-item bt-note">
          <div className="bt-msg-label">Builder</div>
          <Clamp text={item.text} full={item.full} mono={false} collapsedChars={900} />
        </div>
      )
    case 'call':
      return <CallCard item={item} />
    case 'result':
      return <ResultCard item={item} />
    case 'final_eval':
      return (
        <div className="bt-divider bt-divider-strong">
          <span>Final evaluation — held-out test suite</span>
        </div>
      )
    case 'done':
      return (
        <div className="bt-divider bt-divider-strong">
          <span>
            Build ended ({item.reason}) — {item.steps} steps, {item.tool_calls} tool calls
          </span>
        </div>
      )
    default:
      return null
  }
}

const fmtBytes = (n) => (n >= 1024 * 100 ? `${Math.round(n / 1024)} KB` : n >= 1024 ? `${(n / 1024).toFixed(1)} KB` : `${n} B`)

const FILE_ICONS = { py: '🐍', md: '📘', json: '{}', yaml: '⚙️', yml: '⚙️', toml: '⚙️', txt: '📄', js: '📜', ts: '📜', sh: '❯' }
const fileIcon = (path) => FILE_ICONS[path.split('.').pop().toLowerCase()] || '📄'

// Output-kit browser: the final submitted workspace for the same sampled
// build, shipped as relNNN.kit.json next to the trajectory. File tree on the
// left, file contents on the right.
function KitView({ kit, loading, error }) {
  const [selected, setSelected] = useState(null)

  const files = useMemo(() => kit?.files || [], [kit])
  const totalBytes = useMemo(() => files.reduce((a, f) => a + f.size, 0), [files])

  // Group by directory, root files first.
  const groups = useMemo(() => {
    const byDir = new Map()
    for (const f of files) {
      const i = f.path.lastIndexOf('/')
      const dir = i === -1 ? '' : f.path.slice(0, i)
      if (!byDir.has(dir)) byDir.set(dir, [])
      byDir.get(dir).push(f)
    }
    return [...byDir.entries()].sort(([a], [b]) => (a === '' ? -1 : b === '' ? 1 : a.localeCompare(b)))
  }, [files])

  // Default selection: the agent entrypoint if there is one, else first file.
  useEffect(() => {
    if (!files.length) {
      setSelected(null)
      return
    }
    if (selected && files.some((f) => f.path === selected)) return
    const preferred = ['agent.py', 'agent.ts', 'agent.js', 'main.py', 'README.md']
    setSelected((files.find((f) => preferred.includes(f.path)) || files[0]).path)
  }, [files, selected])

  if (loading) return <div className="ht-loading">Loading output kit…</div>
  if (error) return <div className="bt-kit-missing">No output kit is available for this build ({error}).</div>
  if (!kit) return null

  const current = files.find((f) => f.path === selected)

  return (
    <div className="bt-kit">
      <div className="bt-kit-meta">
        Final submitted workspace — {files.length.toLocaleString()} files, {fmtBytes(totalBytes)}
        {kit.skipped?.length > 0 && <span> · {kit.skipped.length} binary/unreadable files omitted</span>}
      </div>
      <div className="bt-kit-panes">
        <div className="bt-kit-tree">
          {groups.map(([dir, dirFiles]) => (
            <div key={dir || '.'} className="bt-kit-group">
              {dir && <div className="bt-kit-dir">📁 {dir}/</div>}
              {dirFiles.map((f) => (
                <button
                  key={f.path}
                  type="button"
                  className={`bt-kit-file ${dir ? 'nested' : ''} ${f.path === selected ? 'active' : ''}`}
                  onClick={() => setSelected(f.path)}
                >
                  <span className="bt-kit-file-icon">{fileIcon(f.path)}</span>
                  <span className="bt-kit-file-name">{f.path.slice(dir ? dir.length + 1 : 0)}</span>
                  <span className="bt-kit-file-size">{fmtBytes(f.size)}</span>
                </button>
              ))}
            </div>
          ))}
        </div>
        <div className="bt-kit-viewer">
          {current ? (
            <>
              <div className="bt-kit-viewer-head">
                <span className="bt-kit-viewer-path">{current.path}</span>
                <span className="bt-kit-viewer-info">
                  {current.text.split('\n').length.toLocaleString()} lines · {fmtBytes(current.size)}
                </span>
              </div>
              <pre className="bt-pre bt-kit-code">{current.text}</pre>
              {current.full && (
                <div className="bt-trunc-note bt-kit-trunc">
                  truncated for display ({current.full.toLocaleString()} chars in the submitted file)
                </div>
              )}
            </>
          ) : (
            <div className="ht-loading">Select a file</div>
          )}
        </div>
      </div>
    </div>
  )
}

const CHUNK = 250

function BuildTrajectories() {
  const [manifest, setManifest] = useState(null)
  const [error, setError] = useState(null)
  const [domainFilter, setDomainFilter] = useState('all')
  const [slot, setSlot] = useState(null)
  const [traj, setTraj] = useState(null)
  const [trajLoading, setTrajLoading] = useState(false)
  const [visible, setVisible] = useState(CHUNK)
  const [view, setView] = useState('trajectory')
  const [kit, setKit] = useState(null)
  const [kitLoading, setKitLoading] = useState(false)
  const [kitError, setKitError] = useState(null)

  useEffect(() => {
    fetch(`${BASE}/manifest.json`, NO_CACHE)
      .then((r) => {
        if (!r.ok) throw new Error(`manifest ${r.status}`)
        return r.json()
      })
      .then((m) => {
        setManifest(m)
        if (m.tasks?.length) setSlot(m.tasks[0].slot)
      })
      .catch((e) => setError(String(e)))
  }, [])

  const tasks = useMemo(() => {
    if (!manifest) return []
    return domainFilter === 'all'
      ? manifest.tasks
      : manifest.tasks.filter((t) => (t.domain || '').startsWith(domainFilter))
  }, [manifest, domainFilter])

  // Keep the selection inside the current filter.
  useEffect(() => {
    if (tasks.length && !tasks.some((t) => t.slot === slot)) setSlot(tasks[0].slot)
  }, [tasks, slot])

  useEffect(() => {
    if (!manifest || !slot) return
    const entry = manifest.tasks.find((t) => t.slot === slot)
    if (!entry) return
    setTrajLoading(true)
    setTraj(null)
    setVisible(CHUNK)
    fetch(`${BASE}/${entry.file}`, NO_CACHE)
      .then((r) => {
        if (!r.ok) throw new Error(`trajectory ${r.status}`)
        return r.json()
      })
      .then((t) => setTraj(t))
      .catch((e) => setError(String(e)))
      .finally(() => setTrajLoading(false))
  }, [manifest, slot])

  // Kit data is per-slot too, but fetched lazily the first time the kit tab
  // is opened for the current slot.
  useEffect(() => {
    setKit(null)
    setKitError(null)
  }, [slot])

  useEffect(() => {
    if (view !== 'kit' || !slot || kit || kitLoading || kitError) return
    setKitLoading(true)
    fetch(`${BASE}/rel${slot}.kit.json`, NO_CACHE)
      .then((r) => {
        if (!r.ok) throw new Error(`kit ${r.status}`)
        return r.json()
      })
      .then((k) => setKit(k))
      .catch((e) => setKitError(String(e.message || e)))
      .finally(() => setKitLoading(false))
  }, [view, slot, kit, kitLoading, kitError])

  if (error) {
    return (
      <div className="leaderboard-wrapper">
        <div className="leaderboard-container">
          <div className="ht-loading">Failed to load trajectories: {error}</div>
        </div>
      </div>
    )
  }
  if (!manifest) {
    return (
      <div className="leaderboard-wrapper">
        <div className="leaderboard-container">
          <div className="ht-loading">Loading trajectories…</div>
        </div>
      </div>
    )
  }

  const idx = tasks.findIndex((t) => t.slot === slot)
  const current = tasks[idx]
  const dom = domainOf(current?.domain)
  const items = traj?.items || []

  return (
    <div className="leaderboard-wrapper">
      <div className="leaderboard-container bt-container">
        <h1 className="leaderboard-title">Build Trajectories</h1>
        <p className="leaderboard-subtitle bt-subtitle">
          One sampled build per{' '}
          <a className="ht-repo-link" href={repoUrl('data/tau2/hyper/tasks', 'tree')} target="_blank" rel="noopener noreferrer">
            release task
          </a>
          , mixed across the developer configurations on the board — how a coding agent constructs
          the agent: reading the evidence, talking to the client, writing code, running tests, and
          submitting. The output kit tab shows the workspace each build submitted.
        </p>

        <div className="bt-controls">
          <div className="bt-domain-chips">
            <button
              type="button"
              className={`bt-chip ${domainFilter === 'all' ? 'active' : ''}`}
              onClick={() => setDomainFilter('all')}
            >
              All ({manifest.tasks.length})
            </button>
            {DOMAINS.map((d) => {
              const n = manifest.tasks.filter((t) => (t.domain || '').startsWith(d.key)).length
              return (
                <button
                  key={d.key}
                  type="button"
                  className={`bt-chip ${domainFilter === d.key ? 'active' : ''}`}
                  onClick={() => setDomainFilter(d.key)}
                >
                  {d.icon} {d.label} ({n})
                </button>
              )
            })}
          </div>
          <div className="bt-task-picker">
            <button
              type="button"
              className="bt-nav-btn"
              disabled={idx <= 0}
              onClick={() => setSlot(tasks[idx - 1].slot)}
            >
              ←
            </button>
            <select
              className="bt-task-select"
              value={slot || ''}
              onChange={(e) => setSlot(e.target.value)}
            >
              {tasks.map((t) => (
                <option key={t.slot} value={t.slot}>
                  {t.slot} · {domainOf(t.domain).label} · {t.builder_label} · {fmtPct(t.final)}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="bt-nav-btn"
              disabled={idx < 0 || idx >= tasks.length - 1}
              onClick={() => setSlot(tasks[idx + 1].slot)}
            >
              →
            </button>
          </div>
        </div>

        {current && (
          <div className="bt-summary">
            <div className="bt-summary-top">
              <span className="bt-slot-badge">Task {current.slot}</span>
              <span className="retrieval-badge">{dom.icon} {dom.label}</span>
              <span className="retrieval-badge">🛠️ {current.builder_label}</span>
              <span className="bt-summary-links">
                <a
                  className="ht-repo-link"
                  href={repoUrl(`data/tau2/hyper/tasks/${current.task_id}.json`)}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  task JSON ↗
                </a>
                <a className="ht-repo-link" href={`${BASE}/${current.file}`} target="_blank" rel="noopener noreferrer">
                  raw trajectory ↗
                </a>
                <a className="ht-repo-link" href={`${BASE}/rel${current.slot}.kit.json`} target="_blank" rel="noopener noreferrer">
                  raw kit ↗
                </a>
              </span>
            </div>
            {traj?.description && <p className="bt-task-desc">{traj.description}</p>}
            <div className="bt-summary-stats">
              <div className="bt-stat">
                <span className="bt-stat-label">Final score</span>
                <div className="bt-stat-score">
                  <div className="score-bar-container bt-score-bar">
                    <div className="score-bar-track">
                      <div className="score-bar-fill" style={{ width: `${current.final * 100}%` }} />
                    </div>
                    <span className="score-bar-value">{fmtPct(current.final)}</span>
                  </div>
                </div>
              </div>
              <div className="bt-stat">
                <span className="bt-stat-label">Evals passed</span>
                <span className="bt-stat-value">
                  {current.eval_passed} / {current.eval_total}
                </span>
              </div>
              <div className="bt-stat">
                <span className="bt-stat-label">Builder steps</span>
                <span className="bt-stat-value">{current.steps.toLocaleString()}</span>
              </div>
              <div className="bt-stat">
                <span className="bt-stat-label">Tool calls</span>
                <span className="bt-stat-value">{current.tool_calls.toLocaleString()}</span>
              </div>
            </div>
          </div>
        )}

        <div className="bt-tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={view === 'trajectory'}
            className={`bt-tab ${view === 'trajectory' ? 'active' : ''}`}
            onClick={() => setView('trajectory')}
          >
            🧭 Build trajectory
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={view === 'kit'}
            className={`bt-tab ${view === 'kit' ? 'active' : ''}`}
            onClick={() => setView('kit')}
          >
            📦 Output kit
          </button>
        </div>

        {/* Both views stay mounted so tab switches keep the kit's file
            selection and the trajectory's scroll/show-more state. */}
        <div hidden={view !== 'kit'}>
          <KitView kit={kit} loading={kitLoading} error={kitError} />
        </div>

        {view === 'trajectory' && trajLoading && <div className="ht-loading">Loading trajectory…</div>}

        {traj && (
          <div hidden={view !== 'trajectory'}>
            <div className="bt-stream">
              {items.slice(0, visible).map((item, i) => (
                <TrajectoryItem key={i} item={item} />
              ))}
            </div>
            {visible < items.length && (
              <div className="bt-more">
                <button type="button" className="bt-more-btn" onClick={() => setVisible(visible + CHUNK)}>
                  Show {Math.min(CHUNK, items.length - visible).toLocaleString()} more
                </button>
                <button type="button" className="bt-more-btn bt-more-all" onClick={() => setVisible(items.length)}>
                  Show all ({(items.length - visible).toLocaleString()} remaining)
                </button>
              </div>
            )}
            {traj.eval_tasks?.length > 0 && visible >= items.length && (
              <div className="bt-eval">
                <div className="bt-eval-head">
                  Held-out evaluation: {traj.result.eval_passed} of {traj.result.eval_total} tasks
                  passed — final score {fmtPct(traj.result.final)}
                </div>
                <div className="bt-eval-strip">
                  {traj.eval_tasks.map(([id, reward]) => (
                    <span
                      key={id}
                      className={`bt-eval-cell ${reward === 1 ? 'pass' : reward > 0 ? 'partial' : 'fail'}`}
                      title={`eval task ${id}: reward ${reward}`}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default BuildTrajectories
