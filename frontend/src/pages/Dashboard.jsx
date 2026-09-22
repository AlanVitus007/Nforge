import React, { useContext, useEffect, useState } from 'react';
import { AuthContext } from '../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import api from '../services/api';
import Button from '../components/Button';
import './Dashboard.css';

const Dashboard = () => {
    const { user, loading: authLoading } = useContext(AuthContext);
    const navigate = useNavigate();

    const [projects, setProjects] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    
    // System diagnostic state
    const [diagnosticStatus, setDiagnosticStatus] = useState('idle'); // 'idle' | 'checking' | 'ok' | 'error'
    const [diagnosticMessage, setDiagnosticMessage] = useState('');

    useEffect(() => {
        if (!authLoading && !user) {
            navigate('/login');
        }
    }, [user, authLoading, navigate]);

    useEffect(() => {
        const fetchDashboardData = async () => {
            if (!user) return;
            try {
                setLoading(true);
                setError('');
                const res = await api.get('/projects/');
                setProjects(res.data || []);
            } catch (err) {
                console.error('Failed to fetch dashboard data', err);
                setError('Unable to load workspace data. Please check connection.');
            } finally {
                setLoading(false);
            }
        };

        fetchDashboardData();
    }, [user]);

    const runDiagnostic = async () => {
        try {
            setDiagnosticStatus('checking');
            setDiagnosticMessage('Pinging /api/auth/test/ ...');
            const response = await api.get('/auth/test/');
            setDiagnosticStatus('ok');
            setDiagnosticMessage(response.data.message || 'Authenticated successfully (200 OK)');
        } catch {
            setDiagnosticStatus('error');
            setDiagnosticMessage('Authentication check failed or token expired.');
        }
    };

    if (authLoading) {
        return (
            <div className="dashboard-container" style={{ textAlign: 'center', padding: '4rem 0' }}>
                <p style={{ color: 'var(--text-secondary)' }}>Loading research workspace...</p>
            </div>
        );
    }

    if (!user) return null;

    // Metrics computation
    const totalProjects = projects.length;
    const totalPapers = projects.reduce((acc, curr) => acc + (curr.paper_count || 0), 0);
    const recentProjects = projects.slice(0, 5);

    // Format date nicely
    const formatDate = (dateStr) => {
        if (!dateStr) return '';
        const d = new Date(dateStr);
        return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
    };

    return (
        <div className="dashboard-container animate-fade-in">
            {/* Header / Greeting Bar */}
            <header className="dashboard-hero">
                <div className="dashboard-hero-title-group">
                    <div className="dashboard-badge">
                        <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--accent-primary)' }}></span>
                        <span>Workspace Active</span>
                    </div>
                    <h1 className="dashboard-hero-title">
                        Welcome, {user.username}
                    </h1>
                    <p className="dashboard-hero-sub">
                        Overview of your literature collections, indexed papers, and synthesis tools.
                    </p>
                </div>

                <div className="dashboard-hero-actions">
                    <Button variant="secondary" onClick={() => navigate('/projects')}>
                        View All Projects
                    </Button>
                    <Button onClick={() => navigate('/projects')}>
                        <span style={{ marginRight: '0.35rem', fontWeight: 'bold' }}>+</span> New Project
                    </Button>
                </div>
            </header>

            {error && (
                <div style={{
                    padding: '0.85rem 1.25rem',
                    marginBottom: '1.75rem',
                    background: 'rgba(239, 68, 68, 0.08)',
                    border: '1px solid var(--danger)',
                    borderRadius: 'var(--radius-md)',
                    color: 'var(--danger)',
                    fontSize: '0.875rem'
                }}>
                    {error}
                </div>
            )}

            {/* Metrics Overview Strip */}
            <section className="dashboard-stats-grid">
                <div className="stat-card">
                    <div className="stat-content">
                        <span className="stat-label">Active Projects</span>
                        <span className="stat-value">{loading ? '-' : totalProjects}</span>
                    </div>
                    <div className="stat-icon-wrapper">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                        </svg>
                    </div>
                </div>

                <div className="stat-card">
                    <div className="stat-content">
                        <span className="stat-label">Papers Ingested</span>
                        <span className="stat-value">{loading ? '-' : totalPapers}</span>
                    </div>
                    <div className="stat-icon-wrapper">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                            <polyline points="14 2 14 8 20 8"></polyline>
                            <line x1="16" y1="13" x2="8" y2="13"></line>
                            <line x1="16" y1="17" x2="8" y2="17"></line>
                            <polyline points="10 9 9 9 8 9"></polyline>
                        </svg>
                    </div>
                </div>
            </section>

            {/* Recent Projects Section */}
            <section className="dashboard-section">
                <div className="section-header-bar">
                    <h3 className="section-title">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <circle cx="12" cy="12" r="10"></circle>
                            <polyline points="12 6 12 12 16 14"></polyline>
                        </svg>
                        Recent Projects
                    </h3>
                    {projects.length > 0 && (
                        <Link to="/projects" className="section-action-link">
                            <span>Manage all ({projects.length})</span>
                            <span>&rarr;</span>
                        </Link>
                    )}
                </div>

                {loading ? (
                    <div style={{ textAlign: 'center', padding: '3rem 0', color: 'var(--text-secondary)' }}>
                        Loading research projects...
                    </div>
                ) : projects.length === 0 ? (
                    <div className="dashboard-empty-projects">
                        <div style={{
                            width: '3.5rem',
                            height: '3.5rem',
                            borderRadius: '50%',
                            background: 'var(--bg-primary)',
                            border: '1px solid var(--border-color)',
                            display: 'inline-flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: 'var(--text-muted)'
                        }}>
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                            </svg>
                        </div>
                        <h4>No research projects yet</h4>
                        <p>Create your first project to begin uploading academic papers, extracting methodologies, and cross-comparing findings.</p>
                        <Button onClick={() => navigate('/projects')}>
                            Create First Project
                        </Button>
                    </div>
                ) : (
                    <div className="projects-grid">
                        {recentProjects.map((proj) => (
                            <Link 
                                to={`/projects/${proj.id}`} 
                                key={proj.id} 
                                className="project-card-item"
                            >
                                <div>
                                    <div className="project-card-top">
                                        <h4 className="project-card-title">{proj.title}</h4>
                                        <span className="project-card-arrow">&rarr;</span>
                                    </div>
                                    <p className="project-card-desc">
                                        {proj.description || "No project description provided."}
                                    </p>
                                </div>

                                <div className="project-card-footer">
                                    <span className="paper-count-badge">
                                        <span className="paper-count-dot"></span>
                                        {proj.paper_count !== undefined 
                                            ? `${proj.paper_count} ${proj.paper_count === 1 ? 'paper' : 'papers'}` 
                                            : 'Open project'}
                                    </span>
                                    <span>{formatDate(proj.created_at)}</span>
                                </div>
                            </Link>
                        ))}

                        {/* Quick create shortcut card */}
                        <div 
                            className="create-project-card" 
                            onClick={() => navigate('/projects')}
                        >
                            <div className="create-icon-bubble">
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <line x1="12" y1="5" x2="12" y2="19"></line>
                                    <line x1="5" y1="12" x2="19" y2="12"></line>
                                </svg>
                            </div>
                            <span className="create-project-label">New Research Project</span>
                            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>
                                Add papers & start synthesizing
                            </span>
                        </div>
                    </div>
                )}
            </section>

            {/* Quick Actions & Research Synthesis Tools */}
            <section className="dashboard-section">
                <div className="section-header-bar">
                    <h3 className="section-title">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
                        </svg>
                        Research Shortcuts
                    </h3>
                </div>

                <div className="quick-shortcuts-grid">
                    <Link to="/projects" className="shortcut-card">
                        <div className="shortcut-icon-box">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <line x1="12" y1="5" x2="12" y2="19"></line>
                                <line x1="5" y1="12" x2="19" y2="12"></line>
                            </svg>
                        </div>
                        <div className="shortcut-info">
                            <h5>Ingest Literature</h5>
                            <p>Upload new PDF papers to extract key findings, datasets, and methodologies.</p>
                        </div>
                    </Link>

                    <div 
                        className="shortcut-card" 
                        style={{ cursor: projects.length > 0 ? 'pointer' : 'default' }}
                        onClick={() => {
                            if (projects.length > 0) {
                                navigate(`/projects/${projects[0].id}`);
                            } else {
                                navigate('/projects');
                            }
                        }}
                    >
                        <div className="shortcut-icon-box">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                                <line x1="3" y1="9" x2="21" y2="9"></line>
                                <line x1="9" y1="21" x2="9" y2="9"></line>
                            </svg>
                        </div>
                        <div className="shortcut-info">
                            <h5>Synthesis & Comparison</h5>
                            <p>Select multiple papers across your projects to generate comparison matrices.</p>
                        </div>
                    </div>
                </div>
            </section>

            {/* Workflow Guide */}
            <section className="dashboard-section">
                <div className="workflow-guide-panel">
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span style={{ fontSize: '0.85rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-muted)' }}>
                            Synthesis Workflow
                        </span>
                    </div>

                    <div className="workflow-steps-row">
                        <div className="workflow-step">
                            <div className="step-header">
                                <span className="step-num">1</span>
                                <h4 className="step-title">Create Project</h4>
                            </div>
                            <p className="step-desc">
                                Group your papers by literature domain, thesis subject, or systematic review topic.
                            </p>
                        </div>

                        <div className="workflow-step">
                            <div className="step-header">
                                <span className="step-num">2</span>
                                <h4 className="step-title">Ingest PDFs</h4>
                            </div>
                            <p className="step-desc">
                                Drop academic papers into the project. Text, sections, and tables are parsed automatically.
                            </p>
                        </div>

                        <div className="workflow-step">
                            <div className="step-header">
                                <span className="step-num">3</span>
                                <h4 className="step-title">Cross-Synthesize</h4>
                            </div>
                            <p className="step-desc">
                                Compare methodologies and extract verifiable evidence backed by exact source coordinates.
                            </p>
                        </div>
                    </div>
                </div>
            </section>

            {/* Minimalist System Diagnostic / API status */}
            <footer className="system-diagnostic-bar">
                <div className="system-status-indicator">
                    <span className={`status-dot ${diagnosticStatus === 'error' ? 'error' : diagnosticStatus === 'ok' ? '' : 'idle'}`}></span>
                    <span>Backend Connection & Token Diagnostic</span>
                </div>

                <div className="diagnostic-actions">
                    {diagnosticMessage && (
                        <span className="diagnostic-result">{diagnosticMessage}</span>
                    )}
                    <button 
                        className="diagnostic-btn"
                        onClick={runDiagnostic}
                        disabled={diagnosticStatus === 'checking'}
                    >
                        {diagnosticStatus === 'checking' ? 'Pinging...' : 'Verify Token'}
                    </button>
                </div>
            </footer>
        </div>
    );
};

export default Dashboard;
