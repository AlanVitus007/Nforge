
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import api from "../services/api";
import Card from "../components/Card";

function PaperDetails() {
    const { projectId, paperId } = useParams();
    const navigate = useNavigate();

    const [paper, setPaper] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    const [showDeletePopup, setShowDeletePopup] = useState(false);
    const [paperToDelete, setPaperToDelete] = useState(null);
    const [isDeleting, setIsDeleting] = useState(false);

    const [searchQuery, setSearchQuery] = useState("");
    const [searchAnswer, setSearchAnswer] = useState("");
    const [searchLoading, setSearchLoading] = useState(false);
    const [searchError, setSearchError] = useState("");

    useEffect(() => {
        const fetchPaper = async () => {
            try {
                setLoading(true);
                setError("");

                const response = await api.get(
                    `/projects/${projectId}/papers/${paperId}/`
                );

                setPaper(response.data);
            } catch (err) {
                console.error("Failed to load paper:", err);
                setError("Failed to load paper.");
            } finally {
                setLoading(false);
            }
        };

        fetchPaper();
    }, [projectId, paperId]);

    const handleDeletePaper = async () => {
        if (!paperToDelete) return;

        try {
            setIsDeleting(true);

            await api.delete(
                `/projects/${projectId}/papers/${paperToDelete.id}/`
            );

            setShowDeletePopup(false);
            setPaperToDelete(null);

            navigate(`/projects/${projectId}`);
        } catch (err) {
            console.error("Failed to delete paper:", err);
            setError("Failed to delete the paper. Please try again.");
        } finally {
            setIsDeleting(false);
        }
    };

    const handleSemanticSearch = async (event) => {
        event.preventDefault();

        const query = searchQuery.trim();

        if (!query) {
            setSearchError("Please enter a question.");
            setSearchAnswer("");
            return;
        }

        try {
            setSearchLoading(true);
            setSearchError("");
            setSearchAnswer("");

            const response = await api.get(
                `/projects/${projectId}/papers/${paperId}/search/`,
                {
                    params: {
                        q: query,
                    },
                }
            );

            setSearchAnswer(
                response.data.answer ||
                "I could not find an answer in this paper."
            );
        } catch (err) {
            console.error("AI search failed:", err);

            const errorMessage =
                err.response?.data?.detail ||
                "Failed to get an answer from this paper. Please try again.";

            setSearchError(errorMessage);
        } finally {
            setSearchLoading(false);
        }
    };

    if (loading) {
        return (
            <div style={{ textAlign: "center", padding: "3rem" }}>
                Loading paper...
            </div>
        );
    }

    if (error) {
        return (
            <div
                style={{
                    color: "var(--danger)",
                    padding: "2rem",
                }}
            >
                {error}
            </div>
        );
    }

    return (
        <div
            style={{
                width: "100%",
                maxWidth: "1500px",
                margin: "0 auto",
                padding: "0 1.5rem",
                boxSizing: "border-box",
            }}
        >
            <Link
                to={`/projects/${projectId}`}
                style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "0.5rem",
                    marginBottom: "1.5rem",
                    color: "var(--text-secondary)",
                }}
            >
                ← Back to Project
            </Link>

            <div
                style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "flex-start",
                    marginBottom: "2rem",
                    gap: "1rem",
                }}
            >
                <div>
                    <h1
                        style={{
                            fontSize: "2rem",
                            marginBottom: "0.5rem",
                        }}
                    >
                        {paper.title}
                    </h1>

                    <p style={{ color: "var(--text-muted)" }}>
                        Uploaded:{" "}
                        {new Date(paper.uploaded_at).toLocaleDateString()}
                    </p>
                </div>

                <button
                    className="delete-button"
                    onClick={() => {
                        setPaperToDelete(paper);
                        setShowDeletePopup(true);
                    }}
                >
                    Delete
                </button>
            </div>

            <div
                style={{
                    display: "grid",
                    gridTemplateColumns:
                        "minmax(0, 1.5fr) minmax(320px, 1fr)",
                    gap: "2rem",
                    alignItems: "start",
                }}
            >
                <section>
                    {paper.file ? (
                        <Card
                            style={{
                                padding: "0",
                                overflow: "hidden",
                            }}
                        >
                            <div
                                style={{
                                    padding: "1rem",
                                    borderBottom:
                                        "1px solid var(--border-color)",
                                    background: "var(--bg-tertiary)",
                                }}
                            >
                                <h3
                                    style={{
                                        margin: 0,
                                        fontSize: "1rem",
                                    }}
                                >
                                    PDF Viewer
                                </h3>
                            </div>

                            <iframe
                                src={paper.file.replace(
                                    "http://localhost:8000",
                                    ""
                                )}
                                title={paper.title}
                                width="100%"
                                height="800px"
                                style={{
                                    border: "none",
                                    display: "block",
                                }}
                            />
                        </Card>
                    ) : (
                        <Card>
                            <p
                                style={{
                                    color: "var(--text-secondary)",
                                    textAlign: "center",
                                }}
                            >
                                No PDF file available for this paper.
                            </p>
                        </Card>
                    )}
                </section>

                <section>
                    <div
                        style={{
                            display: "flex",
                            flexDirection: "column",
                            gap: "1.5rem",
                        }}
                    >
                        <Card className="card-glass">
                            <h2
                                style={{
                                    fontSize: "1.5rem",
                                    margin: "0 0 1rem 0",
                                }}
                            >
                                AI Workspace{" "}
                                <span
                                    style={{
                                        fontSize: "0.875rem",
                                        padding: "0.25rem 0.5rem",
                                        background: "var(--accent-bg)",
                                        color: "var(--accent-primary)",
                                        borderRadius: "var(--radius-full)",
                                        verticalAlign: "middle",
                                        marginLeft: "0.5rem",
                                    }}
                                >
                                    Beta
                                </span>
                            </h2>

                            <p
                                style={{
                                    color: "var(--text-secondary)",
                                }}
                            >
                                Ask questions and receive answers based on
                                the contents of this paper.
                            </p>
                        </Card>

                        <Card>
                            <h3
                                style={{
                                    margin: "0 0 1rem 0",
                                    display: "flex",
                                    alignItems: "center",
                                    gap: "0.5rem",
                                }}
                            >
                                <span style={{ fontSize: "1.25rem" }}>
                                    📝
                                </span>
                                Summary
                            </h3>

                            <div
                                style={{
                                    padding: "2rem",
                                    textAlign: "center",
                                    background: "var(--bg-tertiary)",
                                    borderRadius: "var(--radius-md)",
                                    color: "var(--text-muted)",
                                }}
                            >
                                Coming soon
                            </div>
                        </Card>

                        <Card>
                            <h3
                                style={{
                                    margin: "0 0 1rem 0",
                                    display: "flex",
                                    alignItems: "center",
                                    gap: "0.5rem",
                                }}
                            >
                                <span style={{ fontSize: "1.25rem" }}>
                                    ❓
                                </span>
                                Ask Questions
                            </h3>

                            <form onSubmit={handleSemanticSearch}>
                                <textarea
                                    value={searchQuery}
                                    onChange={(event) =>
                                        setSearchQuery(event.target.value)
                                    }
                                    placeholder="Ask something about this paper..."
                                    rows={4}
                                    style={{
                                        width: "100%",
                                        resize: "vertical",
                                        padding: "0.8rem",
                                        border: "1px solid var(--border-color)",
                                        borderRadius: "var(--radius-md)",
                                        background: "var(--bg-tertiary)",
                                        color: "var(--text-primary)",
                                        boxSizing: "border-box",
                                        fontFamily: "inherit",
                                    }}
                                />

                                <button
                                    type="submit"
                                    disabled={searchLoading}
                                    style={{
                                        marginTop: "0.8rem",
                                        width: "100%",
                                    }}
                                >
                                    {searchLoading
                                        ? "Generating answer..."
                                        : "Ask AI"}
                                </button>
                            </form>

                            {searchError && (
                                <p
                                    style={{
                                        color: "var(--danger)",
                                        marginTop: "1rem",
                                    }}
                                >
                                    {searchError}
                                </p>
                            )}

                            {searchLoading && (
                                <p
                                    style={{
                                        marginTop: "1rem",
                                        color: "var(--text-secondary)",
                                    }}
                                >
                                    Reading the paper and generating an answer...
                                </p>
                            )}

                            {searchAnswer && !searchLoading && (
                                <div
                                    style={{
                                        marginTop: "1.5rem",
                                        padding: "1.25rem",
                                        border: "1px solid var(--border-color)",
                                        borderRadius: "var(--radius-md)",
                                        background: "var(--bg-tertiary)",
                                    }}
                                >
                                    <h4
                                        style={{
                                            margin: "0 0 0.75rem 0",
                                        }}
                                    >
                                        AI Answer
                                    </h4>

                                    <p
                                        style={{
                                            margin: 0,
                                            lineHeight: 1.7,
                                            whiteSpace: "pre-wrap",
                                        }}
                                    >
                                        {searchAnswer}
                                    </p>
                                </div>
                            )}
                        </Card>

                        <Card>
                            <h3
                                style={{
                                    margin: "0 0 1rem 0",
                                    display: "flex",
                                    alignItems: "center",
                                    gap: "0.5rem",
                                }}
                            >
                                <span style={{ fontSize: "1.25rem" }}>
                                    🔍
                                </span>
                                Research Gaps
                            </h3>

                            <div
                                style={{
                                    padding: "2rem",
                                    textAlign: "center",
                                    background: "var(--bg-tertiary)",
                                    borderRadius: "var(--radius-md)",
                                    color: "var(--text-muted)",
                                }}
                            >
                                Coming soon
                            </div>
                        </Card>
                    </div>
                </section>
            </div>

            {showDeletePopup && (
                <div className="modal-overlay">
                    <div
                        className="delete-modal"
                        role="dialog"
                        aria-modal="true"
                        aria-labelledby="delete-modal-title"
                    >
                        <h2 id="delete-modal-title">Delete PDF?</h2>

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
                                onClick={() => {
                                    setShowDeletePopup(false);
                                    setPaperToDelete(null);
                                }}
                                disabled={isDeleting}
                            >
                                Cancel
                            </button>

                            <button
                                className="confirm-delete-button"
                                onClick={handleDeletePaper}
                                disabled={isDeleting}
                            >
                                {isDeleting ? "Deleting..." : "Delete"}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default PaperDetails;