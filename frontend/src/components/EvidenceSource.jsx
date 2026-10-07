import { useNavigate } from "react-router-dom";

function EvidenceSource({ source, projectId }) {
    const navigate = useNavigate();

    if (!source || !source.paper_id) return null;

    const paperTitle = source.paper_title || `Paper #${source.paper_id}`;
    const hasPage = source.page_number !== null && source.page_number !== undefined && source.page_number !== "";
    const pageNum = hasPage ? `Page ${source.page_number}` : null;

    const handleOpenEvidence = (e) => {
        e.preventDefault();
        if (hasPage) {
            navigate(`/projects/${projectId}/papers/${source.paper_id}?page=${source.page_number}`);
        } else {
            navigate(`/projects/${projectId}/papers/${source.paper_id}`);
        }
    };

    return (
        <div style={{
            background: "var(--bg-tertiary)",
            border: "1px solid var(--border-color)",
            borderRadius: "var(--radius-md)",
            padding: "0.55rem 0.85rem",
            marginTop: "0.5rem",
        }}>
            <div style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: "0.75rem",
                marginBottom: "0.35rem",
                flexWrap: "wrap",
            }}>
                <span style={{ fontWeight: 600, fontSize: "0.825rem", color: "var(--text-primary)" }}>
                    {paperTitle}{pageNum ? ` · ${pageNum}` : ""}
                </span>
                <button
                    onClick={handleOpenEvidence}
                    type="button"
                    style={{
                        background: "var(--accent-primary)",
                        color: "#ffffff",
                        border: "none",
                        borderRadius: "var(--radius-sm)",
                        padding: "0.25rem 0.65rem",
                        fontSize: "0.75rem",
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
                    fontSize: "0.825rem",
                    color: "var(--text-secondary)",
                    fontStyle: "italic",
                    lineHeight: "1.4",
                    borderLeft: "3px solid var(--accent-primary)",
                    paddingLeft: "0.65rem",
                    whiteSpace: "pre-wrap",
                    maxHeight: "85px",
                    overflowY: "auto",
                }}>
                    "{source.text}"
                </p>
            )}
        </div>
    );
}

export default EvidenceSource;
