import React, { useState, useEffect, useCallback } from 'react';
import AdminSidebar from '../components/AdminSidebar';
import { getAdminAIUsage } from '../services/admin';
import './AdminDashboard.css';
import './AdminAIUsage.css';

const AdminAIUsage = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters & Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedOperation, setSelectedOperation] = useState('ALL');
  const [searchInput, setSearchInput] = useState('');
  const [activeSearch, setActiveSearch] = useState('');

  const fetchAIUsage = useCallback(async (page = 1, op = 'ALL', search = '') => {
    try {
      setLoading(true);
      setError(null);

      const params = { page, page_size: 10 };
      if (op && op !== 'ALL') {
        params.operation = op;
      }
      if (search && search.trim()) {
        params.search = search.trim();
      }

      const res = await getAdminAIUsage(params);
      setData(res);
    } catch (err) {
      console.error('Failed to fetch AI usage monitoring data:', err);
      setError(
        err.response?.data?.detail ||
          'Failed to load AI usage telemetry. Please ensure you have administrator privileges.'
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAIUsage(currentPage, selectedOperation, activeSearch);
  }, [fetchAIUsage, currentPage, selectedOperation, activeSearch]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setCurrentPage(1);
    setActiveSearch(searchInput);
  };

  const handleClearSearch = () => {
    setSearchInput('');
    setActiveSearch('');
    setCurrentPage(1);
  };

  const handleOperationChange = (e) => {
    setSelectedOperation(e.target.value);
    setCurrentPage(1);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '—';
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  const getOpBadgeClass = (op) => {
    switch (op) {
      case 'GAP_ANALYSIS':
        return 'ai-op-badge ai-op-gap';
      case 'COMPARE_PAPERS':
        return 'ai-op-badge ai-op-compare';
      case 'THEMATIC_ANALYSIS':
        return 'ai-op-badge ai-op-thematic';
      case 'RESEARCH_TRENDS':
        return 'ai-op-badge ai-op-trend';
      case 'ASK_AI':
      default:
        return 'ai-op-badge ai-op-ask';
    }
  };

  const getOpIcon = (op) => {
    switch (op) {
      case 'GAP_ANALYSIS':
        return '🔍';
      case 'COMPARE_PAPERS':
        return '⚖️';
      case 'THEMATIC_ANALYSIS':
        return '💡';
      case 'RESEARCH_TRENDS':
        return '📈';
      case 'ASK_AI':
      default:
        return '💬';
    }
  };

  const totalActivity = data?.total_ai_activity ?? data?.total_activity ?? 0;
  const byOp = data?.by_operation || {};
  const breakdownList = data?.operations_breakdown || [];
  const topUsers = data?.by_user || [];
  const topProjects = data?.by_project || [];
  const results = data?.results || [];

  const summaryCards = [
    {
      id: 'total',
      label: 'Total AI Activity',
      value: totalActivity,
      icon: '🤖',
    },
    {
      id: 'qna',
      label: 'Paper Q&A Turns',
      value: byOp.ASK_AI ?? 0,
      icon: '💬',
    },
    {
      id: 'compare',
      label: 'Paper Comparisons',
      value: byOp.COMPARE_PAPERS ?? 0,
      icon: '⚖️',
    },
    {
      id: 'gaps',
      label: 'Gap Analyses',
      value: byOp.GAP_ANALYSIS ?? 0,
      icon: '🔍',
    },
    {
      id: 'thematic_trend',
      label: 'Thematic & Trends',
      value: (byOp.THEMATIC_ANALYSIS ?? 0) + (byOp.RESEARCH_TRENDS ?? 0),
      icon: '📊',
    },
  ];

  return (
    <div className="admin-page-container animate-fade-in">
      {/* Header Banner */}
      <header className="admin-header glass-panel">
        <div className="admin-header-main">
          <div className="admin-title-group">
            <div className="admin-badge-strip">
              <span className="admin-badge admin-badge-primary">NForge Admin</span>
              <span className="admin-badge admin-badge-secondary">Telemetry</span>
            </div>
            <h1 className="admin-title">AI Usage Monitoring</h1>
            <p className="admin-subtitle">
              Audit AI operational volume, endpoint distribution, and collaborative researcher queries.
            </p>
          </div>
          <button
            type="button"
            className="admin-btn-secondary"
            onClick={() => fetchAIUsage(currentPage, selectedOperation, activeSearch)}
            disabled={loading}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}
          >
            <span>🔄</span>
            <span>{loading ? 'Refreshing...' : 'Refresh Telemetry'}</span>
          </button>
        </div>
      </header>

      {/* Main Content Layout */}
      <div className="admin-content-layout">
        {/* Navigation Sidebar */}
        <AdminSidebar activeTab="ai-usage" />

        {/* Center Content */}
        <main className="admin-main-section">
          <div className="admin-ai-usage-view">
            {/* Error Banner */}
            {error && (
              <div className="admin-error-banner glass-panel">
                <span className="error-icon">⚠️</span>
                <span className="error-message">{error}</span>
                <button
                  type="button"
                  className="admin-btn-secondary"
                  onClick={() => fetchAIUsage(currentPage, selectedOperation, activeSearch)}
                >
                  Retry
                </button>
              </div>
            )}

            {/* Summary Metrics Banner */}
            <section className="ai-metrics-grid">
              {summaryCards.map((card) => (
                <div key={card.id} className="ai-metric-card glass-panel">
                  <div className="ai-metric-header">
                    <span className="ai-metric-label">{card.label}</span>
                    <span className="ai-metric-icon">{card.icon}</span>
                  </div>
                  <div className="ai-metric-value">
                    {loading && !data ? '—' : card.value.toLocaleString()}
                  </div>
                </div>
              ))}
            </section>

            {/* Distribution & Breakdown Row */}
            <div className="ai-distribution-row">
              {/* Operations Breakdown Panel */}
              <div className="ai-panel glass-panel">
                <div className="ai-panel-header">
                  <div className="ai-panel-title-wrap">
                    <span className="ai-panel-icon">📊</span>
                    <h3 className="ai-panel-title">Operations Breakdown</h3>
                  </div>
                  <span className="admin-badge admin-badge-primary">
                    {totalActivity} Completed
                  </span>
                </div>
                <div className="ai-panel-body">
                  {breakdownList.map((item) => {
                    const count = item.count || 0;
                    const percent =
                      totalActivity > 0 ? Math.round((count / totalActivity) * 100) : 0;

                    let barColor = 'var(--accent-primary)';
                    if (item.operation === 'GAP_ANALYSIS') barColor = '#f59e0b';
                    if (item.operation === 'COMPARE_PAPERS') barColor = '#a855f7';
                    if (item.operation === 'THEMATIC_ANALYSIS') barColor = '#10b981';
                    if (item.operation === 'RESEARCH_TRENDS') barColor = '#ec4899';

                    return (
                      <div key={item.operation} className="ai-op-item">
                        <div className="ai-op-info">
                          <div className="ai-op-name-wrap">
                            <span>{getOpIcon(item.operation)}</span>
                            <span>{item.label}</span>
                          </div>
                          <div className="ai-op-stats">
                            <span>{count} calls</span>
                            <span style={{ fontWeight: 700 }}>{percent}%</span>
                          </div>
                        </div>
                        <div className="ai-op-bar-track">
                          <div
                            className="ai-op-bar-fill"
                            style={{
                              width: `${percent}%`,
                              backgroundColor: barColor,
                            }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Top Entities: Users & Projects */}
              <div className="ai-panel glass-panel">
                <div className="ai-panel-header">
                  <div className="ai-panel-title-wrap">
                    <span className="ai-panel-icon">👥</span>
                    <h3 className="ai-panel-title">Top Activity by Researcher</h3>
                  </div>
                  <span className="admin-badge admin-badge-secondary">Leading Projects</span>
                </div>
                <div className="ai-panel-body">
                  <div className="ai-entity-list">
                    {topUsers.length === 0 && topProjects.length === 0 ? (
                      <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                        No research activity recorded yet.
                      </div>
                    ) : (
                      topUsers.slice(0, 5).map((u) => (
                        <div key={u.user_id} className="ai-entity-item">
                          <div className="ai-entity-main">
                            <div className="ai-entity-avatar">
                              {u.username ? u.username.charAt(0).toUpperCase() : 'U'}
                            </div>
                            <span className="ai-entity-name">{u.username}</span>
                          </div>
                          <span className="ai-entity-count">{u.count} turns</span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Filter Toolbar */}
            <div className="ai-toolbar-panel glass-panel">
              <div className="ai-filters-group">
                {/* Operation Dropdown */}
                <select
                  className="ai-filter-select"
                  value={selectedOperation}
                  onChange={handleOperationChange}
                  aria-label="Filter by Operation"
                >
                  <option value="ALL">All AI Operations</option>
                  <option value="ASK_AI">Paper Q&A</option>
                  <option value="COMPARE_PAPERS">Paper Comparison</option>
                  <option value="GAP_ANALYSIS">Research Gap Analysis</option>
                  <option value="THEMATIC_ANALYSIS">Thematic Analysis</option>
                  <option value="RESEARCH_TRENDS">Trend Analysis</option>
                </select>

                {/* Search Form */}
                <form onSubmit={handleSearchSubmit} className="admin-search-wrapper">
                  <span className="admin-search-icon">🔍</span>
                  <input
                    type="text"
                    className="admin-search-input"
                    placeholder="Search session, project, owner..."
                    value={searchInput}
                    onChange={(e) => setSearchInput(e.target.value)}
                  />
                  {searchInput && (
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
              </div>

              {(selectedOperation !== 'ALL' || activeSearch) && (
                <button
                  type="button"
                  className="admin-btn-secondary"
                  onClick={() => {
                    setSelectedOperation('ALL');
                    handleClearSearch();
                  }}
                  style={{ fontSize: '0.8rem', padding: '0.5rem 0.85rem' }}
                >
                  Reset Filters
                </button>
              )}
            </div>

            {/* Activity Table Panel */}
            <div className="ai-panel glass-panel">
              <div className="ai-panel-header">
                <div className="ai-panel-title-wrap">
                  <span className="ai-panel-icon">⚡</span>
                  <h3 className="ai-panel-title">AI Activity Log</h3>
                </div>
                <span className="admin-badge admin-badge-primary">
                  {data?.count ?? 0} Records
                </span>
              </div>

              <div className="ai-table-wrapper">
                <table className="ai-table">
                  <thead>
                    <tr>
                      <th>Timestamp</th>
                      <th>Operation</th>
                      <th>Research Session & Project</th>
                      <th>Project Owner</th>
                      <th>Citations / Evidence</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {loading ? (
                      // Skeleton Loading
                      Array.from({ length: 5 }).map((_, idx) => (
                        <tr key={`skeleton-${idx}`}>
                          <td colSpan="6">
                            <div
                              style={{
                                height: '24px',
                                background: 'var(--bg-secondary)',
                                borderRadius: '4px',
                                animation: 'pulse 1.5s infinite',
                              }}
                            />
                          </td>
                        </tr>
                      ))
                    ) : results.length === 0 ? (
                      <tr>
                        <td colSpan="6">
                          <div
                            style={{
                              padding: '2.5rem',
                              textAlign: 'center',
                              color: 'var(--text-muted)',
                            }}
                          >
                            <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🤖</div>
                            <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                              No AI Activity Recorded
                            </div>
                            <div style={{ fontSize: '0.85rem', marginTop: '0.25rem' }}>
                              {selectedOperation !== 'ALL' || activeSearch
                                ? 'No entries matched your filter parameters.'
                                : 'Researcher AI queries, comparisons, and gap analyses will appear here in real time.'}
                            </div>
                          </div>
                        </td>
                      </tr>
                    ) : (
                      results.map((row) => (
                        <tr key={row.id}>
                          <td className="ai-table-time">{formatDate(row.created_at)}</td>
                          <td>
                            <span className={getOpBadgeClass(row.operation)}>
                              <span>{getOpIcon(row.operation)}</span>
                              <span>{row.operation_name}</span>
                            </span>
                          </td>
                          <td>
                            <div className="ai-table-session">
                              <span className="ai-session-title">
                                {row.session_title || `Session #${row.session_id}`}
                              </span>
                              <span className="ai-session-project">
                                📁 {row.project_title || 'Untitled Project'}
                              </span>
                            </div>
                          </td>
                          <td>
                            <div className="ai-table-user">
                              <span className="ai-entity-name">{row.username || 'System'}</span>
                            </div>
                          </td>
                          <td>
                            <span
                              className={`ai-evidence-pill ${row.has_evidence ? 'has-evidence' : ''}`}
                            >
                              <span>{row.has_evidence ? '🔬' : '—'}</span>
                              <span>
                                {row.has_evidence
                                  ? `${row.evidence_count} Citations`
                                  : 'No Citations'}
                              </span>
                            </span>
                          </td>
                          <td>
                            <span className="ai-status-pill">
                              <span>✓</span>
                              <span>Completed</span>
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>

              {/* Pagination Controls */}
              {data && data.total_pages > 1 && (
                <div
                  className="admin-pagination glass-panel"
                  style={{
                    borderTop: '1px solid var(--border-color)',
                    borderRadius: '0 0 var(--radius-xl) var(--radius-xl)',
                  }}
                >
                  <div className="pagination-info">
                    Showing page <strong>{data.current_page}</strong> of{' '}
                    <strong>{data.total_pages}</strong> ({data.count} total records)
                  </div>
                  <div className="pagination-buttons">
                    <button
                      type="button"
                      className="admin-btn-secondary"
                      disabled={!data.previous || loading}
                      onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                    >
                      Previous
                    </button>
                    <button
                      type="button"
                      className="admin-btn-secondary"
                      disabled={!data.next || loading}
                      onClick={() => setCurrentPage((p) => p + 1)}
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};

export default AdminAIUsage;
