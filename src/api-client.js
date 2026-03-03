/**
 * AeroChat Broadcasts Module — Frontend API Client
 * ==================================================
 * React service layer for all broadcast API calls.
 * Components import from here instead of fetching directly.
 *
 * Usage:
 *   import { broadcastsApi } from './api-client';
 *   const templates = await broadcastsApi.getTemplates();
 *
 * Configuration:
 *   Set BROADCASTS_API_BASE in your environment or .env file.
 *   Default: '/api/broadcasts' (same-origin, proxied in development)
 */

// =========================================
// Configuration
// =========================================

const API_BASE = process.env.REACT_APP_BROADCASTS_API_BASE || '/api/broadcasts';

// =========================================
// HTTP Helpers
// =========================================

class ApiError extends Error {
  constructor(message, status, detail) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

/**
 * Base fetch wrapper with error handling, auth headers, and JSON parsing.
 * Your developer should add authentication headers here
 * (e.g., Bearer token from your auth system).
 */
async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;

  const config = {
    headers: {
      'Content-Type': 'application/json',
      // TODO: Add your auth header here
      // 'Authorization': `Bearer ${getAuthToken()}`,
      ...options.headers,
    },
    ...options,
  };

  // Don't set Content-Type for FormData (file uploads)
  if (options.body instanceof FormData) {
    delete config.headers['Content-Type'];
  }

  try {
    const response = await fetch(url, config);

    if (!response.ok) {
      let detail = null;
      try {
        const errorBody = await response.json();
        detail = errorBody.detail || errorBody.error || null;
      } catch {
        // Response wasn't JSON
      }
      throw new ApiError(
        `API request failed: ${response.status}`,
        response.status,
        detail
      );
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return null;
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(`Network error: ${error.message}`, 0, null);
  }
}

// =========================================
// API Methods
// =========================================

export const broadcastsApi = {
  // -----------------------------------------
  // Templates
  // -----------------------------------------

  /**
   * Fetch approved WhatsApp templates from Meta (via backend).
   * @returns {Promise<{templates: Array, cached: boolean, cached_at: string|null}>}
   */
  async getTemplates() {
    return request('/templates');
  },

  // -----------------------------------------
  // Segments / Audience
  // -----------------------------------------

  /**
   * List available audience segments.
   * @returns {Promise<{segments: Array, total_opted_in: number}>}
   */
  async getSegments() {
    return request('/segments');
  },

  // -----------------------------------------
  // CSV Upload
  // -----------------------------------------

  /**
   * Upload and parse a CSV file of phone numbers.
   * @param {File} file - The CSV file
   * @returns {Promise<{file_id: string, total_rows: number, valid_phones: number, ...}>}
   */
  async uploadCSV(file) {
    const formData = new FormData();
    formData.append('file', file);
    return request('/csv-upload', {
      method: 'POST',
      body: formData,
    });
  },

  // -----------------------------------------
  // Broadcast CRUD
  // -----------------------------------------

  /**
   * List broadcasts with filtering and pagination.
   * @param {Object} params
   * @param {string} [params.status] - Filter by status (draft|scheduled|sent|sending)
   * @param {string} [params.search] - Search by campaign name
   * @param {number} [params.page=1] - Page number
   * @param {number} [params.pageSize=25] - Items per page
   * @returns {Promise<{broadcasts: Array, total: number, page: number, ...}>}
   */
  async listBroadcasts({ status, search, page = 1, pageSize = 25 } = {}) {
    const params = new URLSearchParams();
    if (status && status !== 'all') params.set('status', status);
    if (search) params.set('search', search);
    params.set('page', String(page));
    params.set('page_size', String(pageSize));
    const qs = params.toString();
    return request(`?${qs}`);
  },

  /**
   * Get aggregate stats for the list page header.
   * @returns {Promise<{total_sent: number, avg_delivery_rate: number, ...}>}
   */
  async getStats() {
    return request('/stats');
  },

  /**
   * Create a new broadcast (saved as draft).
   * @param {Object} data - BroadcastCreate fields
   * @returns {Promise<Object>} - The created broadcast summary
   */
  async createBroadcast(data) {
    return request('', {
      method: 'POST',
      body: JSON.stringify(snakeCaseKeys(data)),
    });
  },

  /**
   * Get full broadcast detail including analytics.
   * @param {string} id - Broadcast ID
   * @returns {Promise<Object>} - Full broadcast detail
   */
  async getBroadcast(id) {
    return request(`/${id}`);
  },

  /**
   * Update a draft or scheduled broadcast.
   * @param {string} id - Broadcast ID
   * @param {Object} data - BroadcastUpdate fields
   * @returns {Promise<Object>} - Updated broadcast summary
   */
  async updateBroadcast(id, data) {
    return request(`/${id}`, {
      method: 'PUT',
      body: JSON.stringify(snakeCaseKeys(data)),
    });
  },

  /**
   * Delete a draft broadcast.
   * @param {string} id - Broadcast ID
   * @returns {Promise<{success: boolean, message: string}>}
   */
  async deleteBroadcast(id) {
    return request(`/${id}`, { method: 'DELETE' });
  },

  // -----------------------------------------
  // Broadcast Actions
  // -----------------------------------------

  /**
   * Send or schedule a broadcast.
   * @param {string} id - Broadcast ID
   * @returns {Promise<{broadcast_id: string, total_sent: number, total_failed: number, ...}>}
   */
  async sendBroadcast(id) {
    return request(`/${id}/send`, { method: 'POST' });
  },

  /**
   * Cancel a scheduled broadcast.
   * @param {string} id - Broadcast ID
   * @returns {Promise<{success: boolean, message: string}>}
   */
  async cancelBroadcast(id) {
    return request(`/${id}/cancel`, { method: 'POST' });
  },

  /**
   * Duplicate a broadcast as a new draft.
   * @param {string} id - Broadcast ID
   * @returns {Promise<Object>} - The new broadcast summary
   */
  async duplicateBroadcast(id) {
    return request(`/${id}/duplicate`, { method: 'POST' });
  },

  /**
   * Get cost estimate for a broadcast.
   * @param {string} id - Broadcast ID
   * @returns {Promise<{recipient_count: number, total_estimated_cost: number, ...}>}
   */
  async getCostEstimate(id) {
    return request(`/${id}/cost-estimate`);
  },
};

// =========================================
// Utility: camelCase → snake_case conversion
// =========================================

/**
 * Convert object keys from camelCase to snake_case for the Python API.
 * Handles nested objects and arrays.
 */
function snakeCaseKeys(obj) {
  if (Array.isArray(obj)) return obj.map(snakeCaseKeys);
  if (obj === null || typeof obj !== 'object') return obj;

  return Object.fromEntries(
    Object.entries(obj).map(([key, value]) => [
      key.replace(/[A-Z]/g, (letter) => `_${letter.toLowerCase()}`),
      snakeCaseKeys(value),
    ])
  );
}

// =========================================
// React Hooks (optional convenience layer)
// =========================================

/**
 * Usage in components:
 *
 *   import { useBroadcasts, useTemplates } from './api-client';
 *
 *   function BroadcastsList() {
 *     const { data, loading, error, refetch } = useBroadcasts({ status: 'sent' });
 *     if (loading) return <Spinner />;
 *     if (error) return <Error message={error} />;
 *     return <Table data={data.broadcasts} />;
 *   }
 */

import { useState, useEffect, useCallback } from 'react';

/**
 * Generic async data hook.
 * @param {Function} fetcher - Async function that returns data
 * @param {Array} deps - Dependencies that trigger re-fetch
 */
function useAsync(fetcher, deps = []) {
  const [state, setState] = useState({ data: null, loading: true, error: null });

  const execute = useCallback(async () => {
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const data = await fetcher();
      setState({ data, loading: false, error: null });
    } catch (err) {
      setState({ data: null, loading: false, error: err.detail || err.message });
    }
  }, deps);

  useEffect(() => {
    execute();
  }, [execute]);

  return { ...state, refetch: execute };
}

/**
 * Hook: Fetch broadcasts list with filters.
 * @param {Object} params - { status, search, page, pageSize }
 */
export function useBroadcasts(params = {}) {
  return useAsync(
    () => broadcastsApi.listBroadcasts(params),
    [params.status, params.search, params.page, params.pageSize]
  );
}

/**
 * Hook: Fetch broadcast stats.
 */
export function useBroadcastStats() {
  return useAsync(() => broadcastsApi.getStats());
}

/**
 * Hook: Fetch approved templates.
 */
export function useTemplates() {
  return useAsync(() => broadcastsApi.getTemplates());
}

/**
 * Hook: Fetch audience segments.
 */
export function useSegments() {
  return useAsync(() => broadcastsApi.getSegments());
}

/**
 * Hook: Fetch single broadcast detail.
 * @param {string} id - Broadcast ID
 */
export function useBroadcastDetail(id) {
  return useAsync(() => broadcastsApi.getBroadcast(id), [id]);
}

/**
 * Hook: Fetch cost estimate.
 * @param {string} id - Broadcast ID
 */
export function useCostEstimate(id) {
  return useAsync(() => broadcastsApi.getCostEstimate(id), [id]);
}

export default broadcastsApi;
