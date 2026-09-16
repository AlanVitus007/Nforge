import React, { useContext, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import { ThemeContext } from '../context/ThemeContext';
import './Layout.css';
import Button from './Button';
import logo from '../assets/logo.png';

const Layout = ({ children }) => {
  const { user, logout } = useContext(AuthContext);
  const { theme, toggleTheme } = useContext(ThemeContext);
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
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
          
          <nav className="nav-links">
            <Link to="/projects" className="nav-link">Projects</Link>
            <Link to="/backend-test" className="nav-link">API Status</Link>
          </nav>

          <div className="auth-section">
            <button 
              className="theme-toggle-btn" 
              onClick={toggleTheme} 
              aria-label="Toggle Theme"
            >
              {theme === 'light' ? (
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>
              )}
            </button>
            {user ? (
              <div className="user-menu">
                <Link to="/dashboard" className="nav-link dashboard-link">Dashboard</Link>
                <Button variant="secondary" onClick={handleLogout} className="logout-btn">
                  Logout
                </Button>
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
      
      <main className="main-content container animate-fade-in">
        {children}
      </main>
      
      <footer className="footer">
        <div className="container">
          <p>&copy; {new Date().getFullYear()} NForge. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
};

export default Layout;
