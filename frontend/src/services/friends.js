import api from "./api";

/**
 * Friends API Service
 * Centralized API helper for user friendships and contact discovery.
 */

export const getFriends = async () => {
    const response = await api.get("/friends/");
    return response.data;
};

export const searchUsers = async (query) => {
    if (!query || !query.trim()) return [];
    const response = await api.get(`/friends/search/?q=${encodeURIComponent(query.trim())}`);
    return response.data;
};

export const sendFriendRequest = async (username) => {
    const response = await api.post("/friends/request/", {
        friend_username: username.trim(),
    });
    return response.data;
};

export const acceptFriendRequest = async (friendshipId) => {
    const response = await api.post(`/friends/requests/${friendshipId}/accept/`);
    return response.data;
};

export const declineFriendRequest = async (friendshipId) => {
    const response = await api.post(`/friends/requests/${friendshipId}/decline/`);
    return response.data;
};

export const removeFriend = async (friendshipId) => {
    const response = await api.delete(`/friends/${friendshipId}/`);
    return response.data;
};
