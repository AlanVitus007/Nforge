import { useState, useEffect } from "react";
import { Link, useParams, useLocation, useNavigate } from "react-router-dom";
import api from "../services/api";
import Card from "../components/Card";
import Button from "../components/Button";
import EvidenceSource from "../components/EvidenceSource";

function MultiPaperComparison() {
    const { projectId } = useParams();
    const location = useLocation();
    const navigate = useNavigate();

    const paperIds = location.state?.paperIds;

    const [paperTitlesMap, setPaperTitlesMap] = useState({});
    const [fetchingPaperNames, setFetchingPaperNames] = useState(false);

    const [question, setQuestion] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [comparisonResult, setComparisonResult] = useState(null);

    // Fetch paper titles once if paperIds exist
    useEffect(() => {
        if (!paperIds || !Array.isArray(paperIds) || paperIds.length < 2) return;

        const fetchPaperNames = async () => {
            try {
                setFetchingPaperNames(true);
                const resp = await api.get(`/projects/${projectId}/papers/`);
                const allPapers = resp.data || [];
                const map = {};
                allPapers.forEach((p) => {
                    map[p.id] = p.title;
                });
                setPaperTitlesMap(map);
            } catch (err) {
                console.error("Failed to load paper titles for header:", err);
            } finally {
                setFetchingPaperNames(false);
            }
        };

        fetchPaperNames();
    }, [projectId, paperIds]);

    // Handle missing paperIds (Direct URL access)
    if (!paperIds || !Array.isArray(paperIds) || paperIds.length < 2) {
        return (
            <div style={{ maxWidth: "800px", margin: "3rem auto", padding: "0 1.5rem" }}>
                <Card style={{ textAlign: "center", padding: "3rem 2rem" }}>
                    <h2 style={{ fontSize: "1.75rem", marginBottom: "1rem" }}>
                        Cross-Paper Research Analysis
                    </h2>
                    <p style={{ color: "var(--danger)", fontWeight: 600, fontSize: "1.1rem" }}>
                        No papers were selected for comparison.
                    </p>
                    <p style={{ color: "var(--text-secondary)", marginBottom: "2rem" }}>
                        Please return to the project page and select between 2 and 4 papers to perform cross-paper synthesis.
                    </p>
                    <Link to={`/projects/${projectId}`}>
                        <Button variant="primary">
                            ← Back to Project
                        </Button>
                    </Link>
                </Card>
            </div>
        );
    }

    const handleGenerate = async (e) => {
        if (e) e.preventDefault();

        // Protect Gemini calls: strict guard against duplicate in-flight calls
        if (loading) return;

        try {
            setLoading(true);
            setError("");

            const payload = {
                paper_ids: paperIds,
                question: question.trim(),
            };

            const response = await api.post("/ai/compare/", payload);

            setComparisonResult(response.data);
        } catch (err) {
            console.error("Comparison request failed:", err);
            const status = err.response?.status;
            let errMsg = err.response?.data?.error;

            if (status === 400) {
                errMsg = errMsg || "Please select between 2 and 4 papers.";
            } else if (status === 401) {
                errMsg = "Authentication required.";
            } else if (status === 403) {
                errMsg = "You do not have access to one or more selected papers.";
            } else if (status === 404) {
                errMsg = "One or more selected papers could not be found.";
            } else if (status === 429) {
                errMsg = "Gemini API rate limit exceeded. Please try again later.";
            } else if (status === 503) {
                errMsg = "Gemini is temporarily unavailable. Please try again shortly.";
            } else {
                errMsg = errMsg || "Something went wrong while generating comparison.";
            }

            setError(errMsg);
        } finally {
            setLoading(false);
        }
    };

    const handleExampleClick = (exampleText) => {
        setQuestion(exampleText);
    };

    const comparison = comparisonResult?.comparison;
    const responsePapers = comparisonResult?.papers || [];

    // Helper to resolve paper title from returned papers or paperTitlesMap
    const getPaperTitle = (pid) => {
        const found = responsePapers.find((p) => p.paper_id === pid);
        if (found?.title) return found.title;
        if (paperTitlesMap[pid]) return paperTitlesMap[pid];
        return `Paper #${pid}`;
    };

    return (
        <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "0 1.5rem 4rem 1.5rem" }}>
            <Link
                to={`/projects/${projectId}`}
                style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "0.5rem",
                    marginBottom: "1.5rem",
                    color: "var(--text-secondary)",
                    fontWeight: 500,
                }}
            >
                ← Back to Project
            </Link>

            <div style={{ marginBottom: "2rem" }}>
                <h1 style={{ fontSize: "2.25rem", marginBottom: "0.5rem" }}>
                    Cross-Paper Research Analysis
                </h1>
                <p style={{ color: "var(--text-secondary)", fontSize: "1.05rem" }}>
                    Synthesize methodologies, findings, similarities, differences, and research gaps across your selected papers.
                </p>
            </div>

            {/* Selected Papers Header Card */}
            <Card style={{ marginBottom: "2rem", background: "var(--bg-secondary)" }}>
                <h3 style={{ marginTop: 0, fontSize: "1.1rem", color: "var(--text-primary)" }}>
                    Selected Papers ({paperIds.length})
                </h3>
                <ul style={{ margin: "0.5rem 0 0 0", paddingLeft: "1.25rem", color: "var(--text-secondary)" }}>
                    {paperIds.map((pid) => (
                        <li key={pid} style={{ marginBottom: "0.35rem", fontWeight: 500 }}>
                            {paperTitlesMap[pid] || `Paper #${pid}`}
                        </li>
                    ))}
                </ul>
            </Card>

            {/* Research Question Form */}
            <Card style={{ marginBottom: "2rem" }}>
                <label
                    htmlFor="comparison-question"
                    style={{
                        display: "block",
                        fontWeight: 600,
                        fontSize: "1rem",
                        marginBottom: "0.5rem",
                        color: "var(--text-primary)",
                    }}
                >
                    Research Question / Comparison Focus <span style={{ fontWeight: 400, color: "var(--text-muted)", fontSize: "0.875rem" }}>(Optional)</span>
                </label>
                <textarea
                    id="comparison-question"
                    rows={3}
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="What would you like to compare across these papers?"
                    disabled={loading}
                    style={{
                        width: "100%",
                        padding: "0.75rem",
                        borderRadius: "var(--radius-md)",
                        border: "1px solid var(--border-color)",
                        background: "var(--bg-primary)",
                        color: "var(--text-primary)",
                        fontSize: "0.95rem",
                        fontFamily: "inherit",
                        resize: "vertical",
                        boxSizing: "border-box",
                    }}
                />

                {/* Example prompts */}
                <div style={{ marginTop: "0.75rem" }}>
                    <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "var(--text-muted)", display: "block", marginBottom: "0.35rem" }}>
                        Try an example focus:
                    </span>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
                        {[
                            "Compare the methodologies used in these studies.",
                            "What findings do these papers agree or disagree on?",
                            "What research gaps remain across these studies?",
                        ].map((example, idx) => (
                            <button
                                key={idx}
                                type="button"
                                onClick={() => handleExampleClick(example)}
                                disabled={loading}
                                style={{
                                    background: "var(--bg-tertiary)",
                                    border: "1px solid var(--border-color)",
                                    borderRadius: "var(--radius-full)",
                                    padding: "0.25rem 0.75rem",
                                    fontSize: "0.8rem",
                                    color: "var(--accent-primary)",
                                    cursor: "pointer",
                                    transition: "background 0.2s",
                                }}
                            >
                                {example}
                            </button>
                        ))}
                    </div>
                </div>

                <div style={{ marginTop: "1.5rem" }}>
                    <Button
                        variant="primary"
                        onClick={handleGenerate}
                        disabled={loading}
                        style={{ padding: "0.75rem 1.5rem", fontSize: "1rem" }}
                    >
                        {loading ? "Analyzing Papers..." : "Generate Comparison"}
                    </Button>
                </div>
            </Card>

            {/* Error Banner */}
            {error && (
                <Card style={{ marginBottom: "2rem", borderLeft: "4px solid var(--danger)", background: "rgba(239, 68, 68, 0.08)" }}>
                    <p style={{ color: "var(--danger)", margin: 0, fontWeight: 600 }}>
                        {error}
                    </p>
                </Card>
            )}

            {/* Loading Banner */}
            {loading && (
                <Card style={{ marginBottom: "2rem", textAlign: "center", padding: "2.5rem 1.5rem" }}>
                    <div style={{ fontSize: "1.1rem", fontWeight: 600, color: "var(--accent-primary)", marginBottom: "0.5rem" }}>
                        Analyzing the selected papers...
                    </div>
                    <p style={{ color: "var(--text-secondary)", margin: 0, fontSize: "0.9rem" }}>
                        Retrieving evidence and generating synthesis...
                    </p>
                </Card>
            )}

            {/* Results Sections */}
            {comparison && (
                <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
                    <h2 style={{ fontSize: "1.75rem", margin: "1rem 0 0 0" }}>
                        Comparison Results
                    </h2>

                    {/* 1. Overall Synthesis */}
                    {comparison.overall_synthesis && (
                        <Card>
                            <h3 style={{ marginTop: 0, color: "var(--accent-primary)", fontSize: "1.3rem" }}>
                                Overall Synthesis
                            </h3>
                            <p style={{ margin: 0, lineHeight: "1.6", color: "var(--text-primary)" }}>
                                {comparison.overall_synthesis}
                            </p>
                        </Card>
                    )}

                    {/* 2. Similarities */}
                    {Array.isArray(comparison.similarities) && comparison.similarities.length > 0 && (
                        <div>
                            <h3 style={{ marginBottom: "1rem", fontSize: "1.3rem" }}>
                                Similarities
                            </h3>
                            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                                {comparison.similarities.map((item, idx) => (
                                    <Card key={idx}>
                                        <p style={{ margin: 0, fontWeight: 500, color: "var(--text-primary)", fontSize: "1rem" }}>
                                            {item.statement}
                                        </p>
                                        {Array.isArray(item.sources) && item.sources.length > 0 && (
                                            <div style={{ marginTop: "0.5rem" }}>
                                                {item.sources.map((src, sIdx) => (
                                                    <EvidenceSource key={sIdx} source={src} projectId={projectId} />
                                                ))}
                                            </div>
                                        )}
                                    </Card>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* 3. Differences */}
                    {Array.isArray(comparison.differences) && comparison.differences.length > 0 && (
                        <div>
                            <h3 style={{ marginBottom: "1rem", fontSize: "1.3rem" }}>
                                Differences
                            </h3>
                            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                                {comparison.differences.map((item, idx) => (
                                    <Card key={idx}>
                                        <p style={{ margin: 0, fontWeight: 500, color: "var(--text-primary)", fontSize: "1rem" }}>
                                            {item.statement}
                                        </p>
                                        {Array.isArray(item.sources) && item.sources.length > 0 && (
                                            <div style={{ marginTop: "0.5rem" }}>
                                                {item.sources.map((src, sIdx) => (
                                                    <EvidenceSource key={sIdx} source={src} projectId={projectId} />
                                                ))}
                                            </div>
                                        )}
                                    </Card>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* 4. Methodology Comparison */}
                    {Array.isArray(comparison.methodology_comparison) && comparison.methodology_comparison.length > 0 && (
                        <div>
                            <h3 style={{ marginBottom: "1rem", fontSize: "1.3rem" }}>
                                Methodology Comparison
                            </h3>
                            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                                {comparison.methodology_comparison.map((item, idx) => (
                                    <Card key={idx}>
                                        <h4 style={{ marginTop: 0, marginBottom: "0.5rem", color: "var(--accent-secondary)", fontSize: "1.1rem" }}>
                                            {getPaperTitle(item.paper_id)}
                                        </h4>
                                        <p style={{ margin: 0, color: "var(--text-primary)", lineHeight: "1.5" }}>
                                            {item.summary}
                                        </p>
                                        {Array.isArray(item.sources) && item.sources.length > 0 && (
                                            <div style={{ marginTop: "0.5rem" }}>
                                                {item.sources.map((src, sIdx) => (
                                                    <EvidenceSource key={sIdx} source={src} projectId={projectId} />
                                                ))}
                                            </div>
                                        )}
                                    </Card>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* 5. Findings Comparison */}
                    {Array.isArray(comparison.findings_comparison) && comparison.findings_comparison.length > 0 && (
                        <div>
                            <h3 style={{ marginBottom: "1rem", fontSize: "1.3rem" }}>
                                Findings Comparison
                            </h3>
                            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                                {comparison.findings_comparison.map((item, idx) => (
                                    <Card key={idx}>
                                        <h4 style={{ marginTop: 0, marginBottom: "0.5rem", color: "var(--accent-secondary)", fontSize: "1.1rem" }}>
                                            {getPaperTitle(item.paper_id)}
                                        </h4>
                                        <p style={{ margin: 0, color: "var(--text-primary)", lineHeight: "1.5" }}>
                                            {item.summary}
                                        </p>
                                        {Array.isArray(item.sources) && item.sources.length > 0 && (
                                            <div style={{ marginTop: "0.5rem" }}>
                                                {item.sources.map((src, sIdx) => (
                                                    <EvidenceSource key={sIdx} source={src} projectId={projectId} />
                                                ))}
                                            </div>
                                        )}
                                    </Card>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* 6. Research Gaps */}
                    {Array.isArray(comparison.research_gaps) && comparison.research_gaps.length > 0 && (
                        <div>
                            <h3 style={{ marginBottom: "1rem", fontSize: "1.3rem" }}>
                                Research Gaps & Limitations
                            </h3>
                            <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                                {comparison.research_gaps.map((item, idx) => {
                                    const isExplicit = item.type === "explicit";
                                    return (
                                        <Card key={idx}>
                                            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem", marginBottom: "0.5rem" }}>
                                                <p style={{ margin: 0, fontWeight: 500, color: "var(--text-primary)", fontSize: "1rem" }}>
                                                    {item.statement}
                                                </p>
                                                <span
                                                    style={{
                                                        fontSize: "0.75rem",
                                                        fontWeight: 700,
                                                        textTransform: "uppercase",
                                                        padding: "0.2rem 0.55rem",
                                                        borderRadius: "var(--radius-full)",
                                                        whiteSpace: "nowrap",
                                                        background: isExplicit ? "rgba(37, 99, 235, 0.12)" : "rgba(245, 158, 11, 0.15)",
                                                        color: isExplicit ? "var(--accent-primary)" : "var(--warning)",
                                                        border: isExplicit ? "1px solid var(--accent-primary)" : "1px solid var(--warning)",
                                                    }}
                                                >
                                                    {isExplicit ? "Explicit Gap" : "Potential Gap"}
                                                </span>
                                            </div>
                                            {Array.isArray(item.sources) && item.sources.length > 0 && (
                                                <div style={{ marginTop: "0.5rem" }}>
                                                    {item.sources.map((src, sIdx) => (
                                                        <EvidenceSource key={sIdx} source={src} projectId={projectId} />
                                                    ))}
                                                </div>
                                            )}
                                        </Card>
                                    );
                                })}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}

export default MultiPaperComparison;
