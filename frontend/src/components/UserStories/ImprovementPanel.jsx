import React, { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { X, MessageSquare, AlertCircle, Lightbulb } from 'lucide-react';

export default function ImprovementPanel({ isOpen, storyId, onClose, onSubmitFeedback }) {
  const [feedback, setFeedback] = useState('');

  const suggestions = [
    'Need more detailed acceptance criteria scenarios',
    'Rewrite professionally with formal software engineering terminology',
    'Add edge cases for data validations and network timeouts',
    'Improve business value details and trace them to KPI metrics',
    'Map additional user roles and restrict unauthorized security access'
  ];

  const handleSuggestClick = (sug) => {
    setFeedback(sug);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!feedback.trim()) return;
    onSubmitFeedback(storyId, feedback);
    setFeedback('');
    onClose();
  };

  return (
    <AnimatePresence>
      {isOpen && (
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
              className="w-screen max-w-md bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col justify-between"
            >
              {/* Header */}
              <div className="flex items-center justify-between border-b border-slate-850 bg-slate-950 px-6 py-5">
                <div className="flex items-center space-x-2 text-indigo-400 font-bold text-sm">
                  <MessageSquare size={16} />
                  <span>Improve Story {storyId}</span>
                </div>
                <button
                  onClick={onClose}
                  className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-colors"
                >
                  <X size={18} />
                </button>
              </div>

              {/* Body */}
              <div className="flex-1 overflow-y-auto p-6 space-y-6">
                <div className="rounded-lg bg-slate-950/60 border border-slate-850 p-4 space-y-2.5">
                  <div className="flex items-start space-x-2 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                    <AlertCircle size={14} className="text-indigo-400 shrink-0 mt-0.5" />
                    <span>Isolated Story Regeneration</span>
                  </div>
                  <p className="text-[11px] leading-relaxed text-slate-450">
                    Entering feedback will trigger the LLM to regenerate <strong>only</strong> the user story text, business values, or acceptance criteria mappings of this card. All other stories remain unmodified.
                  </p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="space-y-2 text-left">
                    <label className="text-[10px] font-bold text-slate-350 uppercase tracking-wider">
                      What would you like to improve?
                    </label>
                    <textarea
                      required
                      className="w-full h-32 rounded-lg border border-slate-800 bg-slate-950 p-3.5 text-xs text-slate-100 placeholder-slate-600 outline-none focus:border-indigo-650 resize-none"
                      placeholder="Describe what needs modification (e.g., 'rewrite in formal tone' or 'add details for validation')..."
                      value={feedback}
                      onChange={(e) => setFeedback(e.target.value)}
                    />
                  </div>

                  <button
                    type="submit"
                    className="w-full rounded-lg bg-indigo-650 p-3 text-xs font-bold text-white shadow-lg hover:bg-indigo-600 active:scale-98 transition-all"
                  >
                    Regenerate Selected Story
                  </button>
                </form>

                {/* Suggestions list */}
                <div className="space-y-2.5 text-left border-t border-slate-850 pt-5">
                  <div className="flex items-center space-x-1.5 text-[10px] font-bold text-slate-450 uppercase tracking-wider">
                    <Lightbulb size={12} className="text-amber-450" />
                    <span>Suggested Feedback Queries</span>
                  </div>
                  <div className="flex flex-col space-y-1.5">
                    {suggestions.map((sug, i) => (
                      <button
                        key={i}
                        type="button"
                        onClick={() => handleSuggestClick(sug)}
                        className="rounded-lg bg-slate-950/40 hover:bg-slate-950/80 border border-slate-900 px-3 py-2 text-left text-[11px] leading-relaxed text-slate-400 hover:text-slate-200 transition-colors"
                      >
                        {sug}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* Footer */}
              <div className="border-t border-slate-850 bg-slate-950/40 px-6 py-4 flex items-center justify-between text-[10px] text-slate-500">
                <span>Story Feedback Workspace</span>
                <span>BA Platform</span>
              </div>
            </motion.div>
          </div>
        </div>
      )}
    </AnimatePresence>
  );
}
