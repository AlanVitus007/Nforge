import { useEffect, useState, useContext, useCallback } from "react";
import { Link, useNavigate } from "react-router-dom";
import api from "../services/api";
import { AuthContext } from "../context/AuthContext";
import Button from "../components/Button";
import Input from "../components/Input";
import DeleteModal from "../components/DeleteModal";
import ProjectInvitations from "../components/ProjectInvitations";
import { getProjectMembers } from "../services/collaboration";
import "./Projects.css";

function Projects() {
    const { user } = useContext(AuthContext);
    const navigate = useNavigate();

    const [projects, setProjects] = useState([]);
    const [projectRoles, setProjectRoles] = useState({});
    const [selectedProjectId, setSelectedProjectId] = useState(null);
    const [membersCache, setMembersCache] = useState({});
    const [loadingMembers, setLoadingMembers] = useState(false);

    // New project modal / form state
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [title, setTitle] = useState("");
    const [description, setDescription] = useState("");
    const [creating, setCreating] = useState(false);

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [deleteModal, setDeleteModal] = useState({ open: false, projectId: null, projectTitle: '' });
    const [isDeleting, setIsDeleting] = useState(false);

    const fetchProjects = useCallback(async () => {
        try {
            setLoading(true);
            setError("");
            const response = await api.get("/projects/");
            const projectList = response.data || [];
            setProjects(projectList);

            if (projectList.length > 0 && !selectedProjectId) {
                setSelectedProjectId(projectList[0].id);
            }

            // Fetch member roles for shared projects
            if (user && projectList.length > 0) {
                const sharedProjects = projectList.filter((p) => p.owner !== user.username);
                if (sharedProjects.length > 0) {
                    const roleEntries = await Promise.all(
                        sharedProjects.map(async (p) => {
                            try {
                                const members = await getProjectMembers(p.id);
                                const myMember = members.find(
                                    (m) => m.username === user.username || m.user_id === user.id
                                );
                                return [p.id, myMember?.role || "VIEWER"];
                            } catch {
                                return [p.id, "VIEWER"];
                            }
                        })
                    );
                    setProjectRoles(Object.fromEntries(roleEntries));
                }
            }
        } catch (err) {
            setError("Failed to load projects.");
        } finally {
            setLoading(false);
        }
    }, [user, selectedProjectId]);

    useEffect(() => {
        fetchProjects();
    }, [fetchProjects]);

    // Fetch members for currently selected project (cached)
    useEffect(() => {
        if (!selectedProjectId) return;

        if (membersCache[selectedProjectId]) {
            return; // Already cached
        }

        let isMounted = true;
        const loadActiveMembers = async () => {
            try {
                setLoadingMembers(true);
                const data = await getProjectMembers(selectedProjectId);
                if (isMounted) {
                    setMembersCache((prev) => ({
                        ...prev,
                        [selectedProjectId]: Array.isArray(data) ? data : [],
                    }));
                }
            } catch (err) {
                console.error("Failed to load project members", err);
            } finally {
                if (isMounted) setLoadingMembers(false);
            }
        };

        loadActiveMembers();
        return () => {
            isMounted = false;
        };
    }, [selectedProjectId, membersCache]);

    const activeProject = projects.find((p) => p.id === selectedProjectId) || projects[0] || null;
    const activeMembers = activeProject ? (membersCache[activeProject.id] || []) : [];

    const handleCreate = async (e) => {
        e.preventDefault();

        if (!title.trim()) {
            setError("Project title is required.");
            return;
        }

        try {
            setCreating(true);
            setError("");
            const res = await api.post("/projects/", { title, description });
            setTitle("");
            setDescription("");
            setShowCreateModal(false);
            await fetchProjects();
            if (res.data?.id) {
                setSelectedProjectId(res.data.id);
            }
        } catch (err) {
            setError("Failed to create project.");
        } finally {
            setCreating(false);
        }
    };

    const openDeleteModal = (e, projectId, projectTitle) => {
        e.stopPropagation();
        setDeleteModal({ open: true, projectId, projectTitle });
    };

    const closeDeleteModal = () => {
        if (isDeleting) return;
        setDeleteModal({ open: false, projectId: null, projectTitle: '' });
    };

    const handleDelete = async () => {
        const { projectId } = deleteModal;
        try {
            setIsDeleting(true);
            setError("");
            await api.delete(`/projects/${projectId}/`);
            setProjects((currentProjects) => {
                const updated = currentProjects.filter((project) => project.id !== projectId);
                if (selectedProjectId === projectId && updated.length > 0) {
                    setSelectedProjectId(updated[0].id);
                } else if (updated.length === 0) {
                    setSelectedProjectId(null);
                }
                return updated;
            });
            closeDeleteModal();
        } catch (err) {
            setError("Failed to delete project.");
        } finally {
            setIsDeleting(false);
        }
    };

    const getInitials = (name) => {
        if (!name) return "U";
        return name.slice(0, 2).toUpperCase();
    };

    return (
        <div className="projects-container animate-fade-in">
            {/* Header: Title + [+ New Project] */}
            <div className="projects-header-bar">
                <div>
                    <h1 className="projects-header-title">Projects</h1>
                    <p className="projects-header-subtitle">
                        Create, organize, and synthesize academic literature collections.
                    </p>
                </div>

                <Button onClick={() => setShowCreateModal(true)}>
                    <span style={{ marginRight: "0.35rem", fontWeight: "bold" }}>+</span> New Project
                </Button>
            </div>

            {error && (
                <div style={{
                    padding: "0.75rem 1.25rem",
                    background: "rgba(239, 68, 68, 0.1)",
                    color: "var(--danger)",
                    borderRadius: "var(--radius-md)",
                    marginBottom: "1.5rem",
                    fontSize: "0.875rem",
                }}>
                    {error}
                </div>
            )}

            {/* Pending Invitations Banner */}
            <ProjectInvitations onAccepted={fetchProjects} />

            {/* 2-Column Responsive Layout */}
            <div className="projects-main-layout">
                {/* Left Column: Projects List */}
                <section className="projects-list-col" aria-label="Projects list">
                    {loading ? (
                        <div style={{ textAlign: "center", padding: "3rem 0", color: "var(--text-secondary)" }}>
                            Loading projects...
                        </div>
                    ) : projects.length === 0 ? (
                        <div style={{
                            textAlign: "center",
                            padding: "3rem 2rem",
                            background: "var(--bg-secondary)",
                            borderRadius: "var(--radius-lg)",
                            border: "1px solid var(--border-color)",
                        }}>
                            <h3 style={{ color: "var(--text-secondary)", marginTop: 0 }}>No projects yet</h3>
                            <p style={{ color: "var(--text-muted)", marginBottom: "1.25rem" }}>
                                Start your research by creating a project.
                            </p>
                            <Button onClick={() => setShowCreateModal(true)}>
                                Create First Project
                            </Button>
                        </div>
                    ) : (
                        projects.map((project) => {
                            const isOwner = user && project.owner === user.username;
                            const role = isOwner
                                ? "OWNER"
                                : projectRoles[project.id] || "VIEWER";
                            const roleBadgeClass =
                                role === "OWNER"
                                    ? "role-badge-owner"
                                    : role === "EDITOR"
                                    ? "role-badge-editor"
                                    : "role-badge-viewer";
                            const isSelected = activeProject?.id === project.id;

                            return (
                                <div
                                    key={project.id}
                                    className={`project-item-card ${isSelected ? "active-project" : ""}`}
                                    onClick={() => setSelectedProjectId(project.id)}
                                    role="button"
                                    tabIndex={0}
                                    onKeyDown={(e) => {
                                        if (e.key === "Enter" || e.key === " ") {
                                            setSelectedProjectId(project.id);
                                        }
                                    }}
                                    aria-label={`Project: ${project.title}`}
                                >
                                    <div className="project-item-card-top">
                                        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
                                            <Link
                                                to={`/projects/${project.id}`}
                                                className="project-title-link"
                                                onClick={(e) => e.stopPropagation()}
                                            >
                                                {project.title}
                                            </Link>
                                            <span className={`invitation-role-badge ${roleBadgeClass}`}>
                                                {role === "OWNER" ? "Owner" : role === "EDITOR" ? "Editor" : "Viewer"}
                                            </span>
                                        </div>

                                        <div className="project-item-actions">
                                            {isOwner && (
                                                <Button
                                                    variant="danger"
                                                    onClick={(e) => openDeleteModal(e, project.id, project.title)}
                                                    style={{ padding: "0.25rem 0.5rem", fontSize: "0.75rem" }}
                                                    aria-label={`Delete project ${project.title}`}
                                                >
                                                    Delete
                                                </Button>
                                            )}
                                        </div>
                                    </div>

                                    <p className="project-item-desc">
                                        {project.description || "No description provided."}
                                    </p>

                                    <div className="project-item-meta">
                                        <span>
                                            Owner: @{project.owner} &bull; {project.paper_count || 0} {project.paper_count === 1 ? "paper" : "papers"}
                                        </span>
                                        <span>
                                            {new Date(project.created_at).toLocaleDateString()}
                                        </span>
                                    </div>
                                </div>
                            );
                        })
                    )}
                </section>

                {/* Right Column: Collaborator Panel for Active Project */}
                <aside className="collaborators-panel-col" aria-label="Collaborators panel">
                    <div className="collaborators-panel-header">
                        <h2 className="collaborators-panel-title">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                                <circle cx="9" cy="7" r="4"></circle>
                                <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
                                <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
                            </svg>
                            Collaborators
                        </h2>
                    </div>

                    {activeProject ? (
                        <>
                            <div className="active-project-tag">
                                For: <strong>{activeProject.title}</strong>
                            </div>

                            <div className="collaborators-list">
                                {/* Owner entry */}
                                <div className="collaborator-row">
                                    <div className="collaborator-user-info">
                                        <div className="collaborator-avatar">
                                            {getInitials(activeProject.owner)}
                                        </div>
                                        <span className="collaborator-name">@{activeProject.owner}</span>
                                    </div>
                                    <span className="invitation-role-badge role-badge-owner">Owner</span>
                                </div>

                                {/* Members */}
                                {loadingMembers ? (
                                    <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", margin: "0.5rem 0" }}>
                                        Loading members...
                                    </p>
                                ) : (
                                    activeMembers
                                        .filter((m) => m.username !== activeProject.owner)
                                        .map((m) => (
                                            <div key={m.id || m.username} className="collaborator-row">
                                                <div className="collaborator-user-info">
                                                    <div className="collaborator-avatar">
                                                        {getInitials(m.username)}
                                                    </div>
                                                    <span className="collaborator-name">@{m.username}</span>
                                                </div>
                                                <span className={`invitation-role-badge ${m.role === "EDITOR" ? "role-badge-editor" : "role-badge-viewer"}`}>
                                                    {m.role === "EDITOR" ? "Editor" : "Viewer"}
                                                </span>
                                            </div>
                                        ))
                                )}

                                {!loadingMembers && activeMembers.filter((m) => m.username !== activeProject.owner).length === 0 && (
                                    <p style={{ fontSize: "0.825rem", color: "var(--text-muted)", margin: "0.5rem 0" }}>
                                        No additional collaborators on this project.
                                    </p>
                                )}
                            </div>

                            <div className="collaborators-panel-footer">
                                <Button
                                    variant="secondary"
                                    onClick={() => navigate(`/projects/${activeProject.id}`)}
                                >
                                    Manage
                                </Button>
                            </div>
                        </>
                    ) : (
                        <p style={{ color: "var(--text-muted)", fontSize: "0.875rem" }}>
                            Select a project to view its collaborators.
                        </p>
                    )}
                </aside>
            </div>

            {/* Modal for Creating Project */}
            {showCreateModal && (
                <div
                    className="modal-backdrop animate-fade-in"
                    onClick={() => setShowCreateModal(false)}
                    role="dialog"
                    aria-modal="true"
                    aria-labelledby="create-project-title"
                >
                    <div
                        className="new-project-modal-card"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="modal-header" style={{ padding: "0 0 1rem 0" }}>
                            <h2 id="create-project-title" className="modal-title">Create New Project</h2>
                            <button
                                type="button"
                                className="modal-close-btn"
                                onClick={() => setShowCreateModal(false)}
                                aria-label="Close modal"
                            >
                                &times;
                            </button>
                        </div>

                        <form onSubmit={handleCreate} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                            <Input
                                label="Project Title"
                                id="create-title"
                                type="text"
                                value={title}
                                onChange={(e) => setTitle(e.target.value)}
                                placeholder="E.g., Quantum Machine Learning Review"
                                disabled={creating}
                                autoFocus
                            />

                            <div className="input-group">
                                <label htmlFor="create-desc">Description (Optional)</label>
                                <textarea
                                    id="create-desc"
                                    className="input"
                                    value={description}
                                    onChange={(e) => setDescription(e.target.value)}
                                    placeholder="Brief outline of research topic..."
                                    rows="3"
                                    style={{ resize: "vertical" }}
                                    disabled={creating}
                                />
                            </div>

                            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.75rem", marginTop: "0.5rem" }}>
                                <Button
                                    type="button"
                                    variant="secondary"
                                    onClick={() => setShowCreateModal(false)}
                                    disabled={creating}
                                >
                                    Cancel
                                </Button>
                                <Button type="submit" disabled={creating || !title.trim()}>
                                    {creating ? "Creating..." : "Create Project"}
                                </Button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Delete Modal */}
            <DeleteModal
                isOpen={deleteModal.open}
                onClose={closeDeleteModal}
                onConfirm={handleDelete}
                title="Delete Project?"
                message={
                    <>
                        Are you sure you want to delete{" "}
                        <strong>"{deleteModal.projectTitle}"</strong>?
                    </>
                }
                warning="All papers in this project will also be permanently deleted."
                isDeleting={isDeleting}
            />
        </div>
    );
}

export default Projects;