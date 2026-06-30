import React, { useState, useEffect } from 'react';
import { AppProvider, useApp } from './context/AppContext';
import { AnimatePresence, motion } from 'framer-motion';

// Layout
import Sidebar from './components/Layout/Sidebar';
import Navbar from './components/Layout/Navbar';

// Pages
import Landing from './pages/Landing';
import Dashboard from './pages/Dashboard';
import Analytics from './pages/Analytics';
import HistoryPage from './pages/History';
import Documents from './pages/Documents';
import Settings from './pages/Settings';

// Global overlays
import CommandPalette from './components/Common/CommandPalette';
import FloatingHelp from './components/Common/FloatingHelp';

/* ─────────────────────────────────────────
   AppShell — rendered inside AppProvider
───────────────────────────────────────── */
function AppShell() {
  const { currentPage } = useApp();

  // Track sidebar collapse for main content offset
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Listen for the '[' keypress that Sidebar uses to collapse
  useEffect(() => {
    const handler = (e) => {
      if (e.key === '[' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
        setSidebarCollapsed(prev => !prev);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  // Landing page: full-screen, no sidebar
  if (currentPage === 'landing') {
    return (
      <>
        <CommandPalette />
        <AnimatePresence mode="wait">
          <motion.div
            key="landing"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
          >
            <Landing />
          </motion.div>
        </AnimatePresence>
      </>
    );
  }

  const pageMap = {
    dashboard: <Dashboard />,
    analytics: <Analytics />,
    history:   <HistoryPage />,
    documents: <Documents />,
    settings:  <Settings />,
  };

  const PageContent = pageMap[currentPage] ?? <Dashboard />;

  return (
    <div className="flex min-h-screen bg-slate-950">
      {/* Global overlays */}
      <CommandPalette />

      {/* Sidebar — fixed, toggles width via its own state */}
      <Sidebar onCollapse={setSidebarCollapsed} />

      {/* Main content area — offset mirrors sidebar width */}
      <div
        className="flex flex-1 flex-col min-h-screen transition-all duration-300"
        style={{ marginLeft: sidebarCollapsed ? '4rem' : '16rem' }}
      >
        <Navbar />

        <main className="flex-1 overflow-y-auto p-6 lg:p-8">
          <AnimatePresence mode="wait">
            <motion.div
              key={currentPage}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.2 }}
            >
              {PageContent}
            </motion.div>
          </AnimatePresence>
        </main>
      </div>

      {/* Floating AI Assistant */}
      <FloatingHelp />
    </div>
  );
}

/* ─────────────────────────────────────────
   Root — wrap in context provider
───────────────────────────────────────── */
export default function App() {
  return (
    <AppProvider>
      <AppShell />
    </AppProvider>
  );
}
