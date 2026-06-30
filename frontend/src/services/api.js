/**
 * API Service Client for BA Accelerator Backend
 * Handles direct integrations with FastAPI endpoints
 */

const getApiConfig = () => {
  const customUrl = localStorage.getItem('ba_api_url');
  const customKey = localStorage.getItem('ba_api_key');
  
  return {
    // Default to Vite proxy path '/api' in dev, or localhost:8000
    baseUrl: customUrl || 'http://localhost:8000',
    apiKey: customKey || 'ba-accelerator-secure-api-key-12345'
  };
};

export const api = {
  /**
   * Universal fetch helper injecting the custom API Key header
   */
  async request(endpoint, options = {}) {
    const { baseUrl, apiKey } = getApiConfig();
    const url = `${baseUrl}${endpoint}`;
    
    const headers = {
      'Content-Type': 'application/json',
      'X-API-KEY': apiKey,
      ...(options.headers || {})
    };
    
    const response = await fetch(url, {
      ...options,
      headers
    });
    
    if (!response.ok) {
      const errText = await response.text();
      let errMsg = `Request failed: ${response.status} ${response.statusText}`;
      try {
        const errJson = JSON.parse(errText);
        errMsg = errJson.detail || errMsg;
      } catch (e) {
        if (errText) errMsg = errText;
      }
      throw new Error(errMsg);
    }
    
    return response;
  },

  /**
   * 1. Ingest requirements from direct or remote connector sources
   * @param {string} sourceType - FILE, JIRA, CONFLUENCE, SHAREPOINT, GDRIVE
   * @param {string} targetIdentifier - File path, issue ID, page URL etc
   * @param {object} connectionConfig - Credential overrides dictionary
   */
  async ingest({ sourceType, targetIdentifier, connectionConfig }) {
    const res = await this.request('/ingest', {
      method: 'POST',
      body: JSON.stringify({
        source_type: sourceType,
        target_identifier: targetIdentifier,
        connection_config: connectionConfig || {}
      })
    });
    return res.json();
  },

  /**
   * 2. Triggers the multi-agent graph pipeline processing
   * @param {string} jobId - Ingested transaction job ID
   * @param {number} maxRetries - Maximum retry counts (defaults to 3)
   */
  async runPipeline({ jobId, maxRetries = 3 }) {
    const res = await this.request('/pipeline/run', {
      method: 'POST',
      body: JSON.stringify({
        job_id: jobId,
        max_retries: maxRetries
      })
    });
    return res.json();
  },

  /**
   * 3. Retrieves generated user stories and validation checklists
   * @param {string} jobId - Pipeline job ID
   */
  async getStories(jobId) {
    const res = await this.request(`/stories/${jobId}`);
    return res.json();
  },

  /**
   * 4. Triggers exports (JIRA, EXCEL, PDF, JSON)
   * @param {string} jobId - Pipeline job ID
   * @param {string} exportFormat - JIRA, EXCEL, PDF, or JSON
   * @param {string} projectKey - Target Jira Project key
   */
  async exportStories({ jobId, exportFormat, projectKey }) {
    const { baseUrl, apiKey } = getApiConfig();
    let url = `${baseUrl}/stories/${jobId}/export?export_format=${exportFormat}`;
    if (projectKey) {
      url += `&project_key=${projectKey}`;
    }

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'X-API-KEY': apiKey
      }
    });

    if (!response.ok) {
      const errText = await response.text();
      throw new Error(errText || 'Export failed.');
    }

    // Excel, PDF, JSON return direct files for download if no target path is supplied.
    // For Jira, it returns a JSON status object.
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json') && exportFormat.toUpperCase() === 'JIRA') {
      return response.json();
    }
    
    // Return blob for direct browser downloads
    return response.blob();
  },

  /**
   * 5. Fetches the execution audit logs
   * @param {string} jobId - Filter log logs by job transaction ID
   */
  async getAuditLogs(jobId) {
    let endpoint = '/audit/logs?limit=100';
    if (jobId) {
      endpoint += `&job_id=${jobId}`;
    }
    const res = await this.request(endpoint);
    return res.json();
  },

  /**
   * Helper to build SSE Stream EventSource URL
   */
  getStreamUrl(jobId) {
    const { baseUrl } = getApiConfig();
    return `${baseUrl}/pipeline/stream/${jobId}`;
  }
};
