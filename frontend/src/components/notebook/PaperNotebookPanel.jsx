import React, { useEffect, useState, useRef, useCallback, useMemo } from "react";
import {
    getPaperNotes,
    createPaperNote,
    updatePaperNote,
    deletePaperNote,
} from "../../services/notebookApi";
import "./PaperNotebookPanel.css";

/**
 * Format relative / compact date for research note cards
 */
function formatNoteDate(dateStr) {
    if (!dateStr) return "";
    try {
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return "";
        const now = new Date();
        const diffMs = now - d;
        const diffMins = Math.floor(diffMs / (1000 * 60));
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

        if (diffMins < 1) return "Just now";
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24 && now.getDate() === d.getDate()) {
            return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
        }
        if (diffDays === 1 || (diffHours < 48 && now.getDate() - d.getDate() === 1)) {
            return "Yesterday";
        }
        if (diffDays < 7) {
            return d.toLocaleDateString([], { weekday: "short" });
        }
        return d.toLocaleDateString([], { month: "short", day: "numeric" });
    } catch {
        return "";
    }
}

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
    const [searchQuery, setSearchQuery] = useState("");

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

    // Responsive mobile view: 'list' | 'editor'
    const [mobileView, setMobileView] = useState("list");

    // Confirmation dialog states
    const [showUnsavedModal, setShowUnsavedModal] = useState(false);
    const [pendingAction, setPendingAction] = useState(null);

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
        if (activeNote && activeNote.id === note.id) {
            setMobileView("editor");
            return;
        }
        performGuardedAction(() => {
            setActiveNote(note);
            setTitle(note.title || "Untitled note");
            setContent(note.content || "");
            setSavedTitle(note.title || "Untitled note");
            setSavedContent(note.content || "");
            setSaveStatus("saved");
            setSaveError("");
            setMobileView("editor");
        });
    };

    // New note action with guard
    const handleNewNoteClick = () => {
        performGuardedAction(() => {
            initNewDraft();
            setMobileView("editor");
            setTimeout(() => {
                if (titleInputRef.current) {
                    titleInputRef.current.focus();
                    titleInputRef.current.select();
                }
            }, 50);
        });
    };

    // Mobile back to notes list action with guard
    const handleMobileBackToList = () => {
        performGuardedAction(() => {
            setMobileView("list");
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
    };

    const handleUnsavedModalDiscard = () => {
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
            if (window.innerWidth <= 768) {
                setMobileView("list");
            }
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
    });

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

    // Client-side search filtering
    const filteredNotes = useMemo(() => {
        if (!searchQuery.trim()) return notes;
        const q = searchQuery.toLowerCase().trim();
        return notes.filter((note) => {
            const titleMatch = (note.title || "").toLowerCase().includes(q);
            const contentMatch = (note.content || "").toLowerCase().includes(q);
            return titleMatch || contentMatch;
        });
    }, [notes, searchQuery]);

    if (!isOpen) return null;

    const hasPapers = papers && papers.length > 0;
    const currentPaperObject =
        papers.find((p) => String(p.id) === String(selectedPaperId)) || currentPaper;

    return (
        <div className="nforge-notebook-overlay animate-fade-in" onClick={handleClose}>
            <aside
                className="nforge-notebook-panel animate-slide-left"
                onClick={(e) => e.stopPropagation()}
                role="dialog"
                aria-label="Research Notebook"
            >
                {/* 1. Compact Header */}
                <header className="notebook-panel-header">
                    <div className="notebook-header-left">
                        {/* Mobile back button when viewing editor */}
                        {mobileView === "editor" && (
                            <button
                                type="button"
                                className="notebook-mobile-back-btn"
                                onClick={handleMobileBackToList}
                                title="Back to Notes list"
                                aria-label="Back to Notes"
                            >
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                    <polyline points="15 18 9 12 15 6"></polyline>
                                </svg>
                                <span>Notes</span>
                            </button>
                        )}

                        <div className="notebook-header-icon" aria-hidden="true">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
                                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
                                <line x1="8" y1="7" x2="16" y2="7"></line>
                                <line x1="8" y1="11" x2="14" y2="11"></line>
                            </svg>
                        </div>

                        <div className="notebook-header-titles">
                            <h2 className="notebook-header-title">Research Notebook</h2>
                            {currentPaperObject?.title && (
                                <span className="notebook-header-paper-tag" title={currentPaperObject.title}>
                                    {currentPaperObject.title}
                                </span>
                            )}
                        </div>
                    </div>

                    <div className="notebook-header-right">
                        <button
                            type="button"
                            className="notebook-close-btn"
                            onClick={handleClose}
                            title="Close Notebook (Esc)"
                            aria-label="Close Notebook"
                        >
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <line x1="18" y1="6" x2="6" y2="18"></line>
                                <line x1="6" y1="6" x2="18" y2="18"></line>
                            </svg>
                        </button>
                    </div>
                </header>

                {/* Multi-paper Selector (Research Workspace sessions with multiple papers) */}
                {hasPapers && papers.length > 1 && (
                    <div className="notebook-paper-selector-bar">
                        <label htmlFor="notebook-paper-select" className="notebook-selector-label">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                                <polyline points="14 2 14 8 20 8"></polyline>
                            </svg>
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

                {/* Main Content Area */}
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
                    <div className={`notebook-two-column-body mobile-view-${mobileView}`}>
                        {/* 2. Left Column: Saved Notes List (220-250px) */}
                        <aside className="notebook-notes-sidebar">
                            {/* Search and New Note Toolbar */}
                            <div className="notebook-sidebar-toolbar">
                                <button
                                    type="button"
                                    className="notebook-new-note-btn"
                                    onClick={handleNewNoteClick}
                                    title="Create a new note"
                                >
                                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                        <line x1="12" y1="5" x2="12" y2="19"></line>
                                        <line x1="5" y1="12" x2="19" y2="12"></line>
                                    </svg>
                                    <span>New Note</span>
                                </button>

                                <div className="notebook-search-wrapper">
                                    <svg className="notebook-search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                        <circle cx="11" cy="11" r="8"></circle>
                                        <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                                    </svg>
                                    <input
                                        type="text"
                                        className="notebook-search-input"
                                        placeholder="Search notes..."
                                        value={searchQuery}
                                        onChange={(e) => setSearchQuery(e.target.value)}
                                        aria-label="Search notes"
                                    />
                                    {searchQuery && (
                                        <button
                                            type="button"
                                            className="notebook-search-clear"
                                            onClick={() => setSearchQuery("")}
                                            title="Clear search"
                                        >
                                            ✕
                                        </button>
                                    )}
                                </div>
                            </div>

                            {/* Notes List Content */}
                            <div className="notebook-notes-list-scroll">
                                {listError && (
                                    <div className="notebook-sidebar-alert error">
                                        {listError}
                                    </div>
                                )}

                                {loadingNotes ? (
                                    <div className="notebook-sidebar-loading">
                                        <span className="notebook-spinner" aria-hidden="true"></span>
                                        <span>Loading notes...</span>
                                    </div>
                                ) : notes.length === 0 ? (
                                    <div className="notebook-sidebar-empty">
                                        <p>No notes for this paper yet.</p>
                                        <button
                                            type="button"
                                            className="notebook-create-first-btn"
                                            onClick={handleNewNoteClick}
                                        >
                                            + Start your first note
                                        </button>
                                    </div>
                                ) : filteredNotes.length === 0 ? (
                                    <div className="notebook-sidebar-empty">
                                        <p>No notes match "{searchQuery}"</p>
                                        <button
                                            type="button"
                                            className="notebook-link-btn"
                                            onClick={() => setSearchQuery("")}
                                        >
                                            Clear filter
                                        </button>
                                    </div>
                                ) : (
                                    <div className="notebook-notes-items" role="list">
                                        {filteredNotes.map((note) => {
                                            const isActive = activeNote && activeNote.id === note.id;
                                            const formattedDate = formatNoteDate(note.updated_at || note.created_at);

                                            return (
                                                <div
                                                    key={note.id}
                                                    role="listitem"
                                                    className={`notebook-note-card ${isActive ? "active" : ""}`}
                                                    onClick={() => handleSelectNote(note)}
                                                    tabIndex={0}
                                                    onKeyDown={(e) => {
                                                        if (e.key === "Enter" || e.key === " ") {
                                                            e.preventDefault();
                                                            handleSelectNote(note);
                                                        }
                                                    }}
                                                >
                                                    <div className="note-card-header">
                                                        <h4 className="note-card-title">
                                                            {note.title || "Untitled note"}
                                                        </h4>
                                                        {formattedDate && (
                                                            <span className="note-card-date">
                                                                {formattedDate}
                                                            </span>
                                                        )}
                                                    </div>
                                                    <p className="note-card-snippet">
                                                        {note.content
                                                            ? note.content.slice(0, 80)
                                                            : "Empty note..."}
                                                    </p>
                                                </div>
                                            );
                                        })}
                                    </div>
                                )}
                            </div>
                        </aside>

                        {/* 3. Right Column: Note Editor */}
                        <main className="notebook-editor-main">
                            <div className="notebook-editor-scroll-area">
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

                                {/* Note Title & Character Counter */}
                                <div className="notebook-title-bar">
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
                                        aria-label="Note Title"
                                    />
                                    <span
                                        className={`notebook-char-counter ${title.length >= 190 ? "warning" : ""}`}
                                        title={`${title.length} of 200 characters`}
                                    >
                                        {title.length}/200
                                    </span>
                                </div>

                                {/* Multiline Writing Area */}
                                <div className="notebook-textarea-wrapper">
                                    <textarea
                                        ref={contentTextareaRef}
                                        className="notebook-content-textarea"
                                        placeholder="Type your research notes, findings, equations, hypotheses, or annotations here..."
                                        value={content}
                                        onChange={(e) => {
                                            setContent(e.target.value);
                                            if (saveError) setSaveError("");
                                        }}
                                        spellCheck="false"
                                        aria-label="Note Content"
                                    />
                                </div>
                            </div>

                            {/* 4. Persistent Bottom Action Bar */}
                            <footer className="notebook-bottom-bar">
                                <div className="notebook-status-indicator">
                                    {saveStatus === "saving" ? (
                                        <span className="status-badge saving">
                                            <span className="notebook-spinner-sm" aria-hidden="true"></span>
                                            Saving...
                                        </span>
                                    ) : saveStatus === "error" ? (
                                        <span className="status-badge error" title={saveError}>
                                            <span className="status-dot dot-error" aria-hidden="true"></span>
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

                                <div className="notebook-bottom-actions">
                                    <span className="notebook-shortcut-hint">
                                        <kbd>Ctrl+S</kbd> to save
                                    </span>

                                    {activeNote && activeNote.id && (
                                        <button
                                            type="button"
                                            className="notebook-delete-btn"
                                            onClick={(e) => confirmDeleteNote(activeNote, e)}
                                            title="Delete this note"
                                            aria-label="Delete note"
                                        >
                                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                                <polyline points="3 6 5 6 21 6"></polyline>
                                                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                                            </svg>
                                            <span>Delete Note</span>
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
                            </footer>
                        </main>
                    </div>
                )}
            </aside>

            {/* UNSAVED CHANGES CONFIRMATION DIALOG */}
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

            {/* DELETE NOTE CONFIRMATION DIALOG */}
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
