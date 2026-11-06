# τ^τ-bench Web Interface

## 🚀 Quick Start

### Prerequisites

- **Node.js** (version 16 or higher)
- **npm** (comes with Node.js)

### Installation & Setup

1. **Navigate to the leaderboard directory**
   ```bash
   cd web/leaderboard
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Configure environment (optional)**
   ```bash
   cp .env.example .env.local
   ```
   Uncomment `VITE_HYPER_SUBMISSIONS_BASE_URL` to fetch submission data from S3 instead of the local `public/hyper-submissions/` directory (only needed if submission data moves off-repo).

4. **Start the development server**
   ```bash
   npm run dev
   ```

5. **Open your browser**
   - Navigate to `http://localhost:5173` (or the URL shown in your terminal)
   - The application will automatically reload when you make changes

## Submitting to the Leaderboard

We welcome community submissions! The leaderboard accepts τ^τ-bench build results (a coding harness + Developer model evaluated on the 53 release tasks) through pull requests.

See **[Submitting to the leaderboard](../../README.md#submitting-to-the-leaderboard)** in the repository README for complete instructions on running evaluations, preparing submissions, and submitting a pull request.

## 🔧 Development

### Routing, Prerendering & SEO

The site uses **path-based routing** (`/`, `/trajectories`) driven by
`src/routes.js` — the single source of truth for routes, per-page meta tags and
**where the site is served**: `SITE_ORIGIN` + `SITE_BASE` feed the Vite base
path, the router, the prerender step, `sitemap.xml`/`robots.txt` and the e2e
suite. It is currently the GitHub Pages project URL
(`https://sierra-research.github.io/hyper-tau-bench`); moving to the
`hyper.taubench.com` custom domain is a two-value change in that file.

At deploy time, `scripts/prerender.mjs` snapshots each route into its own
static HTML file (real content + per-page `<title>`/OG tags for crawlers and
link unfurls). Content guards fail the deploy if any page renders empty.
**Adding a new page?** Register it in `src/routes.js` (route, view, meta) and
add a guard in `scripts/prerender.mjs`.

Nothing here requires manual steps: pushes to `main` touching `web/leaderboard/`
trigger `.github/workflows/deploy-leaderboard.yml` (build → prerender → deploy),
and PRs run the Playwright routing tests in `e2e/` via
`.github/workflows/test-leaderboard.yml`.

To reproduce locally:

```bash
npm run build          # build dist/
npm run prerender      # prerender routes into dist/ (needs Chrome)
npm run serve:dist     # serve dist/ with GitHub Pages semantics on :4173
npm run test:e2e       # run the Playwright suite against it
```

### Deep links

`/trajectories?slot=<slot>&view=trajectory|kit&eval=<held-out task id>` opens one build on
one tab with that held-out conversation highlighted in the eval strip (and named in a
chip in the build's summary). The picker and the tabs write `slot` and `view` back, so
the address bar is always a link to what is on screen. Strata's Evaluations page links
each cell of a construction run here.

### Serving the site with a store of builds (Strata's `hyper-tau` service)

`server.mjs` serves `dist/` under `SITE_BASE` (default `/hyper-tau`) and keeps a data
directory of builds that overlay `public/build-trajectories/`:
`PUT <SITE_BASE>/build-trajectories/<slot>` with `{row, trajectory, kit}` — the three
files `scripts/recording-to-trajectory.py … --no-manifest` writes for a run — stores the
build and adds its row to the manifest, so the visualizer lists it beside the board's
own. `Dockerfile` (built from the repository root) packages the two, with the site built
for `SITE_BASE`; Strata's compose files and Helm chart build it at a pinned commit and its
gateway proxies `/hyper-tau/*` to it. The site's origin and base are build-time values:
`VITE_SITE_ORIGIN` and `VITE_SITE_BASE` (see `src/routes.js`).

```bash
npm run build                                                   # with VITE_SITE_BASE=/hyper-tau for the served path
PORT=8001 SITE_BASE=/hyper-tau DATA_DIR=./data node server.mjs
python3 scripts/recording-to-trajectory.py <recording.json> <result.json> <kit>/workspace ./out <slot> "<label>" --no-manifest
curl -X PUT localhost:8001/hyper-tau/build-trajectories/<slot> -H 'content-type: application/json' \
  --data-binary "$(jq -n --slurpfile r out/rel<slot>.row.json --slurpfile t out/rel<slot>.json --slurpfile k out/rel<slot>.kit.json '{row:$r[0],trajectory:$t[0],kit:$k[0]}')"
```

### Project Structure
```
src/
├── components/          # React components
│   ├── HyperTau.jsx        # τ^τ-bench leaderboard (home page)
│   ├── HyperTau.css        # Board styling
│   ├── BuildTrajectories.jsx  # Build-trajectory visualizer
│   ├── BuildTrajectories.css  # Visualizer styling
│   └── Leaderboard.css     # Shared table styles
├── assets/             # Logo images and icons
├── routes.js           # Routes and per-page metadata (single source of truth)
├── App.jsx             # Main application component
├── App.css             # Main application styling
├── index.css           # Global styles
└── main.jsx            # Application entry point

public/
├── hyper-submissions/    # Submission metadata (one dir per harness+model)
├── build-trajectories/   # Scrubbed build trajectories for the visualizer
└── *.png, robots.txt, sitemap.xml
```
