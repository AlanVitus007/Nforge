import React, { useState, useEffect, useCallback } from 'react';
import AdminSidebar from '../components/AdminSidebar';
import { getAdminProjects, getAdminProjectDetail } from '../services/admin';
import './AdminDashboard.css';
import './AdminProjects.css';

const AdminProjects = () => {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Search & Pagination
  const [searchTerm, setSearchTerm] = useState('');
  const [activeQuery, setActiveQuery] = useState('');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  // Detail Modal State
  const [selectedProject, setSelectedProject] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [detailError, setDetailError] = useState(null);

  const fetchProjects = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const params = {
        page,
        page_size: 10,
      };
      if (activeQuery) {
        params.search = activeQuery;
      }
      const data = await getAdminProjects(params);
      if (data && data.results) {
        setProjects(data.results);
        setTotalPages(data.total_pages || 1);
        setTotalCount(data.count || 0);
      } else if (Array.isArray(data)) {
        setProjects(data);
        setTotalPages(1);
        setTotalCount(data.length);
      } else {
        setProjects([]);
      }
    } catch (err) {
      console.error('Failed to fetch admin projects:', err);
      setError(
        err.response?.data?.detail ||
          'Failed to load projects. Ensure you have administrator permissions.'
      );
    } finally {
      setLoading(false);
    }
  }, [page, activeQuery]);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  // Handle Search submit & clear
  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    setActiveQuery(searchTerm.trim());
  };

  const handleClearSearch = () => {
    setSearchTerm('');
    setActiveQuery('');
    setPage(1);
  };

  // Inspect detail
  const handleViewProject = async (project) => {
    setSelectedProject(project);
    setLoadingDetail(true);
    setDetailError(null);
    try {
      const detail = await getAdminProjectDetail(project.id);
      setSelectedProject(detail);
    } catch (err) {
      console.error('Failed to fetch project detail:', err);
      setDetailError(
        err.response?.data?.detail || 'Failed to load complete project details.'
      );
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleCloseModal = () => {
    setSelectedProject(null);
    setDetailError(null);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '—';
    try {
      return new Date(dateStr).toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  const getRoleBadgeClass = (role) => {
    switch (role?.toUpperCase()) {
      case 'OWNER':
        return 'badge-owner';
      case 'EDITOR':
        return 'badge-editor';
      case 'VIEWER':
        return 'badge-viewer';
      default:
        return 'badge-viewer';
    }
  };

  return (
    <div className="admin-page-container animate-fade-in">
      {/* Top Banner / Breadcrumb */}
      <header className="admin-header glass-panel">
        <div className="admin-header-main">
          <div className="admin-title-group">
            <div className="admin-badge-strip">
              <span className="admin-badge admin-badge-primary">NForge Admin</span>
              <span className="admin-badge admin-badge-secondary">Project Governance</span>
            </div>
            <h1 className="admin-title">Project Management</h1>
            <p className="admin-subtitle">
              Inspect workspace portfolios, collaborative access rosters, and attached research assets.
            </p>
          </div>
        </div>
      </header>

      {/* Main Admin Content Layout */}
      <div className="admin-content-layout">
        {/* Admin Navigation Sidebar */}
        <AdminSidebar activeTab="projects" />

        {/* Center Projects Section */}
        <main className="admin-main-section">
          <div className="admin-projects-view">
            {/* Search Toolbar */}
            <div className="admin-toolbar-panel glass-panel">
              <form onSubmit={handleSearchSubmit} className="admin-search-wrapper">
                <span className="admin-search-icon">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <circle cx="11" cy="11" r="8" />
                    <line x1="21" y1="21" x2="16.65" y2="16.65" />
                  </svg>
                </span>
                <input
                  type="text"
                  className="admin-search-input"
                  placeholder="Search projects by title..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
                {searchTerm && (
                  <button
                    type="button"
                    className="admin-search-clear"
                    onClick={handleClearSearch}
                    title="Clear search"
                  >
                    ✕
                  </button>
                )}
              </form>

              <div className="admin-toolbar-stats">
                {loading ? 'Refreshing...' : `Showing ${projects.length} of ${totalCount} projects`}
              </div>
            </div>

            {/* Error State */}
            {error && (
              <div className="admin-error-panel glass-panel">
                <div className="admin-error-icon">⚠️</div>
                <div className="admin-error-message">
                  <strong>Access Restricted or Query Error</strong>
                  <p>{error}</p>
                </div>
                <button
                  type="button"
                  className="admin-btn-retry"
                  onClick={fetchProjects}
                >
                  Retry
                </button>
              </div>
            )}

            {/* Loading Skeleton */}
            {loading && !error && (
              <div className="admin-loading-container glass-panel">
                <div className="admin-spinner" />
                <p>Retrieving project directory...</p>
              </div>
            )}

            {/* Project Table */}
            {!loading && !error && (
              <>
                {projects.length === 0 ? (
                  <div className="admin-empty-state glass-panel">
                    <span className="empty-icon">📁</span>
                    <h3>No Projects Found</h3>
                    <p>
                      {activeQuery
                        ? `No projects matching "${activeQuery}". Try adjusting your search term.`
                        : 'There are currently no research projects registered in NForge.'}
                    </p>
                    {activeQuery && (
                      <button
                        type="button"
                        className="admin-btn-secondary"
                        onClick={handleClearSearch}
                      >
                        Reset Search
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="admin-table-container glass-panel">
                    <table className="admin-table">
                      <thead>
                        <tr>
                          <th>Project Title & Description</th>
                          <th>Owner</th>
                          <th>Papers</th>
                          <th>Members</th>
                          <th>Sessions</th>
                          <th>Created</th>
                          <th>Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {projects.map((proj) => (
                          <tr key={proj.id} className="admin-table-row">
                            <td>
                              <div className="project-identity-cell">
                                <span
                                  className="project-title-link"
                                  onClick={() => handleViewProject(proj)}
                                  role="button"
                                  tabIndex={0}
                                  onKeyDown={(e) => e.key === 'Enter' && handleViewProject(proj)}
                                >
                                  {proj.title}
                                </span>
                                {proj.description && (
                                  <span className="project-desc-snippet" title={proj.description}>
                                    {proj.description}
                                  </span>
                                )}
                              </div>
                            </td>
                            <td>
                              <div className="owner-chip">
                                <div className="owner-avatar-mini">
                                  {proj.owner?.username
                                    ? proj.owner.username.charAt(0).toUpperCase()
                                    : proj.owner_username
                                    ? proj.owner_username.charAt(0).toUpperCase()
                                    : 'O'}
                                </div>
                                <span className="owner-name">
                                  @{proj.owner?.username || proj.owner_username || 'Unknown'}
                                </span>
                              </div>
                            </td>
                            <td>
                              <span className="count-chip" title="Attached Papers">
                                <span className="count-chip-icon">📄</span>
                                {proj.paper_count ?? 0}
                              </span>
                            </td>
                            <td>
                              <span className="count-chip" title="Collaborators / Members">
                                <span className="count-chip-icon">👥</span>
                                {proj.member_count ?? 0}
                              </span>
                            </td>
                            <td>
                              <span className="count-chip" title="Research Sessions">
                                <span className="count-chip-icon">💬</span>
                                {proj.research_session_count ?? 0}
                              </span>
                            </td>
                            <td>{formatDate(proj.created_at)}</td>
                            <td>
                              <button
                                type="button"
                                className="btn-view-project"
                                onClick={() => handleViewProject(proj)}
                              >
                                <span>Inspect</span>
                                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                                  <path d="M5 12h14M12 5l7 7-7 7" />
                                </svg>
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Pagination Controls */}
                {totalPages > 1 && (
                  <div className="admin-pagination-bar">
                    <div className="pagination-info">
                      Page {page} of {totalPages} ({totalCount} total projects)
                    </div>
                    <div className="pagination-controls">
                      <button
                        type="button"
                        className="admin-btn-secondary"
                        disabled={page <= 1}
                        onClick={() => setPage((prev) => Math.max(prev - 1, 1))}
                      >
                        Previous
                      </button>
                      <span className="pagination-page-indicator">{page}</span>
                      <button
                        type="button"
                        className="admin-btn-secondary"
                        disabled={page >= totalPages}
                        onClick={() => setPage((prev) => Math.min(prev + 1, totalPages))}
                      >
                        Next
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </main>
      </div>

      {/* Project Detail Modal */}
      {selectedProject && (
        <div className="admin-modal-backdrop" onClick={handleCloseModal}>
          <div className="admin-detail-modal" onClick={(e) => e.stopPropagation()}>
            {/* Modal Header */}
            <div className="modal-header">
              <div className="modal-header-info">
                <span className="admin-badge admin-badge-primary">Project #{selectedProject.id}</span>
                <h3 className="modal-title-text">{selectedProject.title}</h3>
              </div>
              <button
                type="button"
                className="modal-close-btn"
                onClick={handleCloseModal}
                aria-label="Close"
              >
                ✕
              </button>
            </div>

            {/* Modal Body */}
            <div className="modal-body">
              {detailError && (
                <div className="admin-error-panel" style={{ padding: '0.75rem 1rem' }}>
                  <span>⚠️ {detailError}</span>
                </div>
              )}

              {loadingDetail ? (
                <div className="admin-loading-container" style={{ padding: '2rem' }}>
                  <div className="admin-spinner" />
                  <p>Loading project metadata and relationships...</p>
                </div>
              ) : (
                <>
                  {/* Summary & Overview Card */}
                  <div className="project-summary-card">
                    {selectedProject.description ? (
                      <p className="project-desc-full">{selectedProject.description}</p>
                    ) : (
                      <p className="project-desc-full" style={{ fontStyle: 'italic', opacity: 0.6 }}>
                        No project description provided.
                      </p>
                    )}

                    <div className="project-stats-grid">
                      <div className="project-stat-box">
                        <span className="project-stat-label">Owner</span>
                        <span className="project-stat-value" style={{ fontSize: '0.95rem' }}>
                          @{selectedProject.owner?.username || selectedProject.owner_username || 'Unknown'}
                        </span>
                      </div>
                      <div className="project-stat-box">
                        <span className="project-stat-label">Papers</span>
                        <span className="project-stat-value">
                          {selectedProject.papers?.length ?? selectedProject.paper_count ?? 0}
                        </span>
                      </div>
                      <div className="project-stat-box">
                        <span className="project-stat-label">Members</span>
                        <span className="project-stat-value">
                          {selectedProject.members?.length ?? selectedProject.member_count ?? 0}
                        </span>
                      </div>
                      <div className="project-stat-box">
                        <span className="project-stat-label">Sessions</span>
                        <span className="project-stat-value">
                          {selectedProject.research_sessions?.length ?? selectedProject.research_session_count ?? 0}
                        </span>
                      </div>
                      <div className="project-stat-box">
                        <span className="project-stat-label">Created</span>
                        <span className="project-stat-value" style={{ fontSize: '0.85rem' }}>
                          {formatDate(selectedProject.created_at)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Section 1: Members & Roles */}
                  <div>
                    <h4 className="modal-section-title">
                      <span>👥 Team Members &amp; Access Roles</span>
                    </h4>
                    {selectedProject.members && selectedProject.members.length > 0 ? (
                      <div className="modal-list-card" style={{ marginTop: '0.75rem' }}>
                        {selectedProject.members.map((m, idx) => (
                          <div key={m.id || m.user_id || idx} className="modal-list-row">
                            <div className="modal-list-row-main">
                              <span className="modal-list-item-title">@{m.username}</span>
                              {m.email && (
                                <span className="modal-list-item-sub">{m.email}</span>
                              )}
                            </div>
                            <span className={`role-badge-chip ${getRoleBadgeClass(m.role)}`}>
                              {m.role}
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="modal-empty-section" style={{ marginTop: '0.75rem' }}>
                        No invited members on this project.
                      </div>
                    )}
                  </div>

                  {/* Section 2: Attached Papers */}
                  <div>
                    <h4 className="modal-section-title">
                      <span>📄 Attached Papers</span>
                    </h4>
                    {selectedProject.papers && selectedProject.papers.length > 0 ? (
                      <div className="modal-list-card" style={{ marginTop: '0.75rem' }}>
                        {selectedProject.papers.map((p) => (
                          <div key={p.id} className="modal-list-row">
                            <div className="modal-list-row-main">
                              <span className="modal-list-item-title">{p.title}</span>
                              {p.file_name && (
                                <span className="modal-list-item-sub">File: {p.file_name}</span>
                              )}
                            </div>
                            <span className="modal-list-item-sub">
                              {formatDate(p.uploaded_at)}
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="modal-empty-section" style={{ marginTop: '0.75rem' }}>
                        No papers attached to this project.
                      </div>
                    )}
                  </div>

                  {/* Section 3: Research Sessions */}
                  <div>
                    <h4 className="modal-section-title">
                      <span>💬 Research Sessions</span>
                    </h4>
                    {selectedProject.research_sessions && selectedProject.research_sessions.length > 0 ? (
                      <div className="modal-list-card" style={{ marginTop: '0.75rem' }}>
                        {selectedProject.research_sessions.map((s) => (
                          <div key={s.id} className="modal-list-row">
                            <div className="modal-list-row-main">
                              <span className="modal-list-item-title">{s.title}</span>
                              <span className="modal-list-item-sub">
                                Last updated: {formatDate(s.updated_at || s.created_at)}
                              </span>
                            </div>
                            <span className="count-chip" title="Dialogue Turns">
                              <span className="count-chip-icon">💬</span>
                              {s.message_count ?? 0} turns
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="modal-empty-section" style={{ marginTop: '0.75rem' }}>
                        No research sessions created in this project.
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>

            {/* Modal Footer */}
            <div className="modal-footer">
              <button
                type="button"
                className="admin-btn-secondary"
                onClick={handleCloseModal}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminProjects;
