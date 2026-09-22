import React, { useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import Button from '../components/Button';
import './Landing.css';

const Landing = () => {
    const { user } = useContext(AuthContext);
    const navigate = useNavigate();

    // If user is already logged in, show direct workspace launch CTA
    return (
        <div className="landing-wrapper animate-fade-in">
            {/* Hero Section */}
            <section className="landing-hero">
                <div className="landing-pill">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
                    </svg>
                    <span>Academic Literature Intelligence</span>
                </div>

                <h1 className="landing-headline">
                    Synthesize literature.<br />Accelerate discoveries.
                </h1>

                <p className="landing-subhead">
                    A distraction-free workspace for researchers and academics. Ingest literature PDFs, cross-compare methodology matrices, and extract evidence grounded directly in source texts.
                </p>

                <div className="landing-cta-group">
                    {user ? (
                        <Button 
                            className="landing-cta-primary" 
                            onClick={() => navigate('/dashboard')}
                        >
                            Open Research Workspace &rarr;
                        </Button>
                    ) : (
                        <>
                            <Button 
                                className="landing-cta-primary" 
                                onClick={() => navigate('/register')}
                            >
                                Get Started Free
                            </Button>
                            <Button 
                                variant="secondary" 
                                className="landing-cta-secondary" 
                                onClick={() => navigate('/login')}
                            >
                                Sign In
                            </Button>
                        </>
                    )}
                </div>

                <div className="landing-proof-pills">
                    <div className="proof-item">
                        <span className="proof-dot"></span>
                        <span>Zero AI hallucination - Page-anchored evidence</span>
                    </div>
                    <div className="proof-item">
                        <span className="proof-dot"></span>
                        <span>Side-by-side synthesis matrix</span>
                    </div>
                    <div className="proof-item">
                        <span className="proof-dot"></span>
                        <span>Project-centric workspace</span>
                    </div>
                </div>
            </section>


            {/* Three Core Research Pillars */}
            <section className="landing-pillars">
                <div className="pillars-header">
                    <h3>Engineered for rigorous research</h3>
                    <p style={{ color: 'var(--text-secondary)' }}>Everything you need to turn piles of PDFs into structured, cited literature reviews.</p>
                </div>

                <div className="pillars-grid">
                    <div className="pillar-card">
                        <div className="pillar-icon-box">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
                                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
                            </svg>
                        </div>
                        <h4>Grounded Evidence Citations</h4>
                        <p>
                            Every summary, finding, and methodology comparison is traced back to exact PDF text snippets so you can verify claims instantly.
                        </p>
                    </div>

                    <div className="pillar-card">
                        <div className="pillar-icon-box">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                                <line x1="3" y1="9" x2="21" y2="9"></line>
                                <line x1="9" y1="21" x2="9" y2="9"></line>
                            </svg>
                        </div>
                        <h4>Cross-Paper Synthesis Matrix</h4>
                        <p>
                            Select multiple papers across a project to construct instant comparison matrices examining datasets, methods, and limitations.
                        </p>
                    </div>

                    <div className="pillar-card">
                        <div className="pillar-icon-box">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                            </svg>
                        </div>
                        <h4>Structured Research Workspaces</h4>
                        <p>
                            Keep literature grouped logically by topic, research grant, or thesis chapter, with isolated notes and shared synthesis tools.
                        </p>
                    </div>
                </div>
            </section>

            {/* Bottom Call to Action */}
            <section className="landing-bottom-cta">
                <h3>Ready to streamline your literature review?</h3>
                <p>Join researchers using NForge to synthesize academic papers faster and with greater confidence.</p>
                <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem', flexWrap: 'wrap' }}>
                    <Button onClick={() => navigate(user ? '/dashboard' : '/register')}>
                        {user ? 'Go to Dashboard' : 'Create Free Account'}
                    </Button>
                    {!user && (
                        <Button variant="secondary" onClick={() => navigate('/login')}>
                            Sign In
                        </Button>
                    )}
                </div>
            </section>
        </div>
    );
};

export default Landing;
