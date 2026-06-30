import React, { useState, useEffect } from 'react';
import { useApp } from '../../context/AppContext';
import { BrainCircuit, Loader2, CheckCircle2, Circle, HelpCircle } from 'lucide-react';
import { motion } from 'framer-motion';

export default function ProcessingScreen({ activeNode, logs }) {
  const [progress, setProgress] = useState(5);
  const [phraseIdx, setPhraseIdx] = useState(0);

  // Hidden technical processes rotating messages
  const processPhrases = [
    'Reading Documents...',
    'Understanding Structure...',
    'Extracting Requirements...',
    'Preparing AI Context...',
    'Identifying Business Rules...',
    'Processing Requirements...',
    'Generating Knowledge Graph...',
    'Checking Validation Indices...',
    'Structuring Epics and User Flows...',
    'Almost Ready...'
  ];

  // Rotate phrases
  useEffect(() => {
    const phraseInterval = setInterval(() => {
      setPhraseIdx(prev => (prev + 1) % processPhrases.length);
    }, 3000);
    return () => clearInterval(phraseInterval);
  }, []);

  // Simulate progress indicator (ranges from 5% to 98% until job finishes)
  useEffect(() => {
    const progressInterval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 98) return 98;
        // Slower progress as it approaches the end
        const step = prev < 50 ? 5 : prev < 80 ? 2 : 0.5;
        return prev + step;
      });
    }, 400);

    return () => clearInterval(progressInterval);
  }, []);

  // Mapped user-friendly timeline nodes
  const timelineNodes = [
    { key: 'ingest', label: 'Extracting Raw Document Content' },
    { key: 'agent1', label: 'Understanding Business Requirements' },
    { key: 'agent2', label: 'Analyzing Requirement Relationships' },
    { key: 'agent3', label: 'Synthesizing User Stories & Criteria' },
    { key: 'agent4', label: 'Validating Specification Quality' },
    { key: 'human_review', label: 'Almost Finished...' }
  ];

  // Determine node index
  const getActiveNodeIdx = () => {
    if (!activeNode) return 0;
    const idx = timelineNodes.findIndex(n => n.key === activeNode.toLowerCase());
    return idx === -1 ? 0 : idx;
  };

  const activeIdx = getActiveNodeIdx();

  return (
    <div className="w-full max-w-2xl mx-auto rounded-xl border border-slate-900 bg-slate-900/25 p-8 text-center space-y-8 select-none">
      {/* Orb Spinner */}
      <div className="relative flex items-center justify-center h-28 w-28 mx-auto">
        {/* Glow */}
        <div className="absolute inset-0 rounded-full bg-indigo-500/10 blur-xl animate-pulse" />
        {/* Rotating border */}
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
          className="absolute inset-0 rounded-full border-2 border-indigo-500/10 border-t-indigo-400"
        />
        {/* AI Icon */}
        <BrainCircuit size={40} className="text-indigo-400 animate-pulse relative z-10" />
      </div>

      {/* Title & Micro-Messages */}
      <div className="space-y-2">
        <h3 className="text-lg font-bold text-white tracking-tight">AI Orchestrator Execution</h3>
        <p className="text-xs text-indigo-400 h-4 font-semibold transition-all duration-300">
          {processPhrases[phraseIdx]}
        </p>
      </div>

      {/* Simulated Progress Bar */}
      <div className="space-y-2 max-w-md mx-auto">
        <div className="w-full bg-slate-900 rounded-full h-2 overflow-hidden border border-slate-850">
          <div className="bg-indigo-500 h-full transition-all duration-300 rounded-full" style={{ width: `${progress}%` }} />
        </div>
        <div className="flex justify-between text-[9px] text-slate-500 font-mono font-semibold">
          <span>PIPELINE RUNNING</span>
          <span>ESTIMATED: {Math.floor(progress)}%</span>
        </div>
      </div>

      {/* Timeline Steps */}
      <div className="border-t border-slate-900/60 pt-6 max-w-md mx-auto text-left space-y-3">
        <h4 className="text-[10px] font-bold text-slate-450 uppercase tracking-wider mb-4">Pipeline Node execution Status</h4>
        
        <div className="space-y-3.5">
          {timelineNodes.map((node, idx) => {
            const isCompleted = idx < activeIdx;
            const isCurrent = idx === activeIdx;
            
            return (
              <div
                key={node.key}
                className={`flex items-center justify-between text-xs transition-colors duration-300 ${
                  isCompleted ? 'text-emerald-400 font-semibold' : isCurrent ? 'text-indigo-400 font-bold' : 'text-slate-550'
                }`}
              >
                <div className="flex items-center space-x-3">
                  {isCompleted ? (
                    <CheckCircle2 size={16} className="text-emerald-400 shrink-0" />
                  ) : isCurrent ? (
                    <Loader2 size={16} className="text-indigo-400 animate-spin shrink-0" />
                  ) : (
                    <Circle size={16} className="text-slate-700 shrink-0" />
                  )}
                  <span>{node.label}</span>
                </div>
                {isCompleted && (
                  <span className="text-[9px] font-bold tracking-wider text-emerald-500/80 bg-emerald-500/10 px-1.5 py-0.2 rounded uppercase">
                    COMPLETED
                  </span>
                )}
                {isCurrent && (
                  <span className="text-[9px] font-bold tracking-wider text-indigo-400 bg-indigo-500/10 px-1.5 py-0.2 rounded uppercase animate-pulse">
                    IN PROCESS
                  </span>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
