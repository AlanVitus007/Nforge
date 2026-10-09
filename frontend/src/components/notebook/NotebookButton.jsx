import React from "react";
import "./NotebookButton.css";

const NotebookButton = ({ onClick, isOpen = false, notesCount = null }) => {
    return (
        <button
            type="button"
            id="nforge-notebook-btn"
            className={`nforge-notebook-dock-btn ${isOpen ? "active" : ""}`}
            onClick={onClick}
            title={isOpen ? "Close Notebook" : "Open Paper Notebook"}
            aria-label="Open Paper Notebook"
            aria-expanded={isOpen}
        >
            <div className="dock-btn-icon-wrapper">
                <svg
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                >
                    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
                    <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
                    <line x1="8" y1="7" x2="16" y2="7"></line>
                    <line x1="8" y1="11" x2="14" y2="11"></line>
                </svg>
            </div>
            <span className="dock-btn-label">Notes</span>
            {typeof notesCount === "number" && notesCount > 0 && (
                <span className="dock-btn-count">{notesCount}</span>
            )}
        </button>
    );
};

export default NotebookButton;
