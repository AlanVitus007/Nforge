import React, { useState, useEffect, useCallback } from 'react';
import AdminSidebar from '../components/AdminSidebar';
import { getAdminActivity, getAdminActivityDetail } from '../services/admin';
import './AdminDashboard.css';
import './AdminActivity.css';

const AdminActivity = () => {
  const [activity, setActivity] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Activity Detail Modal State
  const [selectedActivityId, setSelectedActivityId] = useState(null);
  const [detailData, setDetailData] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState(null);

  const fetchActivity = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getAdminActivity();
      setActivity(data);
    } catch (err) {
      console.error('Failed to fetch admin activity:', err);
      setError(
        err.response?.data?.detail ||
          'Failed to load platform activity. Ensure you have administrator permissions.'
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchActivity();
  }, [fetchActivity]);

  const fetchActivityDetail = useCallback(async (messageId) => {
    if (!messageId) return;
    try {
      setDetailLoading(true);
      setDetailError(null);
      const data = await getAdminActivityDetail(messageId);
      setDetailData(data);
    } catch (err) {
      console.error('Failed to fetch activity detail:', err);
      setDetailError(
        err.response?.data?.detail ||
          'Failed to load activity details. Ensure you have administrator permissions.'
      );
    } finally {
      setDetailLoading(false);
    }
  }, []);

  const handleOpenDetail = (messageId) => {
    setSelectedActivityId(messageId);
    fetchActivityDetail(messageId);
  };

  const handleCloseDetail = () => {
    setSelectedActivityId(null);
    setDetailData(null);
    setDetailError(null);
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

  const metrics = [
    {
      id: 'users',
      label: 'Registered Users',
      value: activity?.total_users ?? activity?.users ?? 0,
      icon: '👥',
    },
    {
      id: 'projects',
      label: 'Research Projects',
      value: activity?.total_projects ?? activity?.projects ?? 0,
      icon: '📁',
    },
    {
      id: 'papers',
      label: 'Uploaded Papers',
      value: activity?.total_papers ?? activity?.papers ?? 0,
      icon: '📄',
    },
    {
      id: 'sessions',
      label: 'Research Sessions',
      value: activity?.total_research_sessions ?? activity?.research_sessions ?? 0,
      icon: '🔬',
    },
    {
      id: 'messages',
      label: 'Dialogue Turns',
      value: activity?.total_research_messages ?? activity?.research_messages ?? 0,
      icon: '💬',
    },
  ];

  const recentUsers = activity?.recent_users || activity?.recent_user_registrations || [];
  const recentPapers = activity?.recent_papers || activity?.recently_uploaded_papers || [];
  const recentSessions = activity?.recent_research_sessions || activity?.recently_updated_research_sessions || [];
  const recentTurns = activity?.recent_activity || activity?.recent_messages || [];

  return (
    <div className="admin-page-container animate-fade-in">
      {/* Top Banner / Breadcrumb */}
      <header className="admin-header glass-panel">
        <div className="admin-header-main">
          <div className="admin-title-group">
            <div className="admin-badge-strip">
              <span className="admin-badge admin-badge-primary">NForge Admin</span>
              <span className="admin-badge admin-badge-secondary">Realtime Stream</span>
            </div>
            <h1 className="admin-title">Activity Overview</h1>
            <p className="admin-subtitle">
              Audit live researcher registrations, document uploads, and collaborative inquiry turns.
            </p>
          </div>
          <button
            type="button"
            className="admin-btn-secondary"
            onClick={fetchActivity}
            disabled={loading}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}
          >
            <span>🔄</span>
            <span>{loading ? 'Refreshing...' : 'Refresh Activity'}</span>
          </button>
        </div>
      </header>

      {/* Main Admin Content Layout */}
      <div className="admin-content-layout">
        {/* Admin Navigation Sidebar */}
        <AdminSidebar activeTab="activity" />

        {/* Center Activity Content */}
        <main className="admin-main-section">
          <div className="admin-activity-view">
            {/* Error State */}
            {error && (
              <div className="admin-error-panel glass-panel">
                <div className="admin-error-icon">⚠️</div>
                <div className="admin-error-message">
                  <strong>Access Restricted or Retrieval Error</strong>
                  <p>{error}</p>
                </div>
                <button
                  type="button"
                  className="admin-btn-retry"
                  onClick={fetchActivity}
                >
                  Retry
                </button>
              </div>
            )}

            {/* Loading Skeleton */}
            {loading && !error && (
              <div className="admin-loading-container glass-panel">
                <div className="admin-spinner" />
                <p>Retrieving real-time platform telemetry...</p>
              </div>
            )}

            {/* Content when loaded */}
            {!loading && !error && (
              <>
                {/* Aggregate Metrics Grid */}
                <div className="activity-metrics-grid">
                  {metrics.map((m) => (
                    <div key={m.id} className="activity-metric-card glass-panel">
                      <div className="activity-metric-header">
                        <span className="activity-metric-label">{m.label}</span>
                        <span className="activity-metric-icon">{m.icon}</span>
                      </div>
                      <div className="activity-metric-value">{m.value}</div>
                    </div>
                  ))}
                </div>

                {/* Recent Dialogue & AI Activity Turns (Clickable for Detail Inspection) */}
                {recentTurns.length > 0 && (
                  <div className="activity-section-panel glass-panel">
                    <div className="activity-section-header">
                      <div className="activity-section-title-wrap">
                        <span className="activity-section-icon">⚡</span>
                        <h3 className="activity-section-title">Recent Inquiry & AI Operations</h3>
                      </div>
                      <span className="activity-badge-count">{recentTurns.length} events</span>
                    </div>

                    <div className="activity-list-content">
                      {recentTurns.map((turn) => (
                        <div
                          key={turn.id}
                          className="activity-item-row clickable"
                          onClick={() => handleOpenDetail(turn.id)}
                          title="Click to inspect activity details"
                        >
                          <div className="activity-user-flex">
                            <span className={getOpBadgeClass(turn.operation)}>
                              <span>{getOpIcon(turn.operation)}</span>
                              <span>{turn.operation_name}</span>
                            </span>
                            <div className="activity-item-main">
                              <span className="activity-item-title">
                                {turn.session_title || `Session #${turn.session_id}`}
                              </span>
                              <span className="activity-item-sub">
                                in {turn.project_title || 'Untitled Project'} • @{turn.username || 'Researcher'}
                              </span>
                            </div>
                          </div>

                          <div className="activity-item-meta" style={{ gap: '0.75rem' }}>
                            <span className="activity-item-time">{formatDate(turn.created_at)}</span>
                            {turn.has_evidence && (
                              <span className="activity-item-pill" style={{ color: 'var(--accent-primary)' }}>
                                🔬 {turn.evidence_count} citations
                              </span>
                            )}
                            <button
                              type="button"
                              className="activity-inspect-btn"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleOpenDetail(turn.id);
                              }}
                            >
                              Inspect Details
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 3 Activity Columns */}
                <div className="activity-sections-grid">
                  {/* Column 1: Recent Users */}
                  <div className="activity-section-panel glass-panel">
                    <div className="activity-section-header">
                      <div className="activity-section-title-wrap">
                        <span className="activity-section-icon">👥</span>
                        <h3 className="activity-section-title">New Users</h3>
                      </div>
                      <span className="activity-badge-count">{recentUsers.length}</span>
                    </div>

                    <div className="activity-list-content">
                      {recentUsers.length === 0 ? (
                        <div className="activity-empty-list">
                          <span>👤</span>
                          <p>No recent user registrations</p>
                        </div>
                      ) : (
                        recentUsers.map((u) => (
                          <div key={u.id} className="activity-item-row">
                            <div className="activity-user-flex">
                              <div className="activity-user-avatar">
                                {u.username ? u.username.charAt(0).toUpperCase() : 'U'}
                              </div>
                              <div className="activity-item-main">
                                <span className="activity-item-title">@{u.username}</span>
                                <span className="activity-item-sub">{u.email || 'No email provided'}</span>
                              </div>
                            </div>
                            <div className="activity-item-meta">
                              <span className="activity-item-time">{formatDate(u.date_joined)}</span>
                              {u.is_active ? (
                                <span className="activity-item-pill" style={{ color: 'var(--success)' }}>
                                  Active
                                </span>
                              ) : (
                                <span className="activity-item-pill" style={{ color: 'var(--danger)' }}>
                                  Inactive
                                </span>
                              )}
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>

                  {/* Column 2: Recent Papers */}
                  <div className="activity-section-panel glass-panel">
                    <div className="activity-section-header">
                      <div className="activity-section-title-wrap">
                        <span className="activity-section-icon">📄</span>
                        <h3 className="activity-section-title">Uploaded Papers</h3>
                      </div>
                      <span className="activity-badge-count">{recentPapers.length}</span>
                    </div>

                    <div className="activity-list-content">
                      {recentPapers.length === 0 ? (
                        <div className="activity-empty-list">
                          <span>📄</span>
                          <p>No recently uploaded papers</p>
                        </div>
                      ) : (
                        recentPapers.map((p) => (
                          <div key={p.id} className="activity-item-row">
                            <div className="activity-item-main">
                              <span className="activity-item-title" title={p.title}>
                                {p.title}
                              </span>
                              <span className="activity-item-sub">
                                in {p.project_title || `Project #${p.project_id}`} • @{p.owner_username || 'Owner'}
                              </span>
                            </div>
                            <div className="activity-item-meta">
                              <span className="activity-item-time">{formatDate(p.uploaded_at)}</span>
                              {p.file_name && (
                                <span className="activity-item-pill" title={p.file_name}>
                                  PDF
                                </span>
                              )}
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>

                  {/* Column 3: Recent Research Sessions */}
                  <div className="activity-section-panel glass-panel">
                    <div className="activity-section-header">
                      <div className="activity-section-title-wrap">
                        <span className="activity-section-icon">🔬</span>
                        <h3 className="activity-section-title">Active Sessions</h3>
                      </div>
                      <span className="activity-badge-count">{recentSessions.length}</span>
                    </div>

                    <div className="activity-list-content">
                      {recentSessions.length === 0 ? (
                        <div className="activity-empty-list">
                          <span>💬</span>
                          <p>No active research sessions</p>
                        </div>
                      ) : (
                        recentSessions.map((s) => (
                          <div key={s.id} className="activity-item-row">
                            <div className="activity-item-main">
                              <span className="activity-item-title" title={s.title}>
                                {s.title}
                              </span>
                              <span className="activity-item-sub">
                                in {s.project_title || `Project #${s.project_id}`}
                              </span>
                            </div>
                            <div className="activity-item-meta">
                              <span className="activity-item-time">{formatDate(s.updated_at || s.created_at)}</span>
                              <span className="activity-item-pill">
                                💬 {s.message_count ?? 0} turns
                              </span>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        </main>
      </div>

      {/* Activity Detail Inspection Modal */}
      {selectedActivityId && (
        <div className="admin-modal-backdrop" onClick={handleCloseDetail}>
          <div
            className="admin-modal-container glass-panel"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="activity-modal-title"
          >
            {/* Modal Header */}
            <div className="admin-modal-header">
              <div className="admin-modal-title-group">
                <span style={{ fontSize: '1.25rem' }}>
                  {detailData ? getOpIcon(detailData.operation) : '⚡'}
                </span>
                <h2 id="activity-modal-title" className="admin-modal-title">
                  {detailData ? `${detailData.operation_name} #${detailData.id}` : `Activity #${selectedActivityId}`}
                </h2>
                {detailData && (
                  <span className={getOpBadgeClass(detailData.operation)}>
                    {detailData.operation}
                  </span>
                )}
              </div>
              <button
                type="button"
                className="admin-modal-close"
                onClick={handleCloseDetail}
                aria-label="Close dialog"
              >
                ✕
              </button>
            </div>

            {/* Modal Body */}
            <div className="admin-modal-body">
              {/* Privacy Notice Banner */}
              <div className="admin-privacy-banner">
                <span className="admin-privacy-icon">🛡️</span>
                <div>
                  <strong>Research Privacy Safeguard Active</strong>
                  <p style={{ margin: '0.2rem 0 0 0' }}>
                    Private research dialogue content, user prompts, assistant answers, and evidence texts
                    are intentionally excluded to protect researcher intellectual property.
                  </p>
                </div>
              </div>

              {/* Loading State */}
              {detailLoading && (
                <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                  <div className="admin-spinner" style={{ margin: '0 auto 1rem auto' }} />
                  <p>Retrieving activity metadata...</p>
                </div>
              )}

              {/* Error State */}
              {detailError && (
                <div className="admin-error-panel glass-panel">
                  <div className="admin-error-icon">⚠️</div>
                  <div className="admin-error-message">
                    <strong>Failed to Load Activity Detail</strong>
                    <p>{detailError}</p>
                  </div>
                  <button
                    type="button"
                    className="admin-btn-retry"
                    onClick={() => fetchActivityDetail(selectedActivityId)}
                  >
                    Retry
                  </button>
                </div>
              )}

              {/* Detail Content */}
              {!detailLoading && !detailError && detailData && (
                <>
                  {/* Metadata Grid */}
                  <div className="detail-meta-grid">
                    <div className="detail-meta-card">
                      <span className="detail-meta-label">Operation Type</span>
                      <span className="detail-meta-value">
                        <span>{getOpIcon(detailData.operation)}</span>
                        <span>{detailData.operation_name}</span>
                      </span>
                    </div>

                    <div className="detail-meta-card">
                      <span className="detail-meta-label">Researcher</span>
                      <span className="detail-meta-value">
                        <span>@{detailData.username}</span>
                        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                          ({detailData.user_role})
                        </span>
                      </span>
                    </div>

                    <div className="detail-meta-card">
                      <span className="detail-meta-label">Project</span>
                      <span className="detail-meta-value" title={detailData.project_title}>
                        📁 {detailData.project_title || 'Untitled Project'}
                      </span>
                    </div>

                    <div className="detail-meta-card">
                      <span className="detail-meta-label">Research Session</span>
                      <span className="detail-meta-value" title={detailData.session_title}>
                        🔬 {detailData.session_title || `Session #${detailData.session_id}`}
                      </span>
                    </div>

                    <div className="detail-meta-card">
                      <span className="detail-meta-label">Event Timestamp</span>
                      <span className="detail-meta-value">
                        {formatDate(detailData.created_at)}
                      </span>
                    </div>

                    <div className="detail-meta-card">
                      <span className="detail-meta-label">Execution Status</span>
                      <span className="detail-meta-value" style={{ color: 'var(--success)' }}>
                        ✓ {detailData.status}
                      </span>
                    </div>

                    <div className="detail-meta-card">
                      <span className="detail-meta-label">Evidence / Citations</span>
                      <span className="detail-meta-value">
                        {detailData.has_evidence
                          ? `🔬 ${detailData.evidence_count} Citations`
                          : 'No Citations Linked'}
                      </span>
                    </div>

                    <div className="detail-meta-card">
                      <span className="detail-meta-label">Message Turn</span>
                      <span className="detail-meta-value">
                        {detailData.role === 'ASSISTANT' ? '🤖 Assistant Turn' : '👤 User Prompt'}
                      </span>
                    </div>
                  </div>

                  {/* Related Papers Subsection */}
                  <div className="detail-subsection">
                    <span className="detail-subsection-title">
                      <span>📄</span>
                      <span>Referenced Workspace Papers ({detailData.related_papers?.length || 0})</span>
                    </span>
                    <div className="detail-chips-list">
                      {!detailData.related_papers || detailData.related_papers.length === 0 ? (
                        <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
                          No specific paper bindings associated with this turn.
                        </div>
                      ) : (
                        detailData.related_papers.map((p) => (
                          <div key={p.id} className="detail-paper-chip">
                            <span className="detail-paper-title">{p.title}</span>
                            <span className="detail-paper-meta">
                              {p.file_name && <span>{p.file_name} • </span>}
                              <span>{formatDate(p.uploaded_at)}</span>
                            </span>
                          </div>
                        ))
                      )}
                    </div>
                  </div>

                  {/* Citations Subsection */}
                  {detailData.citations && detailData.citations.length > 0 && (
                    <div className="detail-subsection">
                      <span className="detail-subsection-title">
                        <span>📌</span>
                        <span>Evidence Citations ({detailData.citations.length})</span>
                      </span>
                      <div className="detail-chips-list">
                        {detailData.citations.map((c, idx) => (
                          <div key={`${c.citation_id}-${idx}`} className="detail-citation-chip">
                            <span className="detail-citation-id">{c.citation_id}</span>
                            <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
                              {c.paper_title || `Paper #${c.paper_id}`}
                            </span>
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>
                              {c.page_number ? `Page ${c.page_number}` : 'Full Document'}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Modal Footer */}
            <div className="admin-modal-footer">
              <button
                type="button"
                className="admin-btn-secondary"
                onClick={handleCloseDetail}
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminActivity;
