#!/usr/bin/env node
// web/leaderboard/server.mjs — the built site, with a store of builds that a run lands.
//
// Serves dist/ under SITE_BASE (default /hyper-tau: the path Strata's gateway proxies to
// its `hyper-tau` service) with the single-page fallback for /trajectories and the other
// routes, and keeps a data directory of build trajectories that overlays the shipped
// public/build-trajectories/: a PUT of <SITE_BASE>/build-trajectories/<slot> with
// {row, trajectory, kit} (the three files scripts/recording-to-trajectory.py writes for a
// run) stores rel<slot>.json and rel<slot>.kit.json and adds the row to the manifest, so
// the visualizer lists the build beside the board's own, at /trajectories?slot=<slot>.
//
// No authentication: the server sits on a private network behind the gateway (Strata's
// compose files and chart), or on 127.0.0.1 in dev; the gateway guards the write.
//
//   PORT=8001 SITE_BASE=/hyper-tau DATA_DIR=/data node server.mjs

import { createServer } from 'node:http'
import { existsSync, mkdirSync, readFileSync, renameSync, statSync, writeFileSync } from 'node:fs'
import { dirname, extname, join, normalize, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const HERE = dirname(fileURLToPath(import.meta.url))
const DIST = resolve(HERE, 'dist')
const DATA = resolve(process.env.DATA_DIR || join(HERE, 'data'))
const PORT = Number(process.env.PORT || 8001)
const BASE = (process.env.SITE_BASE ?? '/hyper-tau').replace(/\/+$/, '')
const MAX_BODY = 64 * 1024 * 1024
const SLOT = /^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$/

const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.svg': 'image/svg+xml', '.ico': 'image/x-icon',
  '.woff2': 'font/woff2', '.woff': 'font/woff', '.txt': 'text/plain; charset=utf-8', '.xml': 'application/xml', '.map': 'application/json',
}

mkdirSync(DATA, { recursive: true })

const shippedManifest = () => JSON.parse(readFileSync(join(DIST, 'build-trajectories', 'manifest.json'), 'utf8'))
const manifestPath = join(DATA, 'manifest.json')
/** The manifest the site reads: the shipped one plus every build landed here. */
function manifest() {
  return existsSync(manifestPath) ? JSON.parse(readFileSync(manifestPath, 'utf8')) : shippedManifest()
}
function writeJson(path, value) {
  const tmp = `${path}.${process.pid}.tmp`
  writeFileSync(tmp, JSON.stringify(value))
  renameSync(tmp, path)
}

const send = (res, status, body, type = 'application/json') => {
  const text = typeof body === 'string' || Buffer.isBuffer(body) ? body : JSON.stringify(body)
  res.writeHead(status, { 'content-type': type, 'content-length': Buffer.byteLength(text), 'cache-control': 'no-cache' })
  res.end(text)
}

function readBody(req) {
  return new Promise((done, fail) => {
    const chunks = []
    let size = 0
    req.on('data', (c) => {
      size += c.length
      if (size > MAX_BODY) {
        fail(new Error(`body over ${MAX_BODY} bytes`))
        req.destroy()
        return
      }
      chunks.push(c)
    })
    req.on('end', () => done(Buffer.concat(chunks)))
    req.on('error', fail)
  })
}

/** PUT <base>/build-trajectories/<slot>: {row, trajectory, kit} → the files and the manifest row. */
async function putBuild(req, res, slot) {
  if (!SLOT.test(slot)) return send(res, 400, { error: 'bad_slot', reason: 'a slot is letters, digits, dots, dashes and underscores, at most 81 characters' })
  let body
  try {
    body = JSON.parse((await readBody(req)).toString('utf8'))
  } catch (err) {
    return send(res, 400, { error: 'bad_body', reason: String(err.message || err) })
  }
  const { row, trajectory, kit } = body ?? {}
  if (!row || typeof row !== 'object' || !trajectory || typeof trajectory !== 'object') {
    return send(res, 400, { error: 'bad_body', reason: 'the body is {row, trajectory, kit}: the manifest row, the trajectory file and the kit file the converter wrote' })
  }
  const entry = { ...row, slot, file: `rel${slot}.json` }
  writeJson(join(DATA, `rel${slot}.json`), { ...trajectory, slot })
  if (kit && typeof kit === 'object') writeJson(join(DATA, `rel${slot}.kit.json`), { ...kit, slot })
  const m = manifest()
  m.tasks = [...(m.tasks ?? []).filter((t) => t.slot !== slot), entry]
  writeJson(manifestPath, m)
  send(res, 200, { slot, url: `${BASE}/trajectories?slot=${encodeURIComponent(slot)}`, builds: m.tasks.length })
}

/** A file under dist/ (or, for build-trajectories, the data directory first); null when there is none. */
function fileFor(path) {
  const clean = normalize(path).replace(/^(\.\.(\/|\\|$))+/, '')
  if (clean.includes('..')) return null
  if (clean.startsWith('/build-trajectories/')) {
    const name = clean.slice('/build-trajectories/'.length)
    if (name === 'manifest.json') return { json: manifest() }
    const landed = join(DATA, name)
    if (existsSync(landed) && statSync(landed).isFile()) return { file: landed }
  }
  const shipped = join(DIST, clean)
  if (existsSync(shipped) && statSync(shipped).isFile()) return { file: shipped }
  return null
}

const server = createServer(async (req, res) => {
  const url = new URL(req.url, 'http://placeholder')
  let path = url.pathname
  if (path === '/health' || path === `${BASE}/health`) return send(res, 200, { ok: true, base: BASE, builds: manifest().tasks?.length ?? 0 })
  if (BASE && path !== BASE && !path.startsWith(`${BASE}/`)) return send(res, 404, { error: 'not_found', reason: `the site is served under ${BASE}` })
  path = path.slice(BASE.length) || '/'
  if (req.method === 'PUT' && path.startsWith('/build-trajectories/')) {
    try {
      return await putBuild(req, res, path.slice('/build-trajectories/'.length))
    } catch (err) {
      return send(res, 500, { error: 'write_failed', reason: String(err.message || err) })
    }
  }
  if (req.method !== 'GET' && req.method !== 'HEAD') return send(res, 405, { error: 'method_not_allowed' })
  const hit = fileFor(path === '/' ? '/index.html' : path)
  if (hit?.json) return send(res, 200, hit.json)
  // A route of the single-page app (no extension, no file): the page itself.
  const file = hit?.file ?? (extname(path) === '' ? join(DIST, 'index.html') : null)
  if (!file) return send(res, 404, { error: 'not_found' })
  const body = readFileSync(file)
  const type = MIME[extname(file).toLowerCase()] ?? 'application/octet-stream'
  res.writeHead(200, { 'content-type': type, 'content-length': body.length, 'cache-control': file.endsWith('index.html') || file.endsWith('.json') ? 'no-cache' : 'public, max-age=3600' })
  res.end(req.method === 'HEAD' ? undefined : body)
})

server.listen(PORT, '0.0.0.0', () => {
  console.log(`hyper-tau site on :${PORT} under ${BASE || '/'} (dist ${DIST}, builds in ${DATA}: ${manifest().tasks?.length ?? 0})`)
})
