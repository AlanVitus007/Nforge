import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "../services/api";

function PaperDetails() {
    const { projectId, paperId } = useParams();

    const [paper, setPaper] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    useEffect(() => {
        const fetchPaper = async () => {
            try {
                setLoading(true);
                setError("");

                const response = await api.get(
                    `/projects/${projectId}/papers/${paperId}/`
                );

                setPaper(response.data);;
            } catch (err) {
                console.error(err);
                setError("Failed to load paper.");
            } finally {
                setLoading(false);
            }
        };

        fetchPaper();
    }, [projectId, paperId]);

    if (loading) {
        return <p>Loading paper...</p>;
    }

    if (error) {
        return <p>{error}</p>;
    }

    return (
        <div>
            <Link to={`/projects/${projectId}`}>← Back to Project</Link>

            <h1>{paper.title}</h1>

            <p>Uploaded: {paper.uploaded_at}</p>

            {paper.file && (
                <div>
                    <h2>PDF</h2>

                    <iframe
                        src={paper.file.replace("http://localhost:8000", "")}
                        title={paper.title}
                        width="100%"
                        height="700px"
                        style={{ border: "1px solid #ccc" }}
                    />
                </div>
            )}

            <hr />

            <h2>Paper Workspace</h2>

            <p>AI features will be available here.</p>

            <section>
                <h3>Summary</h3>
                <p>Coming soon.</p>
            </section>

            <section>
                <h3>Ask Questions</h3>
                <p>Coming soon.</p>
            </section>

            <section>
                <h3>Research Gaps</h3>
                <p>Coming soon.</p>
            </section>
        </div>
    );
}

export default PaperDetails;