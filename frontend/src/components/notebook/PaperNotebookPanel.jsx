import React, { useEffect, useState, useRef, useCallback } from "react";
import {
    getPaperNotes,
    createPaperNote,
    updatePaperNote,
    deletePaperNote,
} from "../../services/notebookApi";
import "./PaperNotebookPanel.css";

const PaperNotebookPanel = ({
    isOpen,
    onClose,
    papers = [],
    currentPaper = null,
    onNotesCountChange = null,
}) => {
    // Current selected paper ID
    const [selectedPaperId, setSelectedPaperId] = useState(null);

    // Notes list state
    const [notes, setNotes] = useState([]);
    const [loadingNotes, setLoadingNotes] = useState(false);
    const [listError, setListError] = useState("");

    // Active note editor state
    const [activeNote, setActiveNote] = useState(null); // null if draft/new, or existing note object
    const [title, setTitle] = useState("Untitled note");
    const [content, setContent] = useState("");
    const [savedTitle, setSavedTitle] = useState("Untitled note");
    const [savedContent, setSavedContent] = useState("");

    // Dirty state & save status
    const isDirty = title !== savedTitle || content !== savedContent;
    const [saveStatus, setSaveStatus] = useState("saved"); // 'saved' | 'saving' | 'unsaved' | 'error'
    const [saveError, setSaveError] = useState("");

    // Confirmation dialog states
    const [showUnsavedModal, setShowUnsavedModal] = useState(false);
    const [pendingAction, setPendingAction] = useState(null); // action callback or object to execute after confirm

    const [showDeleteModal, setShowDeleteModal] = useState(false);
    const [noteToDelete, setNoteToDelete] = useState(null);
    const [isDeleting, setIsDeleting] = useState(false);
    const [deleteError, setDeleteError] = useState("");

    const titleInputRef = useRef(null);
    const contentTextareaRef = useRef(null);

    // Synchronize default selected paper
    useEffect(() => {
        if (currentPaper && currentPaper.id) {
            setSelectedPaperId(currentPaper.id);
        } else if (papers && papers.length > 0) {
            // Keep current selection if still valid, else pick first paper
            setSelectedPaperId((prev) => {
                const exists = papers.some((p) => String(p.id) === String(prev));
                return exists ? prev : papers[0].id;
            });
        } else {
            setSelectedPaperId(null);
        }
    }, [currentPaper, papers]);

    // Initialize clean draft state
    const initNewDraft = useCallback(() => {
        setActiveNote(null);
        setTitle("Untitled note");
        setContent("");
        setSavedTitle("Untitled note");
        setSavedContent("");
        setSaveStatus("saved");
        setSaveError("");
    }, []);

    // Fetch notes when panel opens or paper changes
    const fetchNotesForPaper = useCallback(async (paperId) => {
        if (!paperId) {
            setNotes([]);
            return;
        }
        try {
            setLoadingNotes(true);
            setListError("");
            const data = await getPaperNotes(paperId);
            setNotes(data || []);

            if (onNotesCountChange) {
                onNotesCountChange(data ? data.length : 0);
            }

            // If notes exist, select first note; otherwise open a clean new draft
            if (data && data.length > 0) {
                const firstNote = data[0];
                setActiveNote(firstNote);
                setTitle(firstNote.title || "Untitled note");
                setContent(firstNote.content || "");
                setSavedTitle(firstNote.title || "Untitled note");
                setSavedContent(firstNote.content || "");
                setSaveStatus("saved");
            } else {
                initNewDraft();
            }
        } catch (err) {
            console.error("Failed to load paper notes:", err);
            setListError(
                err.response?.data?.detail ||
                err.response?.data?.error ||
                "Failed to load notes for this paper."
            );
            initNewDraft();
        } finally {
            setLoadingNotes(false);
        }
    }, [onNotesCountChange, initNewDraft]);

    useEffect(() => {
        if (isOpen && selectedPaperId) {
            fetchNotesForPaper(selectedPaperId);
        }
    }, [isOpen, selectedPaperId, fetchNotesForPaper]);

    // Save active note handler
    const handleSaveNote = async () => {
        if (!selectedPaperId || saveStatus === "saving") return false;

        const trimmedTitle = title.trim() || "Untitled note";
        if (trimmedTitle.length > 200) {
            setSaveError("Title cannot exceed 200 characters.");
            setSaveStatus("error");
            return false;
        }

        try {
            setSaveStatus("saving");
            setSaveError("");

            let savedNoteResult;

            if (activeNote && activeNote.id) {
                // Update existing note
                savedNoteResult = await updatePaperNote(activeNote.id, {
                    title: trimmedTitle,
                    content,
                });
                setNotes((prev) =>
                    prev.map((n) => (n.id === savedNoteResult.id ? savedNoteResult : n))
                );
            } else {
                // Create new note
                savedNoteResult = await createPaperNote(selectedPaperId, {
                    title: trimmedTitle,
                    content,
                });
                setNotes((prev) => [savedNoteResult, ...prev]);
                if (onNotesCountChange) {
                    onNotesCountChange(notes.length + 1);
                }
            }

            setActiveNote(savedNoteResult);
            setTitle(savedNoteResult.title);
            setContent(savedNoteResult.content || "");
            setSavedTitle(savedNoteResult.title);
            setSavedContent(savedNoteResult.content || "");
            setSaveStatus("saved");
            return true;
        } catch (err) {
            console.error("Failed to save note:", err);
            const msg =
                err.response?.data?.title?.[0] ||
                err.response?.data?.detail ||
                err.response?.data?.error ||
                "Failed to save note. Please check your connection.";
            setSaveError(msg);
            setSaveStatus("error");
            return false;
        }
    };

    // Helper to guard actions when unsaved changes exist
    const performGuardedAction = (action) => {
        if (isDirty) {
            setPendingAction(() => action);
            setShowUnsavedModal(true);
        } else {
            action();
        }
    };

    // Close panel with guard
    const handleClose = () => {
        performGuardedAction(() => {
            onClose();
        });
    };

    // Switch note with guard
    const handleSelectNote = (note) => {
        if (activeNote && activeNote.id === note.id) return;
        performGuardedAction(() => {
            setActiveNote(note);
            setTitle(note.title || "Untitled note");
            setContent(note.content || "");
            setSavedTitle(note.title || "Untitled note");
            setSavedContent(note.content || "");
            setSaveStatus("saved");
            setSaveError("");
        });
    };

    // New note action with guard
    const handleNewNoteClick = () => {
        performGuardedAction(() => {
            initNewDraft();
            if (titleInputRef.current) {
                titleInputRef.current.focus();
                titleInputRef.current.select();
            }
        });
    };

    // Switch paper selector with guard
    const handlePaperSelectChange = (newPaperId) => {
        if (String(newPaperId) === String(selectedPaperId)) return;
        performGuardedAction(() => {
            setSelectedPaperId(newPaperId);
        });
    };

    // Unsaved Changes Modal Actions
    const handleUnsavedModalSave = async () => {
        const success = await handleSaveNote();
        if (success) {
            setShowUnsavedModal(false);
            if (pendingAction) {
                pendingAction();
                setPendingAction(null);
            }
        }
        // If save failed, modal stays open with error shown and content preserved
    };

    const handleUnsavedModalDiscard = () => {
        // Discard local changes and reset to saved state
        setTitle(savedTitle);
        setContent(savedContent);
        setSaveStatus("saved");
        setSaveError("");
        setShowUnsavedModal(false);

        if (pendingAction) {
            pendingAction();
            setPendingAction(null);
        }
    };

    const handleUnsavedModalCancel = () => {
        setShowUnsavedModal(false);
        setPendingAction(null);
    };

    // Delete Note Handlers
    const confirmDeleteNote = (note, e) => {
        if (e) e.stopPropagation();
        setNoteToDelete(note);
        setDeleteError("");
        setShowDeleteModal(true);
    };

    const handleDeleteNoteSubmit = async () => {
        if (!noteToDelete || isDeleting) return;
        try {
            setIsDeleting(true);
            setDeleteError("");
            await deletePaperNote(noteToDelete.id);

            const remaining = notes.filter((n) => n.id !== noteToDelete.id);
            setNotes(remaining);
            if (onNotesCountChange) {
                onNotesCountChange(remaining.length);
            }

            // If deleted note was active, switch to first remaining or draft
            if (activeNote && activeNote.id === noteToDelete.id) {
                if (remaining.length > 0) {
                    const next = remaining[0];
                    setActiveNote(next);
                    setTitle(next.title || "Untitled note");
                    setContent(next.content || "");
                    setSavedTitle(next.title || "Untitled note");
                    setSavedContent(next.content || "");
                } else {
                    initNewDraft();
                }
            }

            setShowDeleteModal(false);
            setNoteToDelete(null);
        } catch (err) {
            console.error("Failed to delete note:", err);
            setDeleteError(
                err.response?.data?.detail || "Failed to delete note. Please try again."
            );
        } finally {
            setIsDeleting(false);
        }
    };

    const handleSaveNoteRef = useRef(handleSaveNote);
    const handleCloseRef = useRef(handleClose);
    useEffect(() => {
        handleSaveNoteRef.current = handleSaveNote;
        handleCloseRef.current = handleClose;
    }, [handleSaveNote, handleClose]);

    // Keyboard shortcut: Ctrl+S / Cmd+S to save, Escape to close
    useEffect(() => {
        if (!isOpen) return;

        const handleKeyDown = (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === "s") {
                e.preventDefault();
                handleSaveNoteRef.current?.();
            } else if (e.key === "Escape") {
                if (showUnsavedModal) {
                    handleUnsavedModalCancel();
                } else if (showDeleteModal) {
                    setShowDeleteModal(false);
                } else {
                    handleCloseRef.current?.();
                }
            }
        };

        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, [isOpen, showUnsavedModal, showDeleteModal]);

    if (!isOpen) return null;

    const hasPapers = papers && papers.length > 0;
    const currentPaperObject = papers.find((p) => String(p.id) === String(selectedPaperId)) || currentPaper;

    return (
        <div className="nforge-notebook-overlay animate-fade-in" onClick={handleClose}>
            <aside
                className="nforge-notebook-panel animate-slide-left"
                onClick={(e) => e.stopPropagation()}
                role="dialog"
                aria-label="Research Paper Notebook"
            >
                {/* Panel Header */}
                <header className="notebook-panel-header">
                    <div className="notebook-header-left">
                        <div className="notebook-header-icon" aria-hidden="true">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
                                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
                                <line x1="8" y1="7" x2="16" y2="7"></line>
                                <line x1="8" y1="11" x2="14" y2="11"></line>
                            </svg>
                        </div>
                        <div>
                            <h2 className="notebook-header-title">Paper Notebook</h2>
                            <p className="notebook-header-sub">Private notes & research observations</p>
                        </div>
                    </div>

                    <button
                        type="button"
                        className="notebook-close-btn"
                        onClick={handleClose}
                        title="Close Notebook (Esc)"
                        aria-label="Close Notebook"
                    >
                        &times;
                    </button>
                </header>

                {/* Paper Selector (Multi-paper sessions in Research Workspace) */}
                {hasPapers && papers.length > 1 && (
                    <div className="notebook-paper-selector-bar">
                        <label htmlFor="notebook-paper-select" className="notebook-selector-label">
                            Paper:
                        </label>
                        <select
                            id="notebook-paper-select"
                            className="notebook-paper-select"
                            value={selectedPaperId || ""}
                            onChange={(e) => handlePaperSelectChange(parseInt(e.target.value, 10))}
                        >
                            {papers.map((paper) => (
                                <option key={paper.id} value={paper.id}>
                                    {paper.title || `Paper #${paper.id}`}
                                </option>
                            ))}
                        </select>
                    </div>
                )}

                {/* Single Paper Title Badge */}
                {hasPapers && papers.length === 1 && currentPaperObject && (
                    <div className="notebook-single-paper-badge" title={currentPaperObject.title}>
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                            <polyline points="14 2 14 8 20 8"></polyline>
                        </svg>
                        <span className="single-paper-name">{currentPaperObject.title}</span>
                    </div>
                )}

                {/* Content Container */}
                {!hasPapers ? (
                    <div className="notebook-empty-view">
                        <div className="notebook-empty-icon" aria-hidden="true">
                            <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                                <circle cx="12" cy="12" r="10"></circle>
                                <line x1="12" y1="8" x2="12" y2="12"></line>
                                <line x1="12" y1="16" x2="12.01" y2="16"></line>
                            </svg>
                        </div>
                        <h3>No Papers Attached</h3>
                        <p>
                            Please attach a research paper to this session to view or take private notes.
                        </p>
                    </div>
                ) : (
                    <div className="notebook-body-container">
                        {/* Notes Sidebar / List */}
                        <div className="notebook-notes-list-section">
                            <div className="notebook-notes-list-header">
                                <span className="notes-count-label">
                                    {notes.length} {notes.length === 1 ? "Note" : "Notes"}
                                </span>
                                <button
                                    type="button"
                                    className="notebook-new-btn"
                                    onClick={handleNewNoteClick}
                                    title="Create a new note"
                                >
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                        <line x1="12" y1="5" x2="12" y2="19"></line>
                                        <line x1="5" y1="12" x2="19" y2="12"></line>
                                    </svg>
                                    New Note
                                </button>
                            </div>

                            {listError && (
                                <div className="notebook-alert notebook-alert-error">
                                    {listError}
                                </div>
                            )}

                            {loadingNotes ? (
                                <div className="notebook-loading-box">
                                    <span className="notebook-spinner" aria-hidden="true"></span>
                                    <span>Loading notes...</span>
                                </div>
                            ) : notes.length === 0 ? (
                                <div className="notebook-no-notes">
                                    <p>No notes for this paper yet.</p>
                                    <button
                                        type="button"
                                        className="notebook-btn-link"
                                        onClick={handleNewNoteClick}
                                    >
                                        + Start your first note
                                    </button>
                                </div>
                            ) : (
                                <ul className="notebook-notes-list" role="list">
                                    {notes.map((note) => {
                                        const isActive = activeNote && activeNote.id === note.id;
                                        return (
                                            <li
                                                key={note.id}
                                                className={`notebook-note-item ${isActive ? "active" : ""}`}
                                                onClick={() => handleSelectNote(note)}
                                            >
                                                <div className="note-item-content">
                                                    <h4 className="note-item-title">
                                                        {note.title || "Untitled note"}
                                                    </h4>
                                                    <p className="note-item-snippet">
                                                        {note.content ? note.content.slice(0, 60) : "No content"}
                                                    </p>
                                                </div>
                                                <button
                                                    type="button"
                                                    className="note-item-delete-btn"
                                                    onClick={(e) => confirmDeleteNote(note, e)}
                                                    title="Delete this note"
                                                    aria-label={`Delete note ${note.title}`}
                                                >
                                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                        <polyline points="3 6 5 6 21 6"></polyline>
                                                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                                                    </svg>
                                                </button>
                                            </li>
                                        );
                                    })}
                                </ul>
                            )}
                        </div>

                        {/* Note Editor Section */}
                        <div className="notebook-editor-section">
                            {/* Editor Status & Action Bar */}
                            <div className="notebook-editor-bar">
                                <div className="notebook-status-indicator">
                                    {saveStatus === "saving" ? (
                                        <span className="status-badge saving">
                                            <span className="notebook-spinner-sm" aria-hidden="true"></span>
                                            Saving...
                                        </span>
                                    ) : saveStatus === "error" ? (
                                        <span className="status-badge error" title={saveError}>
                                            Save Failed
                                        </span>
                                    ) : isDirty ? (
                                        <span className="status-badge unsaved">
                                            <span className="status-dot dot-unsaved" aria-hidden="true"></span>
                                            Unsaved changes
                                        </span>
                                    ) : (
                                        <span className="status-badge saved">
                                            <span className="status-dot dot-saved" aria-hidden="true"></span>
                                            Saved
                                        </span>
                                    )}
                                </div>

                                <div className="notebook-editor-actions">
                                    {activeNote && activeNote.id && (
                                        <button
                                            type="button"
                                            className="notebook-action-icon-btn danger"
                                            onClick={(e) => confirmDeleteNote(activeNote, e)}
                                            title="Delete note"
                                        >
                                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                <polyline points="3 6 5 6 21 6"></polyline>
                                                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                                            </svg>
                                        </button>
                                    )}

                                    <button
                                        type="button"
                                        className="notebook-save-btn"
                                        onClick={handleSaveNote}
                                        disabled={!isDirty || saveStatus === "saving"}
                                        title={isDirty ? "Save changes (Ctrl+S)" : "No unsaved changes"}
                                    >
                                        {saveStatus === "saving" ? "Saving..." : "Save Note"}
                                    </button>
                                </div>
                            </div>

                            {saveError && (
                                <div className="notebook-alert notebook-alert-error animate-fade-in">
                                    <span>{saveError}</span>
                                    <button
                                        type="button"
                                        className="notebook-alert-dismiss"
                                        onClick={() => setSaveError("")}
                                    >
                                        ✕
                                    </button>
                                </div>
                            )}

                            {/* Note Title Input */}
                            <div className="notebook-title-row">
                                <input
                                    ref={titleInputRef}
                                    type="text"
                                    className="notebook-title-input"
                                    placeholder="Note title..."
                                    value={title}
                                    onChange={(e) => {
                                        setTitle(e.target.value);
                                        if (saveError) setSaveError("");
                                    }}
                                    maxLength={200}
                                />
                                <span className="notebook-title-counter">
                                    {title.length}/200
                                </span>
                            </div>

                            {/* Note Content Textarea */}
                            <div className="notebook-textarea-wrapper">
                                <textarea
                                    ref={contentTextareaRef}
                                    className="notebook-content-textarea"
                                    placeholder="Write your research notes, findings, equations, or annotations here..."
                                    value={content}
                                    onChange={(e) => {
                                        setContent(e.target.value);
                                        if (saveError) setSaveError("");
                                    }}
                                />
                            </div>

                            <footer className="notebook-editor-footer">
                                <span className="notebook-keyboard-hint">
                                    Tip: Press <kbd>Ctrl+S</kbd> to save anytime
                                </span>
                            </footer>
                        </div>
                    </div>
                )}
            </aside>

            {/* UNSAVED CHANGES MODAL */}
            {showUnsavedModal && (
                <div
                    className="notebook-modal-backdrop animate-fade-in"
                    onClick={(e) => e.stopPropagation()}
                >
                    <div
                        className="notebook-modal-box"
                        role="dialog"
                        aria-modal="true"
                        aria-labelledby="unsaved-modal-title"
                    >
                        <div className="notebook-modal-header">
                            <div className="notebook-modal-icon warning" aria-hidden="true">
                                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                                    <line x1="12" y1="9" x2="12" y2="13"></line>
                                    <line x1="12" y1="17" x2="12.01" y2="17"></line>
                                </svg>
                            </div>
                            <h3 id="unsaved-modal-title">Unsaved Changes</h3>
                        </div>

                        <p className="notebook-modal-body">
                            You have unsaved changes in{" "}
                            <strong>"{title || "Untitled note"}"</strong>. What would you like to do?
                        </p>

                        {saveError && (
                            <div className="notebook-alert notebook-alert-error">
                                {saveError}
                            </div>
                        )}

                        <div className="notebook-modal-actions">
                            <button
                                type="button"
                                className="notebook-modal-btn cancel"
                                onClick={handleUnsavedModalCancel}
                            >
                                Cancel
                            </button>

                            <button
                                type="button"
                                className="notebook-modal-btn discard"
                                onClick={handleUnsavedModalDiscard}
                            >
                                Discard
                            </button>

                            <button
                                type="button"
                                className="notebook-modal-btn save"
                                onClick={handleUnsavedModalSave}
                                disabled={saveStatus === "saving"}
                            >
                                {saveStatus === "saving" ? "Saving..." : "Save Changes"}
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* DELETE NOTE CONFIRMATION MODAL */}
            {showDeleteModal && (
                <div
                    className="notebook-modal-backdrop animate-fade-in"
                    onClick={(e) => e.stopPropagation()}
                >
                    <div
                        className="notebook-modal-box"
                        role="dialog"
                        aria-modal="true"
                        aria-labelledby="delete-modal-title"
                    >
                        <div className="notebook-modal-header">
                            <div className="notebook-modal-icon danger" aria-hidden="true">
                                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <polyline points="3 6 5 6 21 6"></polyline>
                                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                                    <line x1="10" y1="11" x2="10" y2="17"></line>
                                    <line x1="14" y1="11" x2="14" y2="17"></line>
                                </svg>
                            </div>
                            <h3 id="delete-modal-title">Delete Note?</h3>
                        </div>

                        <p className="notebook-modal-body">
                            Are you sure you want to permanently delete{" "}
                            <strong>"{noteToDelete?.title || "Untitled note"}"</strong>?
                            This action cannot be undone.
                        </p>

                        {deleteError && (
                            <div className="notebook-alert notebook-alert-error">
                                {deleteError}
                            </div>
                        )}

                        <div className="notebook-modal-actions">
                            <button
                                type="button"
                                className="notebook-modal-btn cancel"
                                onClick={() => setShowDeleteModal(false)}
                                disabled={isDeleting}
                            >
                                Cancel
                            </button>

                            <button
                                type="button"
                                className="notebook-modal-btn danger"
                                onClick={handleDeleteNoteSubmit}
                                disabled={isDeleting}
                            >
                                {isDeleting ? "Deleting..." : "Delete Note"}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default PaperNotebookPanel;
