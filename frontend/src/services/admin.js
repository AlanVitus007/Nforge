import api from './api';

export const getAdminDashboardStats = async () => {
  const response = await api.get('/admin/dashboard/');
  return response.data;
};
