import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api from "../services/api";

function Projects() {
    const [projects, setProjects] = useState([]);
    const [title, setTitle] = useState("");
    const [description, setDescription] = useState("");
    const [loading, setLoading] = useState(true);
    const [creating, setCreating] = useState(false);
    const [error, setError] = useState("");

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

            await api.post("/projects/", {
                title,
                description,
            });

            setTitle("");
            setDescription("");

            await fetchProjects();
        } catch (err) {
            setError("Failed to create project.");
        } finally {
            setCreating(false);
        }
    };
    const handleDelete = async (projectId, projectTitle) => {
        const confirmed = window.confirm(
            `Are you sure you want to delete "${projectTitle}"?\n\nAll papers belonging to this project will also be deleted.`
        );

        if (!confirmed) {
            return;
        }

        try {
            setError("");

            await api.delete(`/projects/${projectId}/`);

            setProjects((currentProjects) =>
                currentProjects.filter((project) => project.id !== projectId)
            );
        } catch (err) {
            console.error(err);
            setError("Failed to delete project.");
        }
    };

    return (
        <div>
            <h1>My Projects</h1>

            <p>Create and manage your research projects.</p>

            {error && <p>{error}</p>}

            <section>
                <h2>Create Project</h2>

                <form onSubmit={handleCreate}>
                    <div>
                        <label>Title</label>
                        <br />
                        <input
                            type="text"
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            placeholder="Project title"
                        />
                    </div>

                    <br />

                    <div>
                        <label>Description</label>
                        <br />
                        <textarea
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            placeholder="Project description"
                            rows="4"
                        />
                    </div>

                    <br />

                    <button type="submit" disabled={creating}>
                        {creating ? "Creating..." : "Create Project"}
                    </button>
                </form>
            </section>

            <hr />

            <section>
                <h2>Your Projects</h2>

                {loading ? (
                    <p>Loading projects...</p>
                ) : projects.length === 0 ? (
                    <p>No projects yet. Create your first project above.</p>
                ) : (
                    <div>
                        {projects.map((project) => (
                            <div key={project.id}>
                                <h3>
                                    <Link to={`/projects/${project.id}`}>
                                        {project.title}
                                    </Link>
                                </h3>

                                <p>{project.description || "No description."}</p>
                                <button
                                    type="button"
                                    onClick={() => handleDelete(project.id, project.title)}
                                >
                                    Delete Project
                                </button>
                            </div>
                        ))}
                    </div>
                )}
            </section>
        </div>
    );
}

export default Projects;