import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../services/api";
import Card from "../components/Card";
import Button from "../components/Button";
import Input from "../components/Input";
import DeleteModal from "../components/DeleteModal";

function Projects() {
    const [projects, setProjects] = useState([]);
    const [title, setTitle] = useState("");
    const [description, setDescription] = useState("");
    const [loading, setLoading] = useState(true);
    const [creating, setCreating] = useState(false);
    const [error, setError] = useState("");
    const [deleteModal, setDeleteModal] = useState({ open: false, projectId: null, projectTitle: '' });
    const [isDeleting, setIsDeleting] = useState(false);

    const fetchProjects = async () => {
        try {
            setLoading(true);
            setError("");
            const response = await api.get("/projects/");
            setProjects(response.data);
        } catch (err) {
            setError("Failed to load projects.");
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchProjects();
    }, []);

    const handleCreate = async (e) => {
        e.preventDefault();

        if (!title.trim()) {
            setError("Project title is required.");
            return;
        }

        try {
            setCreating(true);
            setError("");
            await api.post("/projects/", { title, description });
            setTitle("");
            setDescription("");
            await fetchProjects();
        } catch (err) {
            setError("Failed to create project.");
        } finally {
            setCreating(false);
        }
    };

    const openDeleteModal = (projectId, projectTitle) => {
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
            setProjects((currentProjects) =>
                currentProjects.filter((project) => project.id !== projectId)
            );
            closeDeleteModal();
        } catch (err) {
            setError("Failed to delete project.");
        } finally {
            setIsDeleting(false);
        }
    };

    return (
        <>
        <div style={{ maxWidth: '900px', margin: '0 auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <div>
                    <h1 style={{ marginBottom: '0.5rem' }}>My Projects</h1>
                    <p style={{ color: 'var(--text-secondary)' }}>Create and manage your research projects.</p>
                </div>
            </div>

            {error && (
                <div style={{ padding: '1rem', background: 'rgba(239, 68, 68, 0.1)', color: 'var(--danger)', borderRadius: 'var(--radius-md)', marginBottom: '2rem' }}>
                    {error}
                </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '2rem' }}>
                <aside>
                    <Card>
                        <h3 style={{ marginTop: 0, marginBottom: '1.5rem' }}>Create New</h3>
                        <form onSubmit={handleCreate} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                            <Input
                                label="Title"
                                id="title"
                                type="text"
                                value={title}
                                onChange={(e) => setTitle(e.target.value)}
                                placeholder="Project title"
                            />
                            <div className="input-group">
                                <label htmlFor="desc">Description</label>
                                <textarea
                                    id="desc"
                                    className="input"
                                    value={description}
                                    onChange={(e) => setDescription(e.target.value)}
                                    placeholder="Brief description"
                                    rows="4"
                                    style={{ resize: 'vertical' }}
                                />
                            </div>
                            <Button type="submit" disabled={creating} style={{ marginTop: '0.5rem' }}>
                                {creating ? "Creating..." : "Create Project"}
                            </Button>
                        </form>
                    </Card>
                </aside>

                <section>
                    {loading ? (
                        <div style={{ textAlign: 'center', padding: '3rem 0', color: 'var(--text-secondary)' }}>
                            Loading projects...
                        </div>
                    ) : projects.length === 0 ? (
                        <Card style={{ textAlign: 'center', padding: '3rem 2rem' }}>
                            <h3 style={{ color: 'var(--text-secondary)' }}>No projects yet</h3>
                            <p>Create your first project using the form.</p>
                        </Card>
                    ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                            {projects.map((project) => (
                                <Card key={project.id} className="card-glass" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                    <div>
                                        <h3 style={{ margin: '0 0 0.5rem 0' }}>
                                            <Link to={`/projects/${project.id}`} style={{ color: 'var(--text-primary)' }}>
                                                {project.title}
                                            </Link>
                                        </h3>
                                        <p style={{ margin: 0, fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
                                            {project.description || "No description."}
                                        </p>
                                    </div>
                                    <Button 
                                        variant="danger" 
                                        onClick={() => openDeleteModal(project.id, project.title)}
                                        style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                                    >
                                        Delete
                                    </Button>
                                </Card>
                            ))}
                        </div>
                    )}
                </section>
            </div>
        </div>

        <DeleteModal
            isOpen={deleteModal.open}
            onClose={closeDeleteModal}
            onConfirm={handleDelete}
            title="Delete Project?"
            message={
                <>
                    Are you sure you want to delete{' '}
                    <strong>"{deleteModal.projectTitle}"</strong>?
                </>
            }
            warning="All papers in this project will also be permanently deleted."
            isDeleting={isDeleting}
        />
        </>
    );
}

export default Projects;