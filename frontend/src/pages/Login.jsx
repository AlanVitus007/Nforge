import React, { useState, useContext } from 'react';
import { AuthContext } from '../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import Input from '../components/Input';
import Button from '../components/Button';
import './Auth.css';

const Login = () => {
    const [identifier, setIdentifier] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [fieldErrors, setFieldErrors] = useState({});
    const [submitting, setSubmitting] = useState(false);
    const [showForgotNotice, setShowForgotNotice] = useState(false);

    const { login } = useContext(AuthContext);
    const navigate = useNavigate();

    const validateForm = () => {
        const errors = {};
        if (!identifier.trim()) {
            errors.identifier = 'Please enter your username or email address.';
        }
        if (!password) {
            errors.password = 'Please enter your password.';
        }
        setFieldErrors(errors);
        return Object.keys(errors).length === 0;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');

        if (!validateForm() || submitting) {
            return;
        }

        setSubmitting(true);
        try {
            await login(identifier.trim(), password);
            navigate('/dashboard');
        } catch (err) {
            const data = err.response?.data;
            let msg = '';
            if (data) {
                if (typeof data === 'string') {
                    msg = data;
                } else if (data.error) {
                    msg = data.error;
                } else if (data.detail) {
                    msg = data.detail;
                } else if (data.non_field_errors?.[0]) {
                    msg = data.non_field_errors[0];
                } else {
                    const firstVal = Object.values(data)[0];
                    if (Array.isArray(firstVal) && firstVal[0]) {
                        msg = firstVal[0];
                    } else if (typeof firstVal === 'string') {
                        msg = firstVal;
                    }
                }
            } else if (err.message) {
                msg = `Network error (${err.message}). Verify backend server is running and reachable.`;
            }
            setError(msg || 'Invalid username, email, or password. Please try again.');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="auth-page">
            <div className="auth-card">
                <div className="auth-header">
                    <span className="auth-brand-badge">NForge Research</span>
                    <h2 className="auth-title">Welcome Back</h2>
                    <p className="auth-subtitle">Sign in to access your projects and research workspace</p>
                </div>

                {error && (
                    <div className="auth-alert auth-alert-error" role="alert">
                        <svg className="auth-alert-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <circle cx="12" cy="12" r="10"></circle>
                            <line x1="12" y1="8" x2="12" y2="12"></line>
                            <line x1="12" y1="16" x2="12.01" y2="16"></line>
                        </svg>
                        <div>{error}</div>
                    </div>
                )}

                {showForgotNotice && (
                    <div className="auth-alert auth-alert-info">
                        <svg className="auth-alert-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <circle cx="12" cy="12" r="10"></circle>
                            <line x1="12" y1="16" x2="12" y2="12"></line>
                            <line x1="12" y1="8" x2="12.01" y2="8"></line>
                        </svg>
                        <div>
                            <strong>Account Recovery:</strong> Self-service password recovery is not yet configured for this workspace. Please contact your system administrator to reset your credentials.
                        </div>
                    </div>
                )}

                <form onSubmit={handleSubmit} className="auth-form" noValidate>
                    <Input
                        label="Username or Email Address"
                        id="login-identifier"
                        type="text"
                        placeholder="e.g. marie_curie or marie@radium.org"
                        value={identifier}
                        onChange={(e) => {
                            setIdentifier(e.target.value);
                            if (fieldErrors.identifier) {
                                setFieldErrors((prev) => ({ ...prev, identifier: '' }));
                            }
                        }}
                        error={fieldErrors.identifier}
                        required
                        autoComplete="username"
                        disabled={submitting}
                    />

                    <div>
                        <div className="auth-field-header-row">
                            <label htmlFor="login-password" className="input-label" style={{ marginBottom: 0 }}>
                                Password <span className="required-star" aria-hidden="true">*</span>
                            </label>
                            <button
                                type="button"
                                className="auth-forgot-btn"
                                onClick={() => setShowForgotNotice((prev) => !prev)}
                            >
                                Forgot password?
                            </button>
                        </div>
                        <Input
                            id="login-password"
                            type="password"
                            placeholder="Enter your password"
                            value={password}
                            onChange={(e) => {
                                setPassword(e.target.value);
                                if (fieldErrors.password) {
                                setFieldErrors((prev) => ({ ...prev, password: '' }));
                                }
                            }}
                            error={fieldErrors.password}
                            required
                            showPasswordToggle={true}
                            autoComplete="current-password"
                            disabled={submitting}
                        />
                    </div>

                    <Button
                        type="submit"
                        className="auth-submit-btn"
                        disabled={submitting}
                    >
                        {submitting ? (
                            <>
                                <span className="auth-spinner" aria-hidden="true"></span>
                                <span>Signing in...</span>
                            </>
                        ) : (
                            'Sign In'
                        )}
                    </Button>
                </form>

                <div className="auth-footer">
                    Don't have an account?{' '}
                    <Link to="/register" className="auth-footer-link">
                        Create an account
                    </Link>
                </div>
            </div>
        </div>
    );
};

export default Login;
