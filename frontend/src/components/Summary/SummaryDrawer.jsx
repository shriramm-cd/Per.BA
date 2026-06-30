import React, { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { X, Sparkles, FileText, BarChart3, Copy, Check, Info } from 'lucide-react';
import { useApp } from '../../context/AppContext';

export default function SummaryDrawer({ isOpen, summary, onClose }) {
  const { addNotification } = useApp();
  const [copied, setCopied] = useState(false);

  if (!isOpen || !summary) return null;

  const handleCopy = () => {
    const textToCopy = `
Project Executive Summary:
-------------------------
Business Goals: ${summary.businessGoals}
Total Generated Stories: ${summary.totalRequirements || 0}
High Priority: ${summary.highPriorityCount || 0} | Medium Priority: ${summary.mediumPriorityCount || 0} | Low Priority: ${summary.lowPriorityCount || 0}

Executive Summary:
${summary.executiveSummary}
    `.trim();

    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    addNotification('Summary text copied to clipboard.', 'success');
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 overflow-hidden">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="absolute inset-0 bg-slate-950/60 backdrop-blur-xs"
        />

        {/* Panel Container */}
        <div className="absolute inset-y-0 right-0 max-w-full flex pl-10">
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 220 }}
            className="w-screen max-w-lg bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col justify-between"
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-slate-850 bg-slate-950 px-6 py-5">
              <div className="flex items-center space-x-2 text-indigo-400 font-bold text-sm">
                <Sparkles size={16} className="animate-pulse" />
                <span>AI Generated Executive Summary</span>
              </div>
              <div className="flex items-center space-x-3">
                <button
                  onClick={handleCopy}
                  className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-colors"
                  title="Copy Summary"
                >
                  {copied ? <Check size={16} className="text-emerald-400" /> : <Copy size={16} />}
                </button>
                <button
                  onClick={onClose}
                  className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-colors"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            {/* Body */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6 text-left">
              {/* Core metrics grid */}
              <div className="grid grid-cols-2 gap-4">
                <div className="rounded-xl border border-slate-850 bg-slate-950/40 p-4">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Total Requirements</span>
                  <div className="text-xl font-bold text-slate-200 mt-1">{summary.totalRequirements || 0}</div>
                </div>
                <div className="rounded-xl border border-slate-850 bg-slate-950/40 p-4">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Modules Identified</span>
                  <div className="text-xl font-bold text-slate-200 mt-1">{(summary.modules && summary.modules.length) || 0}</div>
                </div>
              </div>

              {/* Functional vs non functional */}
              <div className="rounded-xl border border-slate-850 bg-slate-950/20 p-4 space-y-3">
                <h4 className="text-[10px] font-bold text-slate-450 uppercase tracking-wider flex items-center">
                  <BarChart3 className="mr-1.5 text-indigo-400" size={14} />
                  Functional Distributions
                </h4>
                <div className="grid grid-cols-3 gap-2 text-center text-xs">
                  <div className="rounded-lg bg-slate-950/80 p-2">
                    <span className="text-[9px] text-slate-500 font-semibold uppercase">High</span>
                    <div className="text-sm font-bold text-red-400 mt-0.5">{summary.highPriorityCount || 0}</div>
                  </div>
                  <div className="rounded-lg bg-slate-950/80 p-2">
                    <span className="text-[9px] text-slate-500 font-semibold uppercase">Medium</span>
                    <div className="text-sm font-bold text-orange-400 mt-0.5">{summary.mediumPriorityCount || 0}</div>
                  </div>
                  <div className="rounded-lg bg-slate-950/80 p-2">
                    <span className="text-[9px] text-slate-500 font-semibold uppercase">Low</span>
                    <div className="text-sm font-bold text-slate-400 mt-0.5">{summary.lowPriorityCount || 0}</div>
                  </div>
                </div>
              </div>

              {/* Modules list */}
              {summary.modules && summary.modules.length > 0 && (
                <div className="space-y-2">
                  <span className="text-[10px] font-bold text-slate-450 uppercase tracking-wider">Identified Modules</span>
                  <div className="flex flex-wrap gap-1.5">
                    {summary.modules.map((mod, idx) => (
                      <span key={idx} className="rounded-md bg-indigo-500/10 border border-indigo-500/15 px-2 py-0.8 text-[10px] text-indigo-400 font-semibold">
                        {mod}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Business goals */}
              <div className="space-y-2">
                <span className="text-[10px] font-bold text-slate-450 uppercase tracking-wider flex items-center">
                  <FileText className="mr-1.5 text-indigo-400" size={14} />
                  Core Business Goals
                </span>
                <p className="text-xs leading-relaxed text-slate-350 bg-slate-950/40 border border-slate-850 p-3 rounded-lg">
                  {summary.businessGoals}
                </p>
              </div>

              {/* AI Generated Text Box (ChatGPT Style) */}
              <div className="space-y-3 pt-3 border-t border-slate-850">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">AI Executive Synthesis</span>
                <div className="relative rounded-lg border border-slate-800 bg-slate-950/80 p-4 font-serif text-[13px] leading-relaxed text-slate-300 space-y-3">
                  <div className="absolute top-3.5 right-3.5 text-indigo-500/20">
                    <Sparkles size={24} />
                  </div>
                  <p>{summary.executiveSummary}</p>
                  <p className="text-[11px] text-slate-500 font-sans italic pt-2">
                    * This synthesis is compiled based on requirement structural tags and epic dependency matrices.
                  </p>
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="border-t border-slate-850 bg-slate-950/40 px-6 py-4 flex items-center justify-between text-[10px] text-slate-500">
              <span className="flex items-center">
                <Info size={11} className="mr-1" />
                Data represents active workspace stories
              </span>
              <span>ChatGPT-v4 Summary</span>
            </div>
          </motion.div>
        </div>
      </div>
    </AnimatePresence>
  );
}
