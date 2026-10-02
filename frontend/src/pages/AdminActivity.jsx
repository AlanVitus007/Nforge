import React, { useState, useEffect, useCallback } from 'react';
import AdminSidebar from '../components/AdminSidebar';
import { getAdminActivity } from '../services/admin';
import './AdminDashboard.css';
import './AdminActivity.css';

const AdminActivity = () => {
  const [activity, setActivity] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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
                        <span className="activity-section-icon">⚡</span>
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
    </div>
  );
};

export default AdminActivity;
