import React, { useContext, useEffect, useState, useCallback } from 'react';
import { AuthContext } from '../context/AuthContext';
import { getAdminUsers, getAdminUserDetail } from '../services/admin';
import AdminSidebar from '../components/AdminSidebar';
import Button from '../components/Button';
import './AdminDashboard.css';
import './AdminUsers.css';

const AdminUsers = () => {
  const { user } = useContext(AuthContext);

  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(1);
  const [paginationInfo, setPaginationInfo] = useState({
    count: 0,
    total_pages: 1,
    current_page: 1,
  });

  // Modal / User Detail State
  const [selectedUser, setSelectedUser] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [detailError, setDetailError] = useState('');

  const fetchUsers = useCallback(async (targetPage = 1, search = '') => {
    try {
      setLoading(true);
      setError('');
      const params = { page: targetPage };
      if (search.trim()) {
        params.search = search.trim();
      }
      const data = await getAdminUsers(params);
      setUsers(data.results || []);
      setPaginationInfo({
        count: data.count || 0,
        total_pages: data.total_pages || 1,
        current_page: data.current_page || targetPage,
      });
      setPage(targetPage);
    } catch (err) {
      console.error('Failed to fetch admin users:', err);
      if (err.response?.status === 403) {
        setError('Access denied. Administrator credentials required.');
      } else {
        setError('Failed to retrieve user directory. Please verify backend connection.');
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUsers(1, searchTerm);
  }, [fetchUsers, searchTerm]);

  const handleSearchChange = (e) => {
    setSearchTerm(e.target.value);
  };

  const handleClearSearch = () => {
    setSearchTerm('');
  };

  const handleOpenUserDetail = async (userId) => {
    try {
      setLoadingDetail(true);
      setDetailError('');
      setSelectedUser(null);
      const data = await getAdminUserDetail(userId);
      setSelectedUser(data);
    } catch (err) {
      console.error('Failed to fetch user details:', err);
      setDetailError('Unable to load user details. Please try again.');
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleCloseUserDetail = () => {
    setSelectedUser(null);
    setDetailError('');
  };

  const formatDate = (isoString) => {
    if (!isoString) return '—';
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="admin-page-container animate-fade-in">
      {/* Top Banner */}
      <header className="admin-header glass-panel">
        <div className="admin-header-main">
          <div className="admin-title-group">
            <div className="admin-badge-strip">
              <span className="admin-badge admin-badge-primary">NForge Admin</span>
              <span className="admin-status-indicator">
                <span className="status-dot-pulse" />
                User Directory
              </span>
              {user?.is_superuser && (
                <span className="admin-badge admin-badge-super">Superuser</span>
              )}
              {user?.is_staff && !user?.is_superuser && (
                <span className="admin-badge admin-badge-staff">Staff</span>
              )}
            </div>
            <h1 className="admin-title">User Management</h1>
            <p className="admin-subtitle">
              Inspect registered researcher accounts, platform authority, and workspace memberships.
            </p>
          </div>

          <div className="admin-actions">
            <Button
              variant="secondary"
              onClick={() => fetchUsers(page, searchTerm)}
              disabled={loading}
              className="admin-refresh-btn"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className={`refresh-icon ${loading ? 'spinning' : ''}`}
              >
                <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
              </svg>
              Refresh
            </Button>
          </div>
        </div>
      </header>

      {/* Main Admin Workspace Layout */}
      <div className="admin-workspace-layout">
        {/* Navigation Sidebar */}
        <AdminSidebar activeTab="users" />

        {/* Users Main View */}
        <main className="admin-main-view">
          {error && (
            <div className="admin-error-banner glass-panel">
              <div className="error-icon">⚠️</div>
              <div className="error-content">
                <strong>Administrative Alert:</strong> {error}
              </div>
              <Button variant="secondary" onClick={() => fetchUsers(page, searchTerm)}>
                Retry
              </Button>
            </div>
          )}

          {/* Search Toolbar */}
          <div className="admin-toolbar-panel glass-panel">
            <div className="admin-search-wrapper">
              <span className="admin-search-icon">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="11" cy="11" r="8" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
              </span>
              <input
                type="text"
                className="admin-search-input"
                placeholder="Search users by username or email..."
                value={searchTerm}
                onChange={handleSearchChange}
              />
              {searchTerm && (
                <button
                  type="button"
                  className="admin-search-clear"
                  onClick={handleClearSearch}
                  aria-label="Clear search"
                >
                  ✕
                </button>
              )}
            </div>

            <div className="admin-toolbar-stats">
              {paginationInfo.count} {paginationInfo.count === 1 ? 'user registered' : 'users registered'}
            </div>
          </div>

          {/* User Table List */}
          {loading ? (
            <div className="admin-loading-view glass-panel">
              <div className="spinner" />
              <p>Loading researcher directory...</p>
            </div>
          ) : users.length === 0 ? (
            <div className="admin-info-section glass-panel" style={{ textAlign: 'center', padding: '3.5rem 2rem' }}>
              <h3>No users found</h3>
              <p style={{ color: 'var(--text-muted)', margin: '0.5rem 0 1.5rem 0' }}>
                {searchTerm
                  ? `No user records matching "${searchTerm}". Try a different keyword.`
                  : 'No user accounts are currently present in the database.'}
              </p>
              {searchTerm && (
                <Button variant="secondary" onClick={handleClearSearch}>
                  Clear Search Filter
                </Button>
              )}
            </div>
          ) : (
            <div className="admin-table-container glass-panel">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>User</th>
                    <th>Authority & Status</th>
                    <th>Date Joined</th>
                    <th>Owned Projects</th>
                    <th>Collaborations</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((u) => (
                    <tr key={u.id} className="admin-table-row">
                      <td>
                        <div className="user-cell">
                          <div className="user-avatar-sm">
                            {u.username ? u.username.charAt(0).toUpperCase() : 'U'}
                          </div>
                          <div className="user-identity">
                            <span className="user-username">{u.username}</span>
                            <span className="user-email">{u.email || 'No email registered'}</span>
                          </div>
                        </div>
                      </td>
                      <td>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
                          {u.is_superuser && (
                            <span className="role-badge-chip badge-superuser">Superuser</span>
                          )}
                          {u.is_staff && !u.is_superuser && (
                            <span className="role-badge-chip badge-staff">Staff</span>
                          )}
                          {!u.is_staff && !u.is_superuser && (
                            <span className="role-badge-chip badge-regular">User</span>
                          )}
                          <span
                            className={`role-badge-chip ${u.is_active ? 'badge-active' : 'badge-inactive'}`}
                          >
                            {u.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </div>
                      </td>
                      <td>{formatDate(u.date_joined)}</td>
                      <td>
                        <span className="count-chip">
                          <span className="count-chip-icon">📁</span>
                          {u.project_count ?? 0}
                        </span>
                      </td>
                      <td>
                        <span className="count-chip">
                          <span className="count-chip-icon">👥</span>
                          {u.membership_count ?? 0}
                        </span>
                      </td>
                      <td>
                        <button
                          type="button"
                          className="btn-view-user"
                          onClick={() => handleOpenUserDetail(u.id)}
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                            <circle cx="12" cy="12" r="3" />
                          </svg>
                          Inspect
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {/* Pagination Controls */}
              {paginationInfo.total_pages > 1 && (
                <div className="admin-pagination-bar" style={{ padding: '1rem 1.25rem' }}>
                  <div className="pagination-info">
                    Showing page {paginationInfo.current_page} of {paginationInfo.total_pages}
                  </div>
                  <div className="pagination-controls">
                    <Button
                      variant="secondary"
                      disabled={page <= 1 || loading}
                      onClick={() => fetchUsers(page - 1, searchTerm)}
                    >
                      Previous
                    </Button>
                    <span className="pagination-page-indicator">
                      {paginationInfo.current_page} / {paginationInfo.total_pages}
                    </span>
                    <Button
                      variant="secondary"
                      disabled={page >= paginationInfo.total_pages || loading}
                      onClick={() => fetchUsers(page + 1, searchTerm)}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </main>
      </div>

      {/* User Detail Modal */}
      {(selectedUser || loadingDetail || detailError) && (
        <div className="admin-modal-backdrop" onClick={handleCloseUserDetail}>
          <div
            className="admin-detail-modal animate-fade-in"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header">
              <div className="modal-header-info">
                <div className="user-avatar-sm" style={{ width: 42, height: 42, fontSize: '1.1rem' }}>
                  {selectedUser?.username ? selectedUser.username.charAt(0).toUpperCase() : 'U'}
                </div>
                <div>
                  <h3 style={{ margin: 0, fontSize: '1.1rem', color: 'var(--text-primary)' }}>
                    {selectedUser?.username || 'User Inspection'}
                  </h3>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    {selectedUser?.email || 'User Record'}
                  </span>
                </div>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={handleCloseUserDetail}
                aria-label="Close modal"
              >
                ✕
              </button>
            </div>

            <div className="modal-body">
              {loadingDetail ? (
                <div style={{ textAlign: 'center', padding: '3rem 1rem' }}>
                  <div className="spinner" style={{ margin: '0 auto 1rem auto' }} />
                  <p style={{ color: 'var(--text-muted)' }}>Fetching user workspaces & roles...</p>
                </div>
              ) : detailError ? (
                <div className="admin-error-banner">
                  <div className="error-icon">⚠️</div>
                  <div className="error-content">{detailError}</div>
                </div>
              ) : selectedUser ? (
                <>
                  {/* Account Summary Cards */}
                  <div className="user-meta-summary-card">
                    <div className="meta-summary-item">
                      <span className="meta-summary-label">Account ID</span>
                      <span className="meta-summary-val">#{selectedUser.id}</span>
                    </div>
                    <div className="meta-summary-item">
                      <span className="meta-summary-label">Authority</span>
                      <span className="meta-summary-val">
                        {selectedUser.is_superuser
                          ? 'Superuser'
                          : selectedUser.is_staff
                          ? 'Staff Admin'
                          : 'Researcher'}
                      </span>
                    </div>
                    <div className="meta-summary-item">
                      <span className="meta-summary-label">Status</span>
                      <span className="meta-summary-val" style={{ color: selectedUser.is_active ? 'var(--success)' : 'var(--danger)' }}>
                        {selectedUser.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                    <div className="meta-summary-item">
                      <span className="meta-summary-label">Joined</span>
                      <span className="meta-summary-val">{formatDate(selectedUser.date_joined)}</span>
                    </div>
                    <div className="meta-summary-item">
                      <span className="meta-summary-label">Owned Projects</span>
                      <span className="meta-summary-val">{selectedUser.project_count ?? 0}</span>
                    </div>
                    <div className="meta-summary-item">
                      <span className="meta-summary-label">Collaborations</span>
                      <span className="meta-summary-val">{selectedUser.membership_count ?? 0}</span>
                    </div>
                  </div>

                  {/* Project Memberships */}
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                    <h4 className="modal-section-title">
                      <span>📁</span> Workspace Memberships & Roles
                    </h4>

                    {selectedUser.projects && selectedUser.projects.length > 0 ? (
                      <div className="user-projects-list">
                        {selectedUser.projects.map((proj) => (
                          <div key={proj.id} className="user-project-item">
                            <div className="project-item-main">
                              <span className="project-item-title">{proj.title}</span>
                              {proj.description && (
                                <span className="project-item-desc">{proj.description}</span>
                              )}
                            </div>
                            <div className="project-item-meta">
                              <span className="project-papers-pill">
                                {proj.paper_count} {proj.paper_count === 1 ? 'paper' : 'papers'}
                              </span>
                              <span
                                className={`role-badge-chip ${
                                  proj.role === 'OWNER'
                                    ? 'badge-owner'
                                    : proj.role === 'EDITOR'
                                    ? 'badge-editor'
                                    : 'badge-viewer'
                                }`}
                              >
                                {proj.role}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="modal-empty-projects">
                        This user is not currently an owner or collaborator in any research projects.
                      </div>
                    )}
                  </div>
                </>
              ) : null}
            </div>

            <div className="modal-footer">
              <Button variant="secondary" onClick={handleCloseUserDetail}>
                Done
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminUsers;
