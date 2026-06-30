import React, { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { X, GitBranch, Share2, Disc, Database, CheckCircle2, ChevronRight } from 'lucide-react';
import { useApp } from '../../context/AppContext';

export default function ModalConnectors({ isOpen, type, onClose, onIngestStart }) {
  const { addNotification } = useApp();
  const [step, setStep] = useState(1); // 1 = input credentials, 2 = select target file/epic, 3 = connecting
  const [formData, setFormData] = useState({
    jiraUrl: 'https://company.atlassian.net',
    jiraUsername: 'analyst@company.com',
    jiraToken: '••••••••••••••••••••••••',
    sharepointTenant: 'company.onmicrosoft.com',
    sharepointSite: 'https://company.sharepoint.com/sites/dev',
    sharepointUser: 'analyst@company.com',
    sharepointPass: '••••••••••••',
    confluenceUrl: 'https://company.atlassian.net/wiki',
    confluenceEmail: 'analyst@company.com',
    confluenceToken: '••••••••••••••••••••••••',
    targetId: ''
  });

  const [connectedAccount, setConnectedAccount] = useState(null);

  if (!isOpen) return null;

  const handleInputChange = (field, val) => {
    setFormData(prev => ({ ...prev, [field]: val }));
  };

  const handleConnect = async (e) => {
    e.preventDefault();
    setStep(3); // show spinner

    // Latency simulation
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    setConnectedAccount(formData.jiraUsername || formData.sharepointUser || formData.confluenceEmail || 'google.analyst@company.com');
    setStep(2); // transition to choosing target identifier
    addNotification(`${type} Connected Successfully.`, 'success');
  };

  const handleIngest = (e) => {
    e.preventDefault();
    if (!formData.targetId) {
      addNotification('Please enter a target file, URL, space, or board key.', 'error');
      return;
    }

    // Call Ingest callback
    let target = formData.targetId;
    let config = {};

    if (type === 'JIRA') {
      config = { jira_url: formData.jiraUrl, username: formData.jiraUsername, api_token: formData.jiraToken };
    } else if (type === 'CONFLUENCE') {
      config = { confluence_url: formData.confluenceUrl, username: formData.confluenceEmail, api_token: formData.confluenceToken };
    } else if (type === 'SHAREPOINT') {
      config = { tenant: formData.sharepointTenant, site_url: formData.sharepointSite, username: formData.sharepointUser, password: formData.sharepointPass };
    } else if (type === 'GDRIVE') {
      config = { oauth_account: connectedAccount };
    }

    onIngestStart(type, target, config);
    onClose();
    // Reset steps
    setStep(1);
    setConnectedAccount(null);
  };

  const renderModalContent = () => {
    if (step === 3) {
      return (
        <div className="flex flex-col items-center justify-center py-12 space-y-4">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent" />
          <span className="text-xs text-slate-400 font-semibold">Testing credentials & establishing SSL tunnel...</span>
        </div>
      );
    }

    if (step === 2) {
      return (
        <form onSubmit={handleIngest} className="space-y-5">
          <div className="flex items-center space-x-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/25 p-3 text-xs text-emerald-400">
            <CheckCircle2 size={16} />
            <span>Connected Successfully as <strong>{connectedAccount}</strong></span>
          </div>

          <div className="space-y-1.5 text-left">
            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
              {type === 'JIRA' ? 'Jira Project Key / Board ID' : 
               type === 'CONFLUENCE' ? 'Space Key / Page ID' :
               type === 'SHAREPOINT' ? 'Relative Document Path (e.g. /Shared Documents/BRD.docx)' :
               'Google Drive Doc URL / File ID'}
            </label>
            <input
              type="text"
              required
              className="w-full rounded-lg border border-slate-800 bg-slate-950 p-3 text-xs text-slate-100 placeholder-slate-605 outline-none focus:border-indigo-650"
              placeholder={
                type === 'JIRA' ? 'PROJ-102 or board 4' : 
                type === 'CONFLUENCE' ? 'ENG or page 12345' :
                type === 'SHAREPOINT' ? '/documents/OAuth-Spec.docx' :
                'https://docs.google.com/document/d/...'
              }
              value={formData.targetId}
              onChange={(e) => handleInputChange('targetId', e.target.value)}
            />
          </div>

          <button
            type="submit"
            className="w-full flex items-center justify-center space-x-2 rounded-lg bg-indigo-650 p-3 text-xs font-bold text-white shadow-lg hover:bg-indigo-600 active:scale-98 transition-all"
          >
            <span>Parse & Retrieve Content</span>
            <ChevronRight size={14} />
          </button>
        </form>
      );
    }

    // Input credentials step
    switch (type) {
      case 'JIRA':
        return (
          <form onSubmit={handleConnect} className="space-y-4 text-left">
            <div className="space-y-1.5">
              <label className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">Jira Server URL</label>
              <input
                type="url"
                required
                className="w-full rounded-lg border border-slate-800 bg-slate-950 p-2.5 text-xs text-slate-100 outline-none focus:border-indigo-650"
                value={formData.jiraUrl}
                onChange={(e) => handleInputChange('jiraUrl', e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">Username / Email</label>
              <input
                type="email"
                required
                className="w-full rounded-lg border border-slate-800 bg-slate-950 p-2.5 text-xs text-slate-100 outline-none focus:border-indigo-650"
                value={formData.jiraUsername}
                onChange={(e) => handleInputChange('jiraUsername', e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">API Token</label>
              <input
                type="password"
                required
                className="w-full rounded-lg border border-slate-800 bg-slate-950 p-2.5 text-xs text-slate-100 outline-none focus:border-indigo-650"
                value={formData.jiraToken}
                onChange={(e) => handleInputChange('jiraToken', e.target.value)}
              />
            </div>
            <button
              type="submit"
              className="w-full rounded-lg bg-indigo-655 p-3 text-xs font-bold text-white hover:bg-indigo-600 transition-colors"
            >
              Establish Connection
            </button>
          </form>
        );
      case 'CONFLUENCE':
        return (
          <form onSubmit={handleConnect} className="space-y-4 text-left">
            <div className="space-y-1.5">
              <label className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">Confluence Site URL</label>
              <input
                type="url"
                required
                className="w-full rounded-lg border border-slate-800 bg-slate-950 p-2.5 text-xs text-slate-100 outline-none focus:border-indigo-650"
                value={formData.confluenceUrl}
                onChange={(e) => handleInputChange('confluenceUrl', e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">Email Address</label>
              <input
                type="email"
                required
                className="w-full rounded-lg border border-slate-800 bg-slate-950 p-2.5 text-xs text-slate-100 outline-none focus:border-indigo-650"
                value={formData.confluenceEmail}
                onChange={(e) => handleInputChange('confluenceEmail', e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">API Token</label>
              <input
                type="password"
                required
                className="w-full rounded-lg border border-slate-800 bg-slate-950 p-2.5 text-xs text-slate-100 outline-none focus:border-indigo-650"
                value={formData.confluenceToken}
                onChange={(e) => handleInputChange('confluenceToken', e.target.value)}
              />
            </div>
            <button
              type="submit"
              className="w-full rounded-lg bg-indigo-650 p-3 text-xs font-bold text-white hover:bg-indigo-600 transition-colors"
            >
              Connect Wiki space
            </button>
          </form>
        );
      case 'SHAREPOINT':
        return (
          <form onSubmit={handleConnect} className="space-y-4 text-left">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">Azure Tenant</label>
                <input
                  type="text"
                  required
                  className="w-full rounded-lg border border-slate-800 bg-slate-950 p-2.5 text-xs text-slate-100 outline-none focus:border-indigo-650"
                  value={formData.sharepointTenant}
                  onChange={(e) => handleInputChange('sharepointTenant', e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">Site URL</label>
                <input
                  type="url"
                  required
                  className="w-full rounded-lg border border-slate-800 bg-slate-950 p-2.5 text-xs text-slate-100 outline-none focus:border-indigo-650"
                  value={formData.sharepointSite}
                  onChange={(e) => handleInputChange('sharepointSite', e.target.value)}
                />
              </div>
            </div>
            <div className="space-y-1.5">
              <label className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">Username / Client ID</label>
              <input
                type="text"
                required
                className="w-full rounded-lg border border-slate-800 bg-slate-950 p-2.5 text-xs text-slate-100 outline-none focus:border-indigo-650"
                value={formData.sharepointUser}
                onChange={(e) => handleInputChange('sharepointUser', e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-[9px] font-bold text-slate-400 uppercase tracking-wider">Password / Client Secret</label>
              <input
                type="password"
                required
                className="w-full rounded-lg border border-slate-800 bg-slate-950 p-2.5 text-xs text-slate-100 outline-none focus:border-indigo-650"
                value={formData.sharepointPass}
                onChange={(e) => handleInputChange('sharepointPass', e.target.value)}
              />
            </div>
            <button
              type="submit"
              className="w-full rounded-lg bg-indigo-650 p-3 text-xs font-bold text-white hover:bg-indigo-600 transition-colors"
            >
              Verify Active Directory
            </button>
          </form>
        );
      case 'GDRIVE':
        return (
          <div className="flex flex-col items-center justify-center py-6 space-y-6">
            <div className="flex h-14 w-14 items-center justify-center rounded-full bg-slate-950 border border-slate-800">
              <Disc size={28} className="text-amber-400 animate-spin" />
            </div>
            <div className="text-center space-y-1">
              <h4 className="text-xs font-bold text-slate-200">Google OAuth Validation</h4>
              <p className="text-[10px] text-slate-500 max-w-xs">Access requirement docs securely in Google Drive using standard OAuth2 authorization scopes.</p>
            </div>
            <button
              onClick={handleConnect}
              className="flex items-center space-x-2 rounded-lg border border-slate-850 bg-slate-900 px-5 py-2.5 text-xs font-bold text-slate-200 hover:bg-slate-850 hover:text-white transition-all shadow-md"
            >
              <Disc size={14} className="text-amber-400" />
              <span>Authorize with Google Workspace</span>
            </button>
          </div>
        );
      default:
        return null;
    }
  };

  const getHeaderIcon = () => {
    switch (type) {
      case 'JIRA': return <GitBranch size={16} className="text-sky-400" />;
      case 'SHAREPOINT': return <Share2 size={16} className="text-emerald-400" />;
      case 'GDRIVE': return <Disc size={16} className="text-amber-400" />;
      case 'CONFLUENCE': return <Database size={16} className="text-blue-400" />;
      default: return null;
    }
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="absolute inset-0 bg-slate-950/75 backdrop-blur-xs"
        />

        {/* Modal Container */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 15 }}
          className="relative z-10 w-full max-w-md overflow-hidden rounded-xl border border-slate-800 bg-slate-900 shadow-2xl"
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-slate-850 bg-slate-950 px-5 py-4">
            <div className="flex items-center space-x-2 text-slate-200 font-bold text-sm">
              {getHeaderIcon()}
              <span>Connect {type}</span>
            </div>
            <button
              onClick={onClose}
              className="rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-slate-200 transition-colors"
            >
              <X size={16} />
            </button>
          </div>

          {/* Body */}
          <div className="p-5">
            {renderModalContent()}
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
