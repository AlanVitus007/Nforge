import React, { useContext, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AuthContext } from "../context/AuthContext";
import api from "../services/api";
import ProjectInvitations from "../components/ProjectInvitations";
import "./Profile.css";

const Profile = () => {
    const { user: authUser, updateUser, refreshUser } = useContext(AuthContext);
    const [profileData, setProfileData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [pageError, setPageError] = useState("");

    // Username edit state
    const [usernameInput, setUsernameInput] = useState("");
    const [originalUsername, setOriginalUsername] = useState("");
    const [isSaving, setIsSaving] = useState(false);
    const [saveSuccess, setSaveSuccess] = useState("");
    const [saveError, setSaveError] = useState("");

    useEffect(() => {
        let isMounted = true;

        const fetchProfile = async () => {
            try {
                setLoading(true);
                setPageError("");
                const response = await api.get("/auth/profile/");
                if (isMounted) {
                    setProfileData(response.data);
                    const currentUsername = response.data.username || "";
                    setUsernameInput(currentUsername);
                    setOriginalUsername(currentUsername);
                }
            } catch (err) {
                console.error("Failed to load profile:", err);
                if (isMounted) {
                    setPageError("Unable to refresh profile statistics.");
                    if (authUser) {
                        const fallbackUsername = authUser.username || "";
                        setUsernameInput(fallbackUsername);
                        setOriginalUsername(fallbackUsername);
                    }
                }
            } finally {
                if (isMounted) {
                    setLoading(false);
                }
            }
        };

        fetchProfile();

        return () => {
            isMounted = false;
        };
    }, [authUser]);

    // Update username input when authUser changes if not yet loaded from endpoint
    useEffect(() => {
        if (authUser && !originalUsername && !loading) {
            const fallback = authUser.username || "";
            setUsernameInput(fallback);
            setOriginalUsername(fallback);
        }
    }, [authUser, originalUsername, loading]);

    const user = profileData || authUser;

    // Helper to compute initials from first_name + last_name or username
    const getInitials = (u) => {
        if (!u) return "U";
        if (u.first_name || u.last_name) {
            const first = u.first_name ? u.first_name[0] : "";
            const last = u.last_name ? u.last_name[0] : "";
            const combined = (first + last).trim();
            if (combined) return combined.toUpperCase();
        }
        if (u.username) {
            return u.username.slice(0, 2).toUpperCase();
        }
        return "U";
    };

    // Helper to format member since date
    const formatMemberSince = (dateStr) => {
        if (!dateStr) return "Recently joined";
        try {
            const date = new Date(dateStr);
            return date.toLocaleDateString(undefined, {
                month: "long",
                day: "numeric",
                year: "numeric"
            });
        } catch {
            return "Recently joined";
        }
    };

    // Validation & modification detection
    const trimmedInput = usernameInput.trim();
    const isDirty = originalUsername !== "" && trimmedInput !== originalUsername;

    const getValidationError = () => {
        if (!isDirty) return "";
        if (!trimmedInput) return "Username cannot be empty.";
        if (trimmedInput.length < 3) return "Username must be at least 3 characters long.";
        if (trimmedInput.length > 150) return "Username cannot exceed 150 characters.";
        if (!/^[a-zA-Z0-9_.-]+$/.test(trimmedInput)) {
            return "Username may only contain letters, numbers, and . _ -";
        }
        return "";
    };

    const validationError = getValidationError();
    const canSave = isDirty && !validationError && !isSaving;

    const handleSave = async (e) => {
        if (e) e.preventDefault();
        if (!canSave) return;

        setIsSaving(true);
        setSaveError("");
        setSaveSuccess("");

        try {
            const response = await api.patch("/auth/profile/", {
                username: trimmedInput,
            });

            const updatedProfile = response.data;
            setProfileData(updatedProfile);
            setOriginalUsername(updatedProfile.username);
            setUsernameInput(updatedProfile.username);
            setSaveSuccess(`Username successfully updated to @${updatedProfile.username}`);

            // Update AuthContext so navbar, dropdown, and other UI reflect the update immediately
            if (updateUser) {
                updateUser({ username: updatedProfile.username });
            }
            if (refreshUser) {
                await refreshUser();
            }
        } catch (err) {
            console.error("Failed to update profile username:", err);
            const data = err.response?.data;
            let msg = "Failed to update username. Please try again.";

            if (data) {
                if (typeof data.username === "string") {
                    msg = data.username;
                } else if (Array.isArray(data.username)) {
                    msg = data.username.join(" ");
                } else if (data.error) {
                    msg = data.error;
                } else if (data.detail) {
                    msg = data.detail;
                }
            }
            setSaveError(msg);
        } finally {
            setIsSaving(false);
        }
    };

    const handleCancel = () => {
        setUsernameInput(originalUsername);
        setSaveError("");
        setSaveSuccess("");
    };

    if (!authUser && !loading) {
        return (
            <div className="profile-page-container">
                <div className="profile-alert profile-alert-error">
                    Please log in to view your profile.
                </div>
            </div>
        );
    }

    return (
        <div className="profile-page-container animate-fade-in">
            {/* Header Breadcrumb & Title */}
            <header className="profile-header-banner">
                <Link to="/dashboard" className="profile-breadcrumb">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <line x1="19" y1="12" x2="5" y2="12"></line>
                        <polyline points="12 19 5 12 12 5"></polyline>
                    </svg>
                    Back to Dashboard
                </Link>
                <h1 className="profile-title">Researcher Profile</h1>
                <p className="profile-subtitle">Account overview, identity, and research activity.</p>
            </header>

            {/* Notification / Alert Banners */}
            {saveSuccess && (
                <div className="profile-alert profile-alert-success animate-fade-in" role="status">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                        <polyline points="22 4 12 14.01 9 11.01"></polyline>
                    </svg>
                    <span className="profile-alert-text">{saveSuccess}</span>
                    <button
                        type="button"
                        className="profile-alert-dismiss"
                        onClick={() => setSaveSuccess("")}
                        aria-label="Dismiss alert"
                    >
                        ✕
                    </button>
                </div>
            )}

            {saveError && (
                <div className="profile-alert profile-alert-error animate-fade-in" role="alert">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="12" y1="8" x2="12" y2="12"></line>
                        <line x1="12" y1="16" x2="12.01" y2="16"></line>
                    </svg>
                    <span className="profile-alert-text">{saveError}</span>
                    <button
                        type="button"
                        className="profile-alert-dismiss"
                        onClick={() => setSaveError("")}
                        aria-label="Dismiss alert"
                    >
                        ✕
                    </button>
                </div>
            )}

            {pageError && (
                <div className="profile-alert profile-alert-warning" role="alert">
                    <span className="profile-alert-text">{pageError}</span>
                </div>
            )}

            {/* Profile Card */}
            <div className="profile-card">
                {/* Top Identity Block */}
                <div className="profile-card-top">
                    <div className="profile-avatar-large" aria-hidden="true">
                        {getInitials(user)}
                    </div>
                    <div className="profile-identity">
                        <div className="profile-name-row">
                            <h2 className="profile-username-heading">
                                {user?.username}
                            </h2>
                            <span className="profile-status-badge">
                                <span className="profile-status-dot"></span>
                                Active
                            </span>
                            {Boolean(user?.is_superuser || user?.is_staff) && (
                                <span className="profile-role-badge">
                                    {user?.is_superuser ? "Super Admin" : "Staff"}
                                </span>
                            )}
                        </div>
                        <p className="profile-email-sub">{user?.email || "No email registered"}</p>
                    </div>
                </div>

                {/* Quick Metrics Strip */}
                <div className="profile-metrics-strip">
                    <Link to="/projects" className="profile-metric-item" title="View all projects">
                        <div className="profile-metric-label">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                            </svg>
                            <span>Projects</span>
                        </div>
                        <span className="profile-metric-value">
                            {loading ? "..." : (profileData?.projects_count ?? "—")}
                        </span>
                    </Link>

                    <Link to="/friends" className="profile-metric-item" title="Manage friends">
                        <div className="profile-metric-label">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                                <circle cx="9" cy="7" r="4"></circle>
                                <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                                <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
                            </svg>
                            <span>Friends</span>
                        </div>
                        <span className="profile-metric-value">
                            {loading ? "..." : (profileData?.friends_count ?? "—")}
                        </span>
                    </Link>
                </div>

                {/* Detailed Information Grid */}
                <form className="profile-details-grid" onSubmit={handleSave} noValidate>
                    {/* Username Block (Editable) */}
                    <div className="profile-field-block profile-field-block-editable">
                        <div className="profile-field-header">
                            <label htmlFor="profile-username-input" className="profile-field-label">
                                Username
                            </label>
                            <span className="profile-field-badge editable-badge">
                                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                                </svg>
                                Editable
                            </span>
                        </div>

                        <div className="profile-input-wrapper">
                            <span className="profile-input-prefix">@</span>
                            <input
                                id="profile-username-input"
                                type="text"
                                className={`profile-input ${validationError ? "has-error" : ""} ${isDirty ? "is-modified" : ""}`}
                                value={usernameInput}
                                onChange={(e) => {
                                    setUsernameInput(e.target.value);
                                    if (saveSuccess) setSaveSuccess("");
                                    if (saveError) setSaveError("");
                                }}
                                disabled={isSaving || loading}
                                maxLength={150}
                                autoComplete="username"
                                placeholder="Enter username"
                                aria-describedby="profile-username-feedback"
                            />
                        </div>

                        <div id="profile-username-feedback" className="profile-field-feedback">
                            {validationError ? (
                                <span className="feedback-text error">{validationError}</span>
                            ) : isDirty ? (
                                <span className="feedback-text dirty">Unsaved change — click Save Changes below</span>
                            ) : (
                                <span className="feedback-text hint">Allowed: letters, numbers, and . _ - (3–150 chars)</span>
                            )}
                        </div>
                    </div>

                    {/* Email Block (Read-only) */}
                    <div className="profile-field-block profile-field-block-readonly">
                        <div className="profile-field-header">
                            <label className="profile-field-label">Email Address</label>
                            <span className="profile-field-badge readonly-badge">
                                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                                    <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                                </svg>
                                Read-only
                            </span>
                        </div>
                        <div className="profile-field-value readonly-value">
                            <span className="field-value-text">{user?.email || "—"}</span>
                            <svg className="readonly-lock-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                                <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                            </svg>
                        </div>
                        <div className="profile-field-feedback">
                            <span className="feedback-text readonly-hint">Email address cannot be modified</span>
                        </div>
                    </div>

                    {/* First Name Block (Read-only) */}
                    <div className="profile-field-block profile-field-block-readonly">
                        <div className="profile-field-header">
                            <label className="profile-field-label">First Name</label>
                            <span className="profile-field-badge readonly-badge">
                                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                                    <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                                </svg>
                                Read-only
                            </span>
                        </div>
                        <div className="profile-field-value readonly-value">
                            <span className={`field-value-text ${!user?.first_name ? "empty" : ""}`}>
                                {user?.first_name || "Not specified"}
                            </span>
                            <svg className="readonly-lock-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                                <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                            </svg>
                        </div>
                        <div className="profile-field-feedback">
                            <span className="feedback-text readonly-hint">First name cannot be modified</span>
                        </div>
                    </div>

                    {/* Last Name Block (Read-only) */}
                    <div className="profile-field-block profile-field-block-readonly">
                        <div className="profile-field-header">
                            <label className="profile-field-label">Last Name</label>
                            <span className="profile-field-badge readonly-badge">
                                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                                    <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                                </svg>
                                Read-only
                            </span>
                        </div>
                        <div className="profile-field-value readonly-value">
                            <span className={`field-value-text ${!user?.last_name ? "empty" : ""}`}>
                                {user?.last_name || "Not specified"}
                            </span>
                            <svg className="readonly-lock-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                                <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                            </svg>
                        </div>
                        <div className="profile-field-feedback">
                            <span className="feedback-text readonly-hint">Last name cannot be modified</span>
                        </div>
                    </div>

                    {/* Member Since Block (Read-only) */}
                    <div className="profile-field-block profile-field-block-readonly">
                        <div className="profile-field-header">
                            <label className="profile-field-label">Member Since</label>
                            <span className="profile-field-badge readonly-badge">
                                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                                    <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                                </svg>
                                Read-only
                            </span>
                        </div>
                        <div className="profile-field-value readonly-value">
                            <span className="field-value-text">{formatMemberSince(user?.date_joined)}</span>
                        </div>
                        <div className="profile-field-feedback">
                            <span className="feedback-text readonly-hint">System recorded registration date</span>
                        </div>
                    </div>

                    {/* Account Status Block (Read-only) */}
                    <div className="profile-field-block profile-field-block-readonly">
                        <div className="profile-field-header">
                            <label className="profile-field-label">Account Status</label>
                            <span className="profile-field-badge readonly-badge">
                                <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                    <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
                                    <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
                                </svg>
                                Read-only
                            </span>
                        </div>
                        <div className="profile-field-value readonly-value">
                            <span className="field-value-text">Active</span>
                        </div>
                        <div className="profile-field-feedback">
                            <span className="feedback-text readonly-hint">Managed by system administration</span>
                        </div>
                    </div>
                </form>

                {/* Profile Actions Bar */}
                <div className="profile-actions-bar">
                    <div className="profile-actions-info">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <circle cx="12" cy="12" r="10"></circle>
                            <line x1="12" y1="16" x2="12" y2="12"></line>
                            <line x1="12" y1="8" x2="12.01" y2="8"></line>
                        </svg>
                        <span>
                            {isDirty
                                ? "You have unsaved changes to your username."
                                : "Only username is editable. Personal names and email are protected."}
                        </span>
                    </div>

                    <div className="profile-actions-buttons">
                        <button
                            type="button"
                            className="profile-btn profile-btn-cancel"
                            onClick={handleCancel}
                            disabled={!isDirty || isSaving}
                            title={isDirty ? "Reset to original username" : "No changes to cancel"}
                        >
                            Cancel
                        </button>

                        <button
                            type="button"
                            className="profile-btn profile-btn-save"
                            onClick={handleSave}
                            disabled={!canSave}
                            title={
                                !isDirty
                                    ? "Username is unchanged"
                                    : validationError
                                    ? "Fix validation error to enable save"
                                    : "Save changes"
                            }
                        >
                            {isSaving ? (
                                <>
                                    <span className="profile-btn-spinner" aria-hidden="true"></span>
                                    <span>Saving...</span>
                                </>
                            ) : (
                                <>
                                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                        <polyline points="20 6 9 17 4 12"></polyline>
                                    </svg>
                                    <span>Save Changes</span>
                                </>
                            )}
                        </button>
                    </div>
                </div>
            </div>

            {/* Pending Project Invitations Section */}
            <div style={{ marginTop: "2rem" }}>
                <ProjectInvitations />
            </div>
        </div>
    );
};

export default Profile;
