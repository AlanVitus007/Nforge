import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "../services/api";

function ProjectDetails() {
    const { id } = useParams();

    const [project, setProject] = useState(null);
    const [papers, setPapers] = useState([]);

    const [title, setTitle] = useState("");
    const [file, setFile] = useState(null);

    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState("");

    const fetchProject = async () => {
        try {
            const response = await api.get(`/projects/${id}/`);
            setProject(response.data);
        } catch (err) {
            console.error(err);
            setError("Failed to load project.");
        }
    };

    const fetchPapers = async () => {
        try {
            const response = await api.get(`/projects/${id}/papers/`);
            setPapers(response.data);
        } catch (err) {
            console.error(err);
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
            setError("Please enter a paper title.");
            return;
        }

        if (!file) {
            setError("Please select a PDF file.");
            return;
        }

        if (!file.name.toLowerCase().endsWith(".pdf")) {
            setError("Only PDF files are allowed.");
            return;
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
            console.error(err);

            if (err.response?.data) {
                setError(JSON.stringify(err.response.data));
            } else {
                setError("Failed to upload paper.");
            }
        } finally {
            setUploading(false);
        }
    };

    if (loading) {
        return <p>Loading project...</p>;
    }

    if (error && !project) {
        return <p>{error}</p>;
    }

    return (
        <div>
            <Link to="/projects">← Back to Projects</Link>

            <h1>{project.title}</h1>

            <p>{project.description || "No description."}</p>

            <hr />

            <h2>Upload Research Paper</h2>

            <form onSubmit={handleUpload}>
                <div>
                    <label>Paper Title</label>
                    <br />

                    <input
                        type="text"
                        value={title}
                        onChange={(e) => setTitle(e.target.value)}
                        placeholder="Paper title"
                    />
                </div>

                <br />

                <div>
                    <label>PDF File</label>
                    <br />

                    <input
                        id="paper-file"
                        type="file"
                        accept=".pdf,application/pdf"
                        onChange={(e) => setFile(e.target.files[0])}
                    />
                </div>

                <br />

                <button type="submit" disabled={uploading}>
                    {uploading ? "Uploading..." : "Upload Paper"}
                </button>
            </form>

            {error && <p>{error}</p>}

            <hr />

            <h2>Papers</h2>

            {papers.length === 0 ? (
                <p>No papers uploaded yet.</p>
            ) : (
                <div>
                    {papers.map((paper) => (
                        <div key={paper.id}>
                            <h3>
                                <Link to={`/projects/${id}/papers/${paper.id}`}>
                                    {paper.title}
                                </Link>
                            </h3>

                            <p>Uploaded: {paper.uploaded_at}</p>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

export default ProjectDetails;