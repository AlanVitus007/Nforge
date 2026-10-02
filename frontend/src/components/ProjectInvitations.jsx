import React, { useEffect, useState } from "react";
import { getInvitations, acceptInvitation, declineInvitation } from "../services/collaboration";
import "./ProjectInvitations.css";

/**
 * Incoming Project Invitations UI
 * Displays pending invitations with accept / decline controls.
 */
const ProjectInvitations = ({ onAccepted, onDeclined }) => {
    const [invitations, setInvitations] = useState([]);
    const [loading, setLoading] = useState(true);
    const [actionId, setActionId] = useState(null);
    const [actionType, setActionType] = useState(null); // 'accept' | 'decline'
    const [error, setError] = useState("");
    const [feedback, setFeedback] = useState("");

    const fetchPendingInvitations = async () => {
        try {
            setLoading(true);
            setError("");
            const data = await getInvitations("PENDING");
            setInvitations(Array.isArray(data) ? data : []);
        } catch (err) {
            console.error("Failed to fetch pending invitations", err);
            // Non-fatal, do not show persistent broken banner if invitations fail
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchPendingInvitations();
    }, []);

    const handleAccept = async (invitation) => {
        const id = invitation.id || invitation.invitation_id;
        try {
            setActionId(id);
            setActionType("accept");
            setError("");
            setFeedback("");

            await acceptInvitation(id);
            setFeedback(`Joined "${invitation.project_title || "project"}" successfully.`);
            setInvitations((prev) => prev.filter((item) => (item.id || item.invitation_id) !== id));

            if (onAccepted) {
                await onAccepted();
            }
        } catch (err) {
            console.error("Failed to accept invitation", err);
            setError(err.response?.data?.detail || "Failed to accept invitation.");
        } finally {
            setActionId(null);
            setActionType(null);
        }
    };

    const handleDecline = async (invitation) => {
        const id = invitation.id || invitation.invitation_id;
        try {
            setActionId(id);
            setActionType("decline");
            setError("");
            setFeedback("");

            await declineInvitation(id);
            setFeedback(`Invitation to "${invitation.project_title || "project"}" declined.`);
            setInvitations((prev) => prev.filter((item) => (item.id || item.invitation_id) !== id));

            if (onDeclined) {
                await onDeclined();
            }
        } catch (err) {
            console.error("Failed to decline invitation", err);
            setError(err.response?.data?.detail || "Failed to decline invitation.");
        } finally {
            setActionId(null);
            setActionType(null);
        }
    };

    if (loading || invitations.length === 0) {
        return null;
    }

    const formatDate = (dateStr) => {
        if (!dateStr) return "";
        try {
            const d = new Date(dateStr);
            return d.toLocaleDateString(undefined, {
                month: "short",
                day: "numeric",
                year: "numeric",
            });
        } catch {
            return "";
        }
    };

    return (
        <section className="invitations-panel" aria-label="Pending Project Invitations">
            <div className="invitations-header">
                <div className="invitations-title-group">
                    <div className="invitations-icon">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path>
                            <circle cx="9" cy="7" r="4"></circle>
                            <path d="M22 21v-2a4 4 0 0 0-3-3.87"></path>
                            <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
                        </svg>
                    </div>
                    <h3 className="invitations-title">Pending Invitations</h3>
                    <span className="invitations-count-badge">{invitations.length}</span>
                </div>
            </div>

            {feedback && <div className="invitations-feedback success">{feedback}</div>}
            {error && <div className="invitations-feedback error">{error}</div>}

            <div className="invitations-list">
                {invitations.map((inv) => {
                    const id = inv.id || inv.invitation_id;
                    const isProcessing = actionId === id;
                    const roleClass = inv.role === "EDITOR" ? "role-badge-editor" : "role-badge-viewer";

                    return (
                        <div key={id} className="invitation-item-card">
                            <div className="invitation-details">
                                <h4 className="invitation-project-title">
                                    {inv.project_title || `Project #${inv.project || inv.project_id}`}
                                </h4>
                                <div className="invitation-meta">
                                    <span>
                                        Invited by <strong>@{inv.inviter_username || inv.invited_by || "owner"}</strong>
                                    </span>
                                    <span>&bull;</span>
                                    <span className={`invitation-role-badge ${roleClass}`}>
                                        {inv.role}
                                    </span>
                                    {inv.created_at && (
                                        <>
                                            <span>&bull;</span>
                                            <span>{formatDate(inv.created_at)}</span>
                                        </>
                                    )}
                                </div>
                            </div>

                            <div className="invitation-actions">
                                <button
                                    type="button"
                                    className="invitation-btn-accept"
                                    onClick={() => handleAccept(inv)}
                                    disabled={isProcessing}
                                >
                                    {isProcessing && actionType === "accept" ? "Accepting..." : "Accept"}
                                </button>
                                <button
                                    type="button"
                                    className="invitation-btn-decline"
                                    onClick={() => handleDecline(inv)}
                                    disabled={isProcessing}
                                >
                                    {isProcessing && actionType === "decline" ? "Declining..." : "Decline"}
                                </button>
                            </div>
                        </div>
                    );
                })}
            </div>
        </section>
    );
};

export default ProjectInvitations;
