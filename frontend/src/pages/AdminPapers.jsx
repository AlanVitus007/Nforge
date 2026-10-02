import React, { useState, useEffect, useCallback } from 'react';
import AdminSidebar from '../components/AdminSidebar';
import { getAdminPapers, getAdminPaperDetail } from '../services/admin';
import './AdminDashboard.css';
import './AdminPapers.css';

const AdminPapers = () => {
  const [papers, setPapers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters & Pagination
  const [searchTerm, setSearchTerm] = useState('');
  const [activeQuery, setActiveQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [projectFilter, setProjectFilter] = useState('');
  const [activeProjectId, setActiveProjectId] = useState('');

  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  // Detail Modal State
  const [selectedPaper, setSelectedPaper] = useState(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [detailError, setDetailError] = useState(null);

  const fetchPapers = useCallback(async () => {
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
      if (statusFilter) {
        params.status = statusFilter;
      }
      if (activeProjectId) {
        params.project = activeProjectId;
      }

      const data = await getAdminPapers(params);
      if (data && data.results) {
        setPapers(data.results);
        setTotalPages(data.total_pages || 1);
        setTotalCount(data.count || 0);
      } else if (Array.isArray(data)) {
        setPapers(data);
        setTotalPages(1);
        setTotalCount(data.length);
      } else {
        setPapers([]);
      }
    } catch (err) {
      console.error('Failed to fetch admin papers:', err);
      setError(
        err.response?.data?.detail ||
          'Failed to load papers. Ensure you have administrator permissions.'
      );
    } finally {
      setLoading(false);
    }
  }, [page, activeQuery, statusFilter, activeProjectId]);

  useEffect(() => {
    fetchPapers();
  }, [fetchPapers]);

  // Search submit
  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    setActiveQuery(searchTerm.trim());
    setActiveProjectId(projectFilter.trim());
  };

  const handleResetFilters = () => {
    setSearchTerm('');
    setActiveQuery('');
    setStatusFilter('');
    setProjectFilter('');
    setActiveProjectId('');
    setPage(1);
  };

  // Inspect detail
  const handleViewPaper = async (paper) => {
    setSelectedPaper(paper);
    setLoadingDetail(true);
    setDetailError(null);
    try {
      const detail = await getAdminPaperDetail(paper.id);
      setSelectedPaper(detail);
    } catch (err) {
      console.error('Failed to fetch paper detail:', err);
      setDetailError(
        err.response?.data?.detail || 'Failed to load complete paper details.'
      );
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleCloseModal = () => {
    setSelectedPaper(null);
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

  const getStatusBadge = (status) => {
    const isProc = status?.toUpperCase() === 'PROCESSED';
    return (
      <span className={`status-badge-chip ${isProc ? 'status-processed' : 'status-pending'}`}>
        <span>{isProc ? '●' : '○'}</span>
        {status || 'PENDING'}
      </span>
    );
  };

  const hasActiveFilters = Boolean(activeQuery || statusFilter || activeProjectId);

  return (
    <div className="admin-page-container animate-fade-in">
      {/* Top Banner / Breadcrumb */}
      <header className="admin-header glass-panel">
        <div className="admin-header-main">
          <div className="admin-title-group">
            <div className="admin-badge-strip">
              <span className="admin-badge admin-badge-primary">NForge Admin</span>
              <span className="admin-badge admin-badge-secondary">Paper Assets</span>
            </div>
            <h1 className="admin-title">Paper Management</h1>
            <p className="admin-subtitle">
              Inspect uploaded documents, extracted text status, and vector chunking progress across projects.
            </p>
          </div>
        </div>
      </header>

      {/* Main Admin Content Layout */}
      <div className="admin-content-layout">
        {/* Admin Navigation Sidebar */}
        <AdminSidebar activeTab="papers" />

        {/* Center Papers Section */}
        <main className="admin-main-section">
          <div className="admin-papers-view">
            {/* Filter Toolbar */}
            <div className="admin-toolbar-panel glass-panel">
              <form onSubmit={handleSearchSubmit} className="admin-filters-group">
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
                    placeholder="Search papers by title..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                  />
                  {searchTerm && (
                    <button
                      type="button"
                      className="admin-search-clear"
                      onClick={() => setSearchTerm('')}
                      title="Clear search input"
                    >
                      ✕
                    </button>
                  )}
                </div>

                <select
                  className="admin-filter-select"
                  value={statusFilter}
                  onChange={(e) => {
                    setStatusFilter(e.target.value);
                    setPage(1);
                  }}
                >
                  <option value="">All Statuses</option>
                  <option value="PROCESSED">Processed</option>
                  <option value="PENDING">Pending</option>
                </select>

                <input
                  type="text"
                  className="admin-filter-input"
                  placeholder="Project ID..."
                  value={projectFilter}
                  onChange={(e) => setProjectFilter(e.target.value)}
                  title="Filter by Project ID"
                />

                <button type="submit" className="admin-btn-secondary" style={{ padding: '0.65rem 1rem' }}>
                  Filter
                </button>

                {hasActiveFilters && (
                  <button
                    type="button"
                    className="admin-btn-secondary"
                    style={{ padding: '0.65rem 1rem' }}
                    onClick={handleResetFilters}
                  >
                    Reset
                  </button>
                )}
              </form>

              <div className="admin-toolbar-stats">
                {loading ? 'Refreshing...' : `Showing ${papers.length} of ${totalCount} papers`}
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
                  onClick={fetchPapers}
                >
                  Retry
                </button>
              </div>
            )}

            {/* Loading Skeleton */}
            {loading && !error && (
              <div className="admin-loading-container glass-panel">
                <div className="admin-spinner" />
                <p>Retrieving paper assets directory...</p>
              </div>
            )}

            {/* Papers Table */}
            {!loading && !error && (
              <>
                {papers.length === 0 ? (
                  <div className="admin-empty-state glass-panel">
                    <span className="empty-icon">📄</span>
                    <h3>No Papers Found</h3>
                    <p>
                      {hasActiveFilters
                        ? 'No papers match the specified search or filter criteria.'
                        : 'There are currently no uploaded research papers in NForge.'}
                    </p>
                    {hasActiveFilters && (
                      <button
                        type="button"
                        className="admin-btn-secondary"
                        onClick={handleResetFilters}
                      >
                        Clear All Filters
                      </button>
                    )}
                  </div>
                ) : (
                  <div className="admin-table-container glass-panel">
                    <table className="admin-table">
                      <thead>
                        <tr>
                          <th>Paper Title & File</th>
                          <th>Project & Owner</th>
                          <th>Chunks</th>
                          <th>Pages</th>
                          <th>Processing Status</th>
                          <th>Uploaded</th>
                          <th>Action</th>
                        </tr>
                      </thead>
                      <tbody>
                        {papers.map((p) => (
                          <tr key={p.id} className="admin-table-row">
                            <td>
                              <div className="paper-identity-cell">
                                <span
                                  className="paper-title-text"
                                  onClick={() => handleViewPaper(p)}
                                  role="button"
                                  tabIndex={0}
                                  onKeyDown={(e) => e.key === 'Enter' && handleViewPaper(p)}
                                >
                                  {p.title}
                                </span>
                                {p.file_name && (
                                  <span className="paper-file-sub" title={p.file_name}>
                                    {p.file_name}
                                  </span>
                                )}
                              </div>
                            </td>
                            <td>
                              <div className="paper-project-cell">
                                <span className="paper-project-title">
                                  {p.project?.title || p.project_title || `Project #${p.project_id}`}
                                </span>
                                <span className="paper-project-owner">
                                  @{p.project?.owner_username || p.project_owner || 'Owner'}
                                </span>
                              </div>
                            </td>
                            <td>
                              <span className="count-chip" title="Vector Chunks">
                                <span className="count-chip-icon">🧩</span>
                                {p.chunk_count ?? 0}
                              </span>
                            </td>
                            <td>
                              <span className="count-chip" title="Page Count">
                                <span className="count-chip-icon">📑</span>
                                {p.page_count ?? '—'}
                              </span>
                            </td>
                            <td>{getStatusBadge(p.processing_status)}</td>
                            <td>{formatDate(p.uploaded_at)}</td>
                            <td>
                              <button
                                type="button"
                                className="btn-view-paper"
                                onClick={() => handleViewPaper(p)}
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
                      Page {page} of {totalPages} ({totalCount} total papers)
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

      {/* Paper Detail Modal */}
      {selectedPaper && (
        <div className="admin-modal-backdrop" onClick={handleCloseModal}>
          <div className="admin-detail-modal" onClick={(e) => e.stopPropagation()}>
            {/* Modal Header */}
            <div className="modal-header">
              <div className="modal-header-info">
                <span className="admin-badge admin-badge-primary">Paper #{selectedPaper.id}</span>
                <h3 className="modal-title-text">{selectedPaper.title}</h3>
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
                  <p>Loading paper metadata and chunk assets...</p>
                </div>
              ) : (
                <>
                  {/* Summary Card */}
                  <div className="paper-summary-card">
                    <div className="paper-meta-grid">
                      <div className="paper-stat-box">
                        <span className="paper-stat-label">Project</span>
                        <span className="paper-stat-value">
                          {selectedPaper.project?.title || selectedPaper.project_title || `Project #${selectedPaper.project_id}`}
                        </span>
                      </div>
                      <div className="paper-stat-box">
                        <span className="paper-stat-label">Project Owner</span>
                        <span className="paper-stat-value">
                          @{selectedPaper.project?.owner_username || selectedPaper.project_owner || 'Owner'}
                        </span>
                      </div>
                      <div className="paper-stat-box">
                        <span className="paper-stat-label">Status</span>
                        <span className="paper-stat-value">
                          {getStatusBadge(selectedPaper.processing_status)}
                        </span>
                      </div>
                      <div className="paper-stat-box">
                        <span className="paper-stat-label">Total Chunks</span>
                        <span className="paper-stat-value">
                          {selectedPaper.chunk_count ?? selectedPaper.chunks?.length ?? 0}
                        </span>
                      </div>
                      <div className="paper-stat-box">
                        <span className="paper-stat-label">Page Count</span>
                        <span className="paper-stat-value">
                          {selectedPaper.page_count ?? 'N/A'}
                        </span>
                      </div>
                      <div className="paper-stat-box">
                        <span className="paper-stat-label">Extracted Text</span>
                        <span className="paper-stat-value" style={{ fontSize: '0.85rem' }}>
                          {selectedPaper.has_extracted_text
                            ? `Available (${selectedPaper.extracted_text_length} chars)`
                            : 'Not extracted'}
                        </span>
                      </div>
                      <div className="paper-stat-box">
                        <span className="paper-stat-label">File Name</span>
                        <span className="paper-stat-value" style={{ fontSize: '0.8rem', wordBreak: 'break-all' }}>
                          {selectedPaper.file_name || '—'}
                        </span>
                      </div>
                      <div className="paper-stat-box">
                        <span className="paper-stat-label">Uploaded At</span>
                        <span className="paper-stat-value" style={{ fontSize: '0.85rem' }}>
                          {formatDate(selectedPaper.uploaded_at)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Chunks Breakdown */}
                  <div>
                    <h4 className="modal-section-title">
                      <span>🧩 Vector Chunks Breakdown</span>
                    </h4>
                    {selectedPaper.chunks && selectedPaper.chunks.length > 0 ? (
                      <div className="modal-list-card" style={{ marginTop: '0.75rem', maxHeight: '280px', overflowY: 'auto' }}>
                        {selectedPaper.chunks.map((chk) => (
                          <div key={chk.id || chk.chunk_index} className="modal-list-row">
                            <div className="modal-list-row-main">
                              <span className="modal-list-item-title">
                                Chunk #{chk.chunk_index + 1}
                              </span>
                              <span className="modal-list-item-sub">
                                Page: {chk.page_number ?? 'N/A'}
                              </span>
                            </div>
                            <span className="modal-list-item-sub">
                              {formatDate(chk.created_at)}
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="modal-empty-section" style={{ marginTop: '0.75rem' }}>
                        No vector chunks generated for this paper yet.
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

export default AdminPapers;
