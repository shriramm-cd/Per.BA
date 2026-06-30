import React, { useState, useRef } from 'react';
import { FolderUp, GitBranch, Share2, Disc, Database, UploadCloud } from 'lucide-react';
import { useApp } from '../../context/AppContext';

export default function UploadCard({ onConnectSource }) {
  const { addNotification } = useApp();
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [selectedFolder, setSelectedFolder] = useState(null);
  
  const fileInputRef = useRef(null);

  const sources = [
    { id: 'folder', name: 'Upload Folder', icon: FolderUp, desc: 'Drag and drop an entire local requirements folder', color: 'text-indigo-400 border-indigo-500/10 hover:border-indigo-500/30' },
    { id: 'jira', name: 'Jira Integration', icon: GitBranch, desc: 'Import issues from Atlassian Jira backlogs', color: 'text-sky-400 border-sky-500/10 hover:border-sky-500/30' },
    { id: 'sharepoint', name: 'SharePoint site', icon: Share2, desc: 'Connect to Microsoft SharePoint document site', color: 'text-emerald-400 border-emerald-500/10 hover:border-emerald-500/30' },
    { id: 'gdrive', name: 'Google Drive', icon: Disc, desc: 'Synchronize files from OAuth Google Drive directories', color: 'text-amber-400 border-amber-500/10 hover:border-amber-500/30' },
    { id: 'confluence', name: 'Confluence Wiki', icon: Database, desc: 'Sync descriptions from Atlassian Confluence spaces', color: 'text-blue-400 border-blue-500/10 hover:border-blue-500/30' },
  ];

  // Drag and drop event handlers
  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const simulateFolderUpload = (folderName, fileCount) => {
    setIsUploading(true);
    setUploadProgress(0);
    addNotification(`Parsing requirements folder: ${folderName}...`, 'info');

    const interval = setInterval(() => {
      setUploadProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          setIsUploading(false);
          addNotification('Requirements folder imported successfully.', 'success');
          
          // Trigger successful ingestion callback
          onConnectSource('FILE', folderName, {
            folderName,
            fileCount,
            fileTypes: ['docx', 'pdf', 'txt']
          });
          return 100;
        }
        return prev + 15;
      });
    }, 200);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    
    // Check if items are directories or files
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      // In a real browser, folder upload is done via directories.
      // Here, we grab the first file's folder structure or count total files
      const fileCount = files.length;
      const folderName = files[0].name.split('.')[0] + '_docs';
      simulateFolderUpload(folderName, fileCount);
    }
  };

  const handleFolderSelect = (e) => {
    const files = e.target.files;
    if (files.length > 0) {
      const fileCount = files.length;
      // Get parent path or mock it
      const folderName = files[0].webkitRelativePath?.split('/')[0] || 'specifications_folder';
      simulateFolderUpload(folderName, fileCount);
    }
  };

  const triggerFolderClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-white tracking-tight">Choose Requirement Source</h2>
        <p className="text-xs text-slate-400 mt-1">Select an ingestion connector or drop a folder to populate the requirements stream.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* Source Cards */}
        {sources.map(src => {
          const Icon = src.icon;
          if (src.id === 'folder') {
            return (
              <div
                key={src.id}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={triggerFolderClick}
                className={`relative flex flex-col items-center justify-center p-6 border-2 border-dashed rounded-xl cursor-pointer select-none transition-all duration-300 ${
                  isDragging
                    ? 'border-indigo-500 bg-indigo-500/5'
                    : 'border-slate-850 bg-slate-900/35 hover:bg-slate-900/60'
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  className="hidden"
                  webkitdirectory="true"
                  directory="true"
                  multiple
                  onChange={handleFolderSelect}
                />
                
                {isUploading ? (
                  <div className="w-full text-center space-y-3 py-4">
                    <UploadCloud size={32} className="mx-auto text-indigo-400 animate-bounce" />
                    <div className="text-xs font-bold text-slate-200">Processing Folder ({uploadProgress}%)</div>
                    <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
                      <div className="bg-indigo-500 h-full transition-all duration-150" style={{ width: `${uploadProgress}%` }} />
                    </div>
                  </div>
                ) : (
                  <>
                    <FolderUp size={32} className="text-indigo-400 mb-3" />
                    <h3 className="text-xs font-bold text-slate-100">Upload Folder</h3>
                    <p className="text-[10px] text-slate-500 text-center mt-2 leading-relaxed">
                      Drag & drop folder, or click to choose from local files
                    </p>
                  </>
                )}
              </div>
            );
          }

          return (
            <button
              key={src.id}
              onClick={() => onConnectSource(src.id.toUpperCase())}
              className={`flex flex-col items-start p-5 rounded-xl border border-slate-850 bg-slate-900/35 hover:bg-slate-900/60 text-left transition-all duration-300 hover:border-slate-800`}
            >
              <div className={`rounded-lg bg-slate-950 p-2.5 ${src.color.split(' ')[0]}`}>
                <Icon size={20} />
              </div>
              <h3 className="text-xs font-bold text-slate-100 mt-4">{src.name}</h3>
              <p className="text-[10px] text-slate-500 mt-2 leading-relaxed">{src.desc}</p>
            </button>
          );
        })}
      </div>
    </div>
  );
}
