import api from "./api";

/**
 * Collaboration API Service
 * Centralized API helper for team membership and project invitations.
 */

export const inviteMember = async (projectId, username, role = "VIEWER") => {
    const response = await api.post(`/projects/${projectId}/members/invite/`, {
        username: username.trim(),
        role: role.toUpperCase(),
    });
    return response.data;
};

export const getProjectMembers = async (projectId) => {
    const response = await api.get(`/projects/${projectId}/members/`);
    return response.data;
};

export const removeProjectMember = async (projectId, userId) => {
    const response = await api.delete(`/projects/${projectId}/members/${userId}/`);
    return response.data;
};

export const leaveProject = async (projectId) => {
    const response = await api.post(`/projects/${projectId}/leave/`);
    return response.data;
};

export const getInvitations = async (status = "PENDING") => {
    const response = await api.get(`/projects/invitations/?status=${encodeURIComponent(status)}`);
    return response.data;
};

export const acceptInvitation = async (invitationId) => {
    const response = await api.post(`/projects/invitations/${invitationId}/accept/`);
    return response.data;
};

export const declineInvitation = async (invitationId) => {
    const response = await api.post(`/projects/invitations/${invitationId}/decline/`);
    return response.data;
};

export const cancelInvitation = async (invitationId) => {
    const response = await api.post(`/projects/invitations/${invitationId}/cancel/`);
    return response.data;
};

/**
 * Resolve the current user's role on a given project.
 * Returns 'OWNER', 'EDITOR', 'VIEWER', or null.
 */
export const determineUserRole = (project, user, members = null) => {
    if (!project || !user) return null;

    // Check project owner username
    if (project.owner === user.username) {
        return "OWNER";
    }

    // Check project member list if provided
    if (Array.isArray(members)) {
        const found = members.find(
            (m) =>
                m.username === user.username ||
                (m.user_id && user.id && m.user_id === user.id) ||
                (m.user && user.id && m.user === user.id)
        );
        if (found && found.role) {
            return found.role; // 'EDITOR' | 'VIEWER'
        }
    }

    return "VIEWER";
};
