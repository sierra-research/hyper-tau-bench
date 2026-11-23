// Routing + prerendering behavior tests. Run against the prerendered dist/
// served with GitHub Pages semantics (see playwright.config.js).
import { expect, test } from '@playwright/test'
import { PAPER_URL, REPO_URL, SITE_BASE, SITE_URL } from '../src/routes.js'

// Every request goes through the served base path, like on GitHub Pages.
const at = (route) => `${SITE_BASE}${route}`

// ---------------------------------------------------------------------------
// Direct loads: every route serves a real page with its own title and content.
// ---------------------------------------------------------------------------

test('direct load: homepage is the τ^τ-bench leaderboard', async ({ page, request }) => {
  const [manifest] = await Promise.all([
    page.waitForResponse(response => new URL(response.url()).pathname.endsWith('/manifest.json')),
    page.goto(at('/')),
  ])
  expect(manifest.ok()).toBe(true)
  const { submissions } = await manifest.json()
  await expect(page).toHaveTitle(/hyper-tau-bench/)
  await expect(page.locator('.ht-table .model-row:not(.ht-reference-row)')).toHaveCount(submissions.length)
  await expect(page.locator('.ht-reference-row')).toBeVisible()

  const files = ['reference.json', ...submissions.map(dir => `${dir}/submission.json`)]
  const [reference, ...developers] = await Promise.all(files.map(async file => {
    const response = await request.get(new URL(file, manifest.url()).href)
    await expect(response).toBeOK()
    return response.json()
  }))
  const scored = developers.filter(entry => Number.isFinite(entry.scores?.overall))
    .sort((a, b) => b.scores.overall - a.scores.overall)
  const ranked = page.locator('.ht-table .model-row:not(.ht-reference-row)')
  await expect(ranked.locator('.score-bar-value')).toHaveText(scored.map(entry => `${entry.scores.overall.toFixed(1)}%`))
  for (const [index, entry] of scored.entries()) {
    const row = ranked.nth(index)
    await expect(row.locator('.model-name')).toContainText(entry.builder.model_name)
    await expect(row.locator('.retrieval-badge')).toContainText(entry.harness.name)
    await expect(row.locator('.rank-cell')).toHaveText(`#${index + 1}`)
  }
  const human = page.locator('.ht-reference-row')
  await expect(human.locator('.rank-cell')).toHaveText('—')
  if (Number.isFinite(reference.scores?.overall)) {
    await expect(human.locator('.score-cell')).toHaveText(`${reference.scores.overall.toFixed(1)}%`)
  }
})

test('banking rank and breakdown follow the reported score', async ({ page }) => {
  await page.goto(at('/'))
  await page.getByRole('button', { name: 'Banking', exact: true }).click()
  const leader = page.locator('.model-row:not(.ht-reference-row)').first()
  await expect(leader.locator('.rank-cell')).toHaveText('#1')
  const developer = await leader.locator('.model-name').innerText()
  const harness = await leader.locator('.retrieval-badge').innerText()
  const score = await leader.locator('.score-bar-value').innerText()
  await leader.locator('.expand-cell').click()
  const banking = page.locator('.domain-breakdown-card').filter({ hasText: 'Banking' })
  await expect(banking.locator('.score-bar-value')).toHaveText(score)
  await page.getByTitle('Sorted descending').click()
  const row = page.locator('.model-row').filter({ hasText: developer }).filter({ hasText: harness })
  await expect(row.locator('.rank-cell')).toHaveText('#1')
  await expect(row.locator('.score-bar-value')).toHaveText(score)
})

test('direct load: build trajectories', async ({ page }) => {
  await page.goto(at('/trajectories'))
  await expect(page).toHaveTitle(/Build Trajectories — τ\^τ-bench/)
  // Manifest loads and the first task's stream renders.
  await expect(page.locator('.bt-summary')).toBeVisible()
  await expect(page.locator('.bt-stream .bt-item').first()).toBeVisible()
})

test('trajectories: task picker switches tasks', async ({ page }) => {
  await page.goto(at('/trajectories'))
  await expect(page.locator('.bt-summary')).toBeVisible()
  await page.locator('.bt-task-select').selectOption({ index: 1 })
  await expect(page.locator('.bt-slot-badge')).toHaveText(/Task 002/)
  await expect(page.locator('.bt-stream .bt-item').first()).toBeVisible()
})

test('trajectories: output kit tab shows the submitted workspace', async ({ page }) => {
  await page.goto(at('/trajectories'))
  await expect(page.locator('.bt-summary')).toBeVisible()
  await page.locator('.bt-tab', { hasText: 'Output kit' }).click()
  // Kit loads: file tree with an active file, and its content in the viewer.
  await expect(page.locator('.bt-kit-meta')).toContainText('Final submitted workspace')
  await expect(page.locator('.bt-kit-file.active')).toBeVisible()
  await expect(page.locator('.bt-kit-code')).not.toBeEmpty()
  // Selecting another file swaps the viewer.
  const second = page.locator('.bt-kit-file').nth(1)
  const name = (await second.locator('.bt-kit-file-name').textContent()).trim()
  await second.click()
  await expect(page.locator('.bt-kit-viewer-path')).toHaveText(new RegExp(name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')))
  // Switching tasks refetches the kit for the new slot.
  await page.locator('.bt-task-select').selectOption({ index: 1 })
  await expect(page.locator('.bt-slot-badge')).toHaveText(/Task 002/)
  await expect(page.locator('.bt-kit-file.active')).toBeVisible()
})

// ---------------------------------------------------------------------------
// Navigation.
// ---------------------------------------------------------------------------

test('nav links switch between leaderboard and trajectories', async ({ page }) => {
  await page.goto(at('/'))
  await page.getByRole('button', { name: 'Trajectories' }).click()
  await expect(page).toHaveURL(/\/trajectories/)
  await expect(page).toHaveTitle(/Build Trajectories — τ\^τ-bench/)

  await page.getByRole('button', { name: 'Leaderboard', exact: true }).click()
  await expect(page).toHaveURL(/\/(\?.*)?$/)
  await expect(page.locator('.ht-reference-row')).toBeVisible()
})

test('nav has a button back to the main τ-bench site', async ({ page }) => {
  await page.goto(at('/'))
  const backLink = page.locator('.nav-taubench-btn')
  await expect(backLink).toBeVisible()
  await expect(backLink).toHaveAttribute('href', 'https://taubench.com')
})

test('nav and submission links point at the public repository', async ({ page }) => {
  await page.goto(at('/'))
  const repoLink = page.locator('.nav-github-btn')
  await expect(repoLink).toBeVisible()
  await expect(repoLink).toHaveAttribute('href', REPO_URL)
  await expect(page.locator('.submissions-link.primary')).toHaveAttribute(
    'href',
    `${REPO_URL}#submitting-to-the-leaderboard`
  )
  await expect(page.locator('.submissions-link.secondary')).toHaveAttribute('href', `${REPO_URL}/pulls`)
})

test('nav links the paper after the repository', async ({ page }) => {
  await page.goto(at('/'))
  const paperLink = page.locator('.nav-paper-btn')
  await expect(paperLink).toBeVisible()
  await expect(paperLink).toHaveAttribute('href', PAPER_URL)
  await expect(paperLink).toHaveAttribute('target', '_blank')
  // Order in the nav: GitHub, then Paper, then back to τ-bench.com.
  const hrefs = await page.locator('.nav-links a').evaluateAll((as) => as.map((a) => a.getAttribute('href')))
  expect(hrefs.indexOf(REPO_URL)).toBeGreaterThanOrEqual(0)
  expect(hrefs.indexOf(PAPER_URL)).toBe(hrefs.indexOf(REPO_URL) + 1)
})

test('human chip toggles the easter-egg tooltip', async ({ page }) => {
  await page.goto(at('/'))
  const chip = page.locator('.ht-human-chip')
  await expect(chip).not.toHaveClass(/open/)
  await chip.click()
  await expect(chip).toHaveClass(/open/)
})

// ---------------------------------------------------------------------------
// Prerendered HTML: content and per-route meta exist without JavaScript.
// ---------------------------------------------------------------------------

test('prerendered homepage HTML contains leaderboard content and meta', async ({ request }) => {
  const res = await request.get(at('/'))
  expect(res.status()).toBe(200)
  const html = await res.text()
  expect(html).toContain('<title>τ^τ-bench Leaderboard (hyper-tau-bench)</title>')
  expect(html).toContain('Human performance')
  expect(html).toContain('property="og:title"')
  expect(html).toContain(`${SITE_URL}/`)
  expect(html).not.toContain('Loading leaderboard')
})

test('prerendered trajectories HTML contains content and meta', async ({ request }) => {
  const res = await request.get(at('/trajectories'))
  expect(res.status()).toBe(200)
  const html = await res.text()
  expect(html).toContain('<title>Build Trajectories — τ^τ-bench</title>')
  expect(html).toContain(`${SITE_URL}/trajectories`)
  expect(html).toContain('bt-stream')
  expect(html).not.toContain('Loading trajectories')
})

test('prerendered pages carry absolute og:image for link unfurls', async ({ request }) => {
  const html = await (await request.get(at('/'))).text()
  expect(html).toContain(`property="og:image" content="${SITE_URL}/og-image.png"`)
  expect(html).not.toContain('__SITE_URL__')
})

test('sitemap and robots follow the served site URL', async ({ request }) => {
  const sitemap = await (await request.get(at('/sitemap.xml'))).text()
  expect(sitemap).toContain(`<loc>${SITE_URL}/</loc>`)
  expect(sitemap).toContain(`<loc>${SITE_URL}/trajectories</loc>`)
  const robots = await (await request.get(at('/robots.txt'))).text()
  expect(robots).toContain(`Sitemap: ${SITE_URL}/sitemap.xml`)
})

// ---------------------------------------------------------------------------
// Unknown paths: GitHub Pages serves 404.html, which boots the SPA.
// ---------------------------------------------------------------------------

test('unknown path returns 404 status but renders the leaderboard', async ({ page }) => {
  const response = await page.goto(at('/definitely-not-a-page'))
  expect(response.status()).toBe(404)
  await expect(page.locator('.ht-reference-row')).toBeVisible()
})

test('paths outside the site base are not served', async ({ request }) => {
  test.skip(!SITE_BASE, 'served at a domain root')
  const res = await request.get('/')
  expect(res.status()).toBe(404)
})
