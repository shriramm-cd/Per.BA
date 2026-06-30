import React from 'react';
import { useApp } from '../context/AppContext';
import { BrainCircuit, Compass, FileSpreadsheet, GitBranch, ShieldCheck, Zap, ArrowRight, Server, FileJson } from 'lucide-react';
import { motion } from 'framer-motion';

export default function Landing() {
  const { setCurrentPage } = useApp();

  const features = [
    {
      title: 'Docling Ingestion Engine',
      desc: 'Extract structural rules and raw specification text automatically from PDF, Word, or Markdown files with high-fidelity semantic preservation.',
      icon: BrainCircuit,
    },
    {
      title: 'Multi-Agent State Graph',
      desc: 'Four specialized agents collaborate in cycles to identify business requirements, model epic relations, generate stories, and evaluate quality gates.',
      icon: GitBranch,
    },
    {
      title: 'Human-in-the-Loop Workbench',
      desc: 'Verify generated backlogs directly inside a visual interface. Leave specific feedback and regenerate isolated stories without rebuilding other modules.',
      icon: ShieldCheck,
    },
    {
      title: 'Native Backlog Export',
      desc: 'Sync approved developer-ready user stories and Gherkin Acceptance Criteria directly into Jira projects or download Excel, PDF, and JSON spreadsheets.',
      icon: FileSpreadsheet,
    },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center overflow-x-hidden selection:bg-indigo-500/20">
      {/* Premium Top Bar */}
      <header className="w-full max-w-7xl px-6 py-6 flex justify-between items-center border-b border-slate-900/60 z-10">
        <div className="flex items-center space-x-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-650 text-white font-bold">
            <BrainCircuit size={20} className="animate-pulse" />
          </div>
          <span className="text-md font-bold tracking-tight text-white">BA Accelerator</span>
        </div>
        <button
          onClick={() => setCurrentPage('dashboard')}
          className="group flex items-center space-x-1.5 rounded-lg border border-slate-800 bg-slate-900 px-4 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-850 hover:text-white transition-all"
        >
          <span>Open Dashboard</span>
          <ArrowRight size={14} className="group-hover:translate-x-0.5 transition-transform" />
        </button>
      </header>

      {/* Hero Section */}
      <main className="flex-1 w-full max-w-5xl px-6 flex flex-col items-center justify-center py-20 text-center relative">
        {/* Glow effect */}
        <div className="absolute top-10 left-1/2 -translate-x-1/2 w-[500px] h-[300px] bg-indigo-750/10 blur-[130px] rounded-full pointer-events-none" />

        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="space-y-6 max-w-3xl z-10"
        >
          <span className="inline-flex items-center space-x-2 rounded-full border border-indigo-500/20 bg-indigo-500/5 px-3.5 py-1 text-xs font-semibold text-indigo-400">
            <Zap size={12} className="animate-bounce" />
            <span>Next-Gen Business Analysis Workbench</span>
          </span>

          <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white leading-tight">
            Convert Business Requirements into{' '}
            <span className="bg-gradient-to-r from-indigo-400 via-indigo-200 to-emerald-450 bg-clip-text text-transparent">
              Development-Ready Stories
            </span>
          </h1>

          <p className="text-sm sm:text-lg leading-relaxed text-slate-400 max-w-2xl mx-auto">
            Supercharge your agile sprint planning. Leverage multi-agent LangGraph flows to ingest BRDs, map traceability metrics, compile epics, and auto-generate acceptance criteria.
          </p>

          <div className="pt-6 flex flex-col sm:flex-row items-center justify-center gap-4">
            <button
              onClick={() => setCurrentPage('dashboard')}
              className="w-full sm:w-auto group flex items-center justify-center space-x-2 rounded-lg bg-indigo-650 px-6 py-3.5 text-sm font-bold text-white shadow-lg shadow-indigo-950/40 hover:bg-indigo-600 active:scale-98 transition-all"
            >
              <span>Generate User Stories</span>
              <ArrowRight size={16} className="group-hover:translate-x-0.5 transition-transform" />
            </button>
            <a
              href="#architecture"
              className="w-full sm:w-auto flex items-center justify-center space-x-2 rounded-lg border border-slate-800 bg-slate-900/60 px-6 py-3.5 text-sm font-semibold text-slate-350 hover:bg-slate-850 hover:text-slate-100 transition-all"
            >
              <span>Architecture Overview</span>
            </a>
          </div>
        </motion.div>
      </main>

      {/* Feature Grid */}
      <section className="w-full bg-slate-950 border-t border-slate-900 py-20 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="text-center max-w-2xl mx-auto mb-16 space-y-3">
            <h2 className="text-2xl sm:text-3xl font-bold text-white">Full-Spectrum Backlog Automation</h2>
            <p className="text-xs sm:text-sm text-slate-400">
              Complete abstracting of complex multi-agent architectures behind a beautiful, unified workspace dashboard.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((f, i) => {
              const Icon = f.icon;
              return (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 15 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.1 }}
                  className="rounded-xl border border-slate-900 bg-slate-900/30 hover:border-slate-850 transition-colors p-6 space-y-4"
                >
                  <div className="inline-flex rounded-lg bg-indigo-500/10 p-2.5 text-indigo-400">
                    <Icon size={20} />
                  </div>
                  <h3 className="text-sm font-bold text-slate-100">{f.title}</h3>
                  <p className="text-xs leading-relaxed text-slate-450">{f.desc}</p>
                </motion.div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Architecture Overview Section */}
      <section id="architecture" className="w-full bg-slate-950/40 border-t border-slate-900 py-20 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="text-center max-w-2xl mx-auto mb-16 space-y-3">
            <h2 className="text-2xl sm:text-3xl font-bold text-white">Internal Workflow Pipeline</h2>
            <p className="text-xs sm:text-sm text-slate-400">
              How requirements safely travel through Docling loaders and our multi-agent decision engine.
            </p>
          </div>

          {/* Architecture diagram/cards with connectors */}
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 relative">
            <div className="rounded-xl border border-slate-900 bg-slate-900/50 p-6 flex flex-col items-center text-center space-y-3 z-10">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-800 text-slate-300">
                <Server size={18} />
              </div>
              <h3 className="text-xs font-bold text-slate-100">1. Raw Content Ingest</h3>
              <p className="text-[11px] text-slate-500 leading-relaxed">
                Source BRD texts are normalized. System calculates content hash keys to filter duplicates.
              </p>
              <span className="rounded-full bg-slate-800/80 px-2 py-0.5 text-[9px] text-slate-400 font-mono">Docling Parser</span>
            </div>

            <div className="rounded-xl border border-slate-900 bg-slate-900/50 p-6 flex flex-col items-center text-center space-y-3 z-10">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-indigo-950/80 text-indigo-400">
                <BrainCircuit size={18} />
              </div>
              <h3 className="text-xs font-bold text-slate-100">2. Intelligence Extraction</h3>
              <p className="text-[11px] text-slate-500 leading-relaxed">
                Agent 1 parses business rules and actors. Returns semantic confidence ratings.
              </p>
              <span className="rounded-full bg-indigo-500/10 text-indigo-400 px-2 py-0.5 text-[9px] font-mono">Agent 1: Extraction</span>
            </div>

            <div className="rounded-xl border border-slate-900 bg-slate-900/50 p-6 flex flex-col items-center text-center space-y-3 z-10">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-indigo-950/80 text-indigo-400">
                <GitBranch size={18} />
              </div>
              <h3 className="text-xs font-bold text-slate-100">3. Epic & Feature Planner</h3>
              <p className="text-[11px] text-slate-500 leading-relaxed">
                Agent 2 structures requirements, plots dependencies, and maps traceability matrix nodes.
              </p>
              <span className="rounded-full bg-indigo-500/10 text-indigo-400 px-2 py-0.5 text-[9px] font-mono">Agent 2: Mapping</span>
            </div>

            <div className="rounded-xl border border-slate-900 bg-slate-900/50 p-6 flex flex-col items-center text-center space-y-3 z-10">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-indigo-950/80 text-indigo-400">
                <FileJson size={18} />
              </div>
              <h3 className="text-xs font-bold text-slate-100">4. User Story generator</h3>
              <p className="text-[11px] text-slate-500 leading-relaxed">
                Agent 3 generates standard User Stories and Given-When-Then criteria cards.
              </p>
              <span className="rounded-full bg-indigo-500/10 text-indigo-400 px-2 py-0.5 text-[9px] font-mono">Agent 3: Synthesis</span>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="w-full py-10 px-6 border-t border-slate-900 text-center text-xs text-slate-650">
        <p>&copy; {new Date().getFullYear()} BA Accelerator. Enterprise Agile Specification Generator. All rights reserved.</p>
      </footer>
    </div>
  );
}
