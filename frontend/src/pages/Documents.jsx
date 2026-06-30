import React, { useState } from 'react';
import { useApp } from '../context/AppContext';
import { FileText, Clock, CheckCircle2, Loader2, AlertCircle, Search, Eye, Trash2, HardDrive } from 'lucide-react';
import ConfirmDialog from '../components/Common/ConfirmDialog';

export default function Documents() {
  const { documents, setDocuments, addNotification } = useApp();
  const [search, setSearch] = useState('');
  const [deleteTarget, setDeleteTarget] = useState(null);

  const getTypeIcon = (type) => {
    const ext = (type || '').toLowerCase();
    if (['pdf'].includes(ext)) return { label: 'PDF', color: 'text-red-400 bg-red-500/10 border-red-500/20' };
    if (['docx', 'doc'].includes(ext)) return { label: 'DOCX', color: 'text-blue-400 bg-blue-500/10 border-blue-500/20' };
    if (['xlsx', 'xls'].includes(ext)) return { label: 'XLSX', color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' };
    if (['txt', 'md'].includes(ext)) return { label: ext.toUpperCase(), color: 'text-slate-400 bg-slate-500/10 border-slate-500/20' };
    return { label: ext.toUpperCase() || 'FILE', color: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20' };
  };

  const getStatusIcon = (status) => {
    switch ((status || '').toUpperCase()) {
      case 'PROCESSED':
        return <CheckCircle2 size={14} className="text-emerald-400" />;
      case 'UPLOADING':
      case 'RUNNING':
        return <Loader2 size={14} className="text-orange-400 animate-spin" />;
      case 'FAILED':
        return <AlertCircle size={14} className="text-red-400" />;
      default:
        return <Clock size={14} className="text-slate-500" />;
    }
  };

  const formatSize = (bytes) => {
    if (!bytes) return '—';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const filtered = documents.filter(d =>
    (d.name || '').toLowerCase().includes(search.toLowerCase())
  );

  const handleDelete = () => {
    setDocuments(prev => prev.filter(d => d.name !== deleteTarget));
    addNotification('Document removed from index.', 'success');
    setDeleteTarget(null);
  };

  return (
    <div className="space-y-6 text-left">
      <ConfirmDialog
        isOpen={!!deleteTarget}
        title="Remove Document"
        message={`Remove "${deleteTarget}" from the document index? The associated pipeline job will not be affected.`}
        confirmText="Remove"
        isDestructive
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
      />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Ingested Documents</h2>
          <p className="text-xs text-slate-400 mt-1">All requirement sources parsed and indexed by the pipeline engine.</p>
        </div>

        {/* Search */}
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={14} />
          <input
            type="text"
            className="w-full rounded-lg border border-slate-850 bg-slate-900 pl-8 pr-4 py-2 text-xs text-slate-200 placeholder-slate-550 outline-none focus:border-indigo-600"
            placeholder="Search by filename..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
      </div>

      {/* Stats Bar */}
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-lg border border-slate-900 bg-slate-900/30 p-3 text-center">
          <div className="text-lg font-bold text-white">{documents.length}</div>
          <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mt-0.5">Total Files</div>
        </div>
        <div className="rounded-lg border border-slate-900 bg-slate-900/30 p-3 text-center">
          <div className="text-lg font-bold text-emerald-400">{documents.filter(d => d.status === 'PROCESSED').length}</div>
          <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mt-0.5">Processed</div>
        </div>
        <div className="rounded-lg border border-slate-900 bg-slate-900/30 p-3 text-center">
          <div className="text-lg font-bold text-orange-400">{documents.filter(d => d.status !== 'PROCESSED' && d.status !== 'FAILED').length}</div>
          <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mt-0.5">In Progress</div>
        </div>
      </div>

      {/* Table */}
      {filtered.length > 0 ? (
        <div className="overflow-hidden rounded-xl border border-slate-900">
          {/* Table Head */}
          <div className="grid grid-cols-12 gap-4 px-5 py-3 bg-slate-950 border-b border-slate-900 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
            <span className="col-span-5">File Name</span>
            <span className="col-span-1 text-center">Type</span>
            <span className="col-span-2 text-center">Status</span>
            <span className="col-span-2">Uploaded At</span>
            <span className="col-span-1 text-right">Size</span>
            <span className="col-span-1"></span>
          </div>

          {/* Table Rows */}
          <div className="divide-y divide-slate-900/60">
            {filtered.map((doc, idx) => {
              const typeInfo = getTypeIcon(doc.type);
              return (
                <div
                  key={idx}
                  className="grid grid-cols-12 gap-4 px-5 py-3.5 items-center hover:bg-slate-900/30 transition-colors"
                >
                  {/* Name */}
                  <div className="col-span-5 flex items-center space-x-3 min-w-0">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-slate-950 border border-slate-850">
                      <FileText size={14} className="text-slate-400" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-slate-200 truncate">{doc.name}</p>
                      {doc.jobId && (
                        <p className="text-[9px] text-slate-600 font-mono truncate">Job: {doc.jobId.substring(0, 16)}...</p>
                      )}
                    </div>
                  </div>

                  {/* Type Badge */}
                  <div className="col-span-1 flex justify-center">
                    <span className={`rounded border px-1.5 py-0.5 text-[9px] font-bold uppercase ${typeInfo.color}`}>
                      {typeInfo.label}
                    </span>
                  </div>

                  {/* Status */}
                  <div className="col-span-2 flex items-center justify-center space-x-1.5">
                    {getStatusIcon(doc.status)}
                    <span className="text-[10px] font-semibold text-slate-400">{doc.status || 'Pending'}</span>
                  </div>

                  {/* Date */}
                  <div className="col-span-2 text-[10px] text-slate-500">
                    {doc.uploadedAt ? new Date(doc.uploadedAt).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' }) : '—'}
                  </div>

                  {/* Size */}
                  <div className="col-span-1 text-right text-[10px] text-slate-500 font-mono">
                    {formatSize(doc.size)}
                  </div>

                  {/* Actions */}
                  <div className="col-span-1 flex justify-end">
                    <button
                      onClick={() => setDeleteTarget(doc.name)}
                      className="rounded-lg p-1.5 text-slate-500 hover:bg-red-950/20 hover:text-red-400 transition-colors"
                      title="Remove from index"
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-20 rounded-xl border border-dashed border-slate-900 text-slate-500">
          <HardDrive size={36} className="text-slate-700 mb-3" />
          <h3 className="text-sm font-semibold text-slate-300">No Documents Indexed</h3>
          <p className="text-xs text-slate-600 mt-1 max-w-xs text-center">
            {search ? 'No documents match your search.' : 'Upload a folder or connect an external source to begin ingesting requirements.'}
          </p>
        </div>
      )}
    </div>
  );
}
