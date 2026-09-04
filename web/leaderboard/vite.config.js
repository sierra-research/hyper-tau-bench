import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

import { SITE_BASE, SITE_URL } from './src/routes.js'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    // index.html carries absolute URLs (canonical, og:*) for crawlers that
    // never run JS; they are written as __SITE_URL__ so routes.js stays the
    // single place that knows where the site is served.
    {
      name: 'site-url',
      transformIndexHtml: (html) => html.replaceAll('__SITE_URL__', SITE_URL),
    },
  ],
  // Served under SITE_BASE (a GitHub Pages project path, or '' at a domain root).
  base: `${SITE_BASE}/`,
  build: {
    outDir: 'dist',
  },
})
