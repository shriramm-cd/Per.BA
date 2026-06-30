import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { Save, Key, Server, Bell, Moon, Sun, Download, Trash2, CheckCircle2 } from 'lucide-react';

export default function Settings() {
  const { theme, toggleTheme, addNotification } = useApp();

  const [apiKey, setApiKey] = useState(() => localStorage.getItem('ba_api_key') || 'ba-accelerator-secure-api-key-12345');
  const [apiUrl, setApiUrl] = useState(() => localStorage.getItem('ba_api_url') || 'http://localhost:8000');
  const [exportFormat, setExportFormat] = useState(() => localStorage.getItem('ba_export_format') || 'EXCEL');
  const [notifications, setNotifications] = useState(() => localStorage.getItem('ba_notifications') !== 'false');
  const [maxRetries, setMaxRetries] = useState(() => parseInt(localStorage.getItem('ba_max_retries') || '3'));
  const [saved, setSaved] = useState(false);

  const handleSave = (e) => {
    e.preventDefault();
    localStorage.setItem('ba_api_key', apiKey);
    localStorage.setItem('ba_api_url', apiUrl);
    localStorage.setItem('ba_export_format', exportFormat);
    localStorage.setItem('ba_notifications', notifications.toString());
    localStorage.setItem('ba_max_retries', maxRetries.toString());

    setSaved(true);
    addNotification('Settings saved successfully.', 'success');
    setTimeout(() => setSaved(false), 2000);
  };

  const handleClearData = () => {
    if (window.confirm('This will clear all project history and documents from local storage. Are you sure?')) {
      localStorage.removeItem('ba_projects');
      localStorage.removeItem('ba_docs');
      addNotification('Local workspace data cleared.', 'success');
      window.location.reload();
    }
  };

  const sections = [
    {
      title: 'Backend Connection',
      icon: Server,
      content: (
        <div className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">API Server URL</label>
            <input
              type="url"
              value={apiUrl}
              onChange={e => setApiUrl(e.target.value)}
              className="w-full rounded-lg border border-slate-800 bg-slate-950 p-3 text-xs text-slate-100 placeholder-slate-600 outline-none focus:border-indigo-600"
              placeholder="http://localhost:8000"
            />
            <p className="text-[10px] text-slate-600">Default: http://localhost:8000 — Update to deployed server URL when in production.</p>
          </div>
          <div className="space-y-1.5">
            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center space-x-1">
              <Key size={11} />
              <span>Backend API Key (X-API-KEY Header)</span>
            </label>
            <input
              type="password"
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              className="w-full rounded-lg border border-slate-800 bg-slate-950 p-3 text-xs text-slate-100 placeholder-slate-600 outline-none focus:border-indigo-600 font-mono"
              placeholder="ba-accelerator-secure-api-key-12345"
            />
            <p className="text-[10px] text-slate-600">This key is sent with every API request in the <code className="text-indigo-400">X-API-KEY</code> header.</p>
          </div>
          <div className="space-y-1.5">
            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Pipeline Max Retry Attempts</label>
            <select
              value={maxRetries}
              onChange={e => setMaxRetries(parseInt(e.target.value))}
              className="w-full rounded-lg border border-slate-800 bg-slate-950 p-3 text-xs text-slate-200 outline-none focus:border-indigo-600"
            >
              {[1, 2, 3, 4, 5].map(n => (
                <option key={n} value={n}>{n} {n === 3 ? '(Default)' : ''}</option>
              ))}
            </select>
            <p className="text-[10px] text-slate-600">Number of automatic confidence-threshold retries allowed per pipeline run.</p>
          </div>
        </div>
      )
    },
    {
      title: 'Appearance & Theme',
      icon: theme === 'dark' ? Moon : Sun,
      content: (
        <div className="flex items-center justify-between rounded-lg border border-slate-900 bg-slate-950/40 p-4">
          <div>
            <p className="text-xs font-bold text-slate-200">Interface Color Theme</p>
            <p className="text-[10px] text-slate-500 mt-0.5">Switch between Dark and Light modes for the entire workspace.</p>
          </div>
          <button
            type="button"
            onClick={toggleTheme}
            className={`relative flex h-7 w-14 items-center rounded-full transition-colors ${theme === 'dark' ? 'bg-indigo-600' : 'bg-slate-600'}`}
          >
            <span className={`absolute h-5 w-5 rounded-full bg-white shadow-md transition-transform ${theme === 'dark' ? 'translate-x-7.5' : 'translate-x-1'}`} />
          </button>
        </div>
      )
    },
    {
      title: 'Notifications',
      icon: Bell,
      content: (
        <div className="flex items-center justify-between rounded-lg border border-slate-900 bg-slate-950/40 p-4">
          <div>
            <p className="text-xs font-bold text-slate-200">Toast Notifications</p>
            <p className="text-[10px] text-slate-500 mt-0.5">Show status toasts for pipeline events, exports, and approvals.</p>
          </div>
          <button
            type="button"
            onClick={() => setNotifications(prev => !prev)}
            className={`relative flex h-7 w-14 items-center rounded-full transition-colors ${notifications ? 'bg-indigo-600' : 'bg-slate-700'}`}
          >
            <span className={`absolute h-5 w-5 rounded-full bg-white shadow-md transition-transform ${notifications ? 'translate-x-7.5' : 'translate-x-1'}`} />
          </button>
        </div>
      )
    },
    {
      title: 'Export Preferences',
      icon: Download,
      content: (
        <div className="space-y-1.5">
          <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Default Export Format</label>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {['EXCEL', 'PDF', 'JSON', 'JIRA'].map(fmt => (
              <button
                key={fmt}
                type="button"
                onClick={() => setExportFormat(fmt)}
                className={`rounded-lg border p-3 text-xs font-bold transition-all ${
                  exportFormat === fmt
                    ? 'border-indigo-500 bg-indigo-500/10 text-indigo-400'
                    : 'border-slate-800 bg-slate-900/40 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                }`}
              >
                {fmt}
              </button>
            ))}
          </div>
          <p className="text-[10px] text-slate-600">Selected as the default when clicking "Export Backlog" from the story board.</p>
        </div>
      )
    },
  ];

  return (
    <div className="space-y-6 max-w-3xl text-left">
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight">System Settings</h2>
        <p className="text-xs text-slate-400 mt-1">Configure backend connections, display preferences, and default export behaviors.</p>
      </div>

      <form onSubmit={handleSave} className="space-y-4">
        {sections.map((section, i) => {
          const Icon = section.icon;
          return (
            <div key={i} className="rounded-xl border border-slate-900 bg-slate-900/25 overflow-hidden">
              {/* Section Header */}
              <div className="flex items-center space-x-2.5 border-b border-slate-900 bg-slate-950/50 px-5 py-3.5">
                <Icon size={15} className="text-indigo-400" />
                <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">{section.title}</h3>
              </div>
              {/* Section Content */}
              <div className="p-5">
                {section.content}
              </div>
            </div>
          );
        })}

        {/* Save Button */}
        <div className="flex items-center justify-between pt-2">
          <button
            type="button"
            onClick={handleClearData}
            className="flex items-center space-x-1.5 rounded-lg border border-red-900/40 bg-red-950/20 px-4 py-2 text-xs font-semibold text-red-400 hover:bg-red-950/40 transition-colors"
          >
            <Trash2 size={13} />
            <span>Clear Local Workspace Data</span>
          </button>

          <button
            type="submit"
            className="flex items-center space-x-2 rounded-lg bg-indigo-650 px-5 py-2.5 text-xs font-bold text-white shadow-lg hover:bg-indigo-600 active:scale-98 transition-all"
          >
            {saved ? (
              <>
                <CheckCircle2 size={14} className="text-emerald-400" />
                <span>Saved!</span>
              </>
            ) : (
              <>
                <Save size={14} />
                <span>Save Settings</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
