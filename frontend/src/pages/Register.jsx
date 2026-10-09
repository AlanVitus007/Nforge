import React, { useState, useContext } from 'react';
import { AuthContext } from '../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import Input from '../components/Input';
import Button from '../components/Button';
import './Auth.css';

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const Register = () => {
    const [formData, setFormData] = useState({
        first_name: '',
        last_name: '',
        username: '',
        email: '',
        password: '',
        confirm_password: '',
    });

    const [fieldErrors, setFieldErrors] = useState({});
    const [generalError, setGeneralError] = useState('');
    const [submitting, setSubmitting] = useState(false);

    const { register, login } = useContext(AuthContext);
    const navigate = useNavigate();

    const handleChange = (field) => (e) => {
        const val = e.target.value;
        setFormData((prev) => ({ ...prev, [field]: val }));
        if (fieldErrors[field]) {
            setFieldErrors((prev) => ({ ...prev, [field]: '' }));
        }
        if (generalError) {
            setGeneralError('');
        }
    };

    const validateForm = () => {
        const errors = {};

        if (!formData.first_name.trim()) {
            errors.first_name = 'First name is required.';
        }

        if (!formData.last_name.trim()) {
            errors.last_name = 'Last name is required.';
        }

        if (!formData.username.trim()) {
            errors.username = 'Username is required.';
        } else if (formData.username.trim().length < 3) {
            errors.username = 'Username must be at least 3 characters long.';
        } else if (!/^[a-zA-Z0-9_.-]+$/.test(formData.username.trim())) {
            errors.username = 'Username may only contain letters, numbers, dots, hyphens, and underscores.';
        }

        if (!formData.email.trim()) {
            errors.email = 'Email address is required.';
        } else if (!EMAIL_REGEX.test(formData.email.trim())) {
            errors.email = 'Please enter a valid email address.';
        }

        if (!formData.password) {
            errors.password = 'Password is required.';
        } else if (formData.password.length < 8) {
            errors.password = 'Password must be at least 8 characters long.';
        }

        if (!formData.confirm_password) {
            errors.confirm_password = 'Please confirm your password.';
        } else if (formData.password !== formData.confirm_password) {
            errors.confirm_password = 'Passwords do not match.';
        }

        setFieldErrors(errors);
        return Object.keys(errors).length === 0;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setGeneralError('');

        if (!validateForm() || submitting) {
            return;
        }

        setSubmitting(true);
        try {
            const payload = {
                first_name: formData.first_name.trim(),
                last_name: formData.last_name.trim(),
                username: formData.username.trim(),
                email: formData.email.trim().toLowerCase(),
                password: formData.password,
                confirm_password: formData.confirm_password,
            };

            await register(payload);

            // Auto-login after successful registration
            await login(payload.username, payload.password);
            navigate('/dashboard');
        } catch (err) {
            const data = err.response?.data;
            const newFieldErrors = {};
            let topMsg = '';

            if (data && typeof data === 'object') {
                if (data.first_name) {
                    newFieldErrors.first_name = Array.isArray(data.first_name) ? data.first_name[0] : data.first_name;
                }
                if (data.last_name) {
                    newFieldErrors.last_name = Array.isArray(data.last_name) ? data.last_name[0] : data.last_name;
                }
                if (data.username) {
                    newFieldErrors.username = Array.isArray(data.username) ? data.username[0] : data.username;
                }
                if (data.email) {
                    newFieldErrors.email = Array.isArray(data.email) ? data.email[0] : data.email;
                }
                if (data.password) {
                    newFieldErrors.password = Array.isArray(data.password) ? data.password[0] : data.password;
                }
                if (data.confirm_password) {
                    newFieldErrors.confirm_password = Array.isArray(data.confirm_password) ? data.confirm_password[0] : data.confirm_password;
                }
                if (data.non_field_errors) {
                    topMsg = Array.isArray(data.non_field_errors) ? data.non_field_errors[0] : data.non_field_errors;
                } else if (data.error) {
                    topMsg = data.error;
                } else if (data.detail) {
                    topMsg = data.detail;
                }
            } else if (typeof data === 'string') {
                topMsg = data;
            } else if (err.message) {
                topMsg = `Network error (${err.message}). Verify backend server is running and reachable.`;
            }

            if (Object.keys(newFieldErrors).length > 0) {
                setFieldErrors((prev) => ({ ...prev, ...newFieldErrors }));
            }
            if (topMsg || Object.keys(newFieldErrors).length === 0) {
                setGeneralError(topMsg || 'Registration failed. Please check the highlighted fields and try again.');
            }
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="auth-page">
            <div className="auth-card auth-card-wide">
                <div className="auth-header">
                    <span className="auth-brand-badge">NForge Research Suite</span>
                    <h2 className="auth-title">Create an Account</h2>
                    <p className="auth-subtitle">Join NForge to collaborate on biomedical and technical literature synthesis</p>
                </div>

                {generalError && (
                    <div className="auth-alert auth-alert-error" role="alert">
                        <svg className="auth-alert-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <circle cx="12" cy="12" r="10"></circle>
                            <line x1="12" y1="8" x2="12" y2="12"></line>
                            <line x1="12" y1="16" x2="12.01" y2="16"></line>
                        </svg>
                        <div>{generalError}</div>
                    </div>
                )}

                <form onSubmit={handleSubmit} className="auth-form" noValidate>
                    {/* First & Last Name */}
                    <div className="auth-form-grid-2col">
                        <Input
                            label="First Name"
                            id="reg-first-name"
                            type="text"
                            placeholder="e.g. Marie"
                            value={formData.first_name}
                            onChange={handleChange('first_name')}
                            error={fieldErrors.first_name}
                            required
                            autoComplete="given-name"
                            disabled={submitting}
                        />
                        <Input
                            label="Last Name"
                            id="reg-last-name"
                            type="text"
                            placeholder="e.g. Curie"
                            value={formData.last_name}
                            onChange={handleChange('last_name')}
                            error={fieldErrors.last_name}
                            required
                            autoComplete="family-name"
                            disabled={submitting}
                        />
                    </div>

                    {/* Username */}
                    <Input
                        label="Username"
                        id="reg-username"
                        type="text"
                        placeholder="Choose a unique username"
                        value={formData.username}
                        onChange={handleChange('username')}
                        error={fieldErrors.username}
                        helperText={!fieldErrors.username ? 'Letters, numbers, dots, hyphens, and underscores' : undefined}
                        required
                        autoComplete="username"
                        disabled={submitting}
                    />

                    {/* Email Address */}
                    <Input
                        label="Email Address"
                        id="reg-email"
                        type="email"
                        placeholder="name@institution.org"
                        value={formData.email}
                        onChange={handleChange('email')}
                        error={fieldErrors.email}
                        required
                        autoComplete="email"
                        disabled={submitting}
                    />

                    {/* Password & Confirm Password */}
                    <div className="auth-form-grid-2col">
                        <Input
                            label="Password"
                            id="reg-password"
                            type="password"
                            placeholder="At least 8 characters"
                            value={formData.password}
                            onChange={handleChange('password')}
                            error={fieldErrors.password}
                            required
                            showPasswordToggle={true}
                            autoComplete="new-password"
                            disabled={submitting}
                        />
                        <Input
                            label="Confirm Password"
                            id="reg-confirm-password"
                            type="password"
                            placeholder="Re-enter password"
                            value={formData.confirm_password}
                            onChange={handleChange('confirm_password')}
                            error={fieldErrors.confirm_password}
                            required
                            showPasswordToggle={true}
                            autoComplete="new-password"
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
                                <span>Creating Account...</span>
                            </>
                        ) : (
                            'Create Account'
                        )}
                    </Button>
                </form>

                <div className="auth-footer">
                    Already have an account?{' '}
                    <Link to="/login" className="auth-footer-link">
                        Sign in
                    </Link>
                </div>
            </div>
        </div>
    );
};

export default Register;
