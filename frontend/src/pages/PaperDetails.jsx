import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import api from "../services/api";
import Card from "../components/Card";
import Button from "../components/Button";

function PaperDetails() {
    const { projectId, paperId } = useParams();
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const pageParam = searchParams.get("page");

    const [paper, setPaper] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    const [showDeletePopup, setShowDeletePopup] = useState(false);
    const [paperToDelete, setPaperToDelete] = useState(null);
    const [isDeleting, setIsDeleting] = useState(false);

    const [searchQuery, setSearchQuery] = useState("");
    const [searchAnswer, setSearchAnswer] = useState("");
    const [searchSources, setSearchSources] = useState([]);
    const [searchLoading, setSearchLoading] = useState(false);
    const [searchError, setSearchError] = useState("");

    const [summaryData, setSummaryData] = useState(null);
    const [summarySources, setSummarySources] = useState([]);
    const [summaryLoading, setSummaryLoading] = useState(false);
    const [summaryError, setSummaryError] = useState("");

    const [gapsData, setGapsData] = useState(null);
    const [gapsSources, setGapsSources] = useState([]);
    const [gapsLoading, setGapsLoading] = useState(false);
    const [gapsError, setGapsError] = useState("");

    const [selectedEvidence, setSelectedEvidence] = useState(null);



    // Base PDF URL without any page fragment — set once when the paper loads
    const pdfBaseUrl = useRef("");
    // The src currently shown in the iframe (may include #page=N)
    const [iframeSrc, setIframeSrc] = useState("");

    useEffect(() => {
        const fetchPaper = async () => {
            try {
                setLoading(true);
                setError("");

                const response = await api.get(
                    `/projects/${projectId}/papers/${paperId}/`
                );

                const data = response.data;
                setPaper(data);

                // Build the base PDF URL (strip any server origin for same-host serving)
                if (data.file) {
                    const base = data.file.replace("http://localhost:8000", "");
                    pdfBaseUrl.current = base;
                    if (pageParam) {
                        setIframeSrc(`${base}#page=${pageParam}`);
                    } else {
                        setIframeSrc(base);
                    }
                }
            } catch (err) {
                console.error("Failed to load paper:", err);
                setError("Failed to load paper.");
            } finally {
                setLoading(false);
            }
        };

        fetchPaper();
    }, [projectId, paperId]);

    useEffect(() => {
        if (pdfBaseUrl.current && pageParam) {
            navigateToPdfPage(pageParam);
        }
    }, [pageParam]);

    /**
     * Navigate the PDF iframe to a specific page using the #page=N fragment.
     * Most Chromium-based browsers support this for embedded PDFs.
     * If the browser ignores the fragment the viewer simply stays put — no crash.
     */
    const navigateToPdfPage = (pageNumber) => {
        if (!pdfBaseUrl.current || !pageNumber) return;
        // Force a reload with the new fragment by blanking first
        setIframeSrc("");
        requestAnimationFrame(() => {
            setIframeSrc(`${pdfBaseUrl.current}#page=${pageNumber}`);
        });
    };

    const handleEvidenceClick = (source) => {
        if (!source) return;

        const pageNumber = source.page_number;

        if (!pageNumber) {
            return;
        }

        setSelectedEvidence({
            sourceNumber: source.source_number || null,
            pageNumber,
            chunkId: source.chunk_id || null,
        });

        navigateToPdfPage(pageNumber);

        requestAnimationFrame(() => {
            document
                .getElementById("paper-pdf-viewer")
                ?.scrollIntoView({
                    behavior: "smooth",
                    block: "start",
                });
        });
    };


    const getApiErrorMessage = (err, defaultMsg = "Something went wrong while processing the request.") => {
        if (err.response) {
            const status = err.response.status;
            if (status === 429) {
                return "Gemini API rate limit exceeded. Please try again later.";
            }
            if (status === 503) {
                return "Gemini is temporarily unavailable. Please try again shortly.";
            }
            if (status === 401) {
                return "Authentication failed.";
            }
            if (status === 404) {
                return "Paper not found.";
            }
            return err.response.data?.error || err.response.data?.detail || defaultMsg;
        }
        return defaultMsg;
    };

    const handleGenerateSummary = async () => {
        if (summaryLoading) return; // prevent double-click
        try {
            setSummaryLoading(true);
            setSummaryError("");
            setSummaryData(null);
            setSummarySources([]);

            const response = await api.post("/ai/summary/", {
                paper_id: paperId,
            });

            console.log("Summary response:", response.data);

            setSummaryData(response.data.summary);
            setSummarySources(response.data.sources || []);
        } catch (err) {
            console.error("Summary generation failed:", err);
            setSummaryError(getApiErrorMessage(err, "Failed to generate summary. Please try again."));
        } finally {
            setSummaryLoading(false);
        }
    };

    const handleGenerateResearchGaps = async () => {
        if (gapsLoading) return; // prevent double-click
        try {
            setGapsLoading(true);
            setGapsError("");
            setGapsData(null);
            setGapsSources([]);

            const response = await api.post("/ai/research-gaps/", {
                paper_id: paperId,
            });

            console.log("Research gaps response:", response.data);

            setGapsData(response.data.gaps_data);
            setGapsSources(response.data.sources || []);
        } catch (err) {
            console.error("Research gap detection failed:", err);
            setGapsError(getApiErrorMessage(err, "Failed to detect research gaps. Please try again."));
        } finally {
            setGapsLoading(false);
        }
    };



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
        if (searchLoading) return; // prevent duplicate submission

        const query = searchQuery.trim();

        if (!query) {
            setSearchError("Please enter a question.");
            setSearchAnswer("");
            setSearchSources([]);
            return;
        }

        try {
            setSearchLoading(true);
            setSearchError("");
            setSearchAnswer("");
            setSearchSources([]);

            const response = await api.post("/ai/ask/", {
                paper_id: paperId,
                question: query,
            });

            console.log("AI response:", response.data);

            setSearchAnswer(
                response.data.answer ||
                "I could not find an answer in this paper."
            );

            setSearchSources(response.data.sources || []);
        } catch (err) {
            console.error("AI search failed:", err);
            setSearchError(getApiErrorMessage(err, "Failed to get an answer from this paper. Please try again."));
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
                {/* PDF */}
                <section>
                    {paper.file ? (
                        <Card
                            id="paper-pdf-viewer"
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
                                    display: "flex",
                                    justifyContent: "space-between",
                                    alignItems: "center",
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

                                {selectedEvidence?.pageNumber && (
                                    <span
                                        style={{
                                            fontSize: "0.85rem",
                                            fontWeight: 600,
                                            color: "var(--accent-primary)",
                                            background: "rgba(99, 102, 241, 0.15)",
                                            padding: "0.25rem 0.6rem",
                                            borderRadius: "var(--radius-sm)",
                                        }}
                                    >
                                        Viewing evidence from Page {selectedEvidence.pageNumber}
                                    </span>
                                )}
                            </div>

                            <iframe
                                src={iframeSrc}
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

                {/* AI WORKSPACE */}
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

                        {/* SUMMARY */}
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

                            {!summaryData && !summaryLoading && !summaryError && (
                                <div style={{ textAlign: "center", padding: "1.5rem 0" }}>
                                    <p style={{ color: "var(--text-secondary)", marginBottom: "1rem" }}>
                                        Generate an AI-powered academic summary of this paper.
                                    </p>
                                    <Button
                                        variant="primary"
                                        onClick={handleGenerateSummary}
                                        disabled={summaryLoading}
                                    >
                                        Generate Summary
                                    </Button>
                                </div>
                            )}

                            {summaryLoading && (
                                <div style={{ textAlign: "center", padding: "2rem" }}>
                                    <p style={{ color: "var(--text-secondary)", margin: 0 }}>
                                        Reading the paper and generating summary...
                                    </p>
                                </div>
                            )}

                            {summaryError && (
                                <div style={{ marginTop: "1rem" }}>
                                    <p style={{ color: "var(--danger)", marginBottom: "1rem" }}>
                                        {summaryError}
                                    </p>
                                    <Button
                                        variant="secondary"
                                        onClick={handleGenerateSummary}
                                        disabled={summaryLoading}
                                    >
                                        Try Again
                                    </Button>
                                </div>
                            )}

                            {summaryData && !summaryLoading && (
                                <div
                                    style={{
                                        display: "flex",
                                        flexDirection: "column",
                                        gap: "1.25rem",
                                    }}
                                >
                                    {/* Overview */}
                                    <div style={{ background: "var(--bg-tertiary)", padding: "1rem", borderRadius: "var(--radius-md)" }}>
                                        <h4 style={{ margin: "0 0 0.5rem 0", fontSize: "0.95rem", color: "var(--accent-primary)" }}>
                                            Overview
                                        </h4>
                                        <p style={{ margin: 0, lineHeight: 1.6, color: "var(--text-primary)" }}>
                                            {summaryData.overview}
                                        </p>
                                    </div>

                                    {/* Key Points */}
                                    {summaryData.key_points && summaryData.key_points.length > 0 && (
                                        <div style={{ background: "var(--bg-tertiary)", padding: "1rem", borderRadius: "var(--radius-md)" }}>
                                            <h4 style={{ margin: "0 0 0.5rem 0", fontSize: "0.95rem", color: "var(--accent-primary)" }}>
                                                Key Points
                                            </h4>
                                            <ul style={{ margin: 0, paddingLeft: "1.25rem", lineHeight: 1.6, color: "var(--text-primary)" }}>
                                                {summaryData.key_points.map((pt, idx) => (
                                                    <li key={idx} style={{ marginBottom: "0.35rem" }}>
                                                        {pt}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}

                                    {/* Methodology */}
                                    <div style={{ background: "var(--bg-tertiary)", padding: "1rem", borderRadius: "var(--radius-md)" }}>
                                        <h4 style={{ margin: "0 0 0.5rem 0", fontSize: "0.95rem", color: "var(--accent-primary)" }}>
                                            Main Methodology / Approach
                                        </h4>
                                        <p style={{ margin: 0, lineHeight: 1.6, color: "var(--text-primary)" }}>
                                            {summaryData.methodology}
                                        </p>
                                    </div>

                                    {/* Findings */}
                                    <div style={{ background: "var(--bg-tertiary)", padding: "1rem", borderRadius: "var(--radius-md)" }}>
                                        <h4 style={{ margin: "0 0 0.5rem 0", fontSize: "0.95rem", color: "var(--accent-primary)" }}>
                                            Main Findings / Results
                                        </h4>
                                        <p style={{ margin: 0, lineHeight: 1.6, color: "var(--text-primary)" }}>
                                            {summaryData.findings}
                                        </p>
                                    </div>

                                    {/* Limitations */}
                                    <div style={{ background: "var(--bg-tertiary)", padding: "1rem", borderRadius: "var(--radius-md)" }}>
                                        <h4 style={{ margin: "0 0 0.5rem 0", fontSize: "0.95rem", color: "var(--accent-primary)" }}>
                                            Limitations / Future Work
                                        </h4>
                                        <p style={{ margin: 0, lineHeight: 1.6, color: "var(--text-primary)" }}>
                                            {summaryData.limitations}
                                        </p>
                                    </div>

                                    {/* Summary Sources */}
                                    {summarySources.length > 0 && (
                                        <div style={{ marginTop: "1rem", paddingTop: "1rem", borderTop: "1px solid var(--border-color)" }}>
                                            <h4 style={{ margin: "0 0 0.75rem 0", fontSize: "0.95rem" }}>
                                                Sources from the paper
                                            </h4>
                                            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                                                {summarySources.map((source) => {
                                                    const isSelected =
                                                        selectedEvidence?.chunkId != null &&
                                                        selectedEvidence.chunkId === source.chunk_id;
                                                    return (
                                                        <div
                                                            key={source.chunk_id}
                                                            style={{
                                                                padding: "0.75rem",
                                                                border: isSelected
                                                                    ? "2px solid var(--accent-primary)"
                                                                    : "1px solid var(--border-color)",
                                                                borderRadius: "var(--radius-md)",
                                                                background: isSelected
                                                                    ? "var(--bg-tertiary)"
                                                                    : "var(--bg-secondary)",
                                                                transition: "border-color 0.2s",
                                                            }}
                                                        >
                                                            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.35rem", flexWrap: "wrap" }}>
                                                                <strong>Source {source.source_number}</strong>
                                                                {source.page_number != null ? (
                                                                    <>
                                                                        <span style={{ color: "var(--text-muted)", userSelect: "none" }}>·</span>
                                                                        <button
                                                                            title={`Jump to page ${source.page_number} in the PDF viewer`}
                                                                            onClick={() => handleEvidenceClick(source)}
                                                                            style={{
                                                                                background: "none",
                                                                                border: "none",
                                                                                padding: 0,
                                                                                cursor: "pointer",
                                                                                color: "var(--accent-primary)",
                                                                                fontWeight: 600,
                                                                                fontSize: "inherit",
                                                                                fontFamily: "inherit",
                                                                                textDecoration: "underline",
                                                                                textUnderlineOffset: "2px",
                                                                            }}
                                                                        >
                                                                            Page {source.page_number}
                                                                        </button>
                                                                    </>
                                                                ) : (
                                                                    <span
                                                                        style={{
                                                                            color: "var(--text-muted)",
                                                                            fontSize: "0.85em",
                                                                        }}
                                                                    >
                                                                        · Page information unavailable
                                                                    </span>
                                                                )}
                                                            </div>
                                                            <p style={{ margin: 0, fontSize: "0.875rem", lineHeight: 1.5, color: "var(--text-secondary)" }}>
                                                                {source.text}
                                                            </p>
                                                            {source.page_number != null && (
                                                                <div style={{ marginTop: "0.5rem" }}>
                                                                    <button
                                                                        onClick={() => handleEvidenceClick(source)}
                                                                        title={`Open evidence from page ${source.page_number}`}
                                                                        style={{
                                                                            background: "none",
                                                                            border: "1px solid var(--border-color)",
                                                                            borderRadius: "var(--radius-sm)",
                                                                            color: "var(--accent-primary)",
                                                                            cursor: "pointer",
                                                                            fontSize: "0.8rem",
                                                                            padding: "0.2rem 0.6rem",
                                                                            fontWeight: 600,
                                                                        }}
                                                                    >
                                                                        Open Evidence
                                                                    </button>
                                                                </div>
                                                            )}
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}
                        </Card>

                        {/* ASK QUESTIONS */}
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
                                        border:
                                            "1px solid var(--border-color)",
                                        borderRadius: "var(--radius-md)",
                                        background: "var(--bg-tertiary)",
                                        color: "var(--text-primary)",
                                        boxSizing: "border-box",
                                        fontFamily: "inherit",
                                    }}
                                />

                                <Button
                                    type="submit"
                                    variant="primary"
                                    disabled={searchLoading}
                                    style={{
                                        marginTop: "0.8rem",
                                        width: "100%",
                                    }}
                                >
                                    {searchLoading
                                        ? "Generating answer..."
                                        : "Ask AI"}
                                </Button>
                            </form>

                            {/* ERROR */}
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

                            {/* LOADING */}
                            {searchLoading && (
                                <p
                                    style={{
                                        marginTop: "1rem",
                                        color: "var(--text-secondary)",
                                    }}
                                >
                                    Reading the paper and generating an
                                    answer...
                                </p>
                            )}

                            {/* ANSWER */}
                            {searchAnswer && !searchLoading && (
                                <div
                                    style={{
                                        marginTop: "1.5rem",
                                        padding: "1.25rem",
                                        border:
                                            "1px solid var(--border-color)",
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

                                    {/* SOURCES */}
                                    {searchSources.length > 0 && (
                                        <div
                                            style={{
                                                marginTop: "1.5rem",
                                                paddingTop: "1rem",
                                                borderTop:
                                                    "1px solid var(--border-color)",
                                            }}
                                        >
                                            <h4
                                                style={{
                                                    margin:
                                                        "0 0 1rem 0",
                                                }}
                                            >
                                                Sources from the paper
                                            </h4>

                                            <div
                                                style={{
                                                    display: "flex",
                                                    flexDirection: "column",
                                                    gap: "1rem",
                                                }}
                                            >
                                                {(searchSources ?? []).map(
                                                    (source) => {
                                                        const isSelected =
                                                            selectedEvidence?.chunkId != null &&
                                                            selectedEvidence.chunkId === source.chunk_id;
                                                        return (
                                                            <div
                                                                key={
                                                                    source.chunk_id
                                                                }
                                                                style={{
                                                                    padding:
                                                                        "1rem",
                                                                    border: isSelected
                                                                        ? "2px solid var(--accent-primary)"
                                                                        : "1px solid var(--border-color)",
                                                                    borderRadius:
                                                                        "var(--radius-md)",
                                                                    background: isSelected
                                                                        ? "var(--bg-tertiary)"
                                                                        : "var(--bg-secondary)",
                                                                    transition: "border-color 0.2s",
                                                                }}
                                                            >
                                                                {/* Source header: "Source N · Page X" */}
                                                                <div
                                                                    style={{
                                                                        display: "flex",
                                                                        alignItems: "center",
                                                                        gap: "0.5rem",
                                                                        marginBottom: "0.5rem",
                                                                        flexWrap: "wrap",
                                                                    }}
                                                                >
                                                                    <strong>
                                                                        Source{" "}
                                                                        {source.source_number}
                                                                    </strong>

                                                                    {source.page_number != null ? (
                                                                        <>
                                                                            <span
                                                                                style={{
                                                                                    color: "var(--text-muted)",
                                                                                    userSelect: "none",
                                                                                }}
                                                                            >
                                                                                ·
                                                                            </span>
                                                                            <button
                                                                                title={`Jump to page ${source.page_number} in the PDF viewer`}
                                                                                onClick={() =>
                                                                                    handleEvidenceClick(source)
                                                                                }
                                                                                style={{
                                                                                    background: "none",
                                                                                    border: "none",
                                                                                    padding: 0,
                                                                                    cursor: "pointer",
                                                                                    color: "var(--accent-primary)",
                                                                                    fontWeight: 600,
                                                                                    fontSize: "inherit",
                                                                                    fontFamily: "inherit",
                                                                                    textDecoration: "underline",
                                                                                    textUnderlineOffset: "2px",
                                                                                }}
                                                                            >
                                                                                Page{" "}
                                                                                {source.page_number}
                                                                            </button>
                                                                        </>
                                                                    ) : (
                                                                        <span
                                                                            style={{
                                                                                color: "var(--text-muted)",
                                                                                fontSize: "0.85em",
                                                                            }}
                                                                        >
                                                                            · Page information unavailable
                                                                        </span>
                                                                    )}
                                                                </div>

                                                                <p
                                                                    style={{
                                                                        margin: 0,
                                                                        lineHeight:
                                                                            1.6,
                                                                        color:
                                                                            "var(--text-secondary)",
                                                                    }}
                                                                >
                                                                    {source.text}
                                                                </p>

                                                                {source.page_number != null && (
                                                                    <div style={{ marginTop: "0.75rem" }}>
                                                                        <button
                                                                            onClick={() => handleEvidenceClick(source)}
                                                                            title={`Open evidence from page ${source.page_number}`}
                                                                            style={{
                                                                                background: "none",
                                                                                border: "1px solid var(--border-color)",
                                                                                borderRadius: "var(--radius-sm)",
                                                                                color: "var(--accent-primary)",
                                                                                cursor: "pointer",
                                                                                fontSize: "0.8rem",
                                                                                padding: "0.25rem 0.6rem",
                                                                                fontWeight: 600,
                                                                            }}
                                                                        >
                                                                            Open Evidence
                                                                        </button>
                                                                    </div>
                                                                )}
                                                            </div>
                                                        );
                                                    }
                                                )}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}
                        </Card>

                        {/* RESEARCH GAPS */}
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

                            {!gapsData && !gapsLoading && !gapsError && (
                                <div style={{ textAlign: "center", padding: "1.5rem 0" }}>
                                    <p style={{ color: "var(--text-secondary)", marginBottom: "1rem" }}>
                                        Analyze this paper to identify explicitly stated research gaps, limitations, and future work.
                                    </p>
                                    <Button
                                        variant="primary"
                                        onClick={handleGenerateResearchGaps}
                                        disabled={gapsLoading}
                                    >
                                        Identify Research Gaps
                                    </Button>
                                </div>
                            )}

                            {gapsLoading && (
                                <div style={{ textAlign: "center", padding: "2rem" }}>
                                    <p style={{ color: "var(--text-secondary)", margin: 0 }}>
                                        Analyzing paper for research gaps and limitations...
                                    </p>
                                </div>
                            )}

                            {gapsError && (
                                <div style={{ marginTop: "1rem" }}>
                                    <p style={{ color: "var(--danger)", marginBottom: "1rem" }}>
                                        {gapsError}
                                    </p>
                                    <Button
                                        variant="secondary"
                                        onClick={handleGenerateResearchGaps}
                                        disabled={gapsLoading}
                                    >
                                        Try Again
                                    </Button>
                                </div>
                            )}

                            {gapsData && !gapsLoading && (
                                <div
                                    style={{
                                        display: "flex",
                                        flexDirection: "column",
                                        gap: "1.25rem",
                                    }}
                                >
                                    {/* Overall Synthesis Statement */}
                                    {gapsData.summary_statement && (
                                        <div style={{ background: "var(--bg-tertiary)", padding: "1rem", borderRadius: "var(--radius-md)" }}>
                                            <h4 style={{ margin: "0 0 0.5rem 0", fontSize: "0.95rem", color: "var(--accent-primary)" }}>
                                                Synthesis Statement
                                            </h4>
                                            <p style={{ margin: 0, lineHeight: 1.6, color: "var(--text-primary)" }}>
                                                {gapsData.summary_statement}
                                            </p>
                                        </div>
                                    )}

                                    {/* Individual Gap Cards */}
                                    {gapsData.gaps && gapsData.gaps.length > 0 ? (
                                        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                                            {gapsData.gaps.map((gap, idx) => (
                                                <div
                                                    key={idx}
                                                    style={{
                                                        background: "var(--bg-tertiary)",
                                                        padding: "1rem",
                                                        borderRadius: "var(--radius-md)",
                                                        borderLeft: "3px solid var(--accent-primary)",
                                                    }}
                                                >
                                                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem", flexWrap: "wrap", gap: "0.5rem" }}>
                                                        <h4 style={{ margin: 0, fontSize: "0.95rem", color: "var(--text-primary)" }}>
                                                            {gap.title}
                                                        </h4>
                                                        <span
                                                            style={{
                                                                fontSize: "0.75rem",
                                                                padding: "0.2rem 0.6rem",
                                                                borderRadius: "var(--radius-sm)",
                                                                background: "rgba(99, 102, 241, 0.15)",
                                                                color: "var(--accent-primary)",
                                                                fontWeight: 600,
                                                            }}
                                                        >
                                                            {gap.category}
                                                        </span>
                                                    </div>

                                                    <p style={{ margin: 0, lineHeight: 1.5, fontSize: "0.9rem", color: "var(--text-secondary)" }}>
                                                        {gap.description}
                                                    </p>

                                                    {gap.page_number && (
                                                        <div style={{ marginTop: "0.75rem" }}>
                                                            <button
                                                                onClick={() =>
                                                                    handleEvidenceClick({
                                                                        source_number: null,
                                                                        page_number: gap.page_number,
                                                                        chunk_id: null,
                                                                    })
                                                                }
                                                                style={{
                                                                    background: "none",
                                                                    border: "1px solid var(--border-color)",
                                                                    borderRadius: "var(--radius-sm)",
                                                                    color: "var(--accent-primary)",
                                                                    cursor: "pointer",
                                                                    fontSize: "0.8rem",
                                                                    padding: "0.2rem 0.5rem",
                                                                }}
                                                            >
                                                                Jump to Page {gap.page_number}
                                                            </button>
                                                        </div>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    ) : (
                                        <p style={{ color: "var(--text-secondary)", margin: 0 }}>
                                            No explicit research gaps or limitations were mentioned in the paper text.
                                        </p>
                                    )}

                                    {/* Sources Section */}
                                    {gapsSources && gapsSources.length > 0 && (
                                        <div style={{ marginTop: "1rem", borderTop: "1px solid var(--border-color)", paddingTop: "1rem" }}>
                                            <h4 style={{ margin: "0 0 0.75rem 0", fontSize: "0.9rem", color: "var(--text-secondary)" }}>
                                                Referenced Paper Pages
                                            </h4>
                                            <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                                                {gapsSources.map((source, idx) => {
                                                    const isSelected =
                                                        selectedEvidence?.chunkId != null &&
                                                        selectedEvidence.chunkId === source.chunk_id;
                                                    return (
                                                        <div
                                                            key={idx}
                                                            style={{
                                                                background: isSelected
                                                                    ? "var(--bg-tertiary)"
                                                                    : "var(--bg-tertiary)",
                                                                border: isSelected
                                                                    ? "2px solid var(--accent-primary)"
                                                                    : "1px solid transparent",
                                                                padding: "0.75rem",
                                                                borderRadius: "var(--radius-md)",
                                                                fontSize: "0.85rem",
                                                                transition: "border-color 0.2s",
                                                            }}
                                                        >
                                                            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.35rem" }}>
                                                                <span style={{ fontWeight: 600, color: "var(--accent-primary)" }}>
                                                                    Source {source.source_number}
                                                                </span>
                                                                {source.page_number != null ? (
                                                                    <button
                                                                        onClick={() => handleEvidenceClick(source)}
                                                                        style={{
                                                                            background: "none",
                                                                            border: "none",
                                                                            color: "var(--accent-primary)",
                                                                            cursor: "pointer",
                                                                            textDecoration: "underline",
                                                                            padding: 0,
                                                                            fontSize: "0.85rem",
                                                                            fontWeight: 600,
                                                                        }}
                                                                    >
                                                                        (Page {source.page_number})
                                                                    </button>
                                                                ) : (
                                                                    <span style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
                                                                        (Page information unavailable)
                                                                    </span>
                                                                )}
                                                            </div>
                                                            <p
                                                                style={{
                                                                    margin: 0,
                                                                    color: "var(--text-secondary)",
                                                                    lineHeight: 1.4,
                                                                    display: "-webkit-box",
                                                                    WebkitLineClamp: 2,
                                                                    WebkitBoxOrient: "vertical",
                                                                    overflow: "hidden",
                                                                }}
                                                            >
                                                                {source.text}
                                                            </p>
                                                            {source.page_number != null && (
                                                                <div style={{ marginTop: "0.5rem" }}>
                                                                    <button
                                                                        onClick={() => handleEvidenceClick(source)}
                                                                        title={`Open evidence from page ${source.page_number}`}
                                                                        style={{
                                                                            background: "none",
                                                                            border: "1px solid var(--border-color)",
                                                                            borderRadius: "var(--radius-sm)",
                                                                            color: "var(--accent-primary)",
                                                                            cursor: "pointer",
                                                                            fontSize: "0.8rem",
                                                                            padding: "0.2rem 0.6rem",
                                                                            fontWeight: 600,
                                                                        }}
                                                                    >
                                                                        Open Evidence
                                                                    </button>
                                                                </div>
                                                            )}
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        </div>
                                    )}

                                </div>
                            )}
                        </Card>

                    </div>
                </section>
            </div>

            {/* DELETE MODAL */}
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