import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import ConfirmDialog from '../components/Common/ConfirmDialog';
import { History, Eye, Copy, Trash2, Calendar, GitBranch, AlertTriangle } from 'lucide-react';

export default function HistoryPage() {
  const { projects, setProjects, setCurrentPage, setActiveJobId, setActiveJobStatus, setActiveJobStories, setActiveJobSummary, deleteProject, addNotification } = useApp();
  const [deleteTargetId, setDeleteTargetId] = useState(null);

  const handleOpenProject = (proj) => {
    setActiveJobId(proj.id);
    setActiveJobStatus(proj.status);
    setActiveJobStories(proj.stories || []);
    setActiveJobSummary(proj.summary || null);
    localStorage.setItem('ba_active_job_id', proj.id);
    
    // Switch page to dashboard
    setCurrentPage('dashboard');
    addNotification(`Loaded workspace: ${proj.name}`, 'info');
  };

  const handleDuplicateProject = (proj) => {
    const cloneId = `job-clone-${Math.random().toString(36).substr(2, 9)}`;
    const clonedProj = {
      ...proj,
      id: cloneId,
      name: `${proj.name} (Copy)`,
      createdAt: new Date().toISOString(),
    };
    
    setProjects(prev => [clonedProj, ...prev]);
    addNotification(`Duplicated project workspace: ${proj.name}`, 'success');
  };

  const handleDeleteConfirm = () => {
    if (deleteTargetId) {
      deleteProject(deleteTargetId);
      setDeleteTargetId(null);
    }
  };

  const getSourceIconColor = (src) => {
    switch (src?.toUpperCase()) {
      case 'JIRA': return 'text-sky-400 border-sky-500/20 bg-sky-500/5';
      case 'CONFLUENCE': return 'text-blue-400 border-blue-500/20 bg-blue-500/5';
      case 'SHAREPOINT': return 'text-emerald-400 border-emerald-500/20 bg-emerald-500/5';
      case 'GDRIVE': return 'text-amber-400 border-amber-500/20 bg-amber-500/5';
      default: return 'text-indigo-400 border-indigo-500/20 bg-indigo-500/5';
    }
  };

  return (
    <div className="space-y-6 text-left">
      <ConfirmDialog
        isOpen={deleteTargetId !== null}
        title="Delete Project History"
        message="Are you sure you want to delete this project? This will permanently remove all associated user stories and ingested metadata logs."
        confirmText="Permanently Delete"
        isDestructive={true}
        onConfirm={handleDeleteConfirm}
        onCancel={() => setDeleteTargetId(null)}
      />

      <div>
        <h2 className="text-xl font-bold text-white tracking-tight">Generation History</h2>
        <p className="text-xs text-slate-400 mt-1">Review, clone, reopen, or remove past requirements-to-story compilation environments.</p>
      </div>

      {projects.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {projects.map((proj) => (
            <div key={proj.id} className="rounded-xl border border-slate-900 bg-slate-900/35 hover:border-slate-800 transition-colors p-5 flex flex-col justify-between space-y-4">
              
              <div className="space-y-2">
                {/* Header */}
                <div className="flex items-start justify-between">
                  <h3 className="text-xs font-bold text-slate-100 line-clamp-1 pr-4">{proj.name}</h3>
                  <span className={`rounded-full border px-2 py-0.5 text-[8px] font-bold tracking-wider uppercase ${getSourceIconColor(proj.sourceType)}`}>
                    {proj.sourceType}
                  </span>
                </div>

                {/* Subdetails */}
                <p className="text-[10px] text-slate-500 font-mono truncate" title={proj.targetIdentifier}>
                  Target ID: {proj.targetIdentifier}
                </p>
              </div>

              {/* Middle metrics */}
              <div className="flex items-center space-x-6 text-[10px] text-slate-450">
                <div className="flex items-center space-x-1">
                  <Calendar size={12} className="text-slate-600" />
                  <span>{new Date(proj.createdAt).toLocaleDateString()}</span>
                </div>
                <div className="flex items-center space-x-1">
                  <GitBranch size={12} className="text-slate-600" />
                  <span>{proj.storiesCount || 0} User Stories</span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <span className={`h-1.5 w-1.5 rounded-full ${
                    proj.status === 'COMPLETED' ? 'bg-emerald-450' : 
                    proj.status === 'FAILED' ? 'bg-red-450' : 'bg-orange-450'
                  }`} />
                  <span className="font-semibold text-slate-350">{proj.status}</span>
                </div>
              </div>

              {/* Actions Footer */}
              <div className="flex items-center justify-end space-x-2 pt-2 border-t border-slate-900/60">
                <button
                  onClick={() => handleDuplicateProject(proj)}
                  className="rounded-lg border border-slate-850 bg-slate-900/30 hover:bg-slate-850 p-2 text-slate-400 hover:text-slate-200 transition-colors"
                  title="Clone Workspace"
                >
                  <Copy size={12} />
                </button>
                <button
                  onClick={() => setDeleteTargetId(proj.id)}
                  className="rounded-lg border border-slate-850 bg-slate-900/30 hover:bg-red-950/20 p-2 text-slate-400 hover:text-red-400 hover:border-red-950/30 transition-colors"
                  title="Delete History"
                >
                  <Trash2 size={12} />
                </button>
                <button
                  onClick={() => handleOpenProject(proj)}
                  className="flex items-center space-x-1 rounded-lg bg-indigo-650/15 hover:bg-indigo-650 transition-all px-3 py-1.5 text-[10px] font-bold text-indigo-400 hover:text-white"
                >
                  <Eye size={12} />
                  <span>Open Workbench</span>
                </button>
              </div>

            </div>
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-20 rounded-xl border border-slate-900 bg-slate-900/10 text-slate-500">
          <History size={36} className="text-slate-700 mb-3" />
          <h3 className="text-sm font-semibold text-slate-300">No History Records Found</h3>
          <p className="text-xs text-slate-650 mt-1 max-w-xs text-center">You have not executed any requirements extraction pipelines yet.</p>
          <button
            onClick={() => setCurrentPage('dashboard')}
            className="mt-6 rounded-lg bg-indigo-650 px-5 py-2 text-xs font-bold text-white hover:bg-indigo-600 transition-all shadow-md"
          >
            Create a Workspace
          </button>
        </div>
      )}
    </div>
  );
}
