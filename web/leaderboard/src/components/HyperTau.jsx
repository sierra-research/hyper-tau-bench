import React, { useState, useEffect, useMemo } from 'react'
// Leaderboard.css carries the shared table classes this board is built on
// (imported here directly since the main Leaderboard component itself is not
// part of this site); HyperTau.css layers the deltas on top.
import './Leaderboard.css'
import './HyperTau.css'
import { REPO_URL, repoUrl } from '../routes'

// τ^τ-bench leaderboard — a separate board from the τ²/τ³ tracks because the
// unit of evaluation is different: rows are developer configurations (coding
// harness × builder model), each scored over the 53 release tasks, not models
// scored by pass^k. Numbers mirror the paper's main-results table.
//
// The markup deliberately clones the main Leaderboard's reliability table
// (same shared classes: rank badges, model-info, retrieval-badge chips, the
// pass^k-style scope selector, score bars, and the expandable per-domain
// breakdown) so the two boards read as one site. Keep structure changes in
// sync with Leaderboard.jsx.

const HYPER_BASE = import.meta.env.VITE_HYPER_SUBMISSIONS_BASE_URL
  || `${import.meta.env.BASE_URL}hyper-submissions`

const NO_CACHE = { cache: 'no-cache' }

// Scope selector (the analog of the main board's Pass^1–4 toggle): overall
// first, then the four domains. Banking carries 35 of the 53 tasks.
const SCOPES = [
  { key: 'overall', label: 'Overall', desc: 'Mean over all 53 tasks' },
  { key: 'airline', label: 'Airline', desc: 'Mean over the 6 airline tasks' },
  { key: 'retail', label: 'Retail', desc: 'Mean over the 6 retail tasks' },
  { key: 'telecom', label: 'Telecom', desc: 'Mean over the 6 telecom tasks' },
  { key: 'banking', label: 'Banking', desc: 'Mean over the 35 banking tasks' },
]

const DOMAIN_INFO = [
  {
    key: 'airline',
    label: 'Airline',
    icon: '✈️',
    count: 6,
    desc: 'Dense declarative rules over bookings, baggage, and compensation — failures come from missing or ambiguous edge cases.',
  },
  {
    key: 'retail',
    label: 'Retail',
    icon: '🛍️',
    count: 6,
    desc: 'Order cancellations, returns, exchanges, and gift-card mechanics with derangement-resistant resolution flows.',
  },
  {
    key: 'telecom',
    label: 'Telecom',
    icon: '📱',
    count: 6,
    desc: 'Procedural diagnostic workflows — wrong step ordering and premature escalation are the dominant failure modes.',
  },
  {
    key: 'banking',
    label: 'Banking',
    icon: '🏦',
    count: 35,
    desc: 'Six embedded-policy subdomains over a corpus of nearly 3,000 atomic facts — a single task can draw on up to 580 of them, several times an entire other domain. 35 of the 53 tasks live here.',
  },
]

const fmtDate = (iso) => {
  if (!iso) return null
  return new Date(`${iso}T00:00:00Z`).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC',
  })
}

const HyperTau = () => {
  const [rows, setRows] = useState([])
  const [reference, setReference] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [scope, setScope] = useState('overall')
  const [sortDirection, setSortDirection] = useState('desc')
  const [expandedRows, setExpandedRows] = useState(new Set())
  // Easter egg: clicking the 👤 Human chip reveals who this human actually is.
  const [humanEggOpen, setHumanEggOpen] = useState(false)

  useEffect(() => {
    const load = async () => {
      try {
        const [manifestRes, referenceRes] = await Promise.all([
          fetch(`${HYPER_BASE}/manifest.json`, NO_CACHE),
          fetch(`${HYPER_BASE}/reference.json`, NO_CACHE),
        ])
        if (!manifestRes.ok) throw new Error('Failed to load τ^τ-bench data')
        const manifest = await manifestRes.json()
        const referenceData = referenceRes.ok ? await referenceRes.json() : null

        const submissions = await Promise.all(
          (manifest.submissions || []).map(async (dir) => {
            const res = await fetch(`${HYPER_BASE}/${dir}/submission.json`, NO_CACHE)
            if (!res.ok) return null
            const data = await res.json()
            return { ...data, dir }
          })
        )
        setRows(submissions.filter(Boolean))
        setReference(referenceData)
        setLoading(false)
      } catch (e) {
        setError(e.message)
        setLoading(false)
      }
    }
    load()
  }, [])

  const ranked = useMemo(() => {
    const sorted = [...rows].sort(
      (a, b) => (b.scores?.[scope] ?? -1) - (a.scores?.[scope] ?? -1)
    )
    return sortDirection === 'desc' ? sorted : sorted.reverse()
  }, [rows, scope, sortDirection])

  const toggleExpand = (key) => {
    setExpandedRows((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  const scoreBarCell = (value, referenceRow = false) => (
    <td className="metric-cell score-cell">
      {value === null || value === undefined ? (
        <span className="no-data">—</span>
      ) : (
        <div className="score-bar-container">
          <div className="score-bar-track">
            <div
              className={`score-bar-fill ${referenceRow ? 'ht-reference-fill' : ''}`}
              style={{ width: `${Math.min(value, 100)}%` }}
            />
          </div>
          <span className="score-bar-value">{value.toFixed(1)}%</span>
        </div>
      )}
    </td>
  )

  // Expandable per-domain breakdown, cloned from the main board's
  // domain-detail row; submissions also get a build-stats strip.
  const breakdownRow = (row, isReference = false) => (
    <tr className="domain-detail-row">
      <td colSpan={7} className="domain-detail-cell">
        <div className="domain-breakdown">
          {DOMAIN_INFO.map(({ key, label, icon, count, desc }) => {
            const value = row.scores?.[key]
            return (
              <div key={key} className="domain-breakdown-card">
                <div className="domain-card-header">
                  <span className="domain-breakdown-label">
                    <span className="domain-breakdown-icon">{icon}</span>
                    {label}
                    <span className="ht-domain-count">({count})</span>
                  </span>
                  <span className="domain-info-icon" data-tooltip={desc}>ⓘ</span>
                </div>
                <div className="domain-card-body">
                  {value !== null && value !== undefined ? (
                    <div className="score-bar-container">
                      <div className="score-bar-track">
                        <div
                          className={`score-bar-fill domain-bar-fill ${isReference ? 'ht-reference-fill' : ''}`}
                          style={{ width: `${Math.min(value, 100)}%` }}
                        />
                      </div>
                      <span className="score-bar-value">{value.toFixed(1)}%</span>
                    </div>
                  ) : (
                    <span className="no-data domain-no-data">—</span>
                  )}
                </div>
              </div>
            )
          })}
        </div>
        <div className="ht-build-stats">
          {isReference ? (
            <>
              <div className="ht-build-stat">
                <span className="ht-build-stat-label">Serve credits</span>
                <span className="ht-build-stat-value">
                  {row.serve_credit_ratio === undefined ? '—' : `${row.serve_credit_ratio.toFixed(2)}× budget`}
                </span>
              </div>
              <div className="ht-build-stat">
                <span className="ht-build-stat-label">Source</span>
                <span className="ht-build-stat-value">
                  <a
                    className="ht-repo-link"
                    href={repoUrl('web/leaderboard/public/hyper-submissions/reference.json')}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    reference.json ↗
                  </a>
                </span>
              </div>
            </>
          ) : (
            <>
              <div className="ht-build-stat">
                <span className="ht-build-stat-label">Build time</span>
                <span className="ht-build-stat-value">
                  {row.build_time_min === undefined ? '—' : `${row.build_time_min.toFixed(1)} min / task`}
                </span>
              </div>
              <div className="ht-build-stat">
                <span className="ht-build-stat-label">Build cost</span>
                <span className="ht-build-stat-value">
                  {row.build_cost_usd === undefined ? '—' : `$${row.build_cost_usd.toFixed(1)} / task`}
                </span>
              </div>
              <div className="ht-build-stat">
                <span className="ht-build-stat-label">Serve credits</span>
                <span className="ht-build-stat-value">
                  {row.serve_credit_ratio === undefined ? '—' : `${row.serve_credit_ratio.toFixed(2)}× budget`}
                </span>
              </div>
              <div className="ht-build-stat">
                <span className="ht-build-stat-label">Submitted by</span>
                <span className="ht-build-stat-value">{row.submitting_organization}</span>
              </div>
              <div className="ht-build-stat">
                <span className="ht-build-stat-label">Submission</span>
                <span className="ht-build-stat-value">
                  <a
                    className="ht-repo-link"
                    href={repoUrl(`web/leaderboard/public/hyper-submissions/${row.dir}/submission.json`)}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    submission.json ↗
                  </a>
                </span>
              </div>
            </>
          )}
        </div>
      </td>
    </tr>
  )

  return (
    <div className="leaderboard-wrapper">
      <div className="leaderboard-container">
        <h1 className="leaderboard-title">
          τ<sup>τ</sup>-bench Leaderboard
        </h1>
        <p className="leaderboard-subtitle ht-subtitle">
          pronounced “hyper-tau-bench”
        </p>
        <p className="leaderboard-subtitle ht-subtitle ht-links">
          Coding harness × builder model configurations, each scored over the{' '}
          <a className="ht-repo-link" href={repoUrl('data/tau2/hyper/tasks', 'tree')} target="_blank" rel="noopener noreferrer">
            53 release tasks
          </a>{' '}
          in the sealed runner ·{' '}
          <a className="ht-repo-link" href={REPO_URL} target="_blank" rel="noopener noreferrer">
            code &amp; data on GitHub
          </a>
        </p>

        {loading ? (
          <div className="ht-loading">Loading leaderboard…</div>
        ) : error ? (
          <div className="ht-loading">Failed to load: {error}</div>
        ) : (
          <div className="reliability-metrics">
            <div className="metrics-table-container">
              <table className="reliability-table ht-table">
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Developer</th>
                    <th>Date</th>
                    <th>Harness</th>
                    <th>Reasoning</th>
                    <th className="passk-header-cell">
                      <div className="passk-header-toggle">
                        {SCOPES.map((s) => (
                          <button
                            key={s.key}
                            className={`passk-header-btn ${scope === s.key ? 'active' : ''}`}
                            onClick={() => setScope(s.key)}
                            title={s.desc}
                          >
                            {s.label}
                          </button>
                        ))}
                        <button
                          className="passk-sort-btn"
                          onClick={() => setSortDirection(sortDirection === 'desc' ? 'asc' : 'desc')}
                          title={sortDirection === 'desc' ? 'Sorted descending' : 'Sorted ascending'}
                        >
                          {sortDirection === 'desc' ? '↓' : '↑'}
                        </button>
                      </div>
                    </th>
                    <th className="expand-header"></th>
                  </tr>
                </thead>
                <tbody>
                  {reference && (
                    <React.Fragment>
                      <tr
                        className={`model-row ht-reference-row ${expandedRows.has('__reference') ? 'expanded' : ''}`}
                      >
                        <td className="rank-cell">
                          <span className="rank-number ht-reference-rank">—</span>
                        </td>
                        <td className="model-info">
                          <div className="model-name">{reference.title}</div>
                        </td>
                        <td className="release-date-cell"><span className="no-data">—</span></td>
                        <td className="organization-info organization-info-retrieval">
                          <button
                            type="button"
                            className={`retrieval-badge ht-human-chip ${humanEggOpen ? 'open' : ''}`}
                            data-tooltip={reference.subtitle}
                            aria-label={reference.subtitle}
                            aria-expanded={humanEggOpen}
                            onClick={() => setHumanEggOpen(!humanEggOpen)}
                          >
                            👤 Human
                          </button>
                        </td>
                        <td className="reasoning-info"><span className="no-data">—</span></td>
                        {scoreBarCell(reference.scores?.[scope], true)}
                        <td className="expand-cell" onClick={() => toggleExpand('__reference')}>
                          <span className={`expand-caret ${expandedRows.has('__reference') ? 'open' : ''}`}>▶</span>
                        </td>
                      </tr>
                      {expandedRows.has('__reference') && breakdownRow(reference, true)}
                    </React.Fragment>
                  )}
                  {ranked.map((row, index) => {
                    const isExpanded = expandedRows.has(row.dir)
                    return (
                      <React.Fragment key={row.dir}>
                        <tr className={`model-row ${isExpanded ? 'expanded' : ''}`}>
                          <td className="rank-cell">
                            <span className={`rank-number ${index === 0 ? 'rank-gold' : index === 1 ? 'rank-silver' : index === 2 ? 'rank-bronze' : ''}`}>
                              #{index + 1}
                            </span>
                          </td>
                          <td className="model-info">
                            <div className="model-name">
                              {row.builder.model_name}
                              {row.is_new && <span className="ht-new-chip">NEW</span>}
                            </div>
                          </td>
                          <td className="release-date-cell">
                            {row.submission_date ? (
                              <span className="release-date" title={row.submission_date}>
                                {fmtDate(row.submission_date)}
                              </span>
                            ) : (
                              <span className="no-data">—</span>
                            )}
                          </td>
                          <td className="organization-info organization-info-retrieval">
                            <span className="retrieval-badge">🛠️ {row.harness.name}</span>
                          </td>
                          <td className="reasoning-info">
                            {row.builder.reasoning_effort ? (
                              <span style={{ textTransform: 'lowercase' }}>{row.builder.reasoning_effort}</span>
                            ) : (
                              <span className="no-data">—</span>
                            )}
                          </td>
                          {scoreBarCell(row.scores?.[scope])}
                          <td className="expand-cell" onClick={() => toggleExpand(row.dir)}>
                            <span className={`expand-caret ${isExpanded ? 'open' : ''}`}>▶</span>
                          </td>
                        </tr>
                        {isExpanded && breakdownRow(row)}
                      </React.Fragment>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Submissions notice — same component as the main board. Every link
            is built from routes.js REPO_URL, so it follows the repo. */}
        <div className="submissions-notice">
          <div className="submissions-content">
            <h3>Submit Your Results</h3>
            <p>
              Have new results to share? Submit your developer configuration — coding harness and
              builder model — with a pull request that adds a <code>submission.json</code> under{' '}
              <a
                className="ht-repo-link"
                href={repoUrl('web/leaderboard/public/hyper-submissions', 'tree')}
                target="_blank"
                rel="noopener noreferrer"
              >
                hyper-submissions/
              </a>
              . The README's submission section has the required format and process.
            </p>
            <div className="submission-links">
              <a
                href={`${REPO_URL}#submitting-to-the-leaderboard`}
                target="_blank"
                rel="noopener noreferrer"
                className="submissions-link primary"
              >
                View Submission Guidelines →
              </a>
              <a
                href={`${REPO_URL}/pulls`}
                target="_blank"
                rel="noopener noreferrer"
                className="submissions-link secondary"
              >
                Submit via Pull Request →
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default HyperTau
