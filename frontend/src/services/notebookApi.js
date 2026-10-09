import api from "./api";

/**
 * Service module for Paper-Specific Private Notebook operations.
 */

export const getPaperNotes = async (paperId) => {
    const response = await api.get(`/papers/${paperId}/notes/`);
    return response.data;
};

export const createPaperNote = async (paperId, data) => {
    const response = await api.post(`/papers/${paperId}/notes/`, data);
    return response.data;
};

export const getPaperNote = async (noteId) => {
    const response = await api.get(`/paper-notes/${noteId}/`);
    return response.data;
};

export const updatePaperNote = async (noteId, data) => {
    const response = await api.patch(`/paper-notes/${noteId}/`, data);
    return response.data;
};

export const deletePaperNote = async (noteId) => {
    const response = await api.delete(`/paper-notes/${noteId}/`);
    return response.data;
};
