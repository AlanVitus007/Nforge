import api from './api';

export const getAdminDashboardStats = async () => {
  const response = await api.get('/admin/dashboard/');
  return response.data;
};

export const getAdminUsers = async (params = {}) => {
  const response = await api.get('/admin/users/', { params });
  return response.data;
};

export const getAdminUserDetail = async (userId) => {
  const response = await api.get(`/admin/users/${userId}/`);
  return response.data;
};

export const getAdminProjects = async (params = {}) => {
  const response = await api.get('/admin/projects/', { params });
  return response.data;
};

export const getAdminProjectDetail = async (projectId) => {
  const response = await api.get(`/admin/projects/${projectId}/`);
  return response.data;
};

