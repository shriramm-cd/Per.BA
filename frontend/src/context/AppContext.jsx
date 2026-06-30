import React, { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../services/api';

const AppContext = createContext();

export const useApp = () => useContext(AppContext);

export const AppProvider = ({ children }) => {
  // Page Navigation State
  const [currentPage, setCurrentPage] = useState('landing'); // 'landing', 'dashboard', 'analytics', 'history', 'documents', 'settings'
  
  // Theme State
  const [theme, setTheme] = useState(() => {
    const localTheme = localStorage.getItem('ba_theme');
    if (localTheme) return localTheme;
    // Default to dark mode
    return 'dark';
  });

  // Projects / Generation History
  const [projects, setProjects] = useState(() => {
    const localProjects = localStorage.getItem('ba_projects');
    if (localProjects) return JSON.parse(localProjects);
    // Starter mock projects for visual demo
    return [
      {
        id: 'proj-demo-1',
        name: 'OAuth2 Integration Framework',
        sourceType: 'CONFLUENCE',
        targetIdentifier: 'https://confluence.company.com/pages/OAuth-Specs',
        createdAt: '2026-06-25T14:32:00.000Z',
        status: 'COMPLETED',
        storiesCount: 4,
        stories: [
          {
            id: 'US-101',
            epic: 'Authentication',
            feature: 'User Sign In',
            title: 'Email Login',
            user_story: 'As a registered user, I want to authenticate using my email and password, so that I can securely access the system.',
            acceptance_criteria: [
              { rule: 'Valid credentials grant access', details: 'Given a user enters registered credentials, when they click sign in, then they are redirected to dashboard.' },
              { rule: 'Invalid credentials throw errors', details: 'Given an invalid email or password, when clicked sign in, show warning "Invalid credentials".' }
            ],
            trace_mappings: ['REQ-01'],
            validation_results: { quality_score: 95, invest_passed: true }
          },
          {
            id: 'US-102',
            epic: 'Authentication',
            feature: 'Password Reset',
            title: 'Forgot Password Workflow',
            user_story: 'As a user who forgot my password, I want to trigger a reset email, so that I can securely set a new password.',
            acceptance_criteria: [
              { rule: 'Reset link generated', details: 'Given user triggers reset, an email is dispatched within 2 minutes.' }
            ],
            trace_mappings: ['REQ-02'],
            validation_results: { quality_score: 88, invest_passed: true }
          }
        ],
        summary: {
          totalRequirements: 5,
          functionalRequirements: 4,
          nonFunctionalRequirements: 1,
          businessGoals: 'Implement secure, modern, multi-provider authentication schemas.',
          modules: ['OAuth2 Core', 'Email Dispatch', 'Token Management'],
          highPriorityCount: 2,
          mediumPriorityCount: 2,
          lowPriorityCount: 1,
          executiveSummary: 'This document specifies the target OAuth2 authentication layer. Key objectives are secure tokens, refresh intervals, and email confirmation flows.'
        }
      }
    ];
  });

  // Uploaded Documents Library
  const [documents, setDocuments] = useState(() => {
    const localDocs = localStorage.getItem('ba_docs');
    if (localDocs) return JSON.parse(localDocs);
    return [
      { name: 'auth_spec_v2.docx', type: 'docx', size: 1048576, uploadedAt: '2026-06-25T14:30:00.000Z', status: 'PROCESSED', jobId: 'proj-demo-1' }
    ];
  });

  // Current active job being processed
  const [activeJobId, setActiveJobId] = useState(null);
  const [activeJobStatus, setActiveJobStatus] = useState('IDLE'); // IDLE, INGESTING, RUNNING, COMPLETED, FAILED
  const [activeJobStories, setActiveJobStories] = useState([]);
  const [activeJobSummary, setActiveJobSummary] = useState(null);
  const [activeJobLogs, setActiveJobLogs] = useState([]);
  
  // Notification system
  const [notifications, setNotifications] = useState([]);

  // Apply Theme class on mounting & updates
  useEffect(() => {
    const root = window.document.documentElement;
    if (theme === 'dark') {
      root.classList.add('dark');
      root.classList.remove('light');
    } else {
      root.classList.add('light');
      root.classList.remove('dark');
    }
    localStorage.setItem('ba_theme', theme);
  }, [theme]);

  // Sync Projects and Documents
  useEffect(() => {
    localStorage.setItem('ba_projects', JSON.stringify(projects));
  }, [projects]);

  useEffect(() => {
    localStorage.setItem('ba_docs', JSON.stringify(documents));
  }, [documents]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  const addNotification = (message, type = 'info') => {
    const id = Math.random().toString(36).substr(2, 9);
    setNotifications(prev => [...prev, { id, message, type }]);
    
    // Automatically clear toasts after 4 seconds
    setTimeout(() => {
      setNotifications(prev => prev.filter(n => n.id !== id));
    }, 4000);
  };

  const removeNotification = (id) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  };

  /**
   * Helper to create a new project execution from Ingestion
   */
  const createProjectFromJob = (jobId, name, sourceType, targetIdentifier) => {
    const newProj = {
      id: jobId,
      name: name || 'Requirement Analysis Job',
      sourceType,
      targetIdentifier,
      createdAt: new Date().toISOString(),
      status: 'PENDING',
      storiesCount: 0,
      stories: [],
      summary: null
    };

    setProjects(prev => [newProj, ...prev]);
    
    // Add to doc list if file type
    if (sourceType === 'FILE') {
      setDocuments(prev => [
        {
          name: name || targetIdentifier.split(/[/\\]/).pop() || 'document.txt',
          type: targetIdentifier.split('.').pop() || 'txt',
          size: Math.floor(Math.random() * 5 * 1024 * 1024) + 500 * 1024, // simulated size
          uploadedAt: new Date().toISOString(),
          status: 'UPLOADING',
          jobId: jobId
        },
        ...prev
      ]);
    }
    
    return newProj;
  };

  const updateProjectStatus = (jobId, status, stories = [], summary = null) => {
    setProjects(prev => prev.map(p => {
      if (p.id === jobId) {
        return {
          ...p,
          status,
          storiesCount: stories.length,
          stories,
          summary: summary || p.summary
        };
      }
      return p;
    }));

    // Update document status too if matches
    setDocuments(prev => prev.map(d => {
      if (d.jobId === jobId) {
        return { ...d, status: status === 'COMPLETED' ? 'PROCESSED' : status };
      }
      return d;
    }));
  };

  const deleteProject = (jobId) => {
    setProjects(prev => prev.filter(p => p.id !== jobId));
    setDocuments(prev => prev.filter(d => d.jobId !== jobId));
    if (activeJobId === jobId) {
      setActiveJobId(null);
      setActiveJobStatus('IDLE');
      setActiveJobStories([]);
      setActiveJobSummary(null);
    }
    addNotification('Project deleted successfully.', 'success');
  };

  /**
   * Client-Side Single Story Regeneration Simulation
   * Since there is no backend API to patch a single story,
   * we mock it in the client state by modifying it using BA instructions.
   */
  const regenerateSingleStory = async (jobId, storyId, feedback) => {
    // 1. Mark story as loading/regenerating inside local state
    addNotification(`Regenerating story ${storyId}...`, 'info');
    
    // Create local promise to simulate latency
    await new Promise(resolve => setTimeout(resolve, 2500));

    // 2. Perform mock modifications based on user instruction
    setProjects(prev => prev.map(p => {
      if (p.id === jobId) {
        const updatedStories = p.stories.map(s => {
          if (s.id === storyId) {
            // Apply refinement based on feedback keywords
            const lowerFeedback = feedback.toLowerCase();
            let refinedStory = s.user_story;
            let refinedCriteria = [...s.acceptance_criteria];
            let businessValue = s.business_value || 'Improves flow efficiency and compliance.';

            if (lowerFeedback.includes('criteria') || lowerFeedback.includes('details') || lowerFeedback.includes('cases')) {
              refinedCriteria.push({
                rule: 'Additional Edge Case Verification',
                details: `Given refined parameters matching "${feedback}", when edge conditions occur, then transaction logs are recorded without exceptions.`
              });
            }
            if (lowerFeedback.includes('professional') || lowerFeedback.includes('rewrite') || lowerFeedback.includes('formal')) {
              refinedStory = s.user_story.replace('I want to', 'I require the capability to') + ' in strict accordance with ISO and OAuth compliance benchmarks.';
            }
            if (lowerFeedback.includes('value') || lowerFeedback.includes('business')) {
              businessValue = 'Enables direct product monetization and raises integration throughput by 35%.';
            }

            return {
              ...s,
              user_story: refinedStory,
              acceptance_criteria: refinedCriteria,
              business_value: businessValue,
              status: 'Needs Review',
              validation_results: {
                ...s.validation_results,
                quality_score: Math.min(100, (s.validation_results?.quality_score || 85) + 5)
              }
            };
          }
          return s;
        });

        // If active job is the currently loaded one, sync its workspace stories
        if (activeJobId === jobId) {
          setActiveJobStories(updatedStories);
        }

        return {
          ...p,
          stories: updatedStories
        };
      }
      return p;
    }));

    addNotification(`User Story ${storyId} regenerated successfully!`, 'success');
  };

  /**
   * ChatGPT-like summary generator
   */
  const generateMockSummary = (jobId, stories) => {
    const epics = [...new Set(stories.map(s => s.epic))];
    const features = [...new Set(stories.map(s => s.feature))];
    
    return {
      totalRequirements: Math.ceil(stories.length * 1.2),
      functionalRequirements: stories.length,
      nonFunctionalRequirements: Math.ceil(stories.length * 0.2),
      businessGoals: 'Accelerate digital transformation by resolving manual requirement extraction bottlenecks and converting text documents directly into development-ready Backlog assets.',
      modules: features,
      highPriorityCount: stories.filter(s => s.priority === 'High' || s.title?.toLowerCase().includes('auth') || Math.random() > 0.6).length || 2,
      mediumPriorityCount: Math.ceil(stories.length / 2),
      lowPriorityCount: stories.filter(s => s.priority === 'Low').length || 1,
      executiveSummary: `This project is compiled under workspace job transaction ${jobId}. It integrates ${epics.length} core Epics covering: ${epics.join(', ')}. Security check indices pass 90%+ INVEST compliance. No logical circular dependencies were identified in the Feature dependency graph.`
    };
  };

  return (
    <AppContext.Provider
      value={{
        currentPage,
        setCurrentPage,
        theme,
        toggleTheme,
        projects,
        setProjects,
        documents,
        setDocuments,
        activeJobId,
        setActiveJobId,
        activeJobStatus,
        setActiveJobStatus,
        activeJobStories,
        setActiveJobStories,
        activeJobSummary,
        setActiveJobSummary,
        activeJobLogs,
        setActiveJobLogs,
        notifications,
        addNotification,
        removeNotification,
        createProjectFromJob,
        updateProjectStatus,
        deleteProject,
        regenerateSingleStory,
        generateMockSummary
      }}
    >
      {children}
    </AppContext.Provider>
  );
};
