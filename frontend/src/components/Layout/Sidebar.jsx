import React, { useState, useEffect } from 'react';
import { useApp } from '../../context/AppContext';
import {
  Compass, History, FileText, BarChart3, Settings,
  Moon, Sun, ChevronLeft, ChevronRight, BrainCircuit
} from 'lucide-react';

export default function Sidebar({ onCollapse }) {
  const { currentPage, setCurrentPage, theme, toggleTheme } = useApp();
  const [isCollapsed, setIsCollapsed] = useState(false);

  const toggle = (next) => {
    setIsCollapsed(next);
    onCollapse?.(next);
  };

  // Keyboard shortcut '[' — only outside inputs
  useEffect(() => {
    const handler = (e) => {
      if (e.key === '[' && e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
        toggle(!isCollapsed);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isCollapsed]);

  const navItems = [
    { label: 'Dashboard',    page: 'dashboard', icon: Compass    },
    { label: 'Previous Jobs', page: 'history',  icon: History    },
    { label: 'Documents',    page: 'documents', icon: FileText   },
    { label: 'Analytics',   page: 'analytics', icon: BarChart3  },
    { label: 'Settings',    page: 'settings',  icon: Settings   },
  ];

  return (
    <aside
      className="fixed inset-y-0 left-0 z-30 flex flex-col justify-between border-r border-slate-900 bg-slate-950 transition-all duration-300"
      style={{ width: isCollapsed ? '4rem' : '16rem' }}
    >
      {/* ── Top ─────────────────────────── */}
      <div className="flex flex-col overflow-hidden">
        {/* Brand */}
        <div className="flex items-center justify-between border-b border-slate-900 px-4 py-5">
          <div className="flex items-center space-x-2.5 overflow-hidden">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-indigo-600 text-white">
              <BrainCircuit size={20} className="animate-pulse" />
            </div>
            {!isCollapsed && (
              <span className="whitespace-nowrap text-sm font-bold tracking-tight text-white select-none">
                BA Accelerator
              </span>
            )}
          </div>

          {/* Collapse button */}
          <button
            onClick={() => toggle(!isCollapsed)}
            className="hidden sm:flex rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-colors shrink-0"
            title="Toggle sidebar ( [ )"
          >
            {isCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </button>
        </div>

        {/* Nav */}
        <nav className="mt-4 space-y-0.5 px-2">
          {navItems.map(({ label, page, icon: Icon }) => {
            const active = currentPage === page;
            return (
              <button
                key={page}
                onClick={() => setCurrentPage(page)}
                title={label}
                className={`group flex w-full items-center rounded-lg p-3 text-xs font-semibold tracking-wide transition-all
                  ${isCollapsed ? 'justify-center' : 'space-x-3'}
                  ${active
                    ? 'bg-indigo-600 text-white shadow-lg'
                    : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200'}`}
              >
                <Icon
                  size={18}
                  className={active ? 'text-white' : 'text-slate-500 group-hover:text-slate-300'}
                />
                {!isCollapsed && <span>{label}</span>}
              </button>
            );
          })}
        </nav>
      </div>

      {/* ── Bottom ──────────────────────── */}
      <div className="flex flex-col gap-2 border-t border-slate-900 p-2">
        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} mode`}
          className={`flex w-full items-center rounded-lg p-2.5 text-xs text-slate-400 hover:bg-slate-900 hover:text-slate-200 transition-colors
            ${isCollapsed ? 'justify-center' : 'space-x-3'}`}
        >
          {theme === 'dark'
            ? <Sun  size={18} className="text-amber-400" />
            : <Moon size={18} className="text-indigo-400" />}
          {!isCollapsed && <span>{theme === 'dark' ? 'Light Mode' : 'Dark Mode'}</span>}
        </button>

        {/* Profile chip */}
        <div
          className={`flex items-center rounded-lg border border-slate-900 bg-slate-900/50 p-2.5
            ${isCollapsed ? 'justify-center' : 'space-x-3'}`}
        >
          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-800 text-[10px] font-bold text-slate-300 select-none">
            BA
          </div>
          {!isCollapsed && (
            <div className="flex flex-col overflow-hidden text-left">
              <span className="truncate text-[11px] font-bold text-slate-200 leading-none">Analyst Profile</span>
              <span className="truncate text-[9px] font-semibold text-slate-500 mt-1">Admin User</span>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
