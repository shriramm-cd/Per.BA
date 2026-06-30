import React, { useState, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { api } from '../services/api';
import UploadCard from '../components/Upload/UploadCard';
import ModalConnectors from '../components/Upload/ModalConnectors';
import ProcessingScreen from '../components/Processing/ProcessingScreen';
import StoryCard from '../components/UserStories/StoryCard';
import ImprovementPanel from '../components/UserStories/ImprovementPanel';
import SummaryDrawer from '../components/Summary/SummaryDrawer';
import ConfirmDialog from '../components/Common/ConfirmDialog';
import { Play, FileDown, CheckSquare, Search, Sparkles, Filter, SlidersHorizontal, ArrowLeft, Disc } from 'lucide-react';

export default function Dashboard() {
  const {
    projects,
    setProjects,
    activeJobId,
    setActiveJobId,
    activeJobStatus,
    setActiveJobStatus,
    activeJobStories,
    setActiveJobStories,
    activeJobSummary,
    setActiveJobSummary,
    addNotification,
    createProjectFromJob,
    updateProjectStatus,
    regenerateSingleStory,
    generateMockSummary
  } = useApp();

  // Wizard layouts
  const [activeConnectorType, setActiveConnectorType] = useState(null);
  const [activeNode, setActiveNode] = useState('ingest');
  const [logs, setLogs] = useState([]);
  
  // Search & Filter
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedEpic, setSelectedEpic] = useState('All');
  const [selectedPriority, setSelectedPriority] = useState('All');
  const [selectedStatus, setSelectedStatus] = useState('All');
  const [sortBy, setSortBy] = useState('id'); // 'id', 'priority', 'epic'

  // Drawers & Modals
  const [isSummaryOpen, setIsSummaryOpen] = useState(false);
  const [feedbackStoryId, setFeedbackStoryId] = useState(null);
  const [exportFormat, setExportFormat] = useState(null); // 'EXCEL', 'PDF', 'JSON', 'JIRA'
  const [jiraProjectKey, setJiraProjectKey] = useState('');
  const [isConfirmApproveAllOpen, setIsConfirmApproveAllOpen] = useState(false);

  // Individual Card Regenerating Tracking
  const [regeneratingStoryIds, setRegeneratingStoryIds] = useState({});

  // Monitor custom active project changes triggered globally
  useEffect(() => {
    const handleActiveJobEvent = () => {
      const savedJobId = localStorage.getItem('ba_active_job_id');
      if (savedJobId) {
        const found = projects.find(p => p.id === savedJobId);
        if (found) {
          setActiveJobId(found.id);
          setActiveJobStatus(found.status);
          setActiveJobStories(found.stories || []);
          setActiveJobSummary(found.summary || null);
        }
      }
    };

    window.addEventListener('storage_active_job', handleActiveJobEvent);
    handleActiveJobEvent(); // run initial check on mount

    return () => window.removeEventListener('storage_active_job', handleActiveJobEvent);
  }, [projects]);

  /**
   * Handle Click of Connection Source Card
   */
  const handleConnectSourceClick = (sourceType) => {
    if (sourceType === 'FILE') {
      // Direct mock upload trigger
      const mockJobId = `job-file-${Math.random().toString(36).substr(2, 9)}`;
      handleStartIngestFlow('FILE', 'requirements_docs', { fileName: 'requirements_docs' }, mockJobId);
    } else {
      // Open modal configuration settings
      setActiveConnectorType(sourceType);
    }
  };

  /**
   * Start Ingesting Content
   */
  const handleStartIngestFlow = async (sourceType, targetIdentifier, connectionConfig, pregeneratedJobId = null) => {
    setActiveJobStatus('INGESTING');
    setLogs([]);
    setActiveNode('ingest');

    try {
      // 1. Ingest call to FastAPI
      let jobId = pregeneratedJobId;
      
      // If NOT mock file, call API
      if (!pregeneratedJobId) {
        addNotification(`Connecting to ${sourceType}...`, 'info');
        const ingestRes = await api.ingest({
          sourceType,
          targetIdentifier,
          connectionConfig
        });
        jobId = ingestRes.job_id;
      }

      setActiveJobId(jobId);
      localStorage.setItem('ba_active_job_id', jobId);

      // Create new project log record
      createProjectFromJob(jobId, `${sourceType}: ${targetIdentifier}`, sourceType, targetIdentifier);

      // 2. Run graph pipeline
      setActiveJobStatus('RUNNING');
      addNotification('Requirement extraction active. Pipeline running...', 'info');

      // Call pipeline endpoint asynchronously (non-blocking)
      api.runPipeline({ jobId, maxRetries: 3 }).catch(err => {
        console.error('Asynchronous pipeline start failure:', err);
      });

      // 3. Connect to EventSource Server-Sent Events to stream node states
      const sseUrl = api.getStreamUrl(jobId);
      const eventSource = new EventSource(sseUrl);

      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.node) {
            setActiveNode(data.node);
            setLogs(prev => [...prev, `[Node: ${data.node}] ${data.summary || 'Processing stage active.'}`]);
          }

          if (data.status === 'FINISHED' || data.node === 'export') {
            eventSource.close();
            fetchCompletedStories(jobId);
          } else if (data.status === 'FAILED') {
            eventSource.close();
            setActiveJobStatus('FAILED');
            addNotification(`Pipeline run aborted: ${data.error || 'Check logs'}`, 'error');
            updateProjectStatus(jobId, 'FAILED');
          }
        } catch (e) {
          console.error('SSE parser error:', e);
        }
      };

      eventSource.onerror = (err) => {
        console.error('SSE connection closed or failed:', err);
        eventSource.close();
        
        // Fallback: If SSE disconnects but process continues, fetch after a delay
        setTimeout(() => {
          fetchCompletedStories(jobId);
        }, 3000);
      };

    } catch (err) {
      console.error(err);
      setActiveJobStatus('FAILED');
      addNotification(`Ingestion failed: ${err.message}`, 'error');
    }
  };

  /**
   * Fetch generated user stories once pipeline finishes
   */
  const fetchCompletedStories = async (jobId) => {
    setActiveJobStatus('COMPLETED');
    addNotification('Stories generated successfully.', 'success');

    try {
      const stories = await api.getStories(jobId);
      
      // If backend returns empty, provide mock template stories
      const parsedStories = stories && stories.length > 0 ? stories : [
        {
          id: 'US-101',
          epic: 'Core Configuration',
          feature: 'Settings Manager',
          title: 'Export Options',
          user_story: 'As a system analyst, I require the ability to export stories, so that I can copy them to Jira.',
          acceptance_criteria: [
            { rule: 'Excel download', details: 'Given stories generated, click excel, downloads stories.xlsx.' }
          ],
          trace_mappings: ['REQ-01'],
          validation_results: { quality_score: 94, invest_passed: true }
        }
      ];

      // Format acceptance criteria correctly if stringified
      const normalizedStories = parsedStories.map(s => ({
        ...s,
        acceptance_criteria: Array.isArray(s.acceptance_criteria) 
          ? s.acceptance_criteria 
          : typeof s.acceptance_criteria === 'string'
            ? [{ rule: 'Acceptance Criteria', details: s.acceptance_criteria }]
            : []
      }));

      // Generate ChatGPT style summary
      const summary = generateMockSummary(jobId, normalizedStories);

      setActiveJobStories(normalizedStories);
      setActiveJobSummary(summary);

      // Save to project history
      updateProjectStatus(jobId, 'COMPLETED', normalizedStories, summary);

    } catch (e) {
      console.error('Story retrieval failed:', e);
      addNotification('Failed to retrieve stories from DB. Showing cache.', 'error');
    }
  };

  /**
   * Story level overrides
   */
  const handleApproveStory = (storyId) => {
    setActiveJobStories(prev => prev.map(s => {
      if (s.id === storyId) {
        return { ...s, status: 'Approved' };
      }
      return s;
    }));

    // Update global project list
    setProjects(prev => prev.map(p => {
      if (p.id === activeJobId) {
        return {
          ...p,
          stories: p.stories.map(s => s.id === storyId ? { ...s, status: 'Approved' } : s)
        };
      }
      return p;
    }));

    addNotification(`Story ${storyId} approved.`, 'success');
  };

  const handleNeedsImprovement = (storyId) => {
    setFeedbackStoryId(storyId);
  };

  const handleSubmitFeedback = async (storyId, feedback) => {
    // Lock this card
    setRegeneratingStoryIds(prev => ({ ...prev, [storyId]: true }));
    
    // Call Context action
    await regenerateSingleStory(activeJobId, storyId, feedback);
    
    // Unlock card
    setRegeneratingStoryIds(prev => ({ ...prev, [storyId]: false }));
  };

  const handleApproveAll = () => {
    setActiveJobStories(prev => prev.map(s => ({ ...s, status: 'Approved' })));
    setProjects(prev => prev.map(p => {
      if (p.id === activeJobId) {
        return { ...p, stories: p.stories.map(s => ({ ...s, status: 'Approved' })) };
      }
      return p;
    }));
    setIsConfirmApproveAllOpen(false);
    addNotification('All user stories approved.', 'success');
  };

  /**
   * Trigger Exporters to download files
   */
  const handleExport = async (format) => {
    if (format === 'JIRA' && !jiraProjectKey) {
      setExportFormat('JIRA');
      return; // Wait for modal input
    }

    addNotification(`Exporting stories as ${format}...`, 'info');
    setExportFormat(null); // close jira input

    try {
      const resBlob = await api.exportStories({
        jobId: activeJobId,
        exportFormat: format,
        projectKey: format === 'JIRA' ? jiraProjectKey : undefined
      });

      // If Jira, it returns a status payload
      if (format === 'JIRA') {
        addNotification(`Jira tickets synced to project ${jiraProjectKey}.`, 'success');
        setJiraProjectKey('');
        return;
      }

      // Handle file download response
      const url = window.URL.createObjectURL(new Blob([resBlob]));
      const link = document.createElement('a');
      link.href = url;
      
      const fileExt = format.toLowerCase() === 'excel' ? 'xlsx' : format.toLowerCase();
      link.setAttribute('download', `stories_${activeJobId}.${fileExt}`);
      
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      
      addNotification(`Downloaded report: stories_${activeJobId}.${fileExt}`, 'success');

    } catch (e) {
      console.error(e);
      addNotification(`Export failed: ${e.message}`, 'error');
    }
  };

  const handleResetWorkspace = () => {
    setActiveJobId(null);
    setActiveJobStatus('IDLE');
    setActiveJobStories([]);
    setActiveJobSummary(null);
    localStorage.removeItem('ba_active_job_id');
  };

  // Get unique lists for filters
  const epicsList = ['All', ...new Set(activeJobStories.map(s => s.epic))];

  // Filtering + Sorting logic
  const filteredStories = activeJobStories.filter(s => {
    const matchesKeyword = searchQuery === '' || 
      s.id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.epic.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.user_story.toLowerCase().includes(searchQuery.toLowerCase());
    
    const matchesEpic = selectedEpic === 'All' || s.epic === selectedEpic;
    const matchesPriority = selectedPriority === 'All' || s.priority === selectedPriority;
    
    const matchesStatus = selectedStatus === 'All' || 
      (selectedStatus === 'Approved' && s.status === 'Approved') ||
      (selectedStatus === 'Needs Review' && s.status === 'Needs Review') ||
      (selectedStatus === 'Pending' && (s.status === 'Pending' || !s.status));

    return matchesKeyword && matchesEpic && matchesPriority && matchesStatus;
  }).sort((a, b) => {
    if (sortBy === 'priority') {
      const priorityWeights = { High: 3, Medium: 2, Low: 1 };
      return (priorityWeights[b.priority] || 0) - (priorityWeights[a.priority] || 0);
    }
    if (sortBy === 'epic') {
      return a.epic.localeCompare(b.epic);
    }
    return a.id.localeCompare(b.id);
  });

  return (
    <div className="space-y-6">
      {/* Connector configuration popup dialog */}
      <ModalConnectors
        isOpen={activeConnectorType !== null}
        type={activeConnectorType}
        onClose={() => setActiveConnectorType(null)}
        onIngestStart={handleStartIngestFlow}
      />

      {/* Jira Target Project Picker popup */}
      {exportFormat === 'JIRA' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-slate-950/70 backdrop-blur-xs" onClick={() => setExportFormat(null)} />
          <div className="relative z-10 w-full max-w-sm overflow-hidden rounded-xl border border-slate-800 bg-slate-900 shadow-2xl p-5 space-y-4">
            <h3 className="text-xs font-bold text-slate-100 uppercase tracking-wider">Sync Backlog with Jira</h3>
            <div className="space-y-1.5 text-left">
              <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Target Project Key</label>
              <input
                type="text"
                required
                className="w-full rounded-lg border border-slate-850 bg-slate-950 p-2.5 text-xs text-slate-100 placeholder-slate-650 outline-none focus:border-indigo-650"
                placeholder="e.g. PROJ, ENG"
                value={jiraProjectKey}
                onChange={(e) => setJiraProjectKey(e.target.value.toUpperCase())}
              />
            </div>
            <div className="flex justify-end space-x-2 pt-2">
              <button
                onClick={() => setExportFormat(null)}
                className="rounded-lg border border-slate-800 bg-slate-900/40 px-3.5 py-1.5 text-[11px] text-slate-350"
              >
                Cancel
              </button>
              <button
                onClick={() => handleExport('JIRA')}
                className="rounded-lg bg-indigo-650 px-4 py-1.5 text-[11px] font-bold text-white hover:bg-indigo-600"
              >
                Push Stories
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation overlays */}
      <ConfirmDialog
        isOpen={isConfirmApproveAllOpen}
        title="Approve All Stories"
        message="Are you sure you want to approve all generated user stories? This action is batch local."
        confirmText="Approve All"
        onConfirm={handleApproveAll}
        onCancel={() => setIsConfirmApproveAllOpen(false)}
      />

      {/* Drawer: Improvement feedback panel */}
      <ImprovementPanel
        isOpen={feedbackStoryId !== null}
        storyId={feedbackStoryId}
        onClose={() => setFeedbackStoryId(null)}
        onSubmitFeedback={handleSubmitFeedback}
      />

      {/* Drawer: ChatGPT style Summary Drawer */}
      <SummaryDrawer
        isOpen={isSummaryOpen}
        summary={activeJobSummary}
        onClose={() => setIsSummaryOpen(false)}
      />

      {/* VIEW DECIIDER */}
      {activeJobStatus === 'IDLE' ? (
        <UploadCard onConnectSource={handleConnectSourceClick} />
      ) : activeJobStatus === 'INGESTING' || activeJobStatus === 'RUNNING' ? (
        <ProcessingScreen activeNode={activeNode} logs={logs} />
      ) : (
        /* Workspace user story dashboard */
        <div className="space-y-6">
          
          {/* Dashboard Header Bar */}
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center border-b border-slate-900 pb-5 gap-4">
            <div className="flex items-center space-x-3">
              <button
                onClick={handleResetWorkspace}
                className="rounded-lg border border-slate-900 bg-slate-950 p-2 text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                title="Back to Upload"
              >
                <ArrowLeft size={16} />
              </button>
              <div>
                <h2 className="text-xl font-bold text-white tracking-tight flex items-center">
                  Requirement Story Board
                  <Sparkles size={16} className="text-indigo-400 ml-2 animate-pulse" />
                </h2>
                <p className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider mt-0.5">
                  Job Context: {activeJobId}
                </p>
              </div>
            </div>

            {/* Bulk Actions */}
            <div className="flex flex-wrap gap-2.5">
              <button
                onClick={() => setIsSummaryOpen(true)}
                className="flex items-center space-x-1.5 rounded-lg border border-indigo-500/10 bg-indigo-500/5 hover:bg-indigo-500/10 transition-colors px-4 py-2 text-xs font-bold text-indigo-400"
              >
                <Sparkles size={14} className="animate-spin" />
                <span>Generate Summary</span>
              </button>
              
              <button
                onClick={() => setIsConfirmApproveAllOpen(true)}
                className="flex items-center space-x-1.5 rounded-lg border border-slate-900 bg-slate-900/60 hover:bg-slate-900 hover:text-slate-200 transition-all px-4 py-2 text-xs font-semibold text-slate-350"
              >
                <CheckSquare size={14} />
                <span>Approve All</span>
              </button>

              {/* Exporters dropdown buttons */}
              <div className="relative group">
                <button className="flex items-center space-x-1.5 rounded-lg bg-indigo-650 hover:bg-indigo-600 transition-all px-4 py-2 text-xs font-bold text-white">
                  <FileDown size={14} />
                  <span>Export Backlog</span>
                </button>
                
                <div className="absolute right-0 mt-1.5 w-40 origin-top-right rounded-lg border border-slate-800 bg-slate-900 shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all p-1 z-20">
                  <button onClick={() => handleExport('EXCEL')} className="flex w-full items-center rounded px-3 py-2 text-left text-xs text-slate-300 hover:bg-slate-800 hover:text-white">Excel Worksheet</button>
                  <button onClick={() => handleExport('PDF')} className="flex w-full items-center rounded px-3 py-2 text-left text-xs text-slate-300 hover:bg-slate-800 hover:text-white">PDF Report Document</button>
                  <button onClick={() => handleExport('JSON')} className="flex w-full items-center rounded px-3 py-2 text-left text-xs text-slate-300 hover:bg-slate-800 hover:text-white">JSON State Dump</button>
                  <button onClick={() => handleExport('JIRA')} className="flex w-full items-center rounded px-3 py-2 text-left text-xs text-slate-300 hover:bg-slate-800 hover:text-white">Atlassian Jira Project</button>
                </div>
              </div>
            </div>
          </div>

          {/* Filters, search and Sorting Panel */}
          <div className="flex flex-col lg:flex-row gap-4 bg-slate-950/60 border border-slate-900 rounded-xl p-4">
            
            {/* Search Input */}
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={16} />
              <input
                type="text"
                className="w-full bg-slate-900 border border-slate-850 rounded-lg pl-9 pr-4 py-2 text-xs text-slate-100 placeholder-slate-550 outline-none focus:border-indigo-650"
                placeholder="Search stories by epic, title, keyword..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>

            {/* Filter selectors */}
            <div className="flex flex-wrap gap-2.5 items-center">
              <div className="flex items-center space-x-1.5 text-xs text-slate-500 font-semibold uppercase tracking-wider">
                <Filter size={12} />
                <span>Filter By:</span>
              </div>

              {/* Epic Select */}
              <select
                className="bg-slate-900 border border-slate-850 rounded-lg px-3 py-2 text-xs text-slate-300 outline-none"
                value={selectedEpic}
                onChange={(e) => setSelectedEpic(e.target.value)}
              >
                <option value="All">All Epics</option>
                {epicsList.filter(e => e !== 'All').map(epic => (
                  <option key={epic} value={epic}>{epic}</option>
                ))}
              </select>

              {/* Priority Select */}
              <select
                className="bg-slate-900 border border-slate-850 rounded-lg px-3 py-2 text-xs text-slate-300 outline-none"
                value={selectedPriority}
                onChange={(e) => setSelectedPriority(e.target.value)}
              >
                <option value="All">All Priorities</option>
                <option value="High">High</option>
                <option value="Medium">Medium</option>
                <option value="Low">Low</option>
              </select>

              {/* Status Select */}
              <select
                className="bg-slate-900 border border-slate-850 rounded-lg px-3 py-2 text-xs text-slate-300 outline-none"
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
              >
                <option value="All">All Statuses</option>
                <option value="Approved">Approved</option>
                <option value="Needs Review">Needs Review</option>
                <option value="Pending">Pending</option>
              </select>

              {/* Sorting */}
              <div className="flex items-center space-x-2 border-l border-slate-900 pl-3">
                <SlidersHorizontal size={12} className="text-slate-500" />
                <select
                  className="bg-slate-900 border border-slate-850 rounded-lg px-3 py-2 text-xs text-slate-300 outline-none"
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                >
                  <option value="id">Sort by ID</option>
                  <option value="priority">Sort by Priority</option>
                  <option value="epic">Sort by Epic</option>
                </select>
              </div>
            </div>
          </div>

          {/* Stories Grid */}
          {filteredStories.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {filteredStories.map((story) => (
                <StoryCard
                  key={story.id}
                  story={story}
                  onApprove={handleApproveStory}
                  onNeedsImprovement={handleNeedsImprovement}
                  isRegenerating={!!regeneratingStoryIds[story.id]}
                />
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-20 rounded-xl border border-slate-900 bg-slate-900/10 text-slate-500">
              <Disc size={36} className="text-slate-700 animate-spin mb-3" />
              <h3 className="text-sm font-semibold text-slate-300">No Stories Match Search Filter</h3>
              <p className="text-xs text-slate-600 mt-1">Adjust your epic, priority, or search term query settings.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
