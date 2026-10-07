import { useEffect, useState, useContext } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import api from "../services/api";
import { AuthContext } from "../context/AuthContext";
import Card from "../components/Card";
import Button from "../components/Button";
import Input from "../components/Input";
import {
    getProjectMembers,
    inviteMember,
    removeProjectMember,
    determineUserRole,
} from "../services/collaboration";
import { getFriends } from "../services/friends";
import "./ProjectDetails.css";

function ProjectDetails() {
    const { id } = useParams();
    const navigate = useNavigate();
    const { user } = useContext(AuthContext);

    const [project, setProject] = useState(null);
    const [papers, setPapers] = useState([]);
    const [title, setTitle] = useState("");
    const [file, setFile] = useState(null);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState("");

    // Collaboration state
    const [members, setMembers] = useState([]);
    const [friendsList, setFriendsList] = useState([]);
    const [selectedFriend, setSelectedFriend] = useState("");
    const [inviteUsername, setInviteUsername] = useState("");
    const [inviteRole, setInviteRole] = useState("VIEWER");
    const [inviting, setInviting] = useState(false);
    const [inviteError, setInviteError] = useState("");
    const [inviteSuccess, setInviteSuccess] = useState("");
    const [removingMemberId, setRemovingMemberId] = useState(null);
    const [memberError, setMemberError] = useState("");

    const [showDeletePopup, setShowDeletePopup] = useState(false);
    const [paperToDelete, setPaperToDelete] = useState(null);
    const [isDeleting, setIsDeleting] = useState(false);

    // Phase 1: Selection State
    const [selectedPaperIds, setSelectedPaperIds] = useState([]);
    const [selectionNotice, setSelectionNotice] = useState("");
    const [tempMessage, setTempMessage] = useState("");

    // Rename project state
    const [isEditingTitle, setIsEditingTitle] = useState(false);
    const [editTitle, setEditTitle] = useState("");
    const [isSavingTitle, setIsSavingTitle] = useState(false);
    const [renameError, setRenameError] = useState("");

    const isOwner = Boolean(user && project && project.owner === user.username);
    const currentRole = determineUserRole(project, user, members);
    const isEditor = currentRole === "EDITOR";
    const canEditContent = isOwner || isEditor;

    const handleSaveTitle = async () => {
        if (!isOwner) return;
        const trimmed = editTitle.trim();
        if (!trimmed) {
            setRenameError("Project title cannot be empty.");
            return;
        }
        if (trimmed === project.title) {
            setIsEditingTitle(false);
            setRenameError("");
            return;
        }
        try {
            setIsSavingTitle(true);
            setRenameError("");
            const response = await api.patch(`/projects/${id}/`, { title: trimmed });
            setProject(response.data);
            setIsEditingTitle(false);
        } catch (err) {
            setRenameError(
                err.response?.data?.title?.[0] ||
                err.response?.data?.detail ||
                "Failed to update project title."
            );
        } finally {
            setIsSavingTitle(false);
        }
    };

    const fetchProject = async () => {
        try {
            const response = await api.get(`/projects/${id}/`);
            setProject(response.data);
            return response.data;
        } catch (err) {
            console.error("Failed to load project:", err);
            if (err.response?.status === 403) {
                setError("You don't have permission to view this project.");
            } else if (err.response?.status === 404) {
                setError("Project not found.");
            } else {
                setError("Unable to load project. Please try again.");
            }
            return null;
        }
    };

    const fetchPapers = async () => {
        try {
            const response = await api.get(`/projects/${id}/papers/`);
            setPapers(response.data || []);
        } catch (err) {
            console.error("Failed to load papers:", err);
        }
    };

    const fetchMembers = async () => {
        try {
            setMemberError("");
            const data = await getProjectMembers(id);
            setMembers(Array.isArray(data) ? data : []);
        } catch (err) {
            console.error("Failed to load members:", err);
        }
    };

    useEffect(() => {
        let isMounted = true;

        const loadData = async () => {
            if (!id) return;
            setLoading(true);
            setError("");

            try {
                // 1. Fetch project first
                const projectData = await fetchProject();
                if (!projectData || !isMounted) {
                    return;
                }

                // 2. Concurrently fetch papers, members, and friends
                await Promise.allSettled([
                    fetchPapers(),
                    fetchMembers(),
                    getFriends().then((friendsData) => {
                        if (isMounted) {
                            setFriendsList(friendsData.friends || []);
                        }
                    }).catch(() => {})
                ]);
            } catch (err) {
                if (isMounted) {
                    console.error("Unexpected error in loadData:", err);
                    setError("Unable to load project. Please try again.");
                }
            } finally {
                if (isMounted) {
                    setLoading(false);
                }
            }
        };

        loadData();

        return () => {
            isMounted = false;
        };
    }, [id]);

    const handleInvite = async (e) => {
        e?.preventDefault();
        const trimmed = inviteUsername.trim();
        if (!trimmed) {
            setInviteError("Please select a friend or enter a username to invite.");
            return;
        }

        if (user && trimmed.toLowerCase() === user.username.toLowerCase()) {
            setInviteError("You cannot invite yourself.");
            return;
        }

        if (
            members.some((m) => m.username.toLowerCase() === trimmed.toLowerCase()) ||
            (project && project.owner && project.owner.toLowerCase() === trimmed.toLowerCase())
        ) {
            setInviteError("This user is already a collaborator on this project.");
            return;
        }

        try {
            setInviting(true);
            setInviteError("");
            setInviteSuccess("");

            await inviteMember(id, trimmed, inviteRole);
            setInviteSuccess(`Invitation sent to @${trimmed} as ${inviteRole}.`);
            setInviteUsername("");
            setSelectedFriend("");
            setInviteRole("VIEWER");
        } catch (err) {
            console.error("Failed to invite collaborator", err);
            setInviteError(
                err.response?.data?.detail ||
                err.response?.data?.username?.[0] ||
                "Failed to send invitation."
            );
        } finally {
            setInviting(false);
        }
    };

    const handleRemoveMember = async (memberUserId, memberUsername) => {
        if (!window.confirm(`Are you sure you want to remove @${memberUsername} from this project?`)) {
            return;
        }
        try {
            setRemovingMemberId(memberUserId);
            setMemberError("");
            await removeProjectMember(id, memberUserId);
            setMembers((prev) =>
                prev.filter((m) => (m.user_id || m.user) !== memberUserId)
            );
        } catch (err) {
            console.error("Failed to remove collaborator", err);
            setMemberError(err.response?.data?.detail || "Failed to remove collaborator.");
        } finally {
            setRemovingMemberId(null);
        }
    };

    const handleUpload = async (e) => {
        e.preventDefault();

        if (!title.trim()) {
            return setError("Please enter a paper title.");
        }

        if (!file) {
            return setError("Please select a PDF file.");
        }

        if (!file.name.toLowerCase().endsWith(".pdf")) {
            return setError("Only PDF files are allowed.");
        }

        try {
            setUploading(true);
            setError("");

            const formData = new FormData();
            formData.append("title", title);
            formData.append("file", file);

            await api.post(`/projects/${id}/papers/`, formData);

            setTitle("");
            setFile(null);

            document.getElementById("paper-file").value = "";

            await fetchPapers();
        } catch (err) {
            setError(
                err.response?.data
                    ? JSON.stringify(err.response.data)
                    : "Failed to upload paper."
            );
        } finally {
            setUploading(false);
        }
    };

    const openDeletePopup = (paper) => {
        setPaperToDelete(paper);
        setShowDeletePopup(true);
    };

    const closeDeletePopup = () => {
        if (isDeleting) return;

        setShowDeletePopup(false);
        setPaperToDelete(null);
    };

    const handleDeletePaper = async () => {
        if (!paperToDelete) return;

        try {
            setIsDeleting(true);
            setError("");

            await api.delete(
                `/projects/${id}/papers/${paperToDelete.id}/`
            );

            setPapers((currentPapers) =>
                currentPapers.filter(
                    (paper) => paper.id !== paperToDelete.id
                )
            );

            setSelectedPaperIds((prev) =>
                prev.filter((paperId) => paperId !== paperToDelete.id)
            );

            setShowDeletePopup(false);
            setPaperToDelete(null);
        } catch (err) {
            console.error("Failed to delete paper:", err);
            setError("Failed to delete the paper. Please try again.");
        } finally {
            setIsDeleting(false);
        }
    };

    const handlePaperSelectToggle = (paperId, e) => {
        if (e) e.stopPropagation();
        setSelectionNotice("");
        setTempMessage("");
        setSelectedPaperIds((prev) => {
            if (prev.includes(paperId)) {
                return prev.filter((id_) => id_ !== paperId);
            } else {
                if (prev.length >= 4) {
                    setSelectionNotice("You can compare up to 4 papers at a time.");
                    return prev;
                }
                return [...prev, paperId];
            }
        });
    };

    const handleSelectAll = () => {
        setSelectionNotice("");
        setTempMessage("");
        const allIds = papers.map((p) => p.id);
        if (allIds.length > 4) {
            setSelectedPaperIds(allIds.slice(0, 4));
            setSelectionNotice("You can compare up to 4 papers at a time.");
        } else {
            setSelectedPaperIds(allIds);
        }
    };

    const handleClearSelection = () => {
        setSelectionNotice("");
        setTempMessage("");
        setSelectedPaperIds([]);
    };

    const handleCompareClick = () => {
        if (selectedPaperIds.length < 2) return;
        navigate(`/projects/${id}/compare`, {
            state: {
                paperIds: selectedPaperIds
            }
        });
    };

    if (loading) {
        return (
            <div style={{ textAlign: "center", padding: "4rem 1.5rem", color: "var(--text-secondary)" }}>
                <div className="spinner-icon" style={{ margin: "0 auto 1rem auto" }}></div>
                <p style={{ margin: 0, fontSize: "1rem", fontWeight: 500 }}>Loading project...</p>
            </div>
        );
    }

    if (error && !project) {
        return (
            <div style={{ width: "100%", maxWidth: "800px", margin: "2.5rem auto", padding: "0 1.5rem", boxSizing: "border-box" }}>
                <Link
                    to="/projects"
                    style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "0.5rem",
                        marginBottom: "1.5rem",
                        color: "var(--text-secondary)",
                        textDecoration: "none",
                        fontWeight: 500
                    }}
                >
                    ← Back to Projects
                </Link>
                <div style={{
                    padding: "2.5rem 2rem",
                    background: "var(--bg-secondary)",
                    border: "1px solid var(--border-color)",
                    borderRadius: "var(--radius-xl)",
                    textAlign: "center"
                }}>
                    <div style={{
                        width: "3rem",
                        height: "3rem",
                        borderRadius: "50%",
                        background: "rgba(239, 68, 68, 0.1)",
                        color: "var(--danger)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        margin: "0 auto 1.25rem auto"
                    }}>
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <circle cx="12" cy="12" r="10"></circle>
                            <line x1="12" y1="8" x2="12" y2="12"></line>
                            <line x1="12" y1="16" x2="12.01" y2="16"></line>
                        </svg>
                    </div>
                    <h2 style={{ fontSize: "1.25rem", margin: "0 0 0.5rem 0", color: "var(--text-primary)" }}>
                        {error === "Project not found." ? "Project Not Found" : error === "You don't have permission to view this project." ? "Access Denied" : "Unable to Load Project"}
                    </h2>
                    <p style={{ color: "var(--text-secondary)", margin: "0 0 1.5rem 0", fontSize: "0.95rem" }}>
                        {error}
                    </p>
                    <Button onClick={() => navigate("/projects")}>
                        Return to Projects
                    </Button>
                </div>
            </div>
        );
    }

    const selectedCount = selectedPaperIds.length;
    const countText =
        selectedCount === 0
            ? "No papers selected"
            : selectedCount === 1
            ? "1 paper selected"
            : `${selectedCount} papers selected`;

    return (
        <div
            style={{
                width: "100%",
                maxWidth: "1400px",
                margin: "0 auto",
                padding: "0 1.5rem",
                boxSizing: "border-box",
            }}
        >
            <Link
                to="/projects"
                style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "0.5rem",
                    marginBottom: "1.5rem",
                    color: "var(--text-secondary)",
                }}
            >
                ← Back to Projects
            </Link>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "3rem", flexWrap: "wrap", gap: "1rem" }}>
                <div>
                    {!isEditingTitle ? (
                        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.5rem", flexWrap: "wrap" }}>
                            {isOwner && (
                                <button
                                    type="button"
                                    onClick={() => {
                                        setEditTitle(project.title);
                                        setRenameError("");
                                        setIsEditingTitle(true);
                                    }}
                                    title="Rename project"
                                    aria-label="Rename project"
                                    style={{
                                        background: "transparent",
                                        border: "1px solid transparent",
                                        borderRadius: "var(--radius-sm, 6px)",
                                        color: "var(--text-secondary)",
                                        cursor: "pointer",
                                        padding: "6px",
                                        display: "inline-flex",
                                        alignItems: "center",
                                        justifyContent: "center",
                                        transition: "all 0.15s ease",
                                    }}
                                    onMouseEnter={(e) => {
                                        e.currentTarget.style.color = "var(--text-primary)";
                                        e.currentTarget.style.backgroundColor = "var(--bg-surface-raised, rgba(255,255,255,0.08))";
                                        e.currentTarget.style.borderColor = "var(--border-color, rgba(255,255,255,0.12))";
                                    }}
                                    onMouseLeave={(e) => {
                                        e.currentTarget.style.color = "var(--text-secondary)";
                                        e.currentTarget.style.backgroundColor = "transparent";
                                        e.currentTarget.style.borderColor = "transparent";
                                    }}
                                >
                                    <svg
                                        width="20"
                                        height="20"
                                        viewBox="0 0 24 24"
                                        fill="none"
                                        stroke="currentColor"
                                        strokeWidth="2"
                                        strokeLinecap="round"
                                        strokeLinejoin="round"
                                        aria-hidden="true"
                                    >
                                        <path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z" />
                                    </svg>
                                </button>
                            )}

                            <h1
                                style={{
                                    fontSize: "2.5rem",
                                    margin: 0,
                                    lineHeight: 1.2,
                                }}
                            >
                                {project.title}
                            </h1>

                            <span className={`invitation-role-badge ${
                                isOwner ? "role-badge-owner" : isEditor ? "role-badge-editor" : "role-badge-viewer"
                            }`}>
                                {isOwner ? "Owner" : isEditor ? "Editor" : "Viewer"}
                            </span>
                        </div>
                    ) : (
                        <div style={{ marginBottom: "0.75rem" }}>
                            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
                                <input
                                    type="text"
                                    value={editTitle}
                                    onChange={(e) => {
                                        setEditTitle(e.target.value);
                                        if (renameError) setRenameError("");
                                    }}
                                    onKeyDown={(e) => {
                                        if (e.key === "Enter") {
                                            e.preventDefault();
                                            handleSaveTitle();
                                        }
                                        if (e.key === "Escape") {
                                            setIsEditingTitle(false);
                                            setRenameError("");
                                        }
                                    }}
                                    autoFocus
                                    disabled={isSavingTitle}
                                    style={{
                                        fontSize: "1.75rem",
                                        fontWeight: "700",
                                        padding: "0.35rem 0.75rem",
                                        borderRadius: "var(--radius-md, 8px)",
                                        border: "1px solid var(--accent-primary, #6366f1)",
                                        backgroundColor: "var(--bg-input, var(--bg-surface-raised, #1e2230))",
                                        color: "var(--text-primary, #ffffff)",
                                        outline: "none",
                                        minWidth: "260px",
                                        maxWidth: "600px",
                                    }}
                                />
                                <div style={{ display: "flex", gap: "0.5rem" }}>
                                    <Button
                                        size="small"
                                        variant="primary"
                                        disabled={isSavingTitle || !editTitle.trim()}
                                        onClick={handleSaveTitle}
                                    >
                                        {isSavingTitle ? "Saving..." : "Save"}
                                    </Button>
                                    <Button
                                        size="small"
                                        variant="secondary"
                                        disabled={isSavingTitle}
                                        onClick={() => {
                                            setIsEditingTitle(false);
                                            setRenameError("");
                                        }}
                                    >
                                        Cancel
                                    </Button>
                                </div>
                            </div>
                            {renameError && (
                                <div style={{ color: "var(--danger)", fontSize: "0.875rem", marginTop: "0.35rem" }}>
                                    {renameError}
                                </div>
                            )}
                        </div>
                    )}

                    <p
                        style={{
                            fontSize: "1.125rem",
                            color: "var(--text-secondary)",
                            margin: 0,
                        }}
                    >
                        {project.description || "No description provided."}
                    </p>
                </div>

                <div>
                    <Button
                        variant="secondary"
                        onClick={() => navigate(`/projects/${id}/research`)}
                    >
                        Research Workspace
                    </Button>
                </div>
            </div>

            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: canEditContent ? "minmax(280px, 1fr) minmax(0, 2.5fr)" : "1fr",
                    gap: "2rem",
                }}
            >
                {canEditContent && (
                    <aside>
                        <Card>
                            <h3
                                style={{
                                    marginTop: 0,
                                    marginBottom: "1.5rem",
                                }}
                            >
                                Upload Research Paper
                            </h3>

                            {error && (
                                <div
                                    style={{
                                        padding: "0.75rem",
                                        background:
                                            "rgba(239, 68, 68, 0.1)",
                                        color: "var(--danger)",
                                        borderRadius: "var(--radius-md)",
                                        marginBottom: "1rem",
                                        fontSize: "0.875rem",
                                    }}
                                >
                                    {error}
                                </div>
                            )}

                            <form
                                onSubmit={handleUpload}
                                style={{
                                    display: "flex",
                                    flexDirection: "column",
                                    gap: "1rem",
                                }}
                            >
                                <Input
                                    label="Paper Title"
                                    id="title"
                                    type="text"
                                    value={title}
                                    onChange={(e) =>
                                        setTitle(e.target.value)
                                    }
                                    placeholder="Enter title"
                                />

                                <div className="input-group">
                                    <label htmlFor="paper-file">
                                        PDF Document
                                    </label>

                                    <input
                                        id="paper-file"
                                        type="file"
                                        accept=".pdf,application/pdf"
                                        onChange={(e) =>
                                            setFile(e.target.files[0])
                                        }
                                        className="input"
                                    />
                                </div>

                                <Button
                                    type="submit"
                                    disabled={uploading}
                                    style={{ marginTop: "0.5rem" }}
                                >
                                    {uploading
                                        ? "Uploading..."
                                        : "Upload Paper"}
                                </Button>
                            </form>
                        </Card>
                    </aside>
                )}

                <section>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem", flexWrap: "wrap", gap: "1rem" }}>
                        <h2 style={{ margin: 0 }}>
                            Research Papers
                        </h2>

                        {papers.length > 0 && (
                            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
                                <span style={{ fontSize: "0.875rem", fontWeight: 600, color: "var(--text-secondary)" }}>
                                    {countText}
                                </span>
                                <button
                                    onClick={handleSelectAll}
                                    style={{
                                        background: "none",
                                        border: "1px solid var(--border-color)",
                                        borderRadius: "var(--radius-sm)",
                                        color: "var(--text-primary)",
                                        fontSize: "0.8rem",
                                        padding: "0.3rem 0.6rem",
                                        cursor: "pointer",
                                    }}
                                >
                                    Select All
                                </button>
                                <button
                                    onClick={handleClearSelection}
                                    style={{
                                        background: "none",
                                        border: "1px solid var(--border-color)",
                                        borderRadius: "var(--radius-sm)",
                                        color: "var(--text-secondary)",
                                        fontSize: "0.8rem",
                                        padding: "0.3rem 0.6rem",
                                        cursor: "pointer",
                                    }}
                                >
                                    Clear Selection
                                </button>
                                <Button
                                    variant="primary"
                                    onClick={handleCompareClick}
                                    disabled={selectedPaperIds.length < 2}
                                    style={{ fontSize: "0.875rem" }}
                                >
                                    Compare Selected Papers
                                </Button>
                            </div>
                        )}
                    </div>

                    {selectionNotice && (
                        <div style={{ padding: "0.75rem", background: "rgba(234, 179, 8, 0.15)", color: "#eab308", borderRadius: "var(--radius-md)", marginBottom: "1rem", fontSize: "0.875rem", fontWeight: 500 }}>
                            {selectionNotice}
                        </div>
                    )}

                    {tempMessage && (
                        <div style={{ padding: "0.75rem", background: "rgba(99, 102, 241, 0.15)", color: "var(--accent-primary)", borderRadius: "var(--radius-md)", marginBottom: "1rem", fontSize: "0.875rem", fontWeight: 500 }}>
                            {tempMessage}
                        </div>
                    )}

                    {papers.length === 0 ? (
                        <Card
                            style={{
                                textAlign: "center",
                                padding: "3rem 2rem",
                            }}
                        >
                            <h3
                                style={{
                                    color: "var(--text-secondary)",
                                }}
                            >
                                No papers yet
                            </h3>

                            <p style={{ margin: 0 }}>
                                Upload your first research paper to get
                                started.
                            </p>
                        </Card>
                    ) : (
                        <div
                            style={{
                                display: "grid",
                                gridTemplateColumns:
                                    "repeat(auto-fill, minmax(300px, 1fr))",
                                gap: "1rem",
                            }}
                        >
                            {papers.map((paper) => {
                                const isSelected = selectedPaperIds.includes(paper.id);
                                return (
                                    <Card
                                        key={paper.id}
                                        className="card-glass"
                                        style={{
                                            display: "flex",
                                            flexDirection: "column",
                                            border: isSelected ? "2px solid var(--accent-primary)" : "1px solid var(--border-color)",
                                            transition: "border-color 0.2s",
                                        }}
                                    >
                                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.5rem", marginBottom: "0.5rem" }}>
                                            <h3
                                                style={{
                                                    margin: 0,
                                                    fontSize: "1.25rem",
                                                    lineHeight: "1.3",
                                                }}
                                            >
                                                <Link
                                                    to={`/projects/${id}/papers/${paper.id}`}
                                                    style={{
                                                        color: "var(--text-primary)",
                                                    }}
                                                >
                                                    {paper.title}
                                                </Link>
                                            </h3>
                                            <label
                                                onClick={(e) => e.stopPropagation()}
                                                style={{
                                                    display: "inline-flex",
                                                    alignItems: "center",
                                                    gap: "0.35rem",
                                                    fontSize: "0.8rem",
                                                    cursor: "pointer",
                                                    background: isSelected ? "rgba(99, 102, 241, 0.15)" : "var(--bg-tertiary)",
                                                    color: isSelected ? "var(--accent-primary)" : "var(--text-secondary)",
                                                    padding: "0.25rem 0.5rem",
                                                    borderRadius: "var(--radius-sm)",
                                                    border: isSelected ? "1px solid var(--accent-primary)" : "1px solid var(--border-color)",
                                                    fontWeight: 600,
                                                    whiteSpace: "nowrap",
                                                }}
                                            >
                                                <input
                                                    type="checkbox"
                                                    checked={isSelected}
                                                    onChange={(e) => handlePaperSelectToggle(paper.id, e)}
                                                    onClick={(e) => e.stopPropagation()}
                                                    style={{ cursor: "pointer" }}
                                                />
                                                {isSelected ? "Selected" : "Select"}
                                            </label>
                                        </div>

                                        <p
                                            style={{
                                                margin: "0 0 1.5rem 0",
                                                fontSize: "0.875rem",
                                                color: "var(--text-muted)",
                                            }}
                                        >
                                            Uploaded:{" "}
                                            {new Date(
                                                paper.uploaded_at
                                            ).toLocaleDateString()}
                                        </p>

                                        <div
                                            style={{
                                                marginTop: "auto",
                                                display: "flex",
                                                justifyContent: "space-between",
                                                alignItems: "center",
                                                gap: "1rem",
                                            }}
                                        >
                                            <Link to={`/projects/${id}/papers/${paper.id}`}>
                                                <Button variant="secondary">
                                                    View & Analyze
                                                </Button>
                                            </Link>

                                            {canEditContent && (
                                                <button
                                                    className="delete-button"
                                                    onClick={() => openDeletePopup(paper)}
                                                >
                                                    Delete
                                                </button>
                                            )}
                                        </div>
                                    </Card>
                                );
                            })}
                        </div>
                    )}
                </section>
            </div>

            {/* Collaboration & Team Members Section */}
            <section className="collaboration-card" aria-label="Project Collaborators">
                <div className="collaboration-header">
                    <div className="collaboration-title-wrap">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: "var(--accent-primary)" }}>
                            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                            <circle cx="9" cy="7" r="4"></circle>
                            <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                            <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
                        </svg>
                        <h3 className="collaboration-title">Project Collaborators</h3>
                        <span className="invitations-count-badge">
                            {1 + members.filter((m) => m.username !== project.owner).length}
                        </span>
                    </div>
                </div>

                {memberError && <div className="collaboration-alert error">{memberError}</div>}

                <div className={isOwner ? "collaboration-grid" : ""}>
                    {/* Members List */}
                    <div className="members-list-panel">
                        {/* Authoritative Owner Entry */}
                        <div className="member-item-row">
                            <div className="member-user-info">
                                <span className="member-username">@{project.owner}</span>
                                <span className="invitation-role-badge role-badge-owner">Owner</span>
                                <span className="member-meta-text">&bull; Project Creator</span>
                            </div>
                        </div>

                        {/* Other Project Members */}
                        {members
                            .filter((m) => m.username !== project.owner)
                            .map((member) => {
                                const memberRoleClass =
                                    member.role === "EDITOR" ? "role-badge-editor" : "role-badge-viewer";
                                const mUserId = member.user_id || member.user;
                                const isRemoving = removingMemberId === mUserId;

                                return (
                                    <div key={member.id} className="member-item-row">
                                        <div className="member-user-info">
                                            <span className="member-username">@{member.username}</span>
                                            <span className={`invitation-role-badge ${memberRoleClass}`}>
                                                {member.role === "EDITOR" ? "Editor" : "Viewer"}
                                            </span>
                                            {member.created_at && (
                                                <span className="member-meta-text">
                                                    &bull; Joined {new Date(member.created_at).toLocaleDateString()}
                                                </span>
                                            )}
                                        </div>

                                        {isOwner && (
                                            <button
                                                type="button"
                                                className="member-remove-btn"
                                                onClick={() => handleRemoveMember(mUserId, member.username)}
                                                disabled={isRemoving}
                                            >
                                                {isRemoving ? "Removing..." : "Remove"}
                                            </button>
                                        )}
                                    </div>
                                );
                            })}

                        {members.filter((m) => m.username !== project.owner).length === 0 && (
                            <p style={{ margin: "0.5rem 0", color: "var(--text-muted)", fontSize: "0.875rem" }}>
                                No collaborators added yet. {isOwner ? "Invite editors or viewers using the form." : ""}
                            </p>
                        )}
                    </div>

                    {/* Invite Form (Owner Only) */}
                    {isOwner && (
                        <div className="invite-panel">
                            <h4 className="invite-panel-title">Add Collaborator</h4>

                            {inviteSuccess && (
                                <div className="collaboration-alert success">{inviteSuccess}</div>
                            )}
                            {inviteError && (
                                <div className="collaboration-alert error">{inviteError}</div>
                            )}

                            {/* Friends Section */}
                            <div className="invite-friends-section">
                                <span className="invite-section-subtitle">Friends</span>
                                {friendsList.length === 0 ? (
                                    <p className="invite-no-friends-text">
                                        No friends yet. You can search registered users below or add friends in the Friends menu.
                                    </p>
                                ) : (
                                    <div className="invite-friends-options-list">
                                        {friendsList.map((f) => {
                                            const friendUser = f.user?.username || f.other_username || (f.user_username === user?.username ? f.friend_username : f.user_username);
                                            if (!friendUser) return null;
                                            const friendshipId = f.id || f.friendship_id;
                                            const isAlreadyMember = members.some(
                                                (m) => m.username.toLowerCase() === friendUser.toLowerCase()
                                            ) || (project.owner && project.owner.toLowerCase() === friendUser.toLowerCase());

                                            return (
                                                <label 
                                                    key={friendshipId} 
                                                    className={`invite-friend-row ${selectedFriend === friendUser ? 'selected' : ''} ${isAlreadyMember ? 'disabled' : ''}`}
                                                >
                                                    <div className="invite-friend-radio-label">
                                                        <input
                                                            type="radio"
                                                            name="invite_friend_select"
                                                            value={friendUser}
                                                            checked={selectedFriend === friendUser}
                                                            disabled={isAlreadyMember || inviting}
                                                            onChange={() => {
                                                                setSelectedFriend(friendUser);
                                                                setInviteUsername(friendUser);
                                                                if (inviteError) setInviteError("");
                                                            }}
                                                        />
                                                        <span className="invite-friend-username">@{friendUser}</span>
                                                    </div>
                                                    {isAlreadyMember && (
                                                        <span className="invite-member-status">Member</span>
                                                    )}
                                                </label>
                                            );
                                        })}
                                    </div>
                                )}
                            </div>

                            <form onSubmit={handleInvite} className="invite-form">
                                <div className="invite-search-section">
                                    <label htmlFor="invite-username" className="invite-section-subtitle">
                                        Search registered users
                                    </label>
                                    <Input
                                        id="invite-username"
                                        type="text"
                                        value={inviteUsername}
                                        onChange={(e) => {
                                            setInviteUsername(e.target.value);
                                            setSelectedFriend("");
                                            if (inviteError) setInviteError("");
                                        }}
                                        placeholder="Enter registered username"
                                        disabled={inviting}
                                    />
                                </div>

                                <div className="invite-select-group">
                                    <label htmlFor="invite-role" className="invite-section-subtitle">
                                        Role
                                    </label>
                                    <select
                                        id="invite-role"
                                        className="invite-select"
                                        value={inviteRole}
                                        onChange={(e) => setInviteRole(e.target.value)}
                                        disabled={inviting}
                                    >
                                        <option value="VIEWER">Viewer</option>
                                        <option value="EDITOR">Editor</option>
                                    </select>
                                </div>

                                <div className="invite-buttons-row">
                                    <Button
                                        type="button"
                                        variant="secondary"
                                        onClick={() => {
                                            setInviteUsername("");
                                            setSelectedFriend("");
                                            setInviteError("");
                                            setInviteSuccess("");
                                        }}
                                        disabled={inviting}
                                    >
                                        Cancel
                                    </Button>
                                    <Button type="submit" disabled={inviting || !inviteUsername.trim()}>
                                        {inviting ? "Inviting..." : "Invite"}
                                    </Button>
                                </div>
                            </form>
                        </div>
                    )}
                </div>
            </section>

            {showDeletePopup && (
                <div
                    className="modal-overlay"
                    onClick={closeDeletePopup}
                >
                    <div
                        className="delete-modal"
                        role="dialog"
                        aria-modal="true"
                        aria-labelledby="delete-modal-title"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <h2 id="delete-modal-title">
                            Delete PDF?
                        </h2>

                        <p>
                            Are you sure you want to delete{" "}
                            <strong>{paperToDelete?.title}</strong>?
                        </p>

                        <p className="delete-warning">
                            This action cannot be undone.
                        </p>

                        <div className="modal-actions">
                            <button
                                className="cancel-button"
                                onClick={closeDeletePopup}
                                disabled={isDeleting}
                            >
                                Cancel
                            </button>

                            <button
                                className="confirm-delete-button"
                                onClick={handleDeletePaper}
                                disabled={isDeleting}
                            >
                                {isDeleting
                                    ? "Deleting..."
                                    : "Delete"}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default ProjectDetails;