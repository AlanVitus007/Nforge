import React, { useContext, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AuthContext } from "../context/AuthContext";
import api from "../services/api";
import ProjectInvitations from "../components/ProjectInvitations";
import "./Profile.css";

const Profile = () => {
    const { user: authUser } = useContext(AuthContext);
    const [profileData, setProfileData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        let isMounted = true;

        const fetchProfile = async () => {
            try {
                setLoading(true);
                setError("");
                const response = await api.get("/auth/profile/");
                if (isMounted) {
                    setProfileData(response.data);
                }
            } catch (err) {
                console.error("Failed to load profile:", err);
                if (isMounted) {
                    // Non-fatal: fallback to authUser if endpoint has an issue
                    setError("Unable to refresh profile statistics.");
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
    }, []);

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

    if (!authUser && !loading) {
        return (
            <div className="profile-page-container">
                <div className="alert-box error">Please log in to view your profile.</div>
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

            {error && (
                <div className="alert-box error" style={{ marginBottom: "1.5rem" }}>
                    {error}
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
                <div className="profile-details-grid">
                    <div className="profile-field-block">
                        <label className="profile-field-label">Username</label>
                        <div className="profile-field-value">{user?.username || "—"}</div>
                    </div>

                    <div className="profile-field-block">
                        <label className="profile-field-label">Email</label>
                        <div className="profile-field-value">{user?.email || "—"}</div>
                    </div>

                    <div className="profile-field-block">
                        <label className="profile-field-label">First Name</label>
                        <div className={`profile-field-value ${!user?.first_name ? "empty" : ""}`}>
                            {user?.first_name || "Not specified"}
                        </div>
                    </div>

                    <div className="profile-field-block">
                        <label className="profile-field-label">Last Name</label>
                        <div className={`profile-field-value ${!user?.last_name ? "empty" : ""}`}>
                            {user?.last_name || "Not specified"}
                        </div>
                    </div>

                    <div className="profile-field-block">
                        <label className="profile-field-label">Member Since</label>
                        <div className="profile-field-value">
                            {formatMemberSince(user?.date_joined)}
                        </div>
                    </div>

                    <div className="profile-field-block">
                        <label className="profile-field-label">Account Status</label>
                        <div className="profile-field-value">
                            Active
                        </div>
                    </div>
                </div>
            </div>

            {/* Pending Project Invitations Section (if any pending) */}
            <div style={{ marginTop: "2rem" }}>
                <ProjectInvitations />
            </div>
        </div>
    );
};

export default Profile;
