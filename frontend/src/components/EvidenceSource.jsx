import { useNavigate } from "react-router-dom";

function EvidenceSource({ source, projectId }) {
    const navigate = useNavigate();

    if (!source) return null;

    const paperTitle = source.paper_title || `Paper #${source.paper_id}`;
    const pageNum = source.page_number ? `Page ${source.page_number}` : "Page 1";

    const handleOpenEvidence = (e) => {
        e.preventDefault();
        const targetPage = source.page_number || 1;
        navigate(`/projects/${projectId}/papers/${source.paper_id}?page=${targetPage}`);
    };

    return (
        <div style={{
            background: "var(--bg-tertiary)",
            border: "1px solid var(--border-color)",
            borderRadius: "var(--radius-md)",
            padding: "0.875rem 1rem",
            marginTop: "0.75rem",
        }}>
            <div style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: "1rem",
                marginBottom: "0.5rem",
                flexWrap: "wrap",
            }}>
                <span style={{ fontWeight: 600, fontSize: "0.875rem", color: "var(--text-primary)" }}>
                    {paperTitle} · {pageNum}
                </span>
                <button
                    onClick={handleOpenEvidence}
                    style={{
                        background: "var(--accent-primary)",
                        color: "#ffffff",
                        border: "none",
                        borderRadius: "var(--radius-sm)",
                        padding: "0.35rem 0.85rem",
                        fontSize: "0.8rem",
                        fontWeight: 600,
                        cursor: "pointer",
                        transition: "background 0.2s",
                    }}
                >
                    Open Evidence
                </button>
            </div>
            {source.text && (
                <p style={{
                    margin: 0,
                    fontSize: "0.85rem",
                    color: "var(--text-secondary)",
                    fontStyle: "italic",
                    lineHeight: "1.4",
                    borderLeft: "3px solid var(--accent-primary)",
                    paddingLeft: "0.75rem",
                    whiteSpace: "pre-wrap",
                }}>
                    "{source.text}"
                </p>
            )}
        </div>
    );
}

export default EvidenceSource;
