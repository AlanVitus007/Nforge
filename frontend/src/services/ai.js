import api from './api';

/**
 * AI API Service
 * Centralized service for AI interactions and research sessions.
 */

/**
 * Ask a research question across all papers in the active research session.
 * POST /api/ai/research-ask/
 *
 * @param {string} question - The user's research query
 * @param {number|string} sessionId - The active ResearchSession ID
 * @returns {Promise<Object>} Response object containing answer, sources, citation_map, and session_id
 */
export const askResearchSession = async (question, sessionId) => {
    const response = await api.post('/ai/research-ask/', {
        question: typeof question === 'string' ? question.trim() : question,
        session_id: sessionId,
    });
    return response.data;
};

export default {
    askResearchSession,
};
