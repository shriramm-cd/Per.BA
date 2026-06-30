import React, { useState, useEffect, useRef } from 'react';
import { useApp } from '../../context/AppContext';
import { Search, Compass, History, Settings, FileText, BarChart3, AlertCircle } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';

export default function CommandPalette() {
  const { currentPage, setCurrentPage, projects } = useApp();
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef(null);

  // Monitor keyboard combination Ctrl + K
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.ctrlKey && (e.key === 'k' || e.key === 'K')) {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      } else if (e.key === 'Escape') {
        setIsOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Autofocus input when palette opens
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
      setSelectedIndex(0);
      setQuery('');
    }
  }, [isOpen]);

  const navItems = [
    { label: 'Go to Dashboard Workspace', page: 'dashboard', icon: Compass },
    { label: 'Go to History & Generations', page: 'history', icon: History },
    { label: 'Go to Analytics & Metrics', page: 'analytics', icon: BarChart3 },
    { label: 'Go to Ingested Documents', page: 'documents', icon: FileText },
    { label: 'Go to System Settings', page: 'settings', icon: Settings },
  ];

  // Filter commands and project titles
  const filteredNav = navItems.filter((item) =>
    item.label.toLowerCase().includes(query.toLowerCase())
  );

  const filteredProjects = projects.filter((p) =>
    p.name.toLowerCase().includes(query.toLowerCase())
  ).map((p) => ({
    label: `Open Project: ${p.name}`,
    action: () => {
      setCurrentPage('dashboard');
      // Set this project as active if desired (we will link dashboard to projects)
      localStorage.setItem('ba_active_job_id', p.id);
      window.dispatchEvent(new Event('storage_active_job'));
    },
    icon: FileText
  }));

  const allItems = [
    ...filteredNav.map((item) => ({
      label: item.label,
      action: () => setCurrentPage(item.page),
      icon: item.icon
    })),
    ...filteredProjects
  ];

  // Handle arrow key selections
  const handleKeyDown = (e) => {
    if (!isOpen) return;
    
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % allItems.length);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + allItems.length) % allItems.length);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (allItems[selectedIndex]) {
        allItems[selectedIndex].action();
        setIsOpen(false);
      }
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center p-4 pt-[15vh]">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setIsOpen(false)}
            className="absolute inset-0 bg-slate-950/70 backdrop-blur-xs"
          />

          {/* Dialog Container */}
          <motion.div
            initial={{ opacity: 0, y: -20, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20, scale: 0.97 }}
            className="relative z-10 w-full max-w-xl overflow-hidden rounded-xl border border-slate-800 bg-slate-900 shadow-2xl"
            onKeyDown={handleKeyDown}
          >
            {/* Search Input */}
            <div className="relative flex items-center border-b border-slate-800 px-4 py-3">
              <Search className="text-slate-400 mr-3" size={20} />
              <input
                ref={inputRef}
                type="text"
                className="w-full bg-transparent text-sm text-slate-100 placeholder-slate-500 outline-none border-none ring-0 focus:outline-none focus:ring-0 focus:border-none focus:placeholder-slate-600"
                placeholder="Search workspaces, pages, commands... (Esc to close)"
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setSelectedIndex(0);
                }}
              />
              <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400 font-mono">ESC</span>
            </div>

            {/* Navigation Lists */}
            <div className="max-h-[350px] overflow-y-auto p-2">
              {allItems.length > 0 ? (
                <div className="space-y-0.5">
                  {allItems.map((item, idx) => {
                    const Icon = item.icon;
                    const isSelected = idx === selectedIndex;
                    return (
                      <button
                        key={idx}
                        onClick={() => {
                          item.action();
                          setIsOpen(false);
                        }}
                        className={`flex w-full items-center justify-between rounded-lg px-3 py-2.5 text-left text-xs transition-colors ${
                          isSelected
                            ? 'bg-indigo-650 text-white font-medium'
                            : 'text-slate-450 hover:bg-slate-800/60 hover:text-slate-200'
                        }`}
                      >
                        <div className="flex items-center space-x-2.5">
                          <Icon size={16} className={isSelected ? 'text-white' : 'text-slate-500'} />
                          <span>{item.label}</span>
                        </div>
                        {isSelected && (
                          <span className="text-[10px] font-semibold text-indigo-200 font-mono">↵ Enter</span>
                        )}
                      </button>
                    );
                  })}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-8 text-slate-500">
                  <AlertCircle size={24} className="mb-2" />
                  <span className="text-xs">No matching results found.</span>
                </div>
              )}
            </div>

            {/* Footer tips */}
            <div className="border-t border-slate-850 bg-slate-950 px-4 py-2 flex items-center justify-between text-[10px] text-slate-500">
              <div className="flex items-center space-x-4">
                <span>Use arrows <kbd className="font-mono">↓</kbd> <kbd className="font-mono">↑</kbd> to navigate</span>
                <span>Press <kbd className="font-mono">↵</kbd> to select</span>
              </div>
              <span>Command Bar</span>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
