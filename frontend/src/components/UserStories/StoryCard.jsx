import React, { useState } from 'react';
import { CheckCircle2, AlertCircle, ChevronDown, ChevronUp, RefreshCw, Star, Info } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function StoryCard({ story, onApprove, onNeedsImprovement, isRegenerating }) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Map priority colors
  const getPriorityColor = (p) => {
    switch (p?.toLowerCase()) {
      case 'high': return 'bg-red-500/10 text-red-400 border-red-500/20';
      case 'medium': return 'bg-orange-500/10 text-orange-400 border-orange-500/20';
      case 'low': return 'bg-slate-500/10 text-slate-400 border-slate-500/20';
      default: return 'bg-slate-500/10 text-slate-450 border-slate-505/20';
    }
  };

  // Map status colors
  const getStatusColor = (s) => {
    switch (s?.toLowerCase()) {
      case 'approved': return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
      case 'needs review': return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
      default: return 'bg-slate-500/10 text-slate-450 border-slate-500/20';
    }
  };

  const score = story.validation_results?.quality_score || 85;
  const isApproved = story.status === 'Approved';

  return (
    <div className="relative rounded-xl border border-slate-900 bg-slate-900/35 overflow-hidden transition-all hover:border-slate-800">
      
      {/* Loading Overlay for Single Card Regeneration */}
      {isRegenerating && (
        <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-xs flex flex-col items-center justify-center space-y-3 z-10 animate-pulse">
          <RefreshCw size={24} className="text-indigo-400 animate-spin" />
          <span className="text-[11px] font-bold text-slate-400 tracking-wider">RE-GENERATING STORY INDICES...</span>
        </div>
      )}

      {/* Main Content Area */}
      <div className="p-5 space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-900 pb-3">
          <div className="flex items-center space-x-2">
            <span className="text-xs font-bold font-mono tracking-tight text-white">{story.id}</span>
            <span className={`rounded-full border px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider ${getPriorityColor(story.priority || 'Medium')}`}>
              {story.priority || 'Medium'} Priority
            </span>
            <span className={`rounded-full border px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider ${getStatusColor(story.status || 'Pending')}`}>
              {story.status || 'Pending'}
            </span>
          </div>
          
          <div className="flex items-center space-x-1">
            <div className="flex items-center text-[10px] text-slate-500 mr-2" title="INVEST Quality Score">
              <Star size={12} className="text-amber-500 mr-1 fill-amber-500/30" />
              <span className="font-bold text-slate-350">{score}% Quality</span>
            </div>
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="rounded-lg p-1 text-slate-450 hover:bg-slate-800 hover:text-slate-200 transition-colors"
              title="Expand Details"
            >
              {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
          </div>
        </div>

        {/* Epic & Feature Info */}
        <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-[10px] text-slate-500 font-semibold uppercase tracking-wider">
          <div>Epic: <span className="text-slate-350">{story.epic}</span></div>
          <div className="hidden sm:block text-slate-800">•</div>
          <div>Feature: <span className="text-slate-350">{story.feature || 'Main System'}</span></div>
        </div>

        {/* Source Requirement Text */}
        <div className="rounded-lg bg-slate-950/60 p-3 border border-slate-900">
          <div className="text-[9px] font-bold text-slate-500 uppercase tracking-wider mb-1 flex items-center">
            <Info size={10} className="mr-1" />
            Associated Source Requirement
          </div>
          <p className="text-[11px] leading-relaxed text-slate-400 italic">
            "{story.requirement || (story.trace_mappings && story.trace_mappings[0]) || 'Raw requirement mapping unavailable'}"
          </p>
        </div>

        {/* Generated User Story */}
        <div className="space-y-1.5">
          <div className="text-[9px] font-bold text-slate-500 uppercase tracking-wider">Generated User Story</div>
          <p className="text-xs leading-relaxed text-slate-200 font-medium">
            {story.user_story}
          </p>
        </div>

        {/* Expandable Section: Acceptance Criteria & Business Value */}
        <AnimatePresence>
          {isExpanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              className="overflow-hidden space-y-4 pt-2 border-t border-slate-900"
            >
              {/* Acceptance Criteria */}
              <div className="space-y-2">
                <div className="text-[9px] font-bold text-slate-500 uppercase tracking-wider">Acceptance Criteria (Gherkin Rules)</div>
                <div className="space-y-2">
                  {story.acceptance_criteria && story.acceptance_criteria.length > 0 ? (
                    story.acceptance_criteria.map((crit, idx) => (
                      <div key={idx} className="rounded-lg bg-slate-950/30 border border-slate-900/60 p-2.5 text-[11px] leading-relaxed text-slate-400">
                        <div className="font-bold text-slate-300 text-[10px] mb-0.5">{crit.rule || `Scenario ${idx + 1}`}</div>
                        <p className="font-mono text-slate-450">{crit.details || crit.scenario || JSON.stringify(crit)}</p>
                      </div>
                    ))
                  ) : (
                    <span className="text-[10px] text-slate-600">No acceptance criteria generated.</span>
                  )}
                </div>
              </div>

              {/* Business Value */}
              <div className="space-y-1">
                <div className="text-[9px] font-bold text-slate-500 uppercase tracking-wider">Business Value & Impact</div>
                <p className="text-[11px] leading-relaxed text-slate-400">
                  {story.business_value || 'Direct impact on user workflows and logical validation cycles.'}
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Footer Actions */}
        <div className="flex items-center justify-end space-x-3 border-t border-slate-900 pt-3.5">
          <button
            onClick={() => onNeedsImprovement(story.id)}
            className="rounded-lg border border-slate-800 bg-slate-900/40 px-3.5 py-1.8 text-[11px] font-bold text-slate-300 hover:bg-slate-850 hover:text-white transition-colors"
          >
            Needs Improvement
          </button>
          
          <button
            onClick={() => onApprove(story.id)}
            disabled={isApproved}
            className={`rounded-lg px-4 py-1.8 text-[11px] font-bold text-white transition-all shadow-md ${
              isApproved
                ? 'bg-emerald-600/80 cursor-default shadow-none border border-emerald-500/20'
                : 'bg-indigo-650 hover:bg-indigo-600 shadow-indigo-950/30'
            }`}
          >
            {isApproved ? 'Approved ✓' : 'Approve Story'}
          </button>
        </div>
      </div>
    </div>
  );
}
