import React, { useContext, useState, useRef, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import { ThemeContext } from '../context/ThemeContext';
import './Layout.css';
import Button from './Button';
import logo from '../assets/logo.png';

const Layout = ({ children }) => {
  const { user, logout } = useContext(AuthContext);
  const { theme, toggleTheme } = useContext(ThemeContext);
  const navigate = useNavigate();
  const location = useLocation();

  const [menuOpen, setMenuOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const menuRef = useRef(null);

  const handleLogout = () => {
    setMenuOpen(false);
    logout();
    navigate('/login');
  };

  // Close user menu on route changes
  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  // Handle click outside and Escape key to close dropdown or modal
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuOpen(false);
      }
    };

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        if (settingsOpen) {
          setSettingsOpen(false);
        } else if (menuOpen) {
          setMenuOpen(false);
        }
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [menuOpen, settingsOpen]);

  const handleNavClick = (path) => {
    setMenuOpen(false);
    navigate(path);
  };

  const handleInvitationsClick = () => {
    setMenuOpen(false);
    navigate('/dashboard');
    setTimeout(() => {
      const invElement = document.getElementById('project-invitations-section');
      if (invElement) {
        invElement.scrollIntoView({ behavior: 'smooth' });
      }
    }, 100);
  };

  const handleSettingsClick = () => {
    setMenuOpen(false);
    setSettingsOpen(true);
  };

  const getUserInitials = (username) => {
    if (!username) return 'U';
    return username.slice(0, 2).toUpperCase();
  };

  return (
    <div className="layout">
      <header className="header glass-panel">
        <div className="container header-container">
          <div className="logo-section">
            <Link to="/" className="logo">
              <img src={logo} alt="NForge Logo" className="logo-img" />
              NForge
            </Link>
          </div>
          
          <nav className="nav-links" aria-label="Main Navigation">
            {user && (
              <Link 
                to="/projects" 
                className={`nav-link ${location.pathname.startsWith('/projects') ? 'nav-link-active' : ''}`}
              >
                Projects
              </Link>
            )}
            {/* Note: API Status removed from navbar per Phase 9.3 requirements */}
          </nav>

          <div className="auth-section">
            <button 
              className="theme-toggle-btn" 
              onClick={toggleTheme} 
              aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} theme`}
              title="Toggle theme"
            >
              {theme === 'light' ? (
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>
              )}
            </button>

            {user ? (
              <div className="user-nav-wrapper" ref={menuRef}>
                <button
                  type="button"
                  className={`user-menu-trigger ${menuOpen ? 'active' : ''}`}
                  onClick={() => setMenuOpen((prev) => !prev)}
                  aria-expanded={menuOpen}
                  aria-haspopup="menu"
                  aria-label="User navigation menu"
                >
                  <span className="user-avatar-badge" aria-hidden="true">
                    {getUserInitials(user.username)}
                  </span>
                  <span className="user-menu-name">{user.username}</span>
                  <svg 
                    className={`menu-chevron ${menuOpen ? 'chevron-up' : ''}`} 
                    width="14" 
                    height="14" 
                    viewBox="0 0 24 24" 
                    fill="none" 
                    stroke="currentColor" 
                    strokeWidth="2.5"
                  >
                    <polyline points="6 9 12 15 18 9"></polyline>
                  </svg>
                </button>

                {menuOpen && (
                  <div className="user-dropdown-menu animate-fade-in" role="menu" aria-label="User menu">
                    <div className="user-dropdown-header">
                      <span className="user-dropdown-hint">Signed in as</span>
                      <strong className="user-dropdown-username">{user.username}</strong>
                    </div>

                    <div className="user-dropdown-divider" role="separator" />

                    <button
                      type="button"
                      role="menuitem"
                      className="dropdown-item"
                      onClick={() => handleNavClick('/dashboard')}
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                        <circle cx="12" cy="7" r="4"></circle>
                      </svg>
                      Profile
                    </button>

                    <button
                      type="button"
                      role="menuitem"
                      className="dropdown-item"
                      onClick={() => handleNavClick('/friends')}
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                        <circle cx="9" cy="7" r="4"></circle>
                        <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                        <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
                      </svg>
                      Friends
                    </button>

                    <button
                      type="button"
                      role="menuitem"
                      className="dropdown-item"
                      onClick={handleInvitationsClick}
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path>
                        <polyline points="22,6 12,13 2,6"></polyline>
                      </svg>
                      Invitations
                    </button>

                    <button
                      type="button"
                      role="menuitem"
                      className="dropdown-item"
                      onClick={handleSettingsClick}
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <circle cx="12" cy="12" r="3"></circle>
                        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
                      </svg>
                      Settings
                    </button>

                    {Boolean(user.is_staff || user.is_superuser) && (
                      <button
                        type="button"
                        role="menuitem"
                        className="dropdown-item admin-dropdown-item"
                        onClick={() => handleNavClick('/admin')}
                      >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                          <rect x="3" y="3" width="7" height="7"></rect>
                          <rect x="14" y="3" width="7" height="7"></rect>
                          <rect x="14" y="14" width="7" height="7"></rect>
                          <rect x="3" y="14" width="7" height="7"></rect>
                        </svg>
                        Admin Portal
                      </button>
                    )}

                    <div className="user-dropdown-divider" role="separator" />

                    <button
                      type="button"
                      role="menuitem"
                      className="dropdown-item dropdown-logout-item"
                      onClick={handleLogout}
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                        <polyline points="16 17 21 12 16 7"></polyline>
                        <line x1="21" y1="12" x2="9" y2="12"></line>
                      </svg>
                      Logout
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="auth-buttons">
                <Link to="/login" className="nav-link">Login</Link>
                <Button onClick={() => navigate('/register')}>Sign Up</Button>
              </div>
            )}
          </div>
        </div>
      </header>
      
      <main className={`main-content animate-fade-in ${location.pathname.startsWith('/research') ? 'workspace-main-content' : 'container'}`}>
        {children}
      </main>
      
      {!location.pathname.startsWith('/research') && (
        <footer className="footer">
          <div className="container">
            <p>&copy; {new Date().getFullYear()} NForge. All rights reserved.</p>
          </div>
        </footer>
      )}

      {/* Global Settings Modal */}
      {settingsOpen && (
        <div 
          className="modal-backdrop animate-fade-in" 
          onClick={() => setSettingsOpen(false)}
          role="dialog"
          aria-modal="true"
          aria-labelledby="settings-modal-title"
        >
          <div 
            className="settings-modal-content" 
            onClick={(e) => e.stopPropagation()}
          >
            <div className="modal-header">
              <h2 id="settings-modal-title" className="modal-title">Settings</h2>
              <button 
                type="button" 
                className="modal-close-btn"
                onClick={() => setSettingsOpen(false)}
                aria-label="Close settings modal"
              >
                &times;
              </button>
            </div>

            <div className="settings-modal-body">
              {/* Profile Details */}
              <div className="settings-section">
                <h3 className="settings-section-title">Researcher Account</h3>
                <div className="settings-account-details">
                  <div className="settings-detail-row">
                    <span className="settings-label">Username:</span>
                    <strong className="settings-value">{user?.username}</strong>
                  </div>
                  {user?.email && (
                    <div className="settings-detail-row">
                      <span className="settings-label">Email:</span>
                      <span className="settings-value">{user.email}</span>
                    </div>
                  )}
                  <div className="settings-detail-row">
                    <span className="settings-label">Role:</span>
                    <span className="settings-badge">
                      {user?.is_superuser ? 'Super Administrator' : user?.is_staff ? 'Staff Member' : 'Researcher'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Theme Settings */}
              <div className="settings-section">
                <h3 className="settings-section-title">Appearance</h3>
                <div className="settings-theme-toggle-row">
                  <div>
                    <strong className="settings-item-name">Interface Theme</strong>
                    <p className="settings-item-sub">Switch between Light and Dark mode</p>
                  </div>
                  <Button variant="secondary" onClick={toggleTheme}>
                    Switch to {theme === 'light' ? 'Dark' : 'Light'}
                  </Button>
                </div>
              </div>

              {/* Research Keyboard Shortcuts */}
              <div className="settings-section">
                <h3 className="settings-section-title">Research Workspace Shortcuts</h3>
                <div className="shortcuts-list">
                  <div className="shortcut-row">
                    <span>Submit Question / Prompt</span>
                    <kbd className="shortcut-kbd">Enter</kbd>
                  </div>
                  <div className="shortcut-row">
                    <span>New Line in Composer</span>
                    <kbd className="shortcut-kbd">Shift + Enter</kbd>
                  </div>
                  <div className="shortcut-row">
                    <span>Close Active Modal / Dropdown</span>
                    <kbd className="shortcut-kbd">Escape</kbd>
                  </div>
                </div>
              </div>
            </div>

            <div className="modal-footer">
              <Button onClick={() => setSettingsOpen(false)}>
                Done
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Layout;
