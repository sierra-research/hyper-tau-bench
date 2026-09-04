import { useState, useEffect } from 'react'
import './App.css'
import { getViewFromPath, PAGE_META, REPO_URL, SITE_ORIGIN, VIEW_PATHS } from './routes'
import BuildTrajectories from './components/BuildTrajectories'
import HyperTau from './components/HyperTau'

// Update the document head to match the current view. The prerender step
// (scripts/prerender.mjs) snapshots the DOM after this runs, which is how
// each prerendered page gets its own title/description/canonical tags.
const setHeadContent = (selector, attr, value) => {
  const el = document.head.querySelector(selector)
  if (el) el.setAttribute(attr, value)
}

const applyPageMeta = (view) => {
  const meta = PAGE_META[view]
  if (!meta) return
  const url = `${SITE_ORIGIN}${VIEW_PATHS[view] || '/'}`
  document.title = meta.title
  setHeadContent('meta[name="description"]', 'content', meta.description)
  setHeadContent('link[rel="canonical"]', 'href', url)
  setHeadContent('meta[property="og:url"]', 'content', url)
  setHeadContent('meta[property="og:title"]', 'content', meta.title)
  setHeadContent('meta[property="og:description"]', 'content', meta.description)
  setHeadContent('meta[name="twitter:title"]', 'content', meta.title)
  setHeadContent('meta[name="twitter:description"]', 'content', meta.description)
}

function App() {

  const [currentView, setCurrentView] = useState(() => getViewFromPath(window.location.pathname))
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  // Handle navigation with URL updates
  const navigateTo = (view) => {
    setCurrentView(view)
    setMobileMenuOpen(false) // Close mobile menu when navigating
    const path = VIEW_PATHS[view]
    if (!path) return
    // Preserve existing query params when already on the target path (the
    // visualizer keeps its state in the query string).
    if (window.location.pathname !== path) {
      window.history.pushState(null, '', path)
    }
    // If the view didn't change, React won't re-render anything, so without
    // this a nav click on the current page would visibly do nothing.
    window.scrollTo(0, 0)
  }

  // Toggle mobile menu
  const toggleMobileMenu = () => {
    setMobileMenuOpen(!mobileMenuOpen)
  }

  // Keep the document head (title, description, canonical, og:*) in sync
  // with the current view.
  useEffect(() => {
    applyPageMeta(currentView)
  }, [currentView])

  // Listen for browser back/forward button clicks and handle mobile menu
  useEffect(() => {
    const handlePopState = () => {
      setCurrentView(getViewFromPath(window.location.pathname))
    }

    // Close mobile menu when clicking outside
    const handleClickOutside = (event) => {
      if (mobileMenuOpen && !event.target.closest('.nav-container')) {
        setMobileMenuOpen(false)
      }
    }

    // Listen to events
    window.addEventListener('popstate', handlePopState)
    document.addEventListener('click', handleClickOutside)

    return () => {
      window.removeEventListener('popstate', handlePopState)
      document.removeEventListener('click', handleClickOutside)
    }
  }, [mobileMenuOpen])

  return (
    <div className="App">
      {/* Navigation */}
      <nav className="navbar">
        <div className="nav-container">
          <div className="nav-logo">
            <div className="logo-main" onClick={() => navigateTo('hyper-tau')}>
              <span className="tau-symbol">τ<sup>τ</sup></span>
              <span className="bench-text">-bench</span>
            </div>
            <a href="https://sierra.ai" target="_blank" rel="noopener noreferrer" className="logo-attribution">
              <img src={`${import.meta.env.BASE_URL}sierra_logo.jpeg`} alt="Sierra" className="sierra-logo" />
              <span className="from-text">from Sierra</span>
            </a>
          </div>
          <button className="mobile-menu-toggle" onClick={toggleMobileMenu}>
            <span></span>
            <span></span>
            <span></span>
          </button>
          <div className={`nav-links ${mobileMenuOpen ? '' : 'mobile-hidden'}`}>
            <button onClick={() => navigateTo('hyper-tau')} className={`nav-link ${currentView === 'hyper-tau' ? 'active' : ''}`}>Leaderboard</button>
            <button onClick={() => navigateTo('trajectories')} className={`nav-link ${currentView === 'trajectories' ? 'active' : ''}`}>Trajectories</button>
            <a
              href={REPO_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="nav-github-btn"
              onClick={() => setMobileMenuOpen(false)}
            >
              GitHub ↗
            </a>
            <a href="https://taubench.com" className="nav-taubench-btn" onClick={() => setMobileMenuOpen(false)}>
              ← τ-bench.com
            </a>
          </div>
        </div>
      </nav>

      {/* Conditional Content Rendering */}
      <main className="page-content">
        {currentView === 'trajectories' ? <BuildTrajectories /> : <HyperTau />}
      </main>

      {/* Simple Footer */}
      <footer className="simple-footer">
        <div className="container">
          <p>
            Code, tasks, and submissions live in the{' '}
            <a href={REPO_URL} target="_blank" rel="noopener noreferrer" className="footer-email">
              τ^τ-bench repository
            </a>
            . For questions or feedback, contact{' '}
            <a href="mailto:research@sierra.ai" className="footer-email">
              research@sierra.ai
            </a>
          </p>
        </div>
      </footer>

    </div>
  )
}

export default App
