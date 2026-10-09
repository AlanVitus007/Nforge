import React, { useState } from 'react';
import { getPaperNotes } from '../services/notebookApi';
import './NotebookUsageIndicator.css';

/**
 * NotebookUsageIndicator
 *
 * Reusable indicator rendered beneath an AI answer when personal notebook
 * notes contributed to the response context.
 *
 * Requirements:
 * - Render nothing when notes_used_count is zero, missing, invalid, or no notes were used.
 * - Display a small notebook icon and the label "Personal notes used".
 * - Display the count, for example "3 notes" (or "1 note").
 * - Match existing NForge dark/light themes and violet accent styling.
 * - Compact and visually secondary to the answer.
 * - Accessible with keyboard navigation and an appropriate accessible label.
 * - Expandable section showing note titles if safely resolvable for current user.
 * - Do not display note content, raw note IDs, or another user's private information.
 * - If titles cannot be resolved safely, show the count only.
 */
export default function NotebookUsageIndicator({
    notesUsed = [],
    notesUsedCount = 0,
    paperId = null,
    sessionPapers = null,
    noteTitles = null,
}) {
    // Hooks must be called unconditionally at top of component
    const [isExpanded, setIsExpanded] = useState(false);
    const [resolvedTitles, setResolvedTitles] = useState([]);
    const [loadingTitles, setLoadingTitles] = useState(false);
    const [hasAttemptedResolution, setHasAttemptedResolution] = useState(false);

    const count = Number(
        notesUsedCount !== undefined && notesUsedCount !== null
            ? notesUsedCount
            : (Array.isArray(notesUsed) ? notesUsed.length : 0)
    );

    // Early return: Render nothing when count is zero, missing, invalid, or no notes used
    if (!count || isNaN(count) || count <= 0) {
        return null;
    }

    // Determine current display titles: prop override or resolved titles
    const currentTitles = Array.isArray(noteTitles) && noteTitles.length > 0
        ? noteTitles
        : resolvedTitles;

    // Lazily resolve titles for current user's notes when expanded
    const handleToggleExpand = async () => {
        const nextState = !isExpanded;
        setIsExpanded(nextState);

        if (nextState && !hasAttemptedResolution && currentTitles.length === 0) {
            setLoadingTitles(true);
            try {
                const targetIds = new Set(
                    Array.isArray(notesUsed) ? notesUsed.map((id) => Number(id)) : []
                );

                if (targetIds.size === 0) {
                    setHasAttemptedResolution(true);
                    return;
                }

                const titlesFound = [];

                if (paperId) {
                    // Single-paper mode: fetch authenticated user's notes for this paper
                    const notes = await getPaperNotes(paperId);
                    if (Array.isArray(notes)) {
                        for (const note of notes) {
                            if (targetIds.has(Number(note.id)) && note.title) {
                                titlesFound.push(note.title);
                            }
                        }
                    }
                } else if (Array.isArray(sessionPapers) && sessionPapers.length > 0) {
                    // Research workspace mode: fetch user's notes for session papers
                    const paperRequests = sessionPapers.map((p) =>
                        getPaperNotes(p.id).catch(() => [])
                    );
                    const responses = await Promise.all(paperRequests);
                    for (const notes of responses) {
                        if (Array.isArray(notes)) {
                            for (const note of notes) {
                                if (targetIds.has(Number(note.id)) && note.title) {
                                    titlesFound.push(note.title);
                                }
                            }
                        }
                    }
                }

                if (titlesFound.length > 0) {
                    setResolvedTitles(titlesFound);
                }
            } catch (err) {
                // Non-fatal: if titles cannot be resolved safely, show count only
                console.warn('Could not resolve notebook note titles:', err);
            } finally {
                setLoadingTitles(false);
                setHasAttemptedResolution(true);
            }
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            handleToggleExpand();
        }
    };

    const noteCountLabel = count === 1 ? '1 note' : `${count} notes`;

    return (
        <div className="notebook-usage-container">
            <button
                type="button"
                className={`notebook-usage-badge ${isExpanded ? 'expanded' : ''}`}
                onClick={handleToggleExpand}
                onKeyDown={handleKeyDown}
                aria-expanded={isExpanded}
                aria-label={`Personal notes used: ${noteCountLabel}. Click to toggle note titles.`}
            >
                <span className="notebook-usage-badge-icon" aria-hidden="true">
                    <svg
                        width="13"
                        height="13"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2.2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                    >
                        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
                        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
                        <line x1="8" y1="7" x2="16" y2="7"></line>
                        <line x1="8" y1="11" x2="14" y2="11"></line>
                    </svg>
                </span>
                <span className="notebook-usage-label">Personal notes used</span>
                <span className="notebook-usage-separator" aria-hidden="true">·</span>
                <span className="notebook-usage-count">{noteCountLabel}</span>
                <span className={`notebook-usage-chevron ${isExpanded ? 'rotated' : ''}`} aria-hidden="true">
                    <svg
                        width="11"
                        height="11"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2.5"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                    >
                        <polyline points="6 9 12 15 18 9"></polyline>
                    </svg>
                </span>
            </button>

            {isExpanded && (
                <div className="notebook-usage-dropdown" role="region" aria-label="Titles of notes used">
                    {loadingTitles ? (
                        <div className="notebook-usage-loading">Loading note titles...</div>
                    ) : currentTitles.length > 0 ? (
                        <ul className="notebook-usage-titles-list">
                            {currentTitles.map((title, idx) => (
                                <li key={idx} className="notebook-usage-title-item">
                                    <span className="notebook-usage-title-dot" aria-hidden="true"></span>
                                    <span className="notebook-usage-title-text">{title}</span>
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <div className="notebook-usage-fallback">
                            {count === 1
                                ? '1 personal note from your notebook contributed research context to this answer.'
                                : `${count} personal notes from your notebook contributed research context to this answer.`}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
