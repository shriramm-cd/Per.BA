import React, { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { HelpCircle, X, Compass, Keyboard, Terminal, CheckCircle2 } from 'lucide-react';

export default function FloatingHelp() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="fixed bottom-6 right-6 z-40">
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9, y: 15 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: 15 }}
            className="absolute bottom-16 right-0 w-80 overflow-hidden rounded-xl border border-slate-800 bg-slate-900 shadow-2xl"
          >
            {/* Header */}
            <div className="flex items-center justify-between border-bottom border-slate-850 bg-slate-950 px-4 py-3">
              <div className="flex items-center space-x-2 text-indigo-400 font-semibold text-sm">
                <HelpCircle size={16} />
                <span>Quick Assistant Guide</span>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-colors"
              >
                <X size={14} />
              </button>
            </div>

            {/* Content */}
            <div className="max-h-96 overflow-y-auto p-4 space-y-4 text-xs leading-relaxed text-slate-400">
              {/* Step Flow */}
              <div>
                <h4 className="flex items-center font-bold text-slate-200 uppercase tracking-wider mb-2">
                  <Compass className="mr-1 text-indigo-400" size={14} />
                  Operational Pipeline Flow
                </h4>
                <ul className="space-y-2">
                  <li className="flex items-start">
                    <span className="mr-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-slate-800 text-[10px] text-slate-300 font-bold">1</span>
                    <span><strong>Choose Source:</strong> Connect Jira, SharePoint, Confluence, GDrive, or Drag Folder.</span>
                  </li>
                  <li className="flex items-start">
                    <span className="mr-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-slate-800 text-[10px] text-slate-300 font-bold">2</span>
                    <span><strong>AI Extraction:</strong> Watch Docling parse files into structured requirement contexts.</span>
                  </li>
                  <li className="flex items-start">
                    <span className="mr-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-slate-800 text-[10px] text-slate-300 font-bold">3</span>
                    <span><strong>Multi-Agent Graph:</strong> Agents construct epics, planner dependencies, and user stories.</span>
                  </li>
                  <li className="flex items-start">
                    <span className="mr-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-slate-800 text-[10px] text-slate-300 font-bold">4</span>
                    <span><strong>BA Workbench:</strong> Review, refine single stories with feedback, and export to Excel/Jira/PDF.</span>
                  </li>
                </ul>
              </div>

              {/* Keyboard Shortcuts */}
              <div className="border-t border-slate-850 pt-3">
                <h4 className="flex items-center font-bold text-slate-200 uppercase tracking-wider mb-2">
                  <Keyboard className="mr-1 text-indigo-400" size={14} />
                  Keyboard Shortcuts
                </h4>
                <div className="space-y-1.5">
                  <div className="flex items-center justify-between">
                    <span>Toggle Command Palette</span>
                    <kbd className="rounded border border-slate-700 bg-slate-800 px-1 py-0.5 text-[9px] text-slate-300 font-mono">Ctrl + K</kbd>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Close Active Drawers/Modals</span>
                    <kbd className="rounded border border-slate-700 bg-slate-800 px-1 py-0.5 text-[9px] text-slate-300 font-mono">Esc</kbd>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Toggle Sidebar Collapse</span>
                    <kbd className="rounded border border-slate-700 bg-slate-800 px-1 py-0.5 text-[9px] text-slate-300 font-mono">[</kbd>
                  </div>
                </div>
              </div>

              {/* Integration Notes */}
              <div className="border-t border-slate-850 pt-3">
                <h4 className="flex items-center font-bold text-slate-200 uppercase tracking-wider mb-2">
                  <Terminal className="mr-1 text-indigo-400" size={14} />
                  Backend Connection State
                </h4>
                <div className="flex items-center space-x-1.5 text-[11px] text-emerald-400">
                  <CheckCircle2 size={12} />
                  <span>Configured defaults connect to <code>http://localhost:8000</code>.</span>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex h-12 w-12 items-center justify-center rounded-full bg-indigo-650 text-white shadow-lg hover:bg-indigo-600 hover:scale-105 active:scale-95 transition-all"
        title="Open Guide"
      >
        <HelpCircle size={24} />
      </button>
    </div>
  );
}
