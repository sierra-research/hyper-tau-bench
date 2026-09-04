// Single source of truth for the site's routes and per-page metadata.
//
// Imported by the app (App.jsx) and by scripts/prerender.mjs (plain Node),
// so keep this file free of JSX and browser globals. Adding a page here is
// what makes it exist: the router resolves it, the prerender step emits a
// static HTML file for it, and the e2e suite picks it up.
//
// This site is the standalone τ^τ-bench (hyper-tau-bench) leaderboard. The
// home page IS the leaderboard; the main τ-bench site lives separately at
// https://taubench.com and the nav links back to it.

export const SITE_ORIGIN = 'https://hyper.taubench.com'

// The public τ^τ-bench repository. Every "view on GitHub" link on the site
// (nav button, submission guidelines, per-row submission files, task JSONs on
// the trajectories page) is built from this one constant, so pointing the site
// at a renamed or moved repo is a one-line change here.
export const REPO_URL = 'https://github.com/sierra-research/hyper-tau-bench'

// Deep link into the repo at its default branch: `kind` is 'blob' for a file
// and 'tree' for a directory.
export const repoUrl = (path = '', kind = 'blob') =>
  path ? `${REPO_URL}/${kind}/main/${path.replace(/^\/+/, '')}` : REPO_URL

// path → view name.
export const ROUTES = {
  '/': 'hyper-tau',
  '/trajectories': 'trajectories',
}

// Canonical path for each view (used for navigation and canonical/og:url).
export const VIEW_PATHS = {
  'hyper-tau': '/',
  trajectories: '/trajectories',
}

const SITE_TITLE = 'τ^τ-bench Leaderboard (hyper-tau-bench)'
const SITE_DESCRIPTION =
  'τ^τ-bench (pronounced "hyper-tau-bench") benchmarks agent-building agents: coding harnesses and builder models constructing customer-service agents from evidence corpora and client interaction, scored in a sealed runner.'

export const PAGE_META = {
  'hyper-tau': {
    title: SITE_TITLE,
    description: SITE_DESCRIPTION,
  },
  trajectories: {
    title: 'Build Trajectories — τ^τ-bench',
    description:
      'Explore τ^τ-bench build trajectories: how a coding harness constructs a customer-service agent — client dialogue, tool calls, test runs, and evaluation outcomes for each release task.',
  },
}

const stripTrailingSlash = (p) => (p.length > 1 && p.endsWith('/') ? p.slice(0, -1) : p)

// Resolve a pathname to a view; unknown paths render the leaderboard (home).
export const getViewFromPath = (pathname) => ROUTES[stripTrailingSlash(pathname)] || 'hyper-tau'
