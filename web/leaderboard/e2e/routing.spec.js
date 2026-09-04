// Routing + prerendering behavior tests. Run against the prerendered dist/
// served with GitHub Pages semantics (see playwright.config.js).
import { expect, test } from '@playwright/test'
import { REPO_URL } from '../src/routes.js'

// ---------------------------------------------------------------------------
// Direct loads: every route serves a real page with its own title and content.
// ---------------------------------------------------------------------------

test('direct load: homepage is the τ^τ-bench leaderboard', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveTitle(/hyper-tau-bench/)
  // Reference (human performance) row + the six baseline developer rows.
  await expect(page.locator('.ht-table tbody tr')).toHaveCount(7)
  await expect(page.locator('.ht-reference-row')).toBeVisible()
  // Overall column uses the shared score-bar treatment.
  await expect(page.locator('.ht-table .score-bar-fill')).toHaveCount(7)
})

test('direct load: build trajectories', async ({ page }) => {
  await page.goto('/trajectories')
  await expect(page).toHaveTitle(/Build Trajectories — τ\^τ-bench/)
  // Manifest loads and the first task's stream renders.
  await expect(page.locator('.bt-summary')).toBeVisible()
  await expect(page.locator('.bt-stream .bt-item').first()).toBeVisible()
})

test('trajectories: task picker switches tasks', async ({ page }) => {
  await page.goto('/trajectories')
  await expect(page.locator('.bt-summary')).toBeVisible()
  await page.locator('.bt-task-select').selectOption({ index: 1 })
  await expect(page.locator('.bt-slot-badge')).toHaveText(/Task 002/)
  await expect(page.locator('.bt-stream .bt-item').first()).toBeVisible()
})

test('trajectories: output kit tab shows the submitted workspace', async ({ page }) => {
  await page.goto('/trajectories')
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
  await page.goto('/')
  await page.getByRole('button', { name: 'Trajectories' }).click()
  await expect(page).toHaveURL(/\/trajectories/)
  await expect(page).toHaveTitle(/Build Trajectories — τ\^τ-bench/)

  await page.getByRole('button', { name: 'Leaderboard', exact: true }).click()
  await expect(page).toHaveURL(/\/(\?.*)?$/)
  await expect(page.locator('.ht-reference-row')).toBeVisible()
})

test('nav has a button back to the main τ-bench site', async ({ page }) => {
  await page.goto('/')
  const backLink = page.locator('.nav-taubench-btn')
  await expect(backLink).toBeVisible()
  await expect(backLink).toHaveAttribute('href', 'https://taubench.com')
})

test('nav and submission links point at the public repository', async ({ page }) => {
  await page.goto('/')
  const repoLink = page.locator('.nav-github-btn')
  await expect(repoLink).toBeVisible()
  await expect(repoLink).toHaveAttribute('href', REPO_URL)
  await expect(page.locator('.submissions-link.primary')).toHaveAttribute(
    'href',
    `${REPO_URL}#submitting-to-the-leaderboard`
  )
  await expect(page.locator('.submissions-link.secondary')).toHaveAttribute('href', `${REPO_URL}/pulls`)
})

test('human chip toggles the easter-egg tooltip', async ({ page }) => {
  await page.goto('/')
  const chip = page.locator('.ht-human-chip')
  await expect(chip).not.toHaveClass(/open/)
  await chip.click()
  await expect(chip).toHaveClass(/open/)
})

// ---------------------------------------------------------------------------
// Prerendered HTML: content and per-route meta exist without JavaScript.
// ---------------------------------------------------------------------------

test('prerendered homepage HTML contains leaderboard content and meta', async ({ request }) => {
  const res = await request.get('/')
  expect(res.status()).toBe(200)
  const html = await res.text()
  expect(html).toContain('<title>τ^τ-bench Leaderboard (hyper-tau-bench)</title>')
  expect(html).toContain('Human performance')
  expect(html).toContain('property="og:title"')
  expect(html).toContain('https://hyper.taubench.com/')
  expect(html).not.toContain('Loading leaderboard')
})

test('prerendered trajectories HTML contains content and meta', async ({ request }) => {
  const res = await request.get('/trajectories')
  expect(res.status()).toBe(200)
  const html = await res.text()
  expect(html).toContain('<title>Build Trajectories — τ^τ-bench</title>')
  expect(html).toContain('https://hyper.taubench.com/trajectories')
  expect(html).toContain('bt-stream')
  expect(html).not.toContain('Loading trajectories')
})

// ---------------------------------------------------------------------------
// Unknown paths: GitHub Pages serves 404.html, which boots the SPA.
// ---------------------------------------------------------------------------

test('unknown path returns 404 status but renders the leaderboard', async ({ page }) => {
  const response = await page.goto('/definitely-not-a-page')
  expect(response.status()).toBe(404)
  await expect(page.locator('.ht-reference-row')).toBeVisible()
})
