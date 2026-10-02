import React, { useContext, useEffect, useState, useCallback } from 'react';
import { AuthContext } from '../context/AuthContext';
import { getAdminDashboardStats } from '../services/admin';
import Button from '../components/Button';
import AdminSidebar from '../components/AdminSidebar';
import './AdminDashboard.css';

const AdminDashboard = () => {
  const { user } = useContext(AuthContext);

  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchStats = useCallback(async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true);
      }
      setError('');
      const data = await getAdminDashboardStats();
      setStats(data);
      setLastUpdated(new Date());
    } catch (err) {
      console.error('Failed to fetch admin stats:', err);
      if (err.response?.status === 403) {
        setError('Access denied. You do not possess administrator credentials.');
      } else {
        setError('Failed to retrieve system telemetry. Please verify backend service.');
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  const metricCards = [
    {
      id: 'users',
      label: 'Registered Users',
      value: stats?.users ?? 0,
      description: 'Total user accounts in the platform',
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="4" />
          <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
          <path d="M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
      ),
      badge: 'Accounts',
    },
    {
      id: 'projects',
      label: 'Research Projects',
      value: stats?.projects ?? 0,
      description: 'Active research workspaces created',
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
        </svg>
      ),
      badge: 'Workspaces',
    },
    {
      id: 'papers',
      label: 'Indexed Papers',
      value: stats?.papers ?? 0,
      description: 'Extracted & indexed literature documents',
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
          <polyline points="10 9 9 9 8 9" />
        </svg>
      ),
      badge: 'Corpus',
    },
    {
      id: 'research_sessions',
      label: 'Research Sessions',
      value: stats?.research_sessions ?? 0,
      description: 'AI investigation workspaces initiated',
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polygon points="12 2 2 7 12 12 22 7 12 2" />
          <polyline points="2 17 12 22 22 17" />
          <polyline points="2 12 12 17 22 12" />
        </svg>
      ),
      badge: 'Analyses',
    },
    {
      id: 'collaborators',
      label: 'Collaborator Links',
      value: stats?.collaborators ?? 0,
      description: 'Cross-user project memberships',
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="4" />
          <line x1="19" y1="8" x2="19" y2="14" />
          <line x1="22" y1="11" x2="16" y2="11" />
        </svg>
      ),
      badge: 'Teams',
    },
    {
      id: 'research_messages',
      label: 'Research Messages',
      value: stats?.research_messages ?? 0,
      description: 'Evidence-backed researcher dialogue turns',
      icon: (
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      ),
      badge: 'Inference',
    },
  ];


  return (
    <div className="admin-page-container animate-fade-in">
      {/* Top Banner / Breadcrumb */}
      <header className="admin-header glass-panel">
        <div className="admin-header-main">
          <div className="admin-title-group">
            <div className="admin-badge-strip">
              <span className="admin-badge admin-badge-primary">NForge Admin</span>
              <span className="admin-status-indicator">
                <span className="status-dot-pulse" />
                Live Telemetry
              </span>
              {user?.is_superuser && (
                <span className="admin-badge admin-badge-super">Superuser</span>
              )}
              {user?.is_staff && !user?.is_superuser && (
                <span className="admin-badge admin-badge-staff">Staff</span>
              )}
            </div>
            <h1 className="admin-title">System Administration</h1>
            <p className="admin-subtitle">
              Centralized platform metrics, system telemetry, and governance controls.
            </p>
          </div>

          <div className="admin-actions">
            <Button
              variant="secondary"
              onClick={() => fetchStats(true)}
              disabled={refreshing || loading}
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
                className={`refresh-icon ${refreshing ? 'spinning' : ''}`}
              >
                <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
              </svg>
              {refreshing ? 'Refreshing...' : 'Refresh Metrics'}
            </Button>
          </div>
        </div>

        {lastUpdated && (
          <div className="admin-meta-bar">
            <span>Last synchronized: {lastUpdated.toLocaleTimeString()}</span>
            <span className="meta-separator">•</span>
            <span>Auth Policy: Staff / Superuser Authority</span>
            <span className="meta-separator">•</span>
            <span>Database Aggregation: O(1) Engine Queries</span>
          </div>
        )}
      </header>

      {/* Main Admin Workspace Layout */}
      <div className="admin-workspace-layout">
        {/* Navigation Sidebar */}
        <AdminSidebar activeTab="dashboard" />

        {/* Admin Content Area */}
        <main className="admin-main-view">
          {error && (
            <div className="admin-error-banner glass-panel">
              <div className="error-icon">⚠️</div>
              <div className="error-content">
                <strong>Administrative Alert:</strong> {error}
              </div>
              <Button variant="secondary" onClick={() => fetchStats(false)}>
                Retry Connection
              </Button>
            </div>
          )}

          {loading ? (
            <div className="admin-loading-view glass-panel">
              <div className="spinner" />
              <p>Gathering platform aggregate telemetry...</p>
            </div>
          ) : (
            <div className="admin-content-stack">
              {/* Metrics Grid */}
              <section className="admin-metrics-grid">
                {metricCards.map((card) => (
                  <div key={card.id} className="admin-metric-card glass-panel">
                    <div className="metric-header">
                      <div className="metric-icon-wrap">{card.icon}</div>
                      <span className="metric-pill">{card.badge}</span>
                    </div>
                    <div className="metric-body">
                      <span className="metric-number">
                        {typeof card.value === 'number' ? card.value.toLocaleString() : card.value}
                      </span>
                      <h3 className="metric-title">{card.label}</h3>
                      <p className="metric-desc">{card.description}</p>
                    </div>
                  </div>
                ))}
              </section>

              {/* System Architecture and Security Panel */}
              <section className="admin-info-section glass-panel">
                <div className="info-section-header">
                  <div className="info-title-wrap">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
                      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                    </svg>
                    <h2>Security & Telemetry Architecture</h2>
                  </div>
                  <span className="info-status-chip">Backend Authoritative</span>
                </div>

                <div className="info-grid">
                  <div className="info-block">
                    <h4>Server-Side RBAC</h4>
                    <p>
                      Enforced strictly via Django&apos;s <code>IsNForgeAdmin</code> permission handler.
                      Non-staff requests are rejected with HTTP 403 Forbidden regardless of client routing.
                    </p>
                  </div>
                  <div className="info-block">
                    <h4>Zero Content Leakage</h4>
                    <p>
                      Dashboard telemetry operates exclusively on aggregate SQL <code>COUNT(*)</code> queries.
                      No research papers, sessions, or message texts are exposed over administrative feeds.
                    </p>
                  </div>
                  <div className="info-block">
                    <h4>Collaborative Workspace Isolation</h4>
                    <p>
                      Project owners, editors, and viewers maintain scoped workspace permissions without
                      inheriting administrative authority over global platform infrastructure.
                    </p>
                  </div>
                </div>
              </section>
            </div>
          )}
        </main>
      </div>
    </div>
  );
};

export default AdminDashboard;
