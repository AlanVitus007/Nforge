import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "../services/api";
import Card from "../components/Card";
import Button from "../components/Button";
import Input from "../components/Input";

function ProjectDetails() {
    const { id } = useParams();

    const [project, setProject] = useState(null);
    const [papers, setPapers] = useState([]);
    const [title, setTitle] = useState("");
    const [file, setFile] = useState(null);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState("");

    const [showDeletePopup, setShowDeletePopup] = useState(false);
    const [paperToDelete, setPaperToDelete] = useState(null);
    const [isDeleting, setIsDeleting] = useState(false);

    const fetchProject = async () => {
        try {
            const response = await api.get(`/projects/${id}/`);
            setProject(response.data);
        } catch (err) {
            setError("Failed to load project.");
        }
    };

    const fetchPapers = async () => {
        try {
            const response = await api.get(`/projects/${id}/papers/`);
            setPapers(response.data);
        } catch (err) {
            setError("Failed to load papers.");
        }
    };

    useEffect(() => {
        const loadData = async () => {
            setLoading(true);
            setError("");

            await fetchProject();
            await fetchPapers();

            setLoading(false);
        };

        loadData();
    }, [id]);

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

            setShowDeletePopup(false);
            setPaperToDelete(null);
        } catch (err) {
            console.error("Failed to delete paper:", err);
            setError("Failed to delete the paper. Please try again.");
        } finally {
            setIsDeleting(false);
        }
    };

    if (loading) {
        return (
            <div style={{ textAlign: "center", padding: "3rem" }}>
                Loading project...
            </div>
        );
    }

    if (error && !project) {
        return (
            <div style={{ color: "var(--danger)", padding: "2rem" }}>
                {error}
            </div>
        );
    }

    return (
        <div
            style={{
                width: "100%",
                maxWidth: "1400px",
                margin: "0 auto",
                padding: "0 1.5rem",
                boxSizing: "border-box",
            }}
        >            <Link
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

            <div style={{ marginBottom: "3rem" }}>
                <h1
                    style={{
                        fontSize: "2.5rem",
                        marginBottom: "0.5rem",
                    }}
                >
                    {project.title}
                </h1>

                <p
                    style={{
                        fontSize: "1.125rem",
                        color: "var(--text-secondary)",
                    }}
                >
                    {project.description || "No description provided."}
                </p>
            </div>
            <div
                style={{
                    display: "grid",
                    gridTemplateColumns: "minmax(280px, 1fr) minmax(0, 2.5fr)",
                    gap: "2rem",
                }}
            >
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

                <section>
                    <h2 style={{ marginBottom: "1.5rem" }}>
                        Research Papers
                    </h2>

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
                            {papers.map((paper) => (
                                <Card
                                    key={paper.id}
                                    className="card-glass"
                                    style={{
                                        display: "flex",
                                        flexDirection: "column",
                                    }}
                                >
                                    <h3
                                        style={{
                                            margin: "0 0 0.5rem 0",
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

                                        <button
                                            className="delete-button"
                                            onClick={() => openDeletePopup(paper)}
                                        >
                                            Delete
                                        </button>
                                    </div>
                                </Card>
                            ))}
                        </div>
                    )}
                </section>
            </div>

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