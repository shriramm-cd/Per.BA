import React, { useState } from 'react';
import { useApp } from '../../context/AppContext';
import { Bell, Search, Info, CheckCircle2, AlertTriangle, X, Terminal } from 'lucide-react';

export default function Navbar() {
  const { currentPage, projects, activeJobId, notifications, removeNotification } = useApp();
  const [showNotifications, setShowNotifications] = useState(false);

  // Determine current context label for breadcrumb
  let breadcrumbLabel = 'Workspace';
  if (currentPage === 'dashboard') {
    const activeProjId = activeJobId || localStorage.getItem('ba_active_job_id');
    const activeProj = projects.find(p => p.id === activeProjId);
    breadcrumbLabel = activeProj ? activeProj.name : 'New Story Workspace';
  } else if (currentPage === 'history') {
    breadcrumbLabel = 'Previous Jobs';
  } else if (currentPage === 'documents') {
    breadcrumbLabel = 'Ingested Documents';
  } else if (currentPage === 'analytics') {
    breadcrumbLabel = 'Analytics & Insights';
  } else if (currentPage === 'settings') {
    breadcrumbLabel = 'System Settings';
  }

  // Handle opening command palette via manual click
  const triggerCommandPalette = () => {
    // Dispatch a virtual keyboard event for Ctrl + K
    const event = new KeyboardEvent('keydown', {
      key: 'k',
      code: 'KeyK',
      ctrlKey: true,
      bubbles: true
    });
    window.dispatchEvent(event);
  };

  return (
    <header className="sticky top-0 z-20 flex h-16 w-full items-center justify-between border-b border-slate-900 bg-slate-950/80 backdrop-blur-md px-6 shadow-xs">
      {/* Breadcrumb Info */}
      <div className="flex items-center space-x-2 text-xs font-semibold">
        <span className="text-slate-500 select-none">Platform</span>
        <span className="text-slate-700 select-none">/</span>
        <span className="text-slate-200 tracking-wide truncate max-w-[200px] sm:max-w-[400px]">
          {breadcrumbLabel}
        </span>
      </div>

      {/* Center/Right controls */}
      <div className="flex items-center space-x-4">
        {/* Mock Search bar triggering Command Palette */}
        <button
          onClick={triggerCommandPalette}
          className="hidden md:flex items-center space-x-2.5 rounded-lg border border-slate-900 bg-slate-900/60 hover:bg-slate-900/90 transition-colors px-3 py-1.5 text-left text-xs text-slate-500 w-64 select-none"
        >
          <Search size={14} className="text-slate-400" />
          <span className="flex-1">Search or type command...</span>
          <kbd className="rounded border border-slate-800 bg-slate-950 px-1 py-0.2 text-[9px] font-mono">⌘K</kbd>
        </button>

        {/* Notification Icon */}
        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative rounded-lg p-2 text-slate-400 hover:bg-slate-900 hover:text-slate-250 transition-colors"
            title="System logs & status notifications"
          >
            <Bell size={18} />
            {notifications.length > 0 && (
              <span className="absolute top-1.5 right-1.5 flex h-2 w-2 rounded-full bg-indigo-500 ring-2 ring-slate-950" />
            )}
          </button>

          {/* Notifications Dropdown Panel */}
          {showNotifications && (
            <div className="absolute right-0 mt-2 w-72 rounded-xl border border-slate-800 bg-slate-900 shadow-2xl p-3 z-50">
              <div className="flex items-center justify-between border-b border-slate-850 pb-2 mb-2">
                <span className="text-xs font-bold text-slate-200">Recent Status Updates</span>
                {notifications.length > 0 && (
                  <span className="rounded bg-indigo-500/10 text-indigo-400 text-[10px] font-semibold px-1.5 py-0.5">
                    {notifications.length} Info toast(s)
                  </span>
                )}
              </div>

              {notifications.length > 0 ? (
                <div className="max-h-60 overflow-y-auto space-y-2">
                  {notifications.map(n => {
                    const AlertIcon = n.type === 'success' ? CheckCircle2 : n.type === 'error' ? AlertTriangle : Info;
                    const iconColor = n.type === 'success' ? 'text-emerald-400' : n.type === 'error' ? 'text-red-400' : 'text-indigo-400';
                    return (
                      <div key={n.id} className="flex items-start justify-between rounded-lg bg-slate-950/60 border border-slate-900 p-2 text-[11px] leading-relaxed text-slate-450">
                        <div className="flex items-start space-x-1.5">
                          <AlertIcon size={14} className={`${iconColor} mt-0.5 shrink-0`} />
                          <span className="truncate max-w-[190px]">{n.message}</span>
                        </div>
                        <button
                          onClick={() => removeNotification(n.id)}
                          className="text-slate-600 hover:text-slate-300 ml-1.5"
                        >
                          <X size={10} />
                        </button>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="py-6 text-center text-[11px] text-slate-500 flex flex-col items-center">
                  <Terminal size={18} className="text-slate-600 mb-1" />
                  <span>No active warnings. Connected to API.</span>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Floating System Toasts Container (Fixed stack) */}
      <div className="fixed bottom-6 left-6 z-50 flex flex-col space-y-2 max-w-sm w-full pointer-events-none">
        {notifications.map(toast => {
          const AlertIcon = toast.type === 'success' ? CheckCircle2 : toast.type === 'error' ? AlertTriangle : Info;
          const borderStyle = toast.type === 'success' ? 'border-emerald-500/20 bg-slate-900/90' : toast.type === 'error' ? 'border-red-500/20 bg-slate-900/90' : 'border-indigo-500/20 bg-slate-900/90';
          const iconColor = toast.type === 'success' ? 'text-emerald-400' : toast.type === 'error' ? 'text-red-400' : 'text-indigo-400';

          return (
            <div
              key={toast.id}
              className={`pointer-events-auto flex items-center justify-between rounded-lg border p-3.5 shadow-xl backdrop-blur-md transition-all duration-300 ${borderStyle}`}
            >
              <div className="flex items-center space-x-2.5">
                <AlertIcon size={16} className={iconColor} />
                <span className="text-xs font-semibold text-slate-205">{toast.message}</span>
              </div>
              <button
                onClick={() => removeNotification(toast.id)}
                className="text-slate-500 hover:text-slate-350 ml-4 shrink-0"
              >
                <X size={14} />
              </button>
            </div>
          );
        })}
      </div>
    </header>
  );
}
